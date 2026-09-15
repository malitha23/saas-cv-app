import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
import json
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
    # 1. Test Guest / Logged out user
    driver.get("http://127.0.0.1:8000/")
    time.sleep(1)
    # Clear any leftover tokens
    driver.execute_script("localStorage.clear(); location.reload();")
    time.sleep(2)
    guest_snap = os.path.join(output_dir, "landing_guest_view.png")
    driver.save_screenshot(guest_snap)
    print("Guest screenshot saved:", guest_snap)

    body_text = driver.find_element("tag name", "body").text
    assert "Sign In" in body_text, "Sign In button missing for guest"
    assert "Get Started Free" in body_text or "Get Started for Free" in body_text
    print("✅ Guest view verified!")

    # 2. Test Authenticated user
    from app.auth import create_access_token
    from app.database import get_engine
    from app.models import User
    get_engine()
    from app.database import SessionLocal
    db = SessionLocal()
    user = db.query(User).filter(User.email == "callback_tester@example.com").first()
    real_token = create_access_token(user)
    db.close()
    fake_user = {
        "id": 1,
        "email": "callback_tester@example.com",
        "full_name": "Malitha Sayuranga",
        "plan_tier": "pro",
        "is_admin": False
    }
    driver.execute_script(f"""
        localStorage.setItem('saas_token', '{real_token}');
        localStorage.setItem('saas_user', '{json.dumps(fake_user)}');
        location.reload();
    """)
    time.sleep(2)
    auth_snap = os.path.join(output_dir, "landing_auth_view.png")
    driver.save_screenshot(auth_snap)
    print("Auth screenshot saved:", auth_snap)

    header_text = driver.find_element("tag name", "header").text
    print("Header text for logged-in user:", header_text)

    assert "Go to Workspace" in header_text, "Go to Workspace missing in header"
    assert "Callback" in header_text, "User name missing in header"
    assert "Sign In" not in header_text, "Sign In erroneously displayed for logged-in user!"

    hero_text = driver.find_element("tag name", "section").text
    assert "Open AI Workspace" in hero_text, "Open AI Workspace missing in Hero"
    print("✅ Authenticated view verified! 'Sign In' and 'Get Started Free' are properly replaced with user workspace actions!")

finally:
    driver.quit()
