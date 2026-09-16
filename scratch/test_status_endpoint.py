import os
import sys
from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import get_engine, SessionLocal
from app.models import User, OnlinePaymentOrder
from app.auth import hash_password

client = TestClient(app)

def test_status_page():
    from app.database import get_engine
    get_engine()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # Check or create user
        test_email = "status_page_tester@example.com"
        user = db.scalars(select(User).where(User.email == test_email)).first()
        if not user:
            user = User(
                email=test_email,
                full_name="Status Page Tester",
                hashed_password=hash_password("Pass123!"),
                plan_tier="free"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create a pending order
        order_id = "ORD-TEST-PENDING-999"
        order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id)).first()
        if not order:
            order = OnlinePaymentOrder(
                user_id=user.id,
                order_id=order_id,
                target_plan="pro",
                amount=990.0,
                currency="LKR",
                status="pending",
                status_message="Waiting for customer payment"
            )
            db.add(order)
            db.commit()

        print(f"Testing /payment/status?order_id={order_id}&status=pending ...")
        res = client.get(f"/payment/status?order_id={order_id}&status=pending")
        print("Status code:", res.status_code)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text[:300]}"
        assert "Payment" in res.text
        print("✅ /payment/status rendered successfully with HTTP 200!")

        # Also test with an order that doesn't exist
        res_none = client.get("/payment/status?order_id=ORD-NON-EXISTENT&status=pending")
        print("Non-existent order status code:", res_none.status_code)
        assert res_none.status_code == 200
        print("✅ Non-existent order handled cleanly with HTTP 200 fallback!")

    finally:
        db.close()

if __name__ == "__main__":
    test_status_page()
