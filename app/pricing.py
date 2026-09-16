import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.auth import get_saas_setting

DEFAULT_COUNTRY_PRICING_DATA: Dict[str, Dict[str, Any]] = {
    "DEFAULT": {
        "country_code": "DEFAULT",
        "country_name": "Global (USD)",
        "currency_code": "USD",
        "currency_symbol": "$",
        "sprint_price": "$4.99",
        "plans": [
            {
                "plan_key": "free",
                "title": "Free Starter",
                "badge": "Freemium",
                "price_display": "$0",
                "period_display": "/ forever",
                "sub_billing_text": "No Credit Card Required",
                "description": "Great for trying out AI resume keyword tailoring & ATS match scoring.",
                "features": [
                    "2 AI Tailored Runs per day",
                    "ATS Keyword Match & Score (0-100)",
                    "2 Classic ATS PDF Downloads (Lifetime Free)",
                    "1 Visual Photo CV Download (Lifetime Free)",
                    "3 AI Cover Letters (1st Clean • 2 Watermarked)",
                    "AI Job Recommendations (Top 3 Roles Preview)",
                    "AI Job Hunter (Basic Search • 4 Vacancies)",
                    "1-Click Application Copilot (1 Free Kit/day)",
                    "Job Application Tracker (Up to 3 Jobs)",
                    "AI Career Copilot Chat (3 Free Prompts/day)",
                    "Interactive Web Portfolio Studio (Live Preview)",
                    "MySQL Cloud Auto-Save (Restoring requires Pro)"
                ],
                "is_popular": False,
                "button_text": "Current Plan"
            },
            {
                "plan_key": "pro",
                "title": "Pro Career",
                "badge": "🔥 Best Seller",
                "price_display": "$9",
                "period_display": "/ month",
                "sub_billing_text": "or $19 for 3-Month Job Hunt Pass",
                "description": "Everything needed to land senior interviews with unbranded formats & live cloud sync.",
                "features": [
                    "Unlimited AI Tailoring runs",
                    "Unlimited ATS & Visual Photo CV Downloads",
                    "Unlimited AI Cover Letters (100% Watermark-Free & Clean)",
                    "Photo & Digital Signature Upload",
                    "Hosted Live Portfolio Subdomain (.dreemfolio.com)",
                    "MySQL Cloud Auto-Save & Instant Version Restore",
                    "✨ Unlimited AI Job Recommendations & Re-Tailoring",
                    "⚡ Unlimited AI Job Hunter with LinkedIn Easy Apply",
                    "🚀 Unlimited 1-Click Application Screening Kits",
                    "📊 Unlimited Kanban Job Application Tracker",
                    "💬 Unlimited 24/7 AI Career Copilot Chatbot"
                ],
                "is_popular": True,
                "button_text": "Upgrade to Pro ($9/mo)"
            },
            {
                "plan_key": "elite",
                "title": "Executive Elite",
                "badge": "Personal Brand",
                "price_display": "$19",
                "period_display": "/ month",
                "sub_billing_text": "or $39 for 3-Month Elite Pass",
                "description": "For Tech Leads, Architects & Executives building an elite digital brand.",
                "features": [
                    "Everything in Pro Career",
                    "Priority AI Processing Queue (Ultra-Fast Copilot)",
                    "Executive Mock Interviews (C-Level & Leadership)",
                    "All 8 Portfolio Web Architectures",
                    "100% Full CRUD Portfolio Studio",
                    "Connect Custom Private Domain & SSL",
                    "Standalone Website HTML Export"
                ],
                "is_popular": False,
                "button_text": "Upgrade to Elite ($19/mo)"
            }
        ]
    },
    "LK": {
        "country_code": "LK",
        "country_name": "Sri Lanka (LKR)",
        "currency_code": "LKR",
        "currency_symbol": "Rs.",
        "sprint_price": "Rs. 490",
        "plans": [
            {
                "plan_key": "free",
                "title": "Free Starter",
                "badge": "Freemium",
                "price_display": "Rs. 0",
                "period_display": "/ forever",
                "sub_billing_text": "No Credit Card Required",
                "description": "Great for trying out AI resume keyword tailoring & ATS match scoring.",
                "features": [
                    "2 AI Tailored Runs per day",
                    "ATS Keyword Match & Score (0-100)",
                    "2 Classic ATS PDF Downloads (Lifetime Free)",
                    "1 Visual Photo CV Download (Lifetime Free)",
                    "3 AI Cover Letters (1st Clean • 2 Watermarked)",
                    "AI Job Recommendations (Top 3 Roles Preview)",
                    "AI Job Hunter (Basic Search • 4 Vacancies)",
                    "1-Click Application Copilot (1 Free Kit/day)",
                    "Job Application Tracker (Up to 3 Jobs)",
                    "AI Career Copilot Chat (3 Free Prompts/day)",
                    "Interactive Web Portfolio Studio (Live Preview)",
                    "MySQL Cloud Auto-Save (Restoring requires Pro)"
                ],
                "is_popular": False,
                "button_text": "Current Plan"
            },
            {
                "plan_key": "pro",
                "title": "Pro Career",
                "badge": "🔥 Best Seller",
                "price_display": "Rs. 990",
                "period_display": "/ month",
                "sub_billing_text": "or Rs. 2,490 for 3-Month Job Hunt Pass",
                "description": "Everything needed to land senior interviews with unbranded formats & live cloud sync.",
                "features": [
                    "Unlimited AI Tailoring runs",
                    "Unlimited ATS & Visual Photo CV Downloads",
                    "Unlimited AI Cover Letters (100% Watermark-Free & Clean)",
                    "Photo & Digital Signature Upload",
                    "Hosted Live Portfolio Subdomain (.dreemfolio.com)",
                    "MySQL Cloud Auto-Save & Instant Version Restore",
                    "✨ Unlimited AI Job Recommendations & Re-Tailoring",
                    "⚡ Unlimited AI Job Hunter with LinkedIn Easy Apply",
                    "🚀 Unlimited 1-Click Application Screening Kits",
                    "📊 Unlimited Kanban Job Application Tracker",
                    "💬 Unlimited 24/7 AI Career Copilot Chatbot"
                ],
                "is_popular": True,
                "button_text": "Upgrade to Pro (Rs. 990/mo)"
            },
            {
                "plan_key": "elite",
                "title": "Executive Elite",
                "badge": "Personal Brand",
                "price_display": "Rs. 2,490",
                "period_display": "/ month",
                "sub_billing_text": "or Rs. 5,900 for 3-Month Elite Pass",
                "description": "For Tech Leads, Architects & Executives building an elite digital brand.",
                "features": [
                    "Everything in Pro Career",
                    "Priority AI Processing Queue (Ultra-Fast Copilot)",
                    "Executive Mock Interviews (C-Level & Leadership)",
                    "All 8 Portfolio Web Architectures",
                    "100% Full CRUD Portfolio Studio",
                    "Connect Custom Private Domain & SSL",
                    "Standalone Website HTML Export"
                ],
                "is_popular": False,
                "button_text": "Upgrade to Elite (Rs. 2,490/mo)"
            }
        ]
    }
}

DEFAULT_PLANS_CONFIG_DATA = DEFAULT_COUNTRY_PRICING_DATA["DEFAULT"]["plans"]


def _get_country_pricing_dict(db: Session) -> Dict[str, Dict[str, Any]]:
    """Helper to retrieve all dynamic country pricing rules from database with fallback."""
    raw = get_saas_setting(db, "saas_country_pricing_json", "")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "DEFAULT" in parsed:
                return parsed
        except Exception:
            pass
    return DEFAULT_COUNTRY_PRICING_DATA
