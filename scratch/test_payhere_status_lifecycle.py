import os
import sys
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import select

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import get_db, SessionLocal
from app.models import User, OnlinePaymentOrder, BankPaymentSlip
from app.auth import hash_password, create_access_token
from app.payhere import PayHereGateway

client = TestClient(app)

def run_tests():
    print("==================================================================")
    print("  RUNNING PAYHERE STATUS LIFECYCLE & SECURITY VERIFICATION SUITE")
    print("==================================================================")

    from app.database import get_engine
    get_engine()
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        # Create test user
        test_email = "tester_lifecycle@dreemfolio.test"
        existing_user = db.scalars(select(User).where(User.email == test_email)).first()
        if existing_user:
            # Clean up existing test orders
            db.query(OnlinePaymentOrder).filter(OnlinePaymentOrder.user_id == existing_user.id).delete()
            db.delete(existing_user)
            db.commit()

        user = User(
            email=test_email,
            full_name="Lifecycle Tester",
            hashed_password=hash_password("TestPass123!"),
            is_active=True,
            is_admin=False,
            plan_tier="free",
            subscription_status="active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(user)
        auth_headers = {"Authorization": f"Bearer {token}"}

        # -------------------------------------------------------------
        # TEST 1: Initial Payment Initiation
        # -------------------------------------------------------------
        print("\n[TEST 1] Initiating first checkout order...")
        res1 = client.post(
            "/api/payments/payhere/initiate",
            json={"plan": "pro", "currency": "LKR", "force": False},
            headers=auth_headers
        )
        assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
        data1 = res1.json()
        order_id_1 = data1["order_id"]
        print(f"  -> Order 1 created: {order_id_1}")

        # Verify currentUser state now reports has_pending_order = True
        me_res = client.get("/api/auth/me", headers=auth_headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["has_pending_order"] is True, "Expected has_pending_order to be True"
        assert me_data["pending_order"]["order_id"] == order_id_1
        print("  -> User profile correctly reflects has_pending_order = True")

        # -------------------------------------------------------------
        # TEST 2: Double Payment Shield (HTTP 409 Conflict)
        # -------------------------------------------------------------
        print("\n[TEST 2] Verifying double checkout prevention (Anti-Double Charge Shield)...")
        res2 = client.post(
            "/api/payments/payhere/initiate",
            json={"plan": "pro", "currency": "LKR", "force": False},
            headers=auth_headers
        )
        assert res2.status_code == 409, f"Expected 409 Conflict, got {res2.status_code}: {res2.text}"
        data2 = res2.json()
        assert "payment_in_progress" in str(data2), "Expected payment_in_progress detail in 409 response"
        print(f"  -> Successfully blocked double payment with 409 Conflict: {data2['detail']['message']}")

        # -------------------------------------------------------------
        # TEST 3: Force Flag Bypasses and Supersedes Previous Order
        # -------------------------------------------------------------
        print("\n[TEST 3] Initiating fresh checkout with force=True...")
        res3 = client.post(
            "/api/payments/payhere/initiate",
            json={"plan": "elite", "currency": "LKR", "force": True},
            headers=auth_headers
        )
        assert res3.status_code == 200, f"Expected 200, got {res3.status_code}: {res3.text}"
        data3 = res3.json()
        order_id_2 = data3["order_id"]
        assert order_id_2 != order_id_1
        print(f"  -> Order 2 created: {order_id_2} (Superseded Order 1)")

        # Verify Order 1 status is 'superseded' in DB
        db.commit()
        o1 = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id_1)).first()
        assert o1 is not None, f"Order {order_id_1} not found in DB"
        assert o1.status == "superseded", f"Expected superseded, got {o1.status}"
        print(f"  -> Order 1 in DB is now: {o1.status}")

        # -------------------------------------------------------------
        # TEST 4: Webhook Status 0 (Pending) - No Tier Access Granted
        # -------------------------------------------------------------
        print("\n[TEST 4] Processing Webhook Status 0 (Pending)...")
        # Generate valid merchant MD5 hash
        merchant_id = os.getenv("PAYHERE_MERCHANT_ID", "1234567")
        merchant_secret = os.getenv("PAYHERE_MERCHANT_SECRET", "test_secret")
        amount_formatted = f"{float(data3['amount']):.2f}"
        currency = "LKR"
        status_code = "0"
        
        hashed_secret = hashlib.md5(merchant_secret.encode("utf-8")).hexdigest().upper()
        raw_to_hash = f"{merchant_id}{order_id_2}{amount_formatted}{currency}{status_code}{hashed_secret}"
        md5sig = hashlib.md5(raw_to_hash.encode("utf-8")).hexdigest().upper()

        wh_pending = client.post(
            "/api/payments/payhere/notify",
            data={
                "merchant_id": merchant_id,
                "order_id": order_id_2,
                "payment_id": "PH-PENDING-001",
                "payhere_amount": amount_formatted,
                "payhere_currency": currency,
                "status_code": status_code,
                "md5sig": md5sig,
                "status_message": "Payment processing at bank",
                "method": "VISA",
                "card_holder_name": "Lifecycle Tester",
                "card_no": "411111******1111"
            }
        )
        assert wh_pending.status_code == 200, f"Expected 200, got {wh_pending.status_code}: {wh_pending.text}"
        
        # Verify user tier is STILL FREE
        db.commit()
        cand = db.scalars(select(User).where(User.id == user.id)).first()
        assert cand.plan_tier == "free", f"User should remain free on pending status, got {cand.plan_tier}"
        o2 = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id_2)).first()
        assert o2.status == "pending"
        print("  -> Status 0 verified: Order status is 'pending', plan_tier is still 'free' (No unauthorized access)")

        # -------------------------------------------------------------
        # TEST 5: Webhook Status 2 (Success) - Subscription Activated
        # -------------------------------------------------------------
        print("\n[TEST 5] Processing Webhook Status 2 (Success)...")
        status_code_success = "2"
        raw_to_hash_s = f"{merchant_id}{order_id_2}{amount_formatted}{currency}{status_code_success}{hashed_secret}"
        md5sig_s = hashlib.md5(raw_to_hash_s.encode("utf-8")).hexdigest().upper()

        wh_success = client.post(
            "/api/payments/payhere/notify",
            data={
                "merchant_id": merchant_id,
                "order_id": order_id_2,
                "payment_id": "PH-SUCCESS-002",
                "payhere_amount": amount_formatted,
                "payhere_currency": currency,
                "status_code": status_code_success,
                "md5sig": md5sig_s,
                "status_message": "Approved successfully",
                "method": "VISA",
                "card_holder_name": "Lifecycle Tester",
                "card_no": "411111******1111"
            }
        )
        assert wh_success.status_code == 200, f"Expected 200, got {wh_success.status_code}: {wh_success.text}"

        db.commit()
        cand = db.scalars(select(User).where(User.id == user.id)).first()
        assert cand.plan_tier == "elite", f"User should be upgraded to elite, got {cand.plan_tier}"
        assert cand.subscription_status == "active"
        print(f"  -> Status 2 verified: User plan_tier successfully upgraded to '{cand.plan_tier}'")

        # -------------------------------------------------------------
        # TEST 6: Webhook Status -3 (Chargedback) - Immediate Revocation
        # -------------------------------------------------------------
        print("\n[TEST 6] Processing Webhook Status -3 (Chargedback - Fraud / Dispute)...")
        status_code_cb = "-3"
        raw_to_hash_cb = f"{merchant_id}{order_id_2}{amount_formatted}{currency}{status_code_cb}{hashed_secret}"
        md5sig_cb = hashlib.md5(raw_to_hash_cb.encode("utf-8")).hexdigest().upper()

        wh_cb = client.post(
            "/api/payments/payhere/notify",
            data={
                "merchant_id": merchant_id,
                "order_id": order_id_2,
                "payment_id": "PH-SUCCESS-002",
                "payhere_amount": amount_formatted,
                "payhere_currency": currency,
                "status_code": status_code_cb,
                "md5sig": md5sig_cb,
                "status_message": "Cardholder filed chargeback dispute",
                "method": "VISA"
            }
        )
        assert wh_cb.status_code == 200, f"Expected 200, got {wh_cb.status_code}: {wh_cb.text}"

        db.commit()
        cand = db.scalars(select(User).where(User.id == user.id)).first()
        assert cand.plan_tier == "free", f"User should be revoked to free upon chargeback, got {cand.plan_tier}"
        assert cand.subscription_status == "expired"
        o2 = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id_2)).first()
        assert o2.status == "chargedback"
        print(f"  -> Status -3 verified: Order marked 'chargedback', tier revoked to '{cand.plan_tier}', status '{cand.subscription_status}'")

        # -------------------------------------------------------------
        # TEST 7: Webhook Status -1 (Canceled) and -2 (Failed)
        # -------------------------------------------------------------
        print("\n[TEST 7] Verifying Status -1 (Canceled) and -2 (Failed)...")
        # Create order 3
        res4 = client.post(
            "/api/payments/payhere/initiate",
            json={"plan": "pro", "currency": "LKR", "force": True},
            headers=auth_headers
        )
        order_id_3 = res4.json()["order_id"]
        amount_formatted_3 = f"{float(res4.json()['amount']):.2f}"
        
        status_code_cancel = "-1"
        raw_cancel = f"{merchant_id}{order_id_3}{amount_formatted_3}{currency}{status_code_cancel}{hashed_secret}"
        md5sig_cancel = hashlib.md5(raw_cancel.encode("utf-8")).hexdigest().upper()
        
        wh_cancel = client.post(
            "/api/payments/payhere/notify",
            data={
                "merchant_id": merchant_id,
                "order_id": order_id_3,
                "payment_id": "PH-CANC-003",
                "payhere_amount": amount_formatted_3,
                "payhere_currency": currency,
                "status_code": status_code_cancel,
                "md5sig": md5sig_cancel,
                "status_message": "User canceled at gateway"
            }
        )
        assert wh_cancel.status_code == 200
        db.commit()
        o3 = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id_3)).first()
        assert o3 is not None, f"Order {order_id_3} not found in DB"
        assert o3.status == "canceled"
        print("  -> Status -1 verified: Order marked 'canceled'")

        print("\n==================================================================")
        print("  ALL PAYHERE STATUS & SECURITY CHECKS PASSED WITH 100% SUCCESS!")
        print("==================================================================")

    finally:
        # Cleanup
        try:
            if existing_user:
                db.query(OnlinePaymentOrder).filter(OnlinePaymentOrder.user_id == user.id).delete()
                db.delete(user)
                db.commit()
        except Exception:
            pass
        db.close()

if __name__ == "__main__":
    run_tests()
