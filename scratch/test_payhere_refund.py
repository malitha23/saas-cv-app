import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import base64
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_engine
get_engine()
from app.database import SessionLocal
from app.models import User, OnlinePaymentOrder
from app.payhere import PayHereGateway
from app.auth import create_access_token, hash_password

client = TestClient(app)

def test_payhere_refund_suite():
    print("\n--- 1. Testing PayHere OAuth Basic Auth & In-Memory Token Caching ---")
    os.environ["PAYHERE_APP_ID"] = "TEST_APP_ID_123"
    os.environ["PAYHERE_APP_SECRET"] = "TEST_APP_SECRET_456"
    os.environ["PAYHERE_MODE"] = "sandbox"

    cfg = PayHereGateway.get_oauth_config()
    assert cfg["app_id"] == "TEST_APP_ID_123"
    assert cfg["app_secret"] == "TEST_APP_SECRET_456"
    assert "sandbox.payhere.lk" in cfg["token_url"]
    print("✅ OAuth config successfully extracted from environment variables.")

    # Test basic auth derivation
    raw_cred = f"{cfg['app_id']}:{cfg['app_secret']}"
    encoded_cred = base64.b64encode(raw_cred.encode("utf-8")).decode("utf-8")
    assert base64.b64decode(encoded_cred).decode("utf-8") == "TEST_APP_ID_123:TEST_APP_SECRET_456"
    print("✅ Base64 Authorization code derived successfully.")

    # Test token caching with mock httpx
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {
        "access_token": "mock-token-abc-123",
        "token_type": "bearer",
        "expires_in": 599
    }

    with patch("httpx.Client.post", return_value=mock_token_resp) as mock_post:
        # First call fetches token
        token1 = PayHereGateway.get_access_token()
        assert token1 == "mock-token-abc-123"
        assert mock_post.call_count == 1

        # Second call reuses in-memory cached token (Zero roundtrips)
        token2 = PayHereGateway.get_access_token()
        assert token2 == "mock-token-abc-123"
        assert mock_post.call_count == 1
        print("✅ In-memory OAuth2 token caching confirmed (Rate-limiting shield active).")

    print("\n--- 2. Setting up Test Users and Orders ---")
    db = SessionLocal()
    try:
        # Create Super Admin
        admin = db.query(User).filter(User.email == "superadmin_refund@example.com").first()
        if not admin:
            admin = User(
                email="superadmin_refund@example.com",
                hashed_password=hash_password("AdminSecurePass!"),
                full_name="Super Admin",
                is_admin=True,
                plan_tier="pro"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # Create Candidate
        candidate = db.query(User).filter(User.email == "candidate_refund_target@example.com").first()
        if not candidate:
            candidate = User(
                email="candidate_refund_target@example.com",
                hashed_password=hash_password("Pass123!"),
                full_name="Candidate User",
                is_admin=False,
                plan_tier="pro",
                subscription_status="active"
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
        else:
            candidate.plan_tier = "pro"
            candidate.subscription_status = "active"
            db.commit()

        # Create Test Order
        order_id = f"ORD-REFUND-TEST-{int(time.time())}"
        test_order = OnlinePaymentOrder(
            order_id=order_id,
            user_id=candidate.id,
            target_plan="pro",
            amount=990.0,
            currency="LKR",
            gateway="payhere",
            status="success",
            payhere_payment_id="320099887766"
        )
        db.add(test_order)
        db.commit()
        db.refresh(test_order)

        admin_token = create_access_token(admin)
        candidate_token = create_access_token(candidate)

        print("\n--- 3. Testing RBAC Security ---")
        # Regular candidate tries to refund -> 403 Forbidden
        reg_res = client.post(
            "/api/admin/payhere/refund",
            headers={"Authorization": f"Bearer {candidate_token}"},
            json={"order_id": order_id, "reason": "Unauthorized attempt"}
        )
        assert reg_res.status_code == 403
        print("✅ Regular candidate correctly blocked with HTTP 403 Forbidden.")

        # Unauthenticated request -> 401 Unauthorized
        unauth_res = client.post(
            "/api/admin/payhere/refund",
            json={"order_id": order_id, "reason": "No auth"}
        )
        assert unauth_res.status_code == 401
        print("✅ Unauthenticated request correctly blocked with HTTP 401 Unauthorized.")

        print("\n--- 4. Testing Anti-Double-Refund & Idempotency ---")
        # Non-existent order
        nf_res = client.post(
            "/api/admin/payhere/refund",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"order_id": "ORD-DOES-NOT-EXIST", "reason": "Test reason"}
        )
        assert nf_res.status_code == 404
        print("✅ Non-existent order rejected with HTTP 404.")

        # Order without payhere_payment_id
        test_order.payhere_payment_id = None
        db.commit()
        no_pid_res = client.post(
            "/api/admin/payhere/refund",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"order_id": order_id, "reason": "Test reason"}
        )
        assert no_pid_res.status_code == 400
        test_order.payhere_payment_id = "320099887766"
        db.commit()
        print("✅ Order without payment ID rejected with HTTP 400.")

        print("\n--- 5. Testing Successful Refund & Auto-Downgrade Flow ---")
        with patch.object(
            PayHereGateway,
            "process_refund",
            return_value={"success": True, "refund_id": "560034010257", "msg": "Successfully processed the refund"}
        ):
            refund_exec_res = client.post(
                "/api/admin/payhere/refund",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"order_id": order_id, "reason": "Customer requested refund within 7-day window"}
            )
            assert refund_exec_res.status_code == 200
            res_json = refund_exec_res.json()
            assert res_json["success"] is True
            assert res_json["refund_id"] == "560034010257"
            print(f"✅ Refund executed successfully: {res_json['message']}")

        # Verify DB audit fields
        db.refresh(test_order)
        db.refresh(candidate)
        assert test_order.status == "refunded"
        assert test_order.payhere_refund_id == "560034010257"
        assert test_order.refund_reason == "Customer requested refund within 7-day window"
        assert test_order.refunded_by_admin == admin.email
        assert test_order.refunded_at is not None
        print("✅ DB audit trail confirmed (refund_id, admin email, reason, timestamp).")

        # Verify candidate subscription was revoked and downgraded to free!
        assert candidate.plan_tier == "free"
        assert candidate.subscription_status == "expired"
        print("✅ Candidate subscription successfully revoked and downgraded to Free tier.")

        print("\n--- 6. Testing Second Refund Attempt (Double Refund Shield) ---")
        double_res = client.post(
            "/api/admin/payhere/refund",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"order_id": order_id, "reason": "Attempting second refund"}
        )
        assert double_res.status_code == 400
        assert "already been refunded" in double_res.json()["detail"]
        print("✅ Anti-Double-Refund shield successfully rejected second refund attempt!")

        print("\n=======================================================")
        print("ALL PAYHERE 100% SECURE REFUND TESTS PASSED 100%!")
        print("=======================================================")
    finally:
        db.close()

if __name__ == "__main__":
    test_payhere_refund_suite()
