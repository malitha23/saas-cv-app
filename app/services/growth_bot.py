"""
Autonomous Growth & Email Marketing Automation Bot for DreemFolio AI.
Researches database candidate states, identifies high-conversion engagement opportunities,
auto-detects language (Sinhala, English, Tamil), and delivers rate-limited promotional
campaigns during optimal conversion time windows without human intervention.
"""

import os
import re
import time
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any, Tuple

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    User, MarketingLead, GrowthBotConfig, GrowthBotLog,
    UserResume, AffiliateCommission
)
from app.email_service import send_promotional_campaign_email

logger = logging.getLogger("growth_bot")
logger.setLevel(logging.INFO)

# Sri Lanka Standard Time (UTC+5:30)
SL_TZ = timezone(timedelta(hours=5, minutes=30))
COOLDOWN_DAYS = 7
DEFAULT_DAILY_LIMIT = 25


def get_sri_lanka_time() -> datetime:
    """Returns current datetime in Sri Lanka Standard Time (UTC+5:30)."""
    return datetime.now(timezone.utc).astimezone(SL_TZ)


def get_prime_window_info() -> Dict[str, Any]:
    """
    Evaluates whether the current local time falls into high-converting email open windows:
    - Morning Prime Window: 09:30 AM - 11:30 AM (SL Time)
    - Evening Prime Window: 07:30 PM - 09:30 PM (SL Time)
    """
    now_sl = get_sri_lanka_time()
    current_time_dec = now_sl.hour + (now_sl.minute / 60.0)

    # Window 1: Morning 09:30 - 11:30 (9.5 to 11.5)
    is_morning = 9.5 <= current_time_dec < 11.5
    # Window 2: Evening 19:30 - 21:30 (19.5 to 21.5)
    is_evening = 19.5 <= current_time_dec < 21.5

    is_prime = is_morning or is_evening
    window_name = "Morning Prime (09:30 AM - 11:30 AM)" if is_morning else (
        "Evening Prime (07:30 PM - 09:30 PM)" if is_evening else "Off-Peak Sleeping"
    )

    if current_time_dec < 9.5:
        next_run = f"Today at 09:30 AM (Morning Prime)"
    elif 9.5 <= current_time_dec < 19.5:
        next_run = f"Today at 07:30 PM (Evening Prime)"
    else:
        next_run = f"Tomorrow at 09:30 AM (Morning Prime)"

    return {
        "is_prime": is_prime,
        "window_name": window_name,
        "current_sl_time": now_sl.strftime("%Y-%m-%d %I:%M:%S %p"),
        "next_scheduled_window": next_run
    }


def detect_candidate_language(name: Optional[str], email: Optional[str], phone: Optional[str] = None, location: Optional[str] = None) -> str:
    """
    Accurately auto-detects candidate's primary language:
    - 'si' (Sinhala): Sinhala Unicode script, typical Sri Lankan names/regions, or local context.
    - 'ta' (Tamil): Tamil Unicode script, prominent Tamil names/regions in Sri Lanka.
    - 'en' (English): Default for international, corporate, or neutral candidates.
    """
    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()
    combined_text = f"{clean_name} {location or ''} {clean_email}".lower()

    # 1. Sinhala Unicode Range: \u0D80-\u0DFF
    if any('\u0D80' <= c <= '\u0DFF' for c in clean_name):
        return "si"

    # 2. Tamil Unicode Range: \u0B80-\u0BFF
    if any('\u0B80' <= c <= '\u0BFF' for c in clean_name):
        return "ta"

    # 3. Specific Tamil surnames and regions in Sri Lanka
    tamil_markers = [
        "kumar", "selvam", "pillai", "nathan", "rajah", "suresh", "karthik", "lingam",
        "jaffna", "batticaloa", "vavuniya", "kilinochchi", "mannar", "trincomalee", "hatton", "nuwara eliya"
    ]
    if any(re.search(r'\b' + re.escape(m) + r'\b', combined_text) for m in tamil_markers):
        return "ta"

    # 4. Specific Sinhala surnames and regions in Sri Lanka
    sinhala_markers = [
        "perera", "silva", "fernando", "bandara", "jayasinghe", "dissanayake", "gamage",
        "senanayake", "gunasekara", "wickramasinghe", "ranasinghe", "karunaratne", "peiris",
        "colombo", "kandy", "galle", "matara", "gampaha", "kurunegala", "kalutara", "anuradhapura", "ratnapura"
    ]
    if any(re.search(r'\b' + re.escape(m) + r'\b', combined_text) for m in sinhala_markers):
        return "si"

    # 5. Sri Lankan phone code (+94 / 07x) with local identity defaults to Sinhala
    if phone and ("+94" in phone or phone.startswith("07")):
        return "si"

    return "en"


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-CONVERTING MULTILINGUAL EMAIL COPY TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────
BOT_CAMPAIGN_TEMPLATES = {
    # ── 1. AFFILIATE & CASH COMMISSION BOOSTER ─────────────────────────────
    "affiliate_earning": {
        "si": {
            "subject": "💸 {name}, DreemFolio එකෙන් යාළුවන්ට Share කරලා 20% Cash Earn කරන්න පටන් ගන්න!",
            "headline": "💰 Refer Friends & Earn 20% Cash Commissions Direct to Your Bank!",
            "cta_text": "💰 Start Earning Cash Now →",
            "cta_url": "https://www.dreemfolio.com/profile#affiliate",
            "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>DreemFolio AI වෙත සාදරයෙන් පිළිගනිමු! 🎉</p>
<p>ඔබ දන්නවාද? ඔබේ CV එක සාදා ගැනීමට අමතරව, ඔබගේ මිතුරන්ට, University Batch mates ලාට හෝ Job සොයන අයට DreemFolio Refer කර <strong>සැබෑ මුදල් (Cash Commissions)</strong> උපයා ගැනීමේ අවස්ථාව දැන් ඔබට හිමිවී තිබේ!</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #38bdf8; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    💵 කොහොමද මුදල් උපයන්නේ? (Easy 4 Steps)
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>🔗 <strong>1. ඔබේ Link එක ගන්න:</strong> Dashboard එකේ <em>Affiliate / Partner</em> tab එකෙන් ඔබේ unique referral link එක copy කරගන්න.</li>
    <li>📲 <strong>2. Share කරන්න:</strong> WhatsApp, Telegram හෝ Social Media හරහා friends & classmates ලාට share කරන්න.</li>
    <li>🎁 <strong>3. Free Downloads & Cash:</strong>
      <ul style="margin-top: 4px; padding-left: 15px;">
        <li>කවුරුන් හෝ Register වූ සැණින් ඔබට <strong>+1 Free ATS CV Download</strong> එකක් නොමිලේ!</li>
        <li>ඔවුන් Paid Plan එකකට Upgrade කළ විට, එම මුදලින් <strong>20% Instant Cash Commission</strong> එකක් ක්ෂණිකව ඔබේ Wallet එකට!</li>
      </ul>
    </li>
    <li>🏦 <strong>4. Direct Bank Withdrawal:</strong> උපයන මුදල් කෙළින්ම ඔබේ ශ්‍රී ලාංකික ඕනෑම බැංකු ගිණුමකට Withdraw කරගන්න (Min. LKR 2,000).</li>
  </ul>
</div>
<p style="font-size: 13px; color: #cbd5e1;">
  💡 රැකියා සොයන ඔබේ මිතුරන්ටත් Recruiter-Approved Professional CV එකක් හදාගන්න උදව් වෙන ගමන්, අදම ඔබේ Referral Link එක Share කර අමතර ආදායමක් උපයා ගන්න පටන් ගන්න!
</p>
"""
        },
        "en": {
            "subject": "💰 {name}, Earn 20% Cash Commissions by Referring Classmates & Colleagues!",
            "headline": "💸 Turn Your Career Network into Direct Cash with DreemFolio Partner Program",
            "cta_text": "💰 Get My Referral Link & Start Earning →",
            "cta_url": "https://www.dreemfolio.com/profile#affiliate",
            "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Welcome to DreemFolio AI! Did you know you can earn real cash income simply by introducing job-seeking classmates and colleagues to our career platform?</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #38bdf8; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    💵 How You Earn in 3 Easy Steps:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>🔗 <strong>1. Grab Your Personal Link:</strong> Visit your DreemFolio Profile & click the <em>Affiliate / Partner</em> tab.</li>
    <li>📲 <strong>2. Share with Friends:</strong> Post or send via WhatsApp, LinkedIn, or university groups.</li>
    <li>🎁 <strong>3. Instant Rewards:</strong>
      <ul style="margin-top: 4px; padding-left: 15px;">
        <li>Get <strong>+1 Free ATS CV Download</strong> whenever someone signs up with your link.</li>
        <li>Earn an immediate <strong>20% Cash Commission</strong> when they upgrade to any paid package!</li>
      </ul>
    </li>
    <li>🏦 <strong>4. Local Bank Transfer:</strong> Withdraw your commissions directly to any Sri Lankan bank account (Min. LKR 2,000).</li>
  </ul>
</div>
<p style="font-size: 13px; color: #cbd5e1;">
  Help your network build recruiter-ready resumes while creating a sustainable extra income stream today.
</p>
"""
        },
        "ta": {
            "subject": "💸 {name}, DreemFolio மூலம் நண்பர்களை அழைத்து 20% நேரடி கமிஷன் பெறுங்கள்!",
            "headline": "💰 நண்பர்களை அழைத்து உங்கள் வங்கிக் கணக்கில் நேரடி பண வெகுமதிகளைப் பெறுங்கள்!",
            "cta_text": "💰 எனது பரிந்துரை இணைப்பைப் பெறுங்கள் →",
            "cta_url": "https://www.dreemfolio.com/profile#affiliate",
            "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>DreemFolio AI-க்கு நல்வரவு! வேலை தேடும் உங்கள் நண்பர்கள் மற்றும் சக ஊழியர்களுக்கு DreemFolio-ஐ பரிந்துரைத்து <strong>நேரடி பண கமிஷன்களை (20% Cash Commission)</strong> சம்பாதிக்க முடியும் என்பது உங்களுக்குத் தெரியுமா?</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #38bdf8; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    💵 எவ்வாறு சம்பாதிப்பது? (எளிய படிகள்)
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>🔗 <strong>1. உங்கள் இணைப்பைப் பெறுங்கள்:</strong> Dashboard-இல் <em>Affiliate / Partner</em> பகுதிக்குச் சென்று உங்கள் பரிந்துரை இணைப்பை நகலெடுக்கவும்.</li>
    <li>📲 <strong>2. பகிருங்கள்:</strong> WhatsApp, Telegram அல்லது சமூக ஊடகங்களில் பகிருங்கள்.</li>
    <li>🎁 <strong>3. உடனடி நன்மைகள்:</strong>
      <ul style="margin-top: 4px; padding-left: 15px;">
        <li>யாரேனும் பதிவு செய்தால் உங்களுக்கு <strong>+1 இலவச ATS CV Download</strong> கிடைக்கும்!</li>
        <li>அவர்கள் கட்டணத் திட்டத்திற்கு மாறும்போது <strong>20% நேரடி கமிஷன்</strong> உடனடியாக உங்கள் வாலட்டுக்கு வந்து சேரும்!</li>
      </ul>
    </li>
    <li>🏦 <strong>4. வங்கிக்கு மாற்றுங்கள்:</strong> இலங்கையின் எந்தவொரு வங்கிக் கணக்கிற்கும் உங்கள் பணத்தை நேரடியாகப் பெறலாம் (Min. LKR 2,000).</li>
  </ul>
</div>
"""
        }
    },

    # ── 2. ATS CV SCORE & RESUME COMPLETION BOOSTER ─────────────────────────
    "ats_resume": {
        "si": {
            "subject": "📄 {name}, ඔබේ CV එකේ ATS Score එක නොමිලේ පරීක්ෂා කර සම්පූර්ණ කරගන්න!",
            "headline": "🎯 75% ක Scanners පරදවා Shortlist වීමට Recruiter-Approved ATS CV එකක්!",
            "cta_text": "🎯 මගේ ATS Score එක නොමිලේ බලන්න →",
            "cta_url": "https://www.dreemfolio.com/ats-resume-checker",
            "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>ඔබ රැකියාවලට අයදුම් කරන විට ඔබේ CV එක Recruiter කෙනෙකු අතට පත්වීමට පෙර Automated ATS Scanners (Taleo, Workday) මගින් 75% ක්ම ඉවත් වන බව ඔබ දන්නවාද?</p>
<p>DreemFolio AI හරහා ඔබේ CV එකට ලැබෙන Real-Time ATS Score එක සහ අඩුවැඩිකම් තත්පර 10කින් නොමිලේම බලාගත හැක.</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #a78bfa; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    ✨ DreemFolio ATS CV එකක විශේෂතා:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>📄 <strong>Single-Column Scannable Layouts:</strong> Scanners වලට 100% ක් නිවැරදිව කියවිය හැකි පිරිසිදු ආකෘති.</li>
    <li>🎯 <strong>Industry Keywords Matching:</strong> ඔබ ඉල්ලුම් කරන රැකියාවට ගැළපෙන ප්‍රධාන keywords AI මගින් ඇතුළත් කිරීම.</li>
    <li>🚀 <strong>1-Click AI Tailoring:</strong> ඕනෑම Job Description එකකට තත්පර ගණනකින් ඔබේ CV එක ගළපා ගැනීම.</li>
  </ul>
</div>
<p style="font-size: 13px; color: #cbd5e1;">අදම ඔබේ නොමිලේ ATS Score එක ලබාගෙන ඉහළම රැකියා සම්මුඛ පරීක්ෂණ අවස්ථා දිනාගන්න!</p>
"""
        },
        "en": {
            "subject": "🎯 {name}, Boost Your Interview Calls with a Recruiter-Approved ATS Resume!",
            "headline": "📄 Beat the 75% Automated Rejection Rate with AI-Optimized Keywords",
            "cta_text": "Check Your ATS Score Free →",
            "cta_url": "https://www.dreemfolio.com/ats-resume-checker",
            "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Did you know that over 75% of resumes are filtered out by automated Applicant Tracking Systems before a hiring manager ever sees them?</p>
<p>DreemFolio AI analyzes your credentials against real corporate recruitment criteria to ensure your resume scores 85%+ on ATS benchmarks.</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #a78bfa; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    ✨ Why Candidates Land Interviews Faster:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>📄 <strong>Clean Single-Column Vector PDFs:</strong> Fully legible by Taleo, Workday, Greenhouse, and LinkedIn jobs.</li>
    <li>🎯 <strong>Targeted Keyword Placement:</strong> Matches essential competencies for your exact career level.</li>
    <li>⚡ <strong>Live Instant Feedback:</strong> Spot missing qualifications and formatting issues in under 10 seconds.</li>
  </ul>
</div>
"""
        },
        "ta": {
            "subject": "📄 {name}, உங்கள் CV-இன் ATS Score-ஐ இலவசமாகப் பெற்று உடனடி வேலை வாய்ப்பைப் பெறுங்கள்!",
            "headline": "🎯 வேலை வாய்ப்புகளை அதிகரிக்க தானியங்கி ATS-அங்கீகரிக்கப்பட்ட CV!",
            "cta_text": "இலவச ATS Score-ஐ சோதிக்கவும் →",
            "cta_url": "https://www.dreemfolio.com/ats-resume-checker",
            "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>75%-க்கும் மேற்பட்ட ரெஸ்யூம்கள் ஆட்சேர்ப்பு மேலாளர்களை சென்றடைவதற்கு முன்பே கணினி அமைப்புகளால் (ATS) நிராகரிக்கப்படுகின்றன என்பது உங்களுக்குத் தெரியுமா?</p>
<p>DreemFolio AI மூலம் உங்கள் தற்போதைய CV-இன் தரத்தை உடனடியாகச் சரிபார்த்து சிறந்த ATS தரநிலையைப் பெறுங்கள்.</p>
"""
        }
    },

    # ── 3. LIVE WEB PORTFOLIO LAUNCH BOOSTER ────────────────────────────────
    "portfolio_launch": {
        "si": {
            "subject": "🌐 {name}, ඔබේ Live Portfolio Website එක තත්පර 15කින් නොමිලේ Publish කරගන්න!",
            "headline": "🚀 සාම්ප්‍රදායික CV වලට එහා ගිය Interactive Web Portfolio එකක්!",
            "cta_text": "🌐 මගේ Portfolio එක Live දාන්න →",
            "cta_url": "https://www.dreemfolio.com/dashboard",
            "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>රැකියාවලට අයදුම් කරන විට සාම්ප්‍රදායික PDF CV එකක් පමණක් යවනවාට වඩා, ඔබේම නමින් යුත් **Live Web Portfolio Link එකක් (dreemfolio.com/p/yourname)** යොමු කළහොත් Recruiters ලාගේ අවධානය 10 ගුණයකින් දිනාගත හැක!</p>
<p>DreemFolio Studio හරහා ඔබගේ Projects, Certificates සහ Skills ඇතුළත් ලස්සන, Mobile-Friendly Portfolio එකක් 1-Click එකෙන් නොමිලේම Live Host කරගත හැක.</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #38bdf8; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    ✨ Live Portfolio එකක වාසි:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>📱 <strong>100% Mobile & Tablet Responsive:</strong> ඕනෑම දුරකථනයකින් සුපිරියට පෙනෙන අලංකාර නිර්මාණ.</li>
    <li>🔗 <strong>Verified Digital Credentials:</strong> ඔබගේ සහතික සහ Interactive Projects සජීවීව පෙන්වීමේ හැකියාව.</li>
    <li>💼 <strong>LinkedIn & WhatsApp Share Ready:</strong> 1-Click එකෙන් ඕනෑම තැනකට share කළ හැකි සෘජු Link එක.</li>
  </ul>
</div>
<p style="font-size: 13px; color: #cbd5e1;">අදම ඔබේ Dashboard එකට ගොස් ඔබේ Live Portfolio එක Publish කරගන්න!</p>
"""
        },
        "en": {
            "subject": "🚀 {name}, Launch Your Interactive Web Portfolio in 15 Seconds!",
            "headline": "🌐 Stand Out from Hundreds of Candidates with a Live Career Portfolio",
            "cta_text": "Publish My Portfolio Now →",
            "cta_url": "https://www.dreemfolio.com/dashboard",
            "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>In modern recruitment, candidates who provide a live, interactive web portfolio link alongside their PDF resume get up to 3x higher interview response rates.</p>
<p>DreemFolio automatically turns your credentials and project highlights into an animated, mobile-responsive portfolio site (dreemfolio.com/p/your-name) in under 15 seconds.</p>
"""
        },
        "ta": {
            "subject": "🌐 {name}, உங்கள் நேரடி வலை போர்ட்ஃபோலியோவை 15 வினாடிகளில் வெளியிடுங்கள்!",
            "headline": "🚀 வேலை வாய்ப்புகளை எளிதில் பெற உங்களுக்கென ஒரு நேரடி வலைப்பக்கம்!",
            "cta_text": "போர்ட்ஃபோலியோவை வெளியிடவும் →",
            "cta_url": "https://www.dreemfolio.com/dashboard",
            "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>சாதாரண PDF CV-யை விட உங்கள் சொந்த நேரடி வலை போர்ட்ஃபோலியோ (Live Web Portfolio) மூலம் முதலாளிகளின் கவனத்தை எளிதில் ஈர்க்க முடியும்.</p>
"""
        }
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_or_create_growth_bot_config(db: Session) -> GrowthBotConfig:
    """Retrieves singleton GrowthBotConfig record or creates it with safe defaults."""
    cfg = db.scalars(select(GrowthBotConfig).where(GrowthBotConfig.id == 1)).first()
    if not cfg:
        cfg = GrowthBotConfig(
            id=1,
            is_enabled=False,  # Safe default: Disabled until Admin enables it
            daily_limit=DEFAULT_DAILY_LIMIT,
            sent_today=0,
            last_reset_date=get_sri_lanka_time().strftime("%Y-%m-%d"),
            preferred_language="auto",
            enable_affiliate_booster=True,
            enable_resume_booster=True,
            enable_portfolio_booster=True,
            last_run_status="Initialized. Bot is paused."
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def reset_daily_limits_if_needed(cfg: GrowthBotConfig, db: Session):
    """Resets daily sent counter if day rolled over in Sri Lanka time (UTC+5:30)."""
    today_str = get_sri_lanka_time().strftime("%Y-%m-%d")
    if cfg.last_reset_date != today_str:
        cfg.sent_today = 0
        cfg.last_reset_date = today_str
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# CANDIDATE RESEARCH ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def research_system_candidates(db: Session, limit: int = 100, force_fresh: bool = False) -> List[Dict[str, Any]]:
    """
    Intelligently analyzes the database to find eligible candidates for marketing outreach:
    1. Checks cooldown period (7 days in normal autonomous mode, 12 hours when manually triggered).
    2. Excludes active paid users (Pro/Executive) and admin users.
    3. Excludes unsubscribed and bounced leads.
    4. Categorizes candidate into optimal segment:
       - 'affiliate_earning' (0 referrals)
       - 'ats_resume' (0 resumes or downloads)
       - 'portfolio_launch' (has resume but portfolio not live)
    5. Auto-detects preferred language (Sinhala, English, Tamil).
    """
    cooldown_hours = 12 if force_fresh else (COOLDOWN_DAYS * 24)
    cutoff_time = datetime.utcnow() - timedelta(hours=cooldown_hours)
    candidates = []

    # 1. Inspect registered Users first (High intent non-admin users)
    users_stmt = (
        select(User)
        .where(
            User.is_active.isnot(False),
            User.is_admin.isnot(True),
            or_(
                User.plan_tier == "free",
                User.plan_tier == None,
                User.plan_tier == "",
                User.plan_tier == "starter"
            )
        )
        .order_by(desc(User.created_at))
        .limit(limit)
    )
    users = db.scalars(users_stmt).all()

    for u in users:
        # Check recent dispatch logs
        recent_log = db.scalars(
            select(GrowthBotLog)
            .where(
                GrowthBotLog.recipient_email == u.email,
                GrowthBotLog.action == "dispatched",
                GrowthBotLog.created_at >= cutoff_time
            )
        ).first()
        if recent_log:
            continue

        # Check MarketingLead last_sent_at if synced
        mlead = db.scalars(select(MarketingLead).where(MarketingLead.email == u.email)).first()
        if mlead and mlead.status == "unsubscribed":
            continue
        if mlead and mlead.last_sent_at and mlead.last_sent_at >= cutoff_time:
            continue

        # Determine best segment
        resume_count = db.scalar(select(func.count(UserResume.id)).where(UserResume.user_id == u.id)) or 0
        ref_count = u.referral_bonus_downloads or 0

        # Segment assignment priority
        if ref_count == 0:
            segment = "affiliate_earning"
        elif resume_count == 0 or (u.lifetime_ats_downloads_count == 0):
            segment = "ats_resume"
        else:
            segment = "portfolio_launch"

        lang = detect_candidate_language(u.full_name, u.email)
        candidates.append({
            "source_type": "user",
            "id": u.id,
            "email": u.email,
            "name": u.full_name or "Candidate",
            "segment": segment,
            "detected_lang": lang,
            "referrals": ref_count,
            "resumes": resume_count
        })

    # 2. Inspect MarketingLeads that are not registered users
    leads_stmt = (
        select(MarketingLead)
        .where(
            MarketingLead.status.notin_(["unsubscribed", "bounced"]),
            or_(
                MarketingLead.last_sent_at == None,
                MarketingLead.last_sent_at < cutoff_time
            )
        )
        .order_by(MarketingLead.send_count.asc(), desc(MarketingLead.created_at))
        .limit(limit)
    )
    leads = db.scalars(leads_stmt).all()

    existing_emails = {c["email"] for c in candidates}
    for l in leads:
        if l.email in existing_emails:
            continue

        # Check recent log
        recent_log = db.scalars(
            select(GrowthBotLog)
            .where(
                GrowthBotLog.recipient_email == l.email,
                GrowthBotLog.action == "dispatched",
                GrowthBotLog.created_at >= cutoff_time
            )
        ).first()
        if recent_log:
            continue

        lang = detect_candidate_language(l.name, l.email, phone=l.phone)
        candidates.append({
            "source_type": "marketing_lead",
            "id": l.id,
            "email": l.email,
            "name": l.name or "Candidate",
            "segment": "ats_resume",  # Leads prioritize discovering the ATS resume tool
            "detected_lang": lang,
            "referrals": 0,
            "resumes": 0
        })

    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT & DISPATCH EXECUTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def run_growth_bot_audit(db: Session) -> Dict[str, Any]:
    """
    Simulates a comprehensive research audit without sending any emails.
    Returns counts by segment, language breakdown, and sample eligible leads.
    """
    cfg = get_or_create_growth_bot_config(db)
    reset_daily_limits_if_needed(cfg, db)
    window_info = get_prime_window_info()

    eligible = research_system_candidates(db, limit=150)
    by_segment = {"affiliate_earning": 0, "ats_resume": 0, "portfolio_launch": 0}
    by_lang = {"si": 0, "en": 0, "ta": 0}

    for c in eligible:
        seg = c["segment"]
        if seg in by_segment:
            by_segment[seg] += 1
        lang = c["detected_lang"]
        if lang in by_lang:
            by_lang[lang] += 1

    audit_summary = (
        f"Audited system state: {len(eligible)} eligible candidates identified "
        f"({by_segment['affiliate_earning']} Affiliate, {by_segment['ats_resume']} ATS CV, {by_segment['portfolio_launch']} Portfolio). "
        f"Languages: {by_lang['si']} Sinhala, {by_lang['en']} English, {by_lang['ta']} Tamil."
    )

    log_entry = GrowthBotLog(
        action="audit",
        details=audit_summary
    )
    db.add(log_entry)
    cfg.last_run_at = datetime.utcnow()
    cfg.last_run_status = audit_summary
    db.commit()

    return {
        "status": "success",
        "is_enabled": cfg.is_enabled,
        "daily_limit": cfg.daily_limit,
        "sent_today": cfg.sent_today,
        "remaining_today": max(0, cfg.daily_limit - cfg.sent_today),
        "window_info": window_info,
        "total_eligible_candidates": len(eligible),
        "by_segment": by_segment,
        "by_language": by_lang,
        "samples": eligible[:10],
        "summary": audit_summary
    }


def execute_growth_bot_cycle(db: Session, force_now: bool = False, max_to_send: int = 5) -> Dict[str, Any]:
    """
    Executes an autonomous email outreach dispatch cycle:
    - Enforces is_enabled check (unless force_now=True).
    - Enforces Prime Window check (unless force_now=True).
    - Enforces daily rate-limit (sent_today < daily_limit).
    - Respects 7-day cooldown per candidate.
    - Employs gentle delays between sends to ensure pristine deliverability (inbox, not spam).
    """
    cfg = get_or_create_growth_bot_config(db)
    reset_daily_limits_if_needed(cfg, db)
    window_info = get_prime_window_info()

    if not cfg.is_enabled and not force_now:
        return {
            "status": "skipped",
            "reason": "Bot is currently paused/disabled by Administrator.",
            "window_info": window_info
        }

    if not window_info["is_prime"] and not force_now:
        return {
            "status": "skipped",
            "reason": f"Outside prime open-rate window ({window_info['window_name']}). Next run scheduled for {window_info['next_scheduled_window']}.",
            "window_info": window_info
        }

    available_quota = max(0, cfg.daily_limit - cfg.sent_today)
    if available_quota <= 0:
        return {
            "status": "skipped",
            "reason": f"Daily limit reached ({cfg.sent_today}/{cfg.daily_limit} sent today). Will resume tomorrow.",
            "window_info": window_info
        }

    batch_limit = min(max_to_send, available_quota)
    eligible = research_system_candidates(db, limit=50, force_fresh=force_now)

    # Filter by enabled segment flags in config
    filtered = []
    for c in eligible:
        seg = c["segment"]
        if seg == "affiliate_earning" and not cfg.enable_affiliate_booster:
            continue
        if seg == "ats_resume" and not cfg.enable_resume_booster:
            continue
        if seg == "portfolio_launch" and not cfg.enable_portfolio_booster:
            continue
        filtered.append(c)

    if not filtered:
        status_msg = "Research complete: No eligible candidates require engagement right now (all in 7-day cooldown or reached)."
        cfg.last_run_at = datetime.utcnow()
        cfg.last_run_status = status_msg
        db.commit()
        return {"status": "idle", "sent_count": 0, "message": status_msg, "window_info": window_info}

    batch = filtered[:batch_limit]
    sent_count = 0
    failed_count = 0

    for cand in batch:
        target_lang = cfg.preferred_language if cfg.preferred_language != "auto" else cand["detected_lang"]
        seg = cand["segment"]
        templates_for_seg = BOT_CAMPAIGN_TEMPLATES.get(seg, BOT_CAMPAIGN_TEMPLATES["ats_resume"])
        tpl = templates_for_seg.get(target_lang, templates_for_seg["en"])

        rendered_subject = tpl["subject"].format(name=cand["name"])
        rendered_body = tpl["body"].format(name=cand["name"])

        try:
            ok = send_promotional_campaign_email(
                to_email=cand["email"],
                subject=rendered_subject,
                name=cand["name"],
                headline=tpl["headline"],
                message_body=rendered_body,
                cta_text=tpl["cta_text"],
                cta_url=tpl["cta_url"]
            )
            if ok:
                sent_count += 1
                cfg.sent_today += 1

                # Record audit log
                log_entry = GrowthBotLog(
                    action="dispatched",
                    recipient_email=cand["email"],
                    recipient_name=cand["name"],
                    segment=seg,
                    language=target_lang,
                    subject=rendered_subject,
                    details=f"Successfully dispatched {seg} booster in {target_lang}."
                )
                db.add(log_entry)

                # Sync MarketingLead last_sent_at
                mlead = db.scalars(select(MarketingLead).where(MarketingLead.email == cand["email"])).first()
                if mlead:
                    mlead.last_sent_at = datetime.utcnow()
                    mlead.send_count = (mlead.send_count or 0) + 1
                    mlead.status = "sent"

                db.commit()
                # Friendly delay between sends to protect SMTP reputation
                time.sleep(1.5)
            else:
                failed_count += 1
                db.add(GrowthBotLog(
                    action="error",
                    recipient_email=cand["email"],
                    recipient_name=cand["name"],
                    segment=seg,
                    language=target_lang,
                    details="SMTP returned False or delivery failure."
                ))
                db.commit()
        except Exception as e:
            failed_count += 1
            logger.error("Error dispatching bot email to %s: %s", cand["email"], e)
            db.add(GrowthBotLog(
                action="error",
                recipient_email=cand["email"],
                recipient_name=cand["name"],
                segment=seg,
                language=target_lang,
                details=str(e)
            ))
            db.commit()

    cycle_status = f"Dispatched {sent_count} emails ({failed_count} failed) at {window_info['current_sl_time']}. Sent today: {cfg.sent_today}/{cfg.daily_limit}."
    cfg.last_run_at = datetime.utcnow()
    cfg.last_run_status = cycle_status
    db.commit()

    return {
        "status": "success",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "sent_today": cfg.sent_today,
        "daily_limit": cfg.daily_limit,
        "message": cycle_status,
        "window_info": window_info
    }


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND ASYNC WORKER LOOP
# ─────────────────────────────────────────────────────────────────────────────
_bot_worker_active = True

async def growth_bot_worker_loop():
    """
    Standing background daemon loop running every 5 minutes (300 seconds).
    Checks if bot is enabled and within prime delivery windows, then executes
    a gentle outreach batch safely.
    """
    global _bot_worker_active
    logger.info("🤖 Autonomous Growth Bot daemon worker started.")

    while _bot_worker_active:
        try:
            # Check every 5 minutes
            await asyncio.sleep(300)

            # Run cycle inside thread to avoid blocking event loop
            def _run_tick():
                with SessionLocal() as db:
                    cfg = get_or_create_growth_bot_config(db)
                    if not cfg.is_enabled:
                        return
                    w_info = get_prime_window_info()
                    if not w_info["is_prime"]:
                        return
                    execute_growth_bot_cycle(db, force_now=False, max_to_send=5)

            await asyncio.to_thread(_run_tick)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in growth bot background daemon loop: %s", e)
            await asyncio.sleep(60)
