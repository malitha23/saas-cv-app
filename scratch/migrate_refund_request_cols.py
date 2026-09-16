import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.database import get_engine

def migrate_db():
    engine = get_engine()
    with engine.connect() as conn:
        res = conn.execute(text("SHOW COLUMNS FROM online_payment_orders"))
        cols = [r[0] for r in res.fetchall()]
        print("Existing columns:", cols)

        if "refund_requested" not in cols:
            print("Adding refund_requested column...")
            conn.execute(text("ALTER TABLE online_payment_orders ADD COLUMN refund_requested TINYINT(1) DEFAULT 0 NOT NULL"))
            conn.commit()

        if "refund_requested_at" not in cols:
            print("Adding refund_requested_at column...")
            conn.execute(text("ALTER TABLE online_payment_orders ADD COLUMN refund_requested_at DATETIME NULL"))
            conn.commit()

        if "refund_request_reason" not in cols:
            print("Adding refund_request_reason column...")
            conn.execute(text("ALTER TABLE online_payment_orders ADD COLUMN refund_request_reason TEXT NULL"))
            conn.commit()

        print("Migration complete!")

if __name__ == "__main__":
    migrate_db()
