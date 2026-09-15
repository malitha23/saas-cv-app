import os
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280,850")

output_dir = "C:/Users/Malitha/.gemini/antigravity/brain/bccd415f-73cd-4b88-b978-87a0a12ae0ce/scratch"
os.makedirs(output_dir, exist_ok=True)

driver = webdriver.Edge(options=options)
try:
    # 1. Success Page
    driver.get("http://127.0.0.1:8000/payment/status?order_id=ORD-20260915110237-9086E4&status=success")
    time.sleep(2)
    success_path = os.path.join(output_dir, "payment_success_view.png")
    driver.save_screenshot(success_path)
    print("Saved:", success_path)

    # 2. Failed Page with Reason
    driver.get("http://127.0.0.1:8000/payment/status?order_id=ORD-TEST-CB-001&status=failed")
    time.sleep(2)
    failed_path = os.path.join(output_dir, "payment_failed_view.png")
    driver.save_screenshot(failed_path)
    print("Saved:", failed_path)

    # 3. Canceled Page
    driver.get("http://127.0.0.1:8000/payment/status?order_id=ORD-TEST-CB-001&status=canceled")
    time.sleep(2)
    canceled_path = os.path.join(output_dir, "payment_canceled_view.png")
    driver.save_screenshot(canceled_path)
    print("Saved:", canceled_path)
finally:
    driver.quit()
