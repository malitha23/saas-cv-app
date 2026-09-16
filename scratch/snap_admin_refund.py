import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import json
from selenium import webdriver
from selenium.webdriver.edge.options import Options

from app.database import get_engine
get_engine()
from app.database import SessionLocal
from app.models import User, OnlinePaymentOrder
from app.auth import create_access_token

db = SessionLocal()
try:
    admin = db.query(User).filter(User.email == "superadmin_refund@example.com").first()
    assert admin is not None
    admin_token = create_access_token(admin)
finally:
    db.close()

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1400,900")

output_dir = "C:/Users/Malitha/.gemini/antigravity/brain/bccd415f-73cd-4b88-b978-87a0a12ae0ce/scratch"
os.makedirs(output_dir, exist_ok=True)

driver = webdriver.Edge(options=options)
try:
    driver.get("http://127.0.0.1:8000/paneladmin")
    time.sleep(1)

    # Inject admin token and navigate
    driver.execute_script(f"""
        localStorage.setItem('saas_token', '{admin_token}');
        location.reload();
    """)
    time.sleep(2)

    # Click PayHere tab and open modal
    driver.execute_script("""
        const el = document.querySelector('[x-data]');
        if (el && el._x_dataStack) {
            const state = el._x_dataStack[0];
            state.activeTab = 'payhere';
            state.loadPayHereOrders();
            state.loadPayHereConfig();
        }
    """)
    time.sleep(1.5)

    driver.execute_script("""
        const el = document.querySelector('[x-data]');
        if (el && el._x_dataStack) {
            const state = el._x_dataStack[0];
            // Find a successful order or create dummy representation to trigger modal
            const sampleOrder = {
                id: 999,
                order_id: 'ORD-20260916-SAMPLE',
                user_email: 'candidate_refund_target@example.com',
                target_plan: 'pro',
                amount: 990.0,
                currency: 'LKR',
                status: 'success',
                payhere_payment_id: '320099887766'
            };
            state.openRefundModal(sampleOrder);
        }
    """)
    time.sleep(1)

    snap_path = os.path.join(output_dir, "admin_refund_modal_view.png")
    driver.save_screenshot(snap_path)
    print("Screenshot saved to:", snap_path)

finally:
    driver.quit()
