import os
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.edge.options import Options

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1440,900")
# Enable browser logging
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Edge(options=options)
try:
    driver.get("http://127.0.0.1:8000/app")
    time.sleep(3)

    # Capture screenshot
    snap_path = "C:/Users/Malitha/.gemini/antigravity/brain/bccd415f-73cd-4b88-b978-87a0a12ae0ce/scratch/current_app_view.png"
    driver.save_screenshot(snap_path)
    print("Screenshot saved to:", snap_path)

    # Get browser console logs
    logs = driver.get_log('browser')
    print("\n--- BROWSER CONSOLE LOGS ---")
    for entry in logs:
        print(entry['level'], entry['message'])

finally:
    driver.quit()
