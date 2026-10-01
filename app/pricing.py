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
                    "AI Job Hunter (2 Vacancies)",
                    "1-Click Application Copilot (1 Free Kit/day)",
                    "Job Application Tracker (Up to 2 Jobs Kanban)",
                    "AI Voice Mock Interview (3 Sessions Trial)",
                    "AI Video Conference (3 Sessions Trial)",
                    "AI Career Copilot Chat (3 Free Prompts/day)",
                    "Interactive Web Portfolio Studio (In-App Preview)",
                    "Cloud Auto-Save (Restoring drafts requires Pro)"
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
                    "10 Classic ATS PDF Downloads / month",
                    "10 Visual Photo CV Downloads / month",
                    "Unlimited Clean Cover Letters (100% Watermark-Free)",
                    "Photo & Digital Signature Upload",
                    "Hosted Live Portfolio Subdomain (.dreemfolio.com)",
                    "Cloud Auto-Save & Instant Version Restore",
                    "🎯 Top 12 AI Matched Jobs & Tailored Recommendations",
                    "⚡ AI Job Hunter (8 Vacancies • LinkedIn Easy Apply)",
                    "🚀 1-Click Application Copilot (4 Kits / day)",
                    "📊 Job Application Tracker (Up to 5 Jobs Kanban)",
                    "🎙️ AI Voice Mock Interview (12 Sessions / month)",
                    "📹 Real-time Video Conference Coaching (12 Sessions / month)",
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
                    "Unlimited Classic ATS & Visual Photo CV Downloads",
                    "Unlimited AI Matched Jobs & Hunter Searches",
                    "Unlimited 1-Click Application Screening Kits",
                    "Unlimited Kanban Pipeline Job Tracking",
                    "Priority AI Processing Queue (Ultra-Fast Copilot)",
                    "🎙️ Executive Mock Interviews (Unlimited C-Level Simulations)",
                    "📹 Real-time Video Conference (Unlimited High-Priority)",
                    "Connect Custom Private Domain & SSL",
                    "All 8 Portfolio Web Architectures + Standalone HTML Export"
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
        "sprint_price": "Rs. 290",
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
                    "AI Job Hunter (2 Vacancies)",
                    "1-Click Application Copilot (1 Free Kit/day)",
                    "Job Application Tracker (Up to 2 Jobs Kanban)",
                    "AI Voice Mock Interview (3 Sessions Trial)",
                    "AI Video Conference (3 Sessions Trial)",
                    "AI Career Copilot Chat (3 Free Prompts/day)",
                    "Interactive Web Portfolio Studio (In-App Preview)",
                    "Cloud Auto-Save (Restoring drafts requires Pro)"
                ],
                "is_popular": False,
                "button_text": "Current Plan"
            },
            {
                "plan_key": "pro",
                "title": "Pro Career",
                "badge": "🔥 Best Seller",
                "price_display": "Rs. 590",
                "period_display": "/ month",
                "sub_billing_text": "or Rs. 1,590 for 3-Month Job Hunt Pass",
                "description": "Everything needed to land senior interviews with unbranded formats & live cloud sync.",
                "features": [
                    "Unlimited AI Tailoring runs",
                    "10 Classic ATS PDF Downloads / month",
                    "10 Visual Photo CV Downloads / month",
                    "Unlimited Clean Cover Letters (100% Watermark-Free)",
                    "Photo & Digital Signature Upload",
                    "Hosted Live Portfolio Subdomain (.dreemfolio.com)",
                    "Cloud Auto-Save & Instant Version Restore",
                    "🎯 Top 12 AI Matched Jobs & Tailored Recommendations",
                    "⚡ AI Job Hunter (8 Vacancies • LinkedIn Easy Apply)",
                    "🚀 1-Click Application Copilot (4 Kits / day)",
                    "📊 Job Application Tracker (Up to 5 Jobs Kanban)",
                    "🎙️ AI Voice Mock Interview (12 Sessions / month)",
                    "📹 Real-time Video Conference Coaching (12 Sessions / month)",
                    "💬 Unlimited 24/7 AI Career Copilot Chatbot"
                ],
                "is_popular": True,
                "button_text": "Upgrade to Pro (Rs. 590/mo)"
            },
            {
                "plan_key": "elite",
                "title": "Executive Elite",
                "badge": "Personal Brand",
                "price_display": "Rs. 1,950",
                "period_display": "/ month",
                "sub_billing_text": "or Rs. 4,950 for 3-Month Elite Pass",
                "description": "For Tech Leads, Architects & Executives building an elite digital brand.",
                "features": [
                    "Everything in Pro Career",
                    "Unlimited Classic ATS & Visual Photo CV Downloads",
                    "Unlimited AI Matched Jobs & Hunter Searches",
                    "Unlimited 1-Click Application Screening Kits",
                    "Unlimited Kanban Pipeline Job Tracking",
                    "Priority AI Processing Queue (Ultra-Fast Copilot)",
                    "🎙️ Executive Mock Interviews (Unlimited C-Level Simulations)",
                    "📹 Real-time Video Conference (Unlimited High-Priority)",
                    "Connect Custom Private Domain & SSL",
                    "All 8 Portfolio Web Architectures + Standalone HTML Export"
                ],
                "is_popular": False,
                "button_text": "Upgrade to Elite (Rs. 1,950/mo)"
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


def get_dynamic_pricing_context(db: Session = None) -> Dict[str, Any]:
    """
    Returns a unified dynamic pricing dictionary computed from the database.
    Used by Jinja2 templates (terms.html, landing.html, index.html) to render
    live prices with zero hardcoding across the entire SaaS.
    """
    from app.payhere import PayHereGateway

    pricing_lkr = PayHereGateway.get_all_plan_pricing(currency="LKR", db=db)
    pricing_usd = PayHereGateway.get_all_plan_pricing(currency="USD", db=db)

    pro_lkr = pricing_lkr.get("pro", 590.0)
    elite_lkr = pricing_lkr.get("elite", 1950.0)
    sprint_lkr = pricing_lkr.get("sprint", 290.0)

    pro_usd = pricing_usd.get("pro", 9.0)
    elite_usd = pricing_usd.get("elite", 19.0)
    sprint_usd = pricing_usd.get("sprint", 4.99)

    discounts = PayHereGateway.get_billing_discounts(db=db)
    d3m = discounts.get("3m", {})
    d6m = discounts.get("6m", {})
    d12m = discounts.get("12m", {})

    disc_3m_pct = int(d3m.get("discount_percent") or 0)
    disc_6m_pct = int(d6m.get("discount_percent") or 0)
    disc_12m_pct = int(d12m.get("discount_percent") or 0)

    p3m_lkr = int(PayHereGateway.get_plan_price("pro", "LKR", "3m", db=db))
    p6m_lkr = int(PayHereGateway.get_plan_price("pro", "LKR", "6m", db=db))
    p12m_lkr = int(PayHereGateway.get_plan_price("pro", "LKR", "12m", db=db))
    plt_lkr = int(PayHereGateway.get_plan_price("pro", "LKR", "lifetime", db=db))

    p3m_usd = int(PayHereGateway.get_plan_price("pro", "USD", "3m", db=db))
    p6m_usd = int(PayHereGateway.get_plan_price("pro", "USD", "6m", db=db))
    p12m_usd = int(PayHereGateway.get_plan_price("pro", "USD", "12m", db=db))
    plt_usd = int(PayHereGateway.get_plan_price("pro", "USD", "lifetime", db=db))

    elite_lt_lkr = int(PayHereGateway.get_plan_price("elite", "LKR", "lifetime", db=db))
    elite_lt_usd = int(PayHereGateway.get_plan_price("elite", "USD", "lifetime", db=db))

    return {
        "pro_price_lkr": int(pro_lkr),
        "pro_price_lkr_formatted": f"Rs. {int(pro_lkr):,}",
        "pro_price_usd": int(pro_usd),

        "elite_price_lkr": int(elite_lkr),
        "elite_price_lkr_formatted": f"Rs. {int(elite_lkr):,}",
        "elite_price_usd": int(elite_usd),

        "sprint_price_lkr": int(sprint_lkr),
        "sprint_price_lkr_formatted": f"Rs. {int(sprint_lkr):,}",
        "sprint_price_usd": sprint_usd,

        "pro_3m_lkr": p3m_lkr,
        "pro_3m_lkr_formatted": f"Rs. {p3m_lkr:,}",
        "pro_3m_usd": p3m_usd,

        "pro_6m_lkr": p6m_lkr,
        "pro_6m_lkr_formatted": f"Rs. {p6m_lkr:,}",
        "pro_6m_usd": p6m_usd,

        "pro_12m_lkr": p12m_lkr,
        "pro_12m_lkr_formatted": f"Rs. {p12m_lkr:,}",
        "pro_12m_usd": p12m_usd,

        "pro_lifetime_lkr": plt_lkr,
        "pro_lifetime_lkr_formatted": f"Rs. {plt_lkr:,}",
        "pro_lifetime_usd": plt_usd,

        "elite_lifetime_lkr": elite_lt_lkr,
        "elite_lifetime_lkr_formatted": f"Rs. {elite_lt_lkr:,}",
        "elite_lifetime_usd": elite_lt_usd,

        "disc_3m": disc_3m_pct,
        "disc_6m": disc_6m_pct,
        "disc_12m": disc_12m_pct,
    }
