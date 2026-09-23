import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import time
import asyncio
import logging
import socket
from typing import Dict, List
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

old_getaddrinfo = socket.getaddrinfo


def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return old_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = new_getaddrinfo

from app.database import Base, get_engine
from app.state import (
    templates,
    templates_dir,
    PUBLISHED_PORTFOLIOS,
    PUBLISHED_RESUMES,
    CUSTOM_DOMAINS,
    RATE_LIMIT_RULES,
    RATE_LIMIT_STORE,
    PIN_ATTEMPT_STORE,
    _get_client_ip,
    build_user_response,
)
from app.pricing import (
    DEFAULT_COUNTRY_PRICING_DATA,
    DEFAULT_PLANS_CONFIG_DATA,
    _get_country_pricing_dict,
)
from app.routers.payments import sync_order_status_from_payhere
from app.routers import auth, resume, portfolio, payments, career, admin, pages

# Configure logging
logger = logging.getLogger("dreemfolio.main")

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APPLICATION INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ATS-Friendly AI Resume, Cover Letter & Custom Portfolio SaaS",
    description="Micro-SaaS to optimize resumes, generate ATS PDFs, and publish modern custom developer portfolios",
    version="1.3.0",
)

# Hardened CORS configuration (rejects wildcards with credentials to prevent cross-origin hijacking)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
] or [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://dreemfolio.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Enable GZip compression (compresses JS/CSS/HTML responses >1KB by up to 80% for fast page loads)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ─────────────────────────────────────────────────────────────────────────────
# ANTI-ABUSE RATE LIMITING MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """
    Sliding window in-memory rate limiter per IP.
    Thwarts credential stuffing, brute-forcing, and resource exhaustion DoS.
    Includes automated memory garbage collection to prevent RAM leakage under sustained load.
    """
    path = request.url.path
    rule = RATE_LIMIT_RULES.get(path)
    if rule:
        max_reqs, window_secs = rule
        client_ip = _get_client_ip(request)
        now = time.time()
        timestamps = RATE_LIMIT_STORE[client_ip][path]

        # Evict timestamps older than current window
        valid_timestamps = [t for t in timestamps if (now - t) < window_secs]
        RATE_LIMIT_STORE[client_ip][path] = valid_timestamps

        # Memory garbage collection: Prune empty IPs if store grows beyond 3000 entries
        if len(RATE_LIMIT_STORE) > 3000:
            stale_ips = [
                ip
                for ip, paths in list(RATE_LIMIT_STORE.items())
                if not any(paths.values())
            ]
            for ip in stale_ips:
                RATE_LIMIT_STORE.pop(ip, None)

        if len(valid_timestamps) >= max_reqs:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down and try again later.",
                    "retry_after_seconds": (
                        int(window_secs - (now - valid_timestamps[0]))
                        if valid_timestamps
                        else window_secs
                    ),
                },
                headers={"Retry-After": str(window_secs)},
            )

        RATE_LIMIT_STORE[client_ip][path].append(now)

    return await call_next(request)


# ─────────────────────────────────────────────────────────────────────────────
# OWASP ENTERPRISE SECURITY HEADERS MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Apply hardened OWASP security headers to all HTTP responses.
    Protects against Clickjacking, MIME-sniffing, XSS, and Referrer leakage.
    Adds caching headers for static assets (JS, CSS, images).
    """
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"

    # Static assets cache header (speeds up subsequent loads dramatically)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = (
            "public, max-age=86400, stale-while-revalidate=604800"
        )

    return response


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION LIFECYCLE & DATABASE SETUP
# ─────────────────────────────────────────────────────────────────────────────
_email_worker_running = True


async def email_queue_worker_loop():
    """Background task cycling every 60 seconds to retry failed/pending emails."""
    from app.email_service import process_email_queue

    logger.info("🚀 Email queue auto-retry background worker started.")
    while _email_worker_running:
        try:
            await asyncio.sleep(60)
            stats = await asyncio.to_thread(process_email_queue, 25)
            if stats.get("processed", 0) > 0:
                logger.info("📬 Email Queue Worker processed batch: %s", stats)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in email queue worker loop: %s", e)


@app.on_event("startup")
def on_startup():
    """Ensure database tables are created in MySQL on startup and start queue worker."""
    try:
        active_engine = get_engine()
        Base.metadata.create_all(bind=active_engine)
        print("[DB] Database tables successfully initialized!")
    except Exception as e:
        print("[DB] Warning during database table initialization:", str(e))

    # Launch background worker
    try:
        asyncio.create_task(email_queue_worker_loop())
    except Exception as worker_err:
        logger.warning("Failed to start email queue worker: %s", worker_err)


@app.on_event("shutdown")
def on_shutdown():
    """Gracefully terminate background workers."""
    global _email_worker_running
    _email_worker_running = False


# ─────────────────────────────────────────────────────────────────────────────
# STATIC ASSETS MOUNTING
# ─────────────────────────────────────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER DOMAIN SUB-ROUTERS
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(portfolio.router)
app.include_router(payments.router)
app.include_router(career.router)
app.include_router(admin.router)
app.include_router(pages.router)
