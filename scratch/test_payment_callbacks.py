import os
import sys
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import get_db, SessionLocal, get_engine
from app.models import User, OnlinePaymentOrder
from app.payhere import PayHereGateway
from app.auth import hash_password

client = TestClient(app, follow_redirects=False)

def test_payment_callbacks_and_status_pages():
    get_engine()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # 1. Setup a test candidate and order
        test_email = "callback_tester@example.com"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            user = User(
                email=test_email,
                hashed_password=hash_password("Secret123!"),
                full_name="Callback Tester",
                plan_tier="free"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        order_id = "ORD-TEST-CB-001"
        order = db.query(OnlinePaymentOrder).filter(OnlinePaymentOrder.order_id == order_id).first()
        if not order:
            order = OnlinePaymentOrder(
                order_id=order_id,
                user_id=user.id,
                target_plan="pro",
                amount=990.0,
                currency="LKR",
                gateway="payhere",
                status="initiated"
            )
            db.add(order)
            db.commit()
            db.refresh(order)
        else:
            order.status = "initiated"
            db.commit()

        # 2. Test Return URL GET redirect
        ret_get = client.get(f"/api/payments/payhere/return?order_id={order_id}")
        assert ret_get.status_code == 303
        assert "/payment/status" in ret_get.headers["location"]
        assert f"order_id={order_id}" in ret_get.headers["location"]
        print("✅ Return URL GET redirect passed!")

        # 3. Test Return URL POST redirect (PayHere POSTing return)
        ret_post = client.post("/api/payments/payhere/return", data={"order_id": order_id})
        assert ret_post.status_code == 303
        assert "/payment/status" in ret_post.headers["location"]
        print("✅ Return URL POST redirect passed!")

        # 4. Test Cancel URL GET redirect
        cancel_get = client.get(f"/api/payments/payhere/cancel?order_id={order_id}")
        assert cancel_get.status_code == 303
        assert "/payment/status" in cancel_get.headers["location"]
        assert "status=canceled" in cancel_get.headers["location"]
        print("✅ Cancel URL GET redirect passed!")

        # 5. Test Root landing redirect with ?payment=
        root_redir = client.get(f"/?payment=success&order_id={order_id}")
        assert root_redir.status_code == 303
        assert "/payment/status" in root_redir.headers["location"]
        assert f"order_id={order_id}" in root_redir.headers["location"]
        print("✅ Root /?payment= redirect passed!")

        # 6. Test Order Status Polling API
        api_res = client.get(f"/api/payments/orders/{order_id}/status")
        assert api_res.status_code == 200
        api_data = api_res.json()
        assert api_data["order_id"] == order_id
        assert api_data["amount"] == 990.0
        assert api_data["target_plan"] == "pro"
        print("✅ Order Status API endpoint passed!")

        # 7. Test Payment Status Page - Success
        order.status = "success"
        order.payhere_payment_id = "PAYHERE-320099"
        order.payment_method = "VISA"
        db.commit()

        status_success = client.get(f"/payment/status?order_id={order_id}&status=success")
        assert status_success.status_code == 200
        assert "Payment Successful!" in status_success.text
        assert "ගෙවීම සාර්ථකයි" in status_success.text
        assert order_id in status_success.text
        assert "Rs. 990.00" in status_success.text
        assert "Launch AI Workspace" in status_success.text
        print("✅ Payment Success Page rendering verified!")

        # 8. Test Payment Status Page - Canceled
        status_canceled = client.get(f"/payment/status?order_id={order_id}&status=canceled")
        assert status_canceled.status_code == 200
        assert "Payment Canceled" in status_canceled.text
        assert "ගෙවීම ඔබ විසින් අවලංගු කරන ලදී" in status_canceled.text
        assert "Try Payment Again" in status_canceled.text
        print("✅ Payment Canceled Page rendering verified!")

        # 9. Test Payment Status Page - Failed with Reason
        order.status = "failed"
        order.status_message = "Insufficient funds in candidate card"
        db.commit()

        status_failed = client.get(f"/payment/status?order_id={order_id}&status=failed")
        assert status_failed.status_code == 200
        assert "Payment Incomplete or Failed" in status_failed.text
        assert "Insufficient funds in candidate card" in status_failed.text
        print("✅ Payment Failed Page with reason rendering verified!")

        print("\n=======================================================")
        print("ALL CALLBACKS & STATUS PAGE VERIFICATION PASSED 100%!")
        print("=======================================================")
    finally:
        db.close()

if __name__ == "__main__":
    test_payment_callbacks_and_status_pages()
