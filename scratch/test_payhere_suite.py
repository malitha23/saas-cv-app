import os
import sys
import hashlib
import json
from fastapi.testclient import TestClient
from sqlalchemy import select

# Ensure app is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.payhere import PayHereGateway
from app.models import User, OnlinePaymentOrder
from app.database import get_engine, SessionLocal
from app.auth import hash_password, create_access_token

client = TestClient(app)

def test_payhere_crypto_formulas():
    print("\n--- 1. Testing PayHere Cryptographic Hash Formulas ---")
    merchant_id = "1238036"
    order_id = "ORD-TEST-001"
    amount = 990.00
    currency = "LKR"
    secret = "MTQ1MDE1NTA3NjM4NDg0NjI3NzUxNzIxODc0NjQxNDE3NDY3NTY1Mw=="

    # Pre-checkout hash
    generated_hash = PayHereGateway.calculate_hash(
        merchant_id=merchant_id,
        order_id=order_id,
        amount=amount,
        currency=currency,
        merchant_secret=secret
    )
    # Manual calculation
    hashed_secret = hashlib.md5(secret.encode('utf-8')).hexdigest().upper()
    expected_raw = f"{merchant_id}{order_id}990.00{currency}{hashed_secret}"
    expected_hash = hashlib.md5(expected_raw.encode('utf-8')).hexdigest().upper()

    assert generated_hash == expected_hash, f"Hash mismatch: {generated_hash} != {expected_hash}"
    print(f"✅ Pre-checkout hash generated correctly: {generated_hash}")

    # IPN Webhook md5sig verification
    status_code = "2"
    ipn_raw = f"{merchant_id}{order_id}990.00{currency}{status_code}{hashed_secret}"
    valid_sig = hashlib.md5(ipn_raw.encode('utf-8')).hexdigest().upper()

    is_valid = PayHereGateway.verify_ipn_signature(
        merchant_id=merchant_id,
        order_id=order_id,
        payhere_amount="990.00",
        payhere_currency=currency,
        status_code=status_code,
        md5sig=valid_sig,
        merchant_secret=secret
    )
    assert is_valid is True, "Valid IPN signature was rejected!"
    print(f"✅ Valid IPN signature accepted: {valid_sig}")

    # Test forged/tampered signature rejection
    fake_sig = "00000000000000000000000000000000"
    is_fake_valid = PayHereGateway.verify_ipn_signature(
        merchant_id=merchant_id,
        order_id=order_id,
        payhere_amount="990.00",
        payhere_currency=currency,
        status_code=status_code,
        md5sig=fake_sig,
        merchant_secret=secret
    )
    assert is_fake_valid is False, "Forged IPN signature was mistakenly accepted!"
    print("✅ Forged IPN signature rejected properly.")

def test_full_payhere_api_flow():
    print("\n--- 2. Testing Full PayHere API Lifecycle Flow ---")
    get_engine()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # Create or fetch test user
        test_email = "testcandidate_payhere@example.com"
        user = db.scalars(select(User).where(User.email == test_email)).first()
        if not user:
            user = User(
                email=test_email,
                hashed_password=hash_password("Password123!"),
                full_name="Malitha Test User",
                plan_tier="free",
                subscription_status="active"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.plan_tier = "free"
            db.commit()

        token = create_access_token(user)

        # 2a. Initiate Checkout for Pro Plan
        init_res = client.post(
            "/api/payments/payhere/initiate",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan": "pro", "currency": "LKR"}
        )
        assert init_res.status_code == 200, f"Initiate failed: {init_res.text}"
        data = init_res.json()
        assert data["success"] is True
        order_id = data["order_id"]
        assert data["amount"] == 990.0
        assert data["currency"] == "LKR"
        assert "hash" in data["params"]
        assert data["action_url"].startswith("https://")
        print(f"✅ Initiated order successfully: {order_id} (Amount: {data['amount']} {data['currency']})")

        # Verify order exists in DB
        db.commit()
        db_order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id)).first()
        assert db_order is not None
        assert db_order.status == "initiated"
        print("✅ DB order record verified in 'initiated' state.")

        # 2b. Test IPN Price Tampering Protection
        config = PayHereGateway.get_config()
        secret = config["merchant_secret"]
        m_id = config["merchant_id"]

        # Attacker tampers amount to 1.00 LKR
        tampered_amount = "1.00"
        hashed_secret = hashlib.md5(secret.encode('utf-8')).hexdigest().upper()
        tampered_sig_raw = f"{m_id}{order_id}{tampered_amount}LKR2{hashed_secret}"
        tampered_sig = hashlib.md5(tampered_sig_raw.encode('utf-8')).hexdigest().upper()

        tampered_res = client.post(
            "/api/payments/payhere/notify",
            data={
                "merchant_id": m_id,
                "order_id": order_id,
                "payment_id": "PAY-TAMPERED-01",
                "payhere_amount": tampered_amount,
                "payhere_currency": "LKR",
                "status_code": "2",
                "md5sig": tampered_sig,
                "method": "VISA"
            }
        )
        assert tampered_res.status_code == 400, "Tampered amount should be rejected with 400!"
        db.commit()
        db.refresh(db_order)
        assert db_order.status == "amount_tampered"
        print("✅ Anti-Tampering Shield successfully blocked price alteration!")

        # 2c. Test Genuine Successful Callback
        real_amount = "990.00"
        real_sig_raw = f"{m_id}{order_id}{real_amount}LKR2{hashed_secret}"
        real_sig = hashlib.md5(real_sig_raw.encode('utf-8')).hexdigest().upper()

        success_res = client.post(
            "/api/payments/payhere/notify",
            data={
                "merchant_id": m_id,
                "order_id": order_id,
                "payment_id": "320025112233",
                "payhere_amount": real_amount,
                "payhere_currency": "LKR",
                "status_code": "2",
                "md5sig": real_sig,
                "method": "VISA",
                "status_message": "Successfully completed",
                "card_holder_name": "M Sayuranga",
                "card_no": "************1234"
            }
        )
        assert success_res.status_code == 200
        assert success_res.text == "OK"
        print("✅ Genuine IPN callback accepted with HTTP 200 OK.")

        # 2d. Verify DB Status & Automatic User Account Upgrade
        db.commit()
        db.refresh(db_order)
        db.refresh(user)

        assert db_order.status == "success", f"Order status is {db_order.status}"
        assert db_order.payhere_payment_id == "320025112233"
        assert db_order.payment_method == "VISA"
        assert user.plan_tier == "pro", f"User plan tier is {user.plan_tier}"
        assert user.subscription_status == "active"
        assert user.subscription_expires_at is not None
        print(f"🎉 Candidate {user.email} successfully upgraded to {user.plan_tier.upper()}! Expiry: {user.subscription_expires_at}")

        # 2e. Test Return Redirection
        ret_res = client.get(f"/api/payments/payhere/return?order_id={order_id}", follow_redirects=False)
        assert ret_res.status_code == 303
        assert "/payment/status" in ret_res.headers["location"]
        assert "status=success" in ret_res.headers["location"]
        print(f"✅ Return redirect validated: {ret_res.headers['location']}")

    finally:
        db.close()

if __name__ == "__main__":
    test_payhere_crypto_formulas()
    test_full_payhere_api_flow()
    print("\n==========================================")
    print("ALL PAYHERE INTEGRATION TESTS PASSED 100%!")
    print("==========================================\n")
