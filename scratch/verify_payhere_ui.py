import os
import sys
from selenium import webdriver
from selenium.webdriver.edge.options import Options
import time

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1440,900")

driver = webdriver.Edge(options=options)
try:
    print("Navigating to http://127.0.0.1:8000/app ...")
    driver.get("http://127.0.0.1:8000/app")
    time.sleep(2)

    logs = driver.get_log("browser")
    severe_errors = [l for l in logs if l["level"] == "SEVERE" and "favicon" not in l["message"].lower()]
    print(f"Browser severe errors on load: {len(severe_errors)}")
    for err in severe_errors:
        print("  Log:", err["message"])

    driver.execute_script("""
        const app = document.querySelector('[x-data]');
        if (app && app._x_dataStack) {
            app._x_dataStack[0].showOnboardingTour = false;
            app._x_dataStack[0].showPricingModal = true;
            app._x_dataStack[0].pricingPaymentMethod = 'card';
        }
        if (window.lucide) window.lucide.createIcons();
    """)
    time.sleep(1)

    screenshot_path = "C:/Users/Malitha/.gemini/antigravity/brain/bccd415f-73cd-4b88-b978-87a0a12ae0ce/scratch/payhere_online_checkout_view.png"
    driver.save_screenshot(screenshot_path)
    print(f"✅ Screenshot successfully saved: {screenshot_path}")

finally:
    driver.quit()
