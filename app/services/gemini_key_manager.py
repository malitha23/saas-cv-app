import os
import re
import time
import json
import logging
import threading
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import requests
from dotenv import load_dotenv

logger = logging.getLogger("dreemfolio.gemini_keys")

# Cooldown duration for 429 quota exhaustion (in seconds)
QUOTA_COOLDOWN_SECONDS = 60

# Model endpoint used for lightweight, 0-token health verification
VERIFICATION_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiKeyEntry:
    """Represents a single Gemini API key with runtime telemetry and state."""

    def __init__(self, key: str, source: str = "env"):
        self.key: str = key.strip()
        self.source: str = source  # "env", "paneladmin", "saas_setting", "gcp_auto"
        self.status: str = "active"  # "active", "cooldown", "expired"
        self.cooldown_until: float = 0.0
        self.last_used: Optional[str] = None
        self.last_verified: Optional[str] = None
        self.success_count: int = 0
        self.failure_count: int = 0
        self.last_error: Optional[str] = None

    @property
    def is_usable(self) -> bool:
        """Determines if the key is available to handle inference requests."""
        if self.status == "expired":
            return False
        if self.status == "cooldown":
            if time.time() >= self.cooldown_until:
                self.status = "active"
                self.cooldown_until = 0.0
                return True
            return False
        return True

    @property
    def masked_key(self) -> str:
        """Returns security-masked preview of the API key."""
        k = self.key
        if len(k) <= 12:
            return "***"
        return f"{k[:8]}...{k[-4:]}"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes telemetry for the admin dashboard and API responses."""
        return {
            "key_preview": self.masked_key,
            "status": self.status,
            "source": self.source,
            "is_usable": self.is_usable,
            "cooldown_remaining_sec": max(0, int(self.cooldown_until - time.time())) if self.status == "cooldown" else 0,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_used": self.last_used,
            "last_verified": self.last_verified,
            "last_error": self.last_error,
        }


class GeminiKeyManager:
    """
    Enterprise Lifecycle & Resilience Manager for Google Gemini API Keys.
    
    Capabilities:
    1. Multi-key pool rotation (failover & load-distribution).
    2. Dynamic key hot-reloading with instant database persistence (SaasSetting & .env).
    3. Multi-worker synchronization across process reloads & server restarts.
    4. Automatic 429 quota exhaustion cooldown (auto-reactivates after cooldown).
    5. Automatic 400/401/403 deactivation of dead/deleted keys with instant failover.
    6. Programmatic autonomous key minting via Google Cloud API Keys API.
    7. Zero-token fast health validation.
    8. Automated admin alerting upon key failure.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._keys: Dict[str, GeminiKeyEntry] = {}
        self._last_loaded: float = 0.0
        self._env_path: str = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        )
        self.load_keys()

    # ──────────────────────────────────────────────────────────────────────────
    # KEY LOADING & POOL INITIALIZATION
    # ──────────────────────────────────────────────────────────────────────────
    def load_keys(self, db: Optional[Any] = None) -> None:
        """Loads API keys from database (SaasSetting), .env, and environment variables."""
        with self._lock:
            load_dotenv(self._env_path, override=True)

            discovered_keys: List[tuple[str, str]] = []

            # 1. Comma/newline separated pool: GEMINI_API_KEYS
            pool_env = os.getenv("GEMINI_API_KEYS", "").strip()
            if pool_env:
                for k in re.split(r"[,;\n\r]+", pool_env):
                    k_clean = k.strip()
                    if k_clean and len(k_clean) >= 20:
                        discovered_keys.append((k_clean, "env_pool"))

            # 2. Primary legacy key: GEMINI_API_KEY
            primary_key = os.getenv("GEMINI_API_KEY", "").strip()
            if primary_key and len(primary_key) >= 20:
                discovered_keys.append((primary_key, "env_primary"))

            # 3. Numbered keys: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...
            for idx in range(1, 11):
                num_key = os.getenv(f"GEMINI_API_KEY_{idx}", "").strip()
                if num_key and len(num_key) >= 20:
                    discovered_keys.append((num_key, f"env_key_{idx}"))

            # Register discovered keys without resetting existing runtime telemetry
            for k_str, src in discovered_keys:
                if k_str not in self._keys:
                    self._keys[k_str] = GeminiKeyEntry(key=k_str, source=src)

            # 4. Load from SaasSetting in Database (Primary persistence across reloads)
            self._load_from_saas_settings(db=db)

            self._last_loaded = time.time()
            usable_count = sum(1 for e in self._keys.values() if e.is_usable)
            logger.info(
                f"[Gemini Key Manager] Initialized {len(self._keys)} total key(s) ({usable_count} usable)."
            )

    def _load_from_saas_settings(self, db: Optional[Any] = None) -> None:
        """Loads supplementary keys persisted in the database saas_settings table."""
        close_session = False
        active_db = db

        if active_db is None:
            try:
                from app.database import SessionLocal
                active_db = SessionLocal()
                close_session = True
            except Exception as dbe:
                logger.debug(f"[Gemini Key Manager] SaasSetting DB connection skipped: {dbe}")
                return

        try:
            from sqlalchemy import select
            from app.models import SaasSetting

            stmt = select(SaasSetting).where(SaasSetting.key == "gemini_api_key_pool")
            row = active_db.scalars(stmt).first()
            if row and row.value:
                try:
                    stored_list = json.loads(row.value)
                    if isinstance(stored_list, list):
                        for item in stored_list:
                            if isinstance(item, dict):
                                k = str(item.get("key", "")).strip()
                                st = item.get("status", "active")
                                src = item.get("source", "paneladmin")
                            else:
                                k = str(item).strip()
                                st = "active"
                                src = "paneladmin"

                            if k and len(k) >= 20:
                                if k not in self._keys:
                                    self._keys[k] = GeminiKeyEntry(key=k, source=src)
                                    self._keys[k].status = st
                                    if isinstance(item, dict):
                                        self._keys[k].success_count = item.get("success_count", 0)
                                        self._keys[k].failure_count = item.get("failure_count", 0)
                                        self._keys[k].last_used = item.get("last_used")
                                        self._keys[k].last_verified = item.get("last_verified")
                                        self._keys[k].last_error = item.get("last_error")
                except Exception as je:
                    logger.debug(f"[Gemini Key Manager] JSON parse error in saas_settings: {je}")
        except Exception as e:
            logger.debug(f"[Gemini Key Manager] SaasSetting load skipped: {e}")
        finally:
            if close_session and active_db:
                try:
                    active_db.close()
                except Exception:
                    pass

    # ──────────────────────────────────────────────────────────────────────────
    # KEY SELECTION & FAILOVER ROTATION
    # ──────────────────────────────────────────────────────────────────────────
    def get_active_keys(self, provided_key: Optional[str] = None) -> List[str]:
        """
        Returns an ordered list of usable API keys to attempt for a request.
        Priority:
        1. Explicitly provided user key (if valid)
        2. Active keys in the pool (lowest failure count first)
        3. Cooldown keys whose cooldown period has elapsed
        4. Cooldown keys as a last resort before giving up
        """
        with self._lock:
            now = time.time()
            candidates: List[str] = []

            # 1. Provided user key
            if provided_key and len(provided_key.strip()) >= 20:
                clean_prov = provided_key.strip()
                candidates.append(clean_prov)

            # 2. Check and un-cooldown keys if time has elapsed
            for entry in self._keys.values():
                if entry.status == "cooldown" and now >= entry.cooldown_until:
                    entry.status = "active"
                    entry.cooldown_until = 0.0

            # 3. Active healthy keys sorted by failure count ascending
            active_entries = [e for e in self._keys.values() if e.status == "active"]
            active_entries.sort(key=lambda x: (x.failure_count, -x.success_count))
            for e in active_entries:
                if e.key not in candidates:
                    candidates.append(e.key)

            # 4. If no active keys, include cooldown keys as emergency fallback
            if not candidates:
                cooldown_entries = [e for e in self._keys.values() if e.status == "cooldown"]
                cooldown_entries.sort(key=lambda x: x.cooldown_until)
                for e in cooldown_entries:
                    if e.key not in candidates:
                        candidates.append(e.key)

            # 5. If STILL nothing, return whatever keys exist rather than empty
            if not candidates:
                for k in self._keys.keys():
                    if k not in candidates:
                        candidates.append(k)

            return candidates

    def get_active_key(self, provided_key: Optional[str] = None) -> Optional[str]:
        """Returns the primary active key for single-key operations."""
        keys = self.get_active_keys(provided_key=provided_key)
        return keys[0] if keys else None

    # ──────────────────────────────────────────────────────────────────────────
    # RUNTIME RESULT RECORDING & CIRCUIT BREAKER
    # ──────────────────────────────────────────────────────────────────────────
    def record_success(self, key: str) -> None:
        """Records successful inference execution with the given key."""
        with self._lock:
            clean_k = key.strip()
            if clean_k in self._keys:
                entry = self._keys[clean_k]
                entry.status = "active"
                entry.cooldown_until = 0.0
                entry.success_count += 1
                entry.last_used = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                entry.last_error = None

    def record_error(self, key: str, error: Union[Exception, str]) -> Dict[str, Any]:
        """
        Analyzes an API error, applies circuit breaker rules, and triggers failover.
        """
        err_str = str(error).strip()
        with self._lock:
            clean_k = key.strip()
            if clean_k not in self._keys:
                self._keys[clean_k] = GeminiKeyEntry(key=clean_k, source="runtime")
            entry = self._keys[clean_k]

            entry.failure_count += 1
            entry.last_error = err_str[:300]
            entry.last_used = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Check for permanent authentication / key expiration errors
            is_expired = any(
                code in err_str
                for code in (
                    "400",
                    "API_KEY_INVALID",
                    "API key not valid",
                    "401",
                    "UNAUTHENTICATED",
                    "deleted or disabled",
                    "ACCOUNT_STATE_INVALID",
                    "403",
                    "PERMISSION_DENIED",
                    "CONSUMER_SUSPENDED",
                )
            )

            # Check for rate limit / quota exhaustion
            is_quota = any(
                code in err_str
                for code in (
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "Quota exceeded",
                    "Rate limit",
                    "Too Many Requests",
                )
            )

            previous_status = entry.status
            if is_expired:
                entry.status = "expired"
                entry.cooldown_until = 0.0
                logger.error(
                    f"🚨 [Gemini Key Manager] Key {entry.masked_key} is permanently EXPIRED/DELETED! Error: {err_str[:120]}"
                )
                self._notify_key_expired_alert(entry, err_str)

            elif is_quota:
                entry.status = "cooldown"
                entry.cooldown_until = time.time() + QUOTA_COOLDOWN_SECONDS
                logger.warning(
                    f"⚠️ [Gemini Key Manager] Key {entry.masked_key} hit 429 quota. Placed in cooldown for {QUOTA_COOLDOWN_SECONDS}s."
                )

            # Persist status update to DB
            self._persist_keys_to_db()

            usable_remaining = sum(1 for e in self._keys.values() if e.is_usable)

            # If all keys are down, attempt autonomous GCP key generation if available
            if usable_remaining == 0:
                logger.critical(
                    "🚨 [Gemini Key Manager] ALL GEMINI KEYS ARE EXHAUSTED OR EXPIRED! Attempting autonomous recovery..."
                )
                auto_res = self.auto_generate_key_via_gcp()
                if auto_res.get("success"):
                    logger.info("✅ [Gemini Key Manager] Successfully recovered via autonomous GCP key generation!")
                    usable_remaining = 1

            return {
                "key_preview": entry.masked_key,
                "status": entry.status,
                "previous_status": previous_status,
                "usable_remaining": usable_remaining,
                "error": err_str[:150],
            }

    def _notify_key_expired_alert(self, entry: GeminiKeyEntry, error_details: str) -> None:
        """Sends admin email alert when a key expires, detailing failover status."""
        try:
            usable_count = sum(1 for e in self._keys.values() if e.is_usable and e.key != entry.key)
            from app.email_service import notify_admin_of_ai_failure
            context_msg = (
                f"Gemini API Key '{entry.masked_key}' EXPIRED/DELETED. "
                f"Auto-Failover Status: {usable_count} healthy backup key(s) currently active."
            )
            notify_admin_of_ai_failure(
                error_message=f"{error_details}\n\nKey: {entry.masked_key} (Status: EXPIRED)",
                context=context_msg,
            )
        except Exception as alert_err:
            logger.debug(f"[Gemini Key Manager] Alert dispatch error: {alert_err}")

    # ──────────────────────────────────────────────────────────────────────────
    # ZERO-TOKEN HEALTH TESTING
    # ──────────────────────────────────────────────────────────────────────────
    def test_key(self, key_str: str) -> Dict[str, Any]:
        """
        Performs an instant, 0-token health check on an API key via the Google Models API.
        Does NOT consume user token balance or daily model limits.
        """
        clean_k = key_str.strip()
        if not clean_k or len(clean_k) < 20:
            return {
                "valid": False,
                "status": "expired",
                "message": "Key is too short or malformed.",
                "status_code": 400,
            }

        try:
            url = f"{VERIFICATION_MODELS_URL}?key={clean_k}"
            res = requests.get(url, timeout=10)
            now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            if res.status_code == 200:
                data = res.json()
                model_count = len(data.get("models", []))
                return {
                    "valid": True,
                    "status": "active",
                    "message": f"Key is active and responsive ({model_count} models available).",
                    "status_code": 200,
                    "verified_at": now_str,
                }
            elif res.status_code in (400, 401, 403):
                err_msg = res.json().get("error", {}).get("message", res.text[:150])
                return {
                    "valid": False,
                    "status": "expired",
                    "message": f"Google AI rejected key: {err_msg}",
                    "status_code": res.status_code,
                    "verified_at": now_str,
                }
            elif res.status_code == 429:
                return {
                    "valid": False,
                    "status": "cooldown",
                    "message": "Key is valid but currently rate-limited (429 RESOURCE_EXHAUSTED).",
                    "status_code": 429,
                    "verified_at": now_str,
                }
            else:
                return {
                    "valid": False,
                    "status": "unknown",
                    "message": f"Unexpected HTTP status {res.status_code}: {res.text[:150]}",
                    "status_code": res.status_code,
                    "verified_at": now_str,
                }
        except Exception as e:
            return {
                "valid": False,
                "status": "network_error",
                "message": f"Network / connection error: {str(e)}",
                "status_code": 0,
            }

    def test_all_keys(self) -> Dict[str, Any]:
        """Runs live 0-token health checks on all registered keys in the pool."""
        results = []
        with self._lock:
            for entry in list(self._keys.values()):
                test_res = self.test_key(entry.key)
                entry.last_verified = test_res.get("verified_at")
                if test_res.get("status") in ("active", "expired", "cooldown"):
                    entry.status = test_res["status"]
                    if entry.status == "cooldown":
                        entry.cooldown_until = time.time() + QUOTA_COOLDOWN_SECONDS
                    elif entry.status == "active":
                        entry.cooldown_until = 0.0

                results.append({
                    "key_preview": entry.masked_key,
                    "status": entry.status,
                    "valid": test_res.get("valid", False),
                    "message": test_res.get("message", ""),
                    "status_code": test_res.get("status_code", 0),
                })

            # Persist tested status to DB
            self._persist_keys_to_db()

        return {
            "tested_count": len(results),
            "summary": self.get_pool_status(),
            "details": results,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # DYNAMIC KEY MANAGEMENT (ADD, REMOVE, UPDATE)
    # ──────────────────────────────────────────────────────────────────────────
    def add_key(
        self,
        new_key: str,
        test_first: bool = True,
        persist_env: bool = True,
        persist_db: bool = True,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically registers a new Gemini API key into the running system.
        Persists to SaasSetting and .env immediately. No server restart required.
        """
        clean_k = new_key.strip()
        if not clean_k or len(clean_k) < 20:
            return {"success": False, "message": "Key must be a valid Google AI key string (>= 20 characters)."}

        verification = None
        initial_status = "active"
        if test_first:
            verification = self.test_key(clean_k)
            if not verification.get("valid") and verification.get("status") == "expired":
                return {
                    "success": False,
                    "message": f"Key verification failed: {verification.get('message')}",
                    "details": verification,
                }
            initial_status = verification.get("status", "active")

        with self._lock:
            entry = self._keys.get(clean_k)
            if not entry:
                entry = GeminiKeyEntry(key=clean_k, source="paneladmin")
                self._keys[clean_k] = entry
            entry.status = initial_status
            entry.cooldown_until = (
                time.time() + QUOTA_COOLDOWN_SECONDS if initial_status == "cooldown" else 0.0
            )
            entry.last_verified = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Always ensure os.environ has at least one working key
            if os.getenv("GEMINI_API_KEY") != clean_k and initial_status == "active":
                os.environ["GEMINI_API_KEY"] = clean_k

            if persist_db:
                self._persist_keys_to_db(db=db)

            if persist_env:
                self._persist_keys_to_env()

        return {
            "success": True,
            "message": f"Key {entry.masked_key} successfully added, validated, and permanently saved!",
            "key_preview": entry.masked_key,
            "status": entry.status,
            "verification": verification,
            "pool_status": self.get_pool_status(db=db),
        }

    def remove_key(self, key_str: str, persist: bool = True, db: Optional[Any] = None) -> Dict[str, Any]:
        """Removes a key from the rotation pool and updates DB + .env."""
        clean_k = key_str.strip()
        with self._lock:
            # Match by full key or prefix
            target = None
            for k in self._keys.keys():
                if k == clean_k or k.startswith(clean_k) or clean_k in k:
                    target = k
                    break

            if not target:
                return {"success": False, "message": "Key not found in pool."}

            del self._keys[target]

            if persist:
                self._persist_keys_to_db(db=db)
                self._persist_keys_to_env()

        return {
            "success": True,
            "message": "Key successfully removed from pool and database.",
            "pool_status": self.get_pool_status(db=db),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # AUTONOMOUS KEY GENERATION VIA GOOGLE CLOUD API
    # ──────────────────────────────────────────────────────────────────────────
    def auto_generate_key_via_gcp(
        self,
        project_id: Optional[str] = None,
        service_account_json: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Programmatically generates a new Google Cloud API Key using GCP Service Account.
        Uses Google Cloud API Keys API (apikeys.googleapis.com).
        """
        proj_id = project_id or os.getenv("GCP_PROJECT_ID", "").strip()
        sa_creds_raw = service_account_json or os.getenv("GCP_SERVICE_ACCOUNT_JSON", "").strip()
        sa_file_path = os.getenv("GCP_SERVICE_ACCOUNT_FILE", "").strip()

        # Check if file path exists
        if not sa_creds_raw and sa_file_path and os.path.isfile(sa_file_path):
            try:
                with open(sa_file_path, "r", encoding="utf-8") as f:
                    sa_creds_raw = f.read()
            except Exception as fe:
                logger.error(f"[GCP Key Auto-Gen] Failed to read credentials file: {fe}")

        if not sa_creds_raw or not proj_id:
            return {
                "success": False,
                "reason": "gcp_not_configured",
                "message": (
                    "Automated GCP key generation requires GCP_PROJECT_ID and GCP_SERVICE_ACCOUNT_JSON "
                    "with 'API Keys Admin' (roles/serviceusage.apiKeysAdmin) permissions. "
                    "Alternatively, add multiple backup keys to GEMINI_API_KEYS in .env or via Admin Dashboard."
                ),
            }

        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests

            # Parse credentials
            try:
                sa_info = json.loads(sa_creds_raw)
            except Exception:
                return {"success": False, "message": "GCP_SERVICE_ACCOUNT_JSON is not valid JSON."}

            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            credentials = service_account.Credentials.from_service_account_info(
                sa_info, scopes=scopes
            )
            req = google.auth.transport.requests.Request()
            credentials.refresh(req)
            access_token = credentials.token

            # Call Google Cloud API Keys API v2
            timestamp_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            create_url = f"https://apikeys.googleapis.com/v2/projects/{proj_id}/locations/global/keys"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "displayName": f"gemini-auto-key-{timestamp_tag}",
                "restrictions": {
                    "apiTargets": [
                        {"service": "generativelanguage.googleapis.com"}
                    ]
                }
            }

            resp = requests.post(create_url, headers=headers, json=payload, timeout=30)
            if resp.status_code not in (200, 201):
                return {
                    "success": False,
                    "message": f"Google Cloud API Keys API returned {resp.status_code}: {resp.text[:200]}",
                }

            operation_data = resp.json()
            key_string = None

            if "response" in operation_data and "keyString" in operation_data["response"]:
                key_string = operation_data["response"]["keyString"]
            elif "keyString" in operation_data:
                key_string = operation_data["keyString"]
            elif "name" in operation_data and "operations/" in operation_data["name"]:
                op_name = operation_data["name"]
                op_url = f"https://apikeys.googleapis.com/v2/{op_name}"
                for _ in range(5):
                    time.sleep(2)
                    op_resp = requests.get(op_url, headers=headers, timeout=10)
                    if op_resp.status_code == 200:
                        op_res_data = op_resp.json()
                        if op_res_data.get("done"):
                            key_string = op_res_data.get("response", {}).get("keyString")
                            break

            if not key_string:
                return {
                    "success": False,
                    "message": f"Key creation initiated, but keyString could not be parsed: {resp.text[:250]}",
                }

            # Add newly minted key to the active rotation pool
            add_res = self.add_key(
                key_string, test_first=True, persist_env=True, persist_db=True, db=db
            )
            logger.info(
                f"🎉 [GCP Key Auto-Gen] Programmatically minted new Gemini key {key_string[:8]}... via Google Cloud API!"
            )

            return {
                "success": True,
                "message": f"Successfully minted fresh Gemini key via Google Cloud API!",
                "key": key_string,
                "key_preview": f"{key_string[:8]}...{key_string[-4:]}",
                "pool_status": self.get_pool_status(db=db),
            }

        except Exception as exc:
            logger.error(f"[GCP Key Auto-Gen] Exception during autonomous key generation: {exc}")
            return {
                "success": False,
                "message": f"Autonomous key generation failed: {str(exc)}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE HELPERS (.ENV & DATABASE)
    # ──────────────────────────────────────────────────────────────────────────
    def _persist_keys_to_env(self) -> None:
        """Safely updates GEMINI_API_KEY and GEMINI_API_KEYS in .env without modifying other variables."""
        try:
            if not os.path.exists(self._env_path):
                return

            all_keys = [k for k in self._keys.keys() if len(k) >= 20]
            if not all_keys:
                return

            # Best primary key is first active one
            active_keys = [k for k in all_keys if self._keys[k].status == "active"]
            primary_key = active_keys[0] if active_keys else all_keys[0]
            joined_keys = ",".join(all_keys)

            with open(self._env_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace or append GEMINI_API_KEY (matching uncommented lines)
            if re.search(r"^[ \t]*GEMINI_API_KEY\s*=.*$", content, flags=re.MULTILINE):
                content = re.sub(
                    r"^[ \t]*GEMINI_API_KEY\s*=.*$",
                    f"GEMINI_API_KEY={primary_key}",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content += f"\nGEMINI_API_KEY={primary_key}\n"

            # Replace or append GEMINI_API_KEYS (matching uncommented lines)
            if re.search(r"^[ \t]*GEMINI_API_KEYS\s*=.*$", content, flags=re.MULTILINE):
                content = re.sub(
                    r"^[ \t]*GEMINI_API_KEYS\s*=.*$",
                    f"GEMINI_API_KEYS={joined_keys}",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content += f"\nGEMINI_API_KEYS={joined_keys}\n"

            with open(self._env_path, "w", encoding="utf-8") as f:
                f.write(content)

            os.environ["GEMINI_API_KEY"] = primary_key
            os.environ["GEMINI_API_KEYS"] = joined_keys
            logger.info("[Gemini Key Manager] Successfully synchronized key pool to .env.")
        except Exception as e:
            logger.error(f"[Gemini Key Manager] Failed to write keys to .env: {e}")

    def _persist_keys_to_db(self, db: Optional[Any] = None) -> None:
        """Persists the key pool to saas_settings table for database-backed environments."""
        close_session = False
        active_db = db

        if active_db is None:
            try:
                from app.database import SessionLocal
                active_db = SessionLocal()
                close_session = True
            except Exception as dbe:
                logger.error(f"[Gemini Key Manager] Could not connect to DB to save keys: {dbe}")
                return

        try:
            from sqlalchemy import select
            from app.models import SaasSetting

            all_keys = [k for k in self._keys.keys() if len(k) >= 20]
            save_payload = []
            for k in all_keys:
                entry = self._keys[k]
                save_payload.append({
                    "key": entry.key,
                    "status": entry.status,
                    "source": entry.source or "paneladmin",
                    "success_count": entry.success_count,
                    "failure_count": entry.failure_count,
                    "last_used": entry.last_used,
                    "last_verified": entry.last_verified,
                    "last_error": entry.last_error,
                })
            json_val = json.dumps(save_payload)

            stmt = select(SaasSetting).where(SaasSetting.key == "gemini_api_key_pool")
            row = active_db.scalars(stmt).first()
            if row:
                row.value = json_val
                row.updated_at = datetime.utcnow()
            else:
                row = SaasSetting(
                    key="gemini_api_key_pool",
                    value=json_val,
                    description="Active Gemini API Key pool list for failover and load distribution",
                )
                active_db.add(row)

            active_db.commit()
            logger.info(f"✅ [Gemini Key Manager] Successfully saved {len(all_keys)} keys to SaasSetting database!")
        except Exception as e:
            logger.error(f"❌ [Gemini Key Manager] SaasSetting persist failed: {e}")
            try:
                active_db.rollback()
            except Exception:
                pass
        finally:
            if close_session and active_db:
                try:
                    active_db.close()
                except Exception:
                    pass

    # ──────────────────────────────────────────────────────────────────────────
    # STATUS & TELEMETRY REPORTING
    # ──────────────────────────────────────────────────────────────────────────
    def get_pool_status(self, db: Optional[Any] = None) -> Dict[str, Any]:
        """Provides complete health metrics for the admin interface, re-syncing with DB."""
        with self._lock:
            # Re-sync with database first so worker processes never fall out of sync
            self._load_from_saas_settings(db=db)

            entries = list(self._keys.values())
            active_count = sum(1 for e in entries if e.status == "active")
            cooldown_count = sum(1 for e in entries if e.status == "cooldown")
            expired_count = sum(1 for e in entries if e.status == "expired")

            gcp_configured = bool(
                os.getenv("GCP_PROJECT_ID")
                and (os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("GCP_SERVICE_ACCOUNT_FILE"))
            )

            return {
                "total_keys": len(entries),
                "active_keys": active_count,
                "cooldown_keys": cooldown_count,
                "expired_keys": expired_count,
                "is_operational": active_count > 0 or cooldown_count > 0,
                "is_gcp_configured": gcp_configured,
                "keys": [e.to_dict() for e in entries],
            }


# Singleton instance shared across the entire application runtime
gemini_key_manager = GeminiKeyManager()
