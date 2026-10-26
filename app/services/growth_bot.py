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


def parse_time_str_to_dec(time_str: str, default: float) -> float:
    try:
        parts = str(time_str).strip().split(":")
        return float(parts[0]) + (float(parts[1]) / 60.0)
    except Exception:
        return default

def format_time_str_to_ampm(time_str: str, default: str) -> str:
    try:
        parts = str(time_str).strip().split(":")
        h = int(parts[0])
        m = int(parts[1])
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        return f"{h12:02d}:{m:02d} {suffix}"
    except Exception:
        return default

def get_prime_window_info(cfg: Optional[GrowthBotConfig] = None) -> Dict[str, Any]:
    """
    Evaluates whether the current local time falls into high-converting email open windows:
    Supports custom configured morning & evening start/end hours from GrowthBotConfig.
    """
    now_sl = get_sri_lanka_time()
    current_time_dec = now_sl.hour + (now_sl.minute / 60.0)

    m_start_str = getattr(cfg, "morning_window_start", "09:30") or "09:30"
    m_end_str = getattr(cfg, "morning_window_end", "11:30") or "11:30"
    e_start_str = getattr(cfg, "evening_window_start", "19:30") or "19:30"
    e_end_str = getattr(cfg, "evening_window_end", "21:30") or "21:30"

    m_start = parse_time_str_to_dec(m_start_str, 9.5)
    m_end = parse_time_str_to_dec(m_end_str, 11.5)
    e_start = parse_time_str_to_dec(e_start_str, 19.5)
    e_end = parse_time_str_to_dec(e_end_str, 21.5)

    is_morning = m_start <= current_time_dec < m_end
    is_evening = e_start <= current_time_dec < e_end
    is_prime = is_morning or is_evening

    m_start_ampm = format_time_str_to_ampm(m_start_str, "09:30 AM")
    m_end_ampm = format_time_str_to_ampm(m_end_str, "11:30 AM")
    e_start_ampm = format_time_str_to_ampm(e_start_str, "07:30 PM")
    e_end_ampm = format_time_str_to_ampm(e_end_str, "09:30 PM")

    window_name = f"Morning Prime ({m_start_ampm} - {m_end_ampm})" if is_morning else (
        f"Evening Prime ({e_start_ampm} - {e_end_ampm})" if is_evening else "Off-Peak Sleeping"
    )

    if current_time_dec < m_start:
        next_run = f"Today at {m_start_ampm} (Morning Prime)"
    elif m_start <= current_time_dec < e_start:
        next_run = f"Today at {e_start_ampm} (Evening Prime)"
    else:
        next_run = f"Tomorrow at {m_start_ampm} (Morning Prime)"

    return {
        "is_prime": is_prime,
        "window_name": window_name,
        "current_sl_time": now_sl.strftime("%Y-%m-%d %I:%M:%S %p"),
        "next_scheduled_window": next_run,
        "morning_window_start": m_start_str,
        "morning_window_end": m_end_str,
        "evening_window_start": e_start_str,
        "evening_window_end": e_end_str,
        "morning_display": f"{m_start_ampm} - {m_end_ampm}",
        "evening_display": f"{e_start_ampm} - {e_end_ampm}"
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
# HIGH-CONVERTING MULTILINGUAL EMAIL COPY TEMPLATES WITH ROTATING TITLE VARIANTS
# ─────────────────────────────────────────────────────────────────────────────
BOT_CAMPAIGN_TEMPLATES = {
    # ── 1. AFFILIATE & CASH COMMISSION BOOSTER ─────────────────────────────
    "affiliate_earning": {
        "si": {
            "variants": [
                {
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
                {
                    "subject": "💵 {name}, ඔබගේ යාළුවන්ට උදව් කරමින් අමතර මාසික ආදායමක් උපයන්න (LKR 2,000+ Daily)",
                    "headline": "🎁 Share Your Career Link & Get Free Downloads + Instant Bank Cash!",
                    "cta_text": "💵 View My Referral Earnings →",
                    "cta_url": "https://www.dreemfolio.com/profile#affiliate",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>CV එකක් හදන, Job හොයන යාළුවන් ඔබ වටා ඕනෑතරම් ඉන්නවා නේද? ඔවුන්ට DreemFolio AI හඳුන්වා දී <strong>20% Direct Cash Commission</strong> එකක් ලබා ගන්න!</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #38bdf8; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    ⚡ Instant Cash Rewards:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>🔥 Sign-up වෙන හැම කෙනෙකුටම ඔබට +1 Free Download</li>
    <li>💳 ඕනෑම Paid Subscription එකකින් 20% ක්ෂණික මුදල් කොමිස්</li>
    <li>🏦 Local Bank Transfer (Commercial, BOC, Sampath, HNB ආදී ඕනෑම බැංකුවකට)</li>
  </ul>
</div>
"""
                },
                {
                    "subject": "🚀 {name}, Batch Mates ලාට DreemFolio Refer කරලා Wallet එකට Cash ගන්න",
                    "headline": "💸 Earn 20% on Every Single Paid Plan Referral — 100% Guaranteed Payouts",
                    "cta_text": "🚀 Copy My Referral Link Now →",
                    "cta_url": "https://www.dreemfolio.com/profile#affiliate",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>DreemFolio Affiliate Community එකට එකතු වී ඔබේ WhatsApp Groups, LinkedIn Network එක හරහා පහසුවෙන්ම අමතර මුදලක් උපයා ගන්න අදම පටන් ගන්න.</p>
"""
                }
            ]
        },
        "en": {
            "variants": [
                {
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
    <li>🎁 <strong>3. Instant Rewards:</strong> Get <strong>+1 Free ATS CV Download</strong> on every signup + <strong>20% Cash Commission</strong> on every upgrade!</li>
    <li>🏦 <strong>4. Local Bank Transfer:</strong> Direct payouts to any Sri Lankan bank account (Min. LKR 2,000).</li>
  </ul>
</div>
"""
                },
                {
                    "subject": "💵 {name}, Turn Job-Seeking Friends into Daily Income (20% Cash Booster)",
                    "headline": "🚀 Earn 20% Cash on Every CV & Portfolio Upgrade from Your Network",
                    "cta_text": "Start Earning Direct Cash →",
                    "cta_url": "https://www.dreemfolio.com/profile#affiliate",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Help your friends build recruiter-ready resumes while creating a sustainable extra income stream today with DreemFolio's 20% partner program.</p>
"""
                }
            ]
        },
        "ta": {
            "variants": [
                {
                    "subject": "💸 {name}, DreemFolio மூலம் நண்பர்களை அழைத்து 20% நேரடி கமிஷன் பெறுங்கள்!",
                    "headline": "💰 நண்பர்களை அழைத்து உங்கள் வங்கிக் கணக்கில் நேரடி பண வெகுமதிகளைப் பெறுங்கள்!",
                    "cta_text": "💰 எனது பரிந்துரை இணைப்பைப் பெறுங்கள் →",
                    "cta_url": "https://www.dreemfolio.com/profile#affiliate",
                    "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>DreemFolio AI-க்கு நல்வரவு! வேலை தேடும் உங்கள் நண்பர்களுக்கு DreemFolio-ஐ பரிந்துரைத்து <strong>20% நேரடி பண கமிஷனை</strong> உங்கள் வங்கிக் கணக்கில் உடனடியாகப் பெறுங்கள்.</p>
"""
                }
            ]
        }
    },

    # ── 2. ATS CV SCORE & RESUME COMPLETION BOOSTER ─────────────────────────
    "ats_resume": {
        "si": {
            "variants": [
                {
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
                {
                    "subject": "🤦‍♂️ {name}, CVs 50ක් යවලා එක Interview එකකටවත් Reply එකක් ආවේ නැද්ද? මෙන්න හේතුව",
                    "headline": "🛑 Automated ATS Filters Stop Your CV Before HR Even Opens It — Fix It in 10s",
                    "cta_text": "⚡ Fix My CV with AI Now →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>සෑම සතියකම Job Sites වල manual විදියට CVs දුසිම් ගණන් යැව්වත් interview එකකටවත් කතා කරන්නේ නැති එක ගැන ඔබත් කලකිරිලාද? 🤦‍♂️</p>
<p>වරද ඔබගේ සුදුසුකම් වල නොවේ — බොහෝ සමාගම් වල HR බලන්නේ නැතිව AI Bots ලා මඟින් CVs Reject කිරීමයි. DreemFolio හි Recruiter-Engineered Single-Column Formats මඟින් 95%+ ATS Compliance එකක් තත්පරයෙන් හිමිවේ!</p>
"""
                },
                {
                    "subject": "⚡ {name}, Recruiter කෙනෙක් ඔබේ CV එක බලන්න ගත කරන්නේ තත්පර 6යි!",
                    "headline": "📄 Match Top Industry Keywords & Pass ATS with a 95%+ Match Score",
                    "cta_text": "🔍 Optimize My Resume Score →",
                    "cta_url": "https://www.dreemfolio.com/ats-resume-checker",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Recruiters ලා තත්පර 6ක් ඇතුළත ඔබේ CV එක Shortlist කරන විද්‍යාත්මක ආකෘතියට අදම මාරු වන්න. DreemFolio AI ඔබගේ qualifications වලට හරියන keywords auto-embed කර දෙයි.</p>
"""
                }
            ]
        },
        "en": {
            "variants": [
                {
                    "subject": "🎯 {name}, Boost Your Interview Calls with a Recruiter-Approved ATS Resume!",
                    "headline": "📄 Beat the 75% Automated Rejection Rate with AI-Optimized Keywords",
                    "cta_text": "Check Your ATS Score Free →",
                    "cta_url": "https://www.dreemfolio.com/ats-resume-checker",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Did you know that over 75% of resumes are filtered out by automated Applicant Tracking Systems before a hiring manager ever sees them?</p>
<p>DreemFolio AI analyzes your credentials against real corporate recruitment criteria to ensure your resume scores 85%+ on ATS benchmarks.</p>
"""
                },
                {
                    "subject": "🤦‍♂️ Sent 50 Resumes with Zero Interview Replies? {name}, Here is Why",
                    "headline": "⚡ Fix Your Resume ATS Score in 10 Seconds & Land Global Calls",
                    "cta_text": "Audit My Resume Now →",
                    "cta_url": "https://www.dreemfolio.com/ats-resume-checker",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Stop sending unoptimized resumes into the corporate black hole. Generate an ATS-compliant, single-column vector PDF tailored to your exact target role in seconds.</p>
"""
                }
            ]
        },
        "ta": {
            "variants": [
                {
                    "subject": "📄 {name}, உங்கள் CV-இன் ATS Score-ஐ இலவசமாகப் பெற்று உடனடி வேலை வாய்ப்பைப் பெறுங்கள்!",
                    "headline": "🎯 வேலை வாய்ப்புகளை அதிகரிக்க தானியங்கி ATS-அங்கீகரிக்கப்பட்ட CV!",
                    "cta_text": "இலவச ATS Score-ஐ சோதிக்கவும் →",
                    "cta_url": "https://www.dreemfolio.com/ats-resume-checker",
                    "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>75%-க்கும் மேற்பட்ட ரெஸ்யூம்கள் கணினி அமைப்புகளால் (ATS) நிராகரிக்கப்படுகின்றன. DreemFolio AI மூலம் உங்கள் CV-ஐ உடனே மேம்படுத்துங்கள்.</p>
"""
                }
            ]
        }
    },

    # ── 3. LIVE WEB PORTFOLIO LAUNCH BOOSTER ────────────────────────────────
    "portfolio_launch": {
        "si": {
            "variants": [
                {
                    "subject": "🌐 {name}, ඔබේ Live Portfolio Website එක තත්පර 15කින් නොමිලේ Publish කරගන්න!",
                    "headline": "🚀 සාම්ප්‍රදායික CV වලට එහා ගිය Interactive Web Portfolio එකක්!",
                    "cta_text": "🌐 මගේ Portfolio එක Live දාන්න →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>රැකියාවලට අයදුම් කරන විට සාම්ප්‍රදායික PDF CV එකක් පමණක් යවනවාට වඩා, ඔබේම නමින් යුත් <strong>Live Web Portfolio Link එකක් (dreemfolio.com/p/yourname)</strong> යොමු කළහොත් Recruiters ලාගේ අවධානය 10 ගුණයකින් දිනාගත හැක!</p>
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
                {
                    "subject": "✨ {name}, Recruiters ලාව විශ්මයට පත් කරන Live Portfolio Link එකක් සාදා ගන්න",
                    "headline": "📱 1-Click Interactive Portfolio with Verified Projects & Contact Cards",
                    "cta_text": "✨ Launch My Portfolio Link →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>PDF එකක් යැව්වාම ඒක open නොකර skip කරන Recruiters ලා, Live Link එකක් දුන්නම interactive විදියට phone එකෙන් scroll කරලා බලනවා! අදම ඔබගේ web portfolio එක 15s න් activate කරගන්න.</p>
"""
                },
                {
                    "subject": "🌍 Stand Out Globally: {name}, ඔබේම Personal Career Domain එකක් අදම ලබා ගන්න",
                    "headline": "💼 Give Recruiters an Unforgettable Impression with Your Interactive Profile",
                    "cta_text": "🌐 Claim My Live Portfolio →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>Global tech & remote jobs වලට තරඟ කරන විට ඔබේ නමින් යුත් live link එකක් තිබීම ඉහළම සැලකිල්ලට ලක්වේ. DreemFolio Studio හරහා කිසිදු coding දැනුමක් නැතුව ඔබේ portfolio එක live දාන්න.</p>
"""
                }
            ]
        },
        "en": {
            "variants": [
                {
                    "subject": "🚀 {name}, Launch Your Interactive Web Portfolio in 15 Seconds!",
                    "headline": "🌐 Stand Out from Hundreds of Candidates with a Live Career Portfolio",
                    "cta_text": "Publish My Portfolio Now →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>In modern recruitment, candidates who provide a live, interactive web portfolio link alongside their PDF resume get up to 3x higher interview response rates.</p>
<p>DreemFolio automatically turns your credentials and project highlights into an animated, mobile-responsive portfolio site in under 15 seconds.</p>
"""
                },
                {
                    "subject": "📱 {name}, Replace Boring PDFs with a Live Interactive Career Profile",
                    "headline": "⚡ 1-Click Hosted Portfolio at dreemfolio.com/p/yourname",
                    "cta_text": "Create My Live Site →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Give hiring managers a stunning interactive showcase of your verified experience, live project previews, and verified credentials.</p>
"""
                }
            ]
        },
        "ta": {
            "variants": [
                {
                    "subject": "🌐 {name}, உங்கள் நேரடி வலை போர்ட்ஃபோலியோவை 15 வினாடிகளில் வெளியிடுங்கள்!",
                    "headline": "🚀 வேலை வாய்ப்புகளை எளிதில் பெற உங்களுக்கென ஒரு நேரடி வலைப்பக்கம்!",
                    "cta_text": "போர்ட்ஃபோலியோவை வெளியிடவும் →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>சாதாரண PDF CV-யை விட உங்கள் சொந்த நேரடி வலை போர்ட்ஃபோலியோ (Live Web Portfolio) மூலம் முதலாளிகளின் கவனத்தை எளிதில் ஈர்க்க முடியும்.</p>
"""
                }
            ]
        }
    },

    # ── 4. AI JOB HUNTER & REMOTE VACANCY MATCHES ───────────────────────────
    "job_hunter_matches": {
        "si": {
            "variants": [
                {
                    "subject": "🎯 2026 දී Manual විදියට පැය ගණන් Jobs හොයන කාලේ ඉවරයි! {name}, Meet Your AI Job Hunter",
                    "headline": "🤖 24/7 Global & Remote Jobs ($100k+) Matched Directly to Your CV Profile!",
                    "cta_text": "🎯 මගේ AI Job Matches බලන්න →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>2026 දී Job Sites වල පැය ගණන් රස්සා හොයන කාලේ ඉවරයි! 🛑 ඔබ වෙනුවෙන් 24/7 Global & Remote Jobs හොයලා, Match කරලා දෙන <strong>DreemFolio AI Job Hunter</strong> හඳුන්වා දෙන්නෙමු!</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #10b981; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    🌟 DreemFolio AI Job Hunter විශේෂාංග:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>🎯 <strong>98% AI Career Matches:</strong> ඔබේ qualifications වලට 100% ක් ගැළපෙන Remote Jobs තත්පරයෙන් Match වීම.</li>
    <li>⚡ <strong>LinkedIn Easy Apply Ready:</strong> 1-Click එකෙන් global vacancies වලට අයදුම් කිරීමේ පහසුකම.</li>
    <li>💵 <strong>High-Paying Remote Vacancies:</strong> $100k+ global tech & business opportunities සජීවීව බලාගැනීම.</li>
  </ul>
</div>
<p style="font-size: 13px; color: #cbd5e1;">අදම නොමිලේම ඔබගේ පළමු AI Job Matches බලාගන්න!</p>
"""
                },
                {
                    "subject": "🌍 {name}, ඔබේ Qualifications වලට ගැළපෙන $100k+ Remote Jobs තත්පරයෙන් Match කරගන්න!",
                    "headline": "💸 Verified Global Careers: Software, Mobile, Marketing, Design & Fintech",
                    "cta_text": "🌍 Explore Remote Vacancies →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>ලංකාවේ ඉඳන් ඩොලර් වලින් ආදායම් උපයන්න කැමතිද? DreemFolio AI Copilot ඔබගේ CV එක ස්කෑන් කර ලොව පුරා තියෙන හොඳම Remote Vacancies ඔබට ගළපා දෙයි.</p>
"""
                },
                {
                    "subject": "⚡ {name}, Explore 98% Verified Career Matches & 1-Click Global Vacancies",
                    "headline": "💼 Live Global Job Hunter: Stop Searching, Let AI Bring Jobs to You",
                    "cta_text": "⚡ Match My Target Role Now →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>ඔබගේ Target Role එකට ගැළපෙන සජීවී Global Vacancies ලැයිස්තුවක් DreemFolio AI Job Hunter මඟින් ඔබ වෙනුවෙන් සූදානම් කර ඇත.</p>
"""
                }
            ]
        },
        "en": {
            "variants": [
                {
                    "subject": "🎯 {name}, Stop Searching Job Boards: Meet Your AI Job Hunter & Copilot",
                    "headline": "🤖 98% Career Match: Global & Remote Vacancies ($100k+) Matched Instantly",
                    "cta_text": "Discover Verified Career Matches →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Manual job hunting is obsolete. DreemFolio AI scans active global listings 24/7 to match vacancies directly with your verified skillset.</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #10b981; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    🚀 Inside DreemFolio Job Hunter:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>🎯 <strong>Verified AI Matches:</strong> Top 95%+ compatibility with live vacancies.</li>
    <li>⚡ <strong>LinkedIn Easy Apply Shortcuts:</strong> Direct 1-click application portals.</li>
    <li>🌐 <strong>Global Remote Compensation:</strong> High-paying international roles.</li>
  </ul>
</div>
"""
                },
                {
                    "subject": "🌍 {name}, Top Remote Jobs ($100k-$150k) Matched to Your Resume Today",
                    "headline": "💼 1-Click Apply Ready: Explore Verified International Vacancies",
                    "cta_text": "View Live Matched Roles →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Check out verified vacancies in Fintech, Cloud, Mobile, and Web Engineering aligned with your background.</p>
"""
                }
            ]
        },
        "ta": {
            "variants": [
                {
                    "subject": "🎯 {name}, உங்களுக்கான சிறந்த உலகளாவிய தொலைதூர வேலைகளை AI மூலம் கண்டறியுங்கள்!",
                    "headline": "🤖 24/7 சர்வதேச வேலை வாய்ப்புகளை உடனே பெற்று விண்ணப்பியுங்கள்!",
                    "cta_text": "வேலை வாய்ப்புகளைப் பார்க்கவும் →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>DreemFolio AI Job Hunter மூலம் உங்கள் திறமைகளுக்கு ஏற்ற உயர் ஊதிய சர்வதேச வேலைகளை நொடிகளில் கண்டறியுங்கள்.</p>
"""
                }
            ]
        }
    },

    # ── 5. AI MOCK INTERVIEW & VOICE COACH BOOSTER ──────────────────────────
    "mock_interview": {
        "si": {
            "variants": [
                {
                    "subject": "🎙️ {name}, Interview එකට යන්න කලින් AI එකත් එක්ක Voice එකෙන් Practice වෙන්න!",
                    "headline": "📹 Live Voice & AI Video Mock Interviews — Build 10x Confidence",
                    "cta_text": "🎙️ Start Voice Mock Interview →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>Interview එකකට යද්දී බයද? කියන්න ඕන දේවල් අමතක වෙනවද? 🎙️ DreemFolio හි <strong>AI Voice Mock Interview</strong> එක හරහා සැබෑ HR Recruiter කෙනෙක් එක්ක කතා කරනවා වගේම ඔබට Voice එකෙන් practice වෙන්න පුළුවන්!</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #f59e0b; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    🎯 AI Mock Interview වාසි:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>🎙️ <strong>Live Voice Simulation:</strong> ඔබ ලබා දෙන පිළිතුරු වලට ක්ෂණික voice feedback.</li>
    <li>📹 <strong>Video Conference Feel:</strong> සැබෑ interview කාමරයක ඉන්නවා වගේම realistic අත්දැකීමක්.</li>
    <li>💡 <strong>Role-Targeted Questions:</strong> ඔබ ඉල්ලුම් කරන තනතුරටම අදාළ තාක්ෂණික සහ behavioral ප්‍රශ්න.</li>
  </ul>
</div>
<p style="font-size: 13px; color: #cbd5e1;">පළමු interview එකෙන්ම Offer Letter එක දිනාගන්න, අදම නොමිලේ Practice වෙන්න!</p>
"""
                },
                {
                    "subject": "🤝 HR Recruiter කෙනෙක් එක්ක කතා කරනවා වගේ Live Practice Interview එකක් කරන්න!",
                    "headline": "🎯 Real-Time AI Feedback on Your Answers, Tone & Delivery Before the Big Day",
                    "cta_text": "🤝 Practice My Interview Now →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>සැබෑ interview එකේදී පැකිලෙන්න එපා! DreemFolio AI Interview Coach සමඟ ඔබේ පිළිතුරු නිවැරදි කරගෙන 100% ಆತ್ಮවිශ්වාසයෙන් මුහුණ දෙන්න.</p>
"""
                },
                {
                    "subject": "🚀 {name}, Land Your Dream Job Offer on the First Attempt with AI Interview Coach",
                    "headline": "🎙️ Instant Voice Simulation & Role-Specific Interview Questions",
                    "cta_text": "🚀 Start AI Interview Prep →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>තාක්ෂණික හා කළමනාකරණ සම්මුඛ පරීක්ෂණ ජයගැනීමට DreemFolio AI Mock Interview tool එක අදම භාවිතා කරන්න.</p>
"""
                }
            ]
        },
        "en": {
            "variants": [
                {
                    "subject": "🎙️ {name}, Ace Your Next Interview with AI Voice & Video Mock Sessions",
                    "headline": "📹 Realistic Recruiter Simulation: Real-Time Feedback on Tone & Delivery",
                    "cta_text": "Practice Voice Mock Interview →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Eliminate interview anxiety. Practice speaking with our conversational AI voice recruiter and receive instant constructive feedback on every answer.</p>
"""
                },
                {
                    "subject": "🤝 {name}, Don't Wing Your Next Interview: Practice with AI First",
                    "headline": "🎯 Master Technical & Behavioral Questions for Your Exact Target Role",
                    "cta_text": "Start Free Mock Session →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Simulate an authentic HR screening conversation before stepping into the real room.</p>
"""
                }
            ]
        },
        "ta": {
            "variants": [
                {
                    "subject": "🎙️ {name}, உங்கள் நேர்காணலுக்கு முன்பாக AI-உடன் பேசிப் பயிற்சி செய்யுங்கள்!",
                    "headline": "📹 நேரடி குரல் மற்றும் வீடியோ நேர்காணல் பயிற்சி!",
                    "cta_text": "நேர்காணல் பயிற்சியைத் தொடங்குங்கள் →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>DreemFolio AI Voice Mock Interview மூலம் உங்கள் நேர்காணல் அச்சத்தை நீக்கி முழு நம்பிக்கையுடன் வெற்றி பெறுங்கள்.</p>
"""
                }
            ]
        }
    },

    # ── 6. 1-CLICK AUTO-FILL JOB APPLICATION COPILOT ────────────────────────
    "application_copilot": {
        "si": {
            "variants": [
                {
                    "subject": "⚡ හැම Job එකකටම පැය ගණන් Forms පුරවන්න ඕන නෑ! {name}, 1-Click Apply Ready",
                    "headline": "🤖 Auto-Fill Application Copilot Enabled: Apply to 50+ Jobs in Minutes",
                    "cta_text": "⚡ Activate 1-Click Copilot →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>හැම Job Vacancy එකකටම එකම විස්තර ආයෙ ආයෙත් පැය ගණන් Type කරන්න සිදුවීම මහන්සියක් නේද? ⚡ DreemFolio හි <strong>Auto-Fill Application Copilot</strong> මඟින් එක Click එකෙන් ඔබගේ අයදුම්පත පුරවා දෙයි!</p>
<div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
  <p style="color: #8b5cf6; font-weight: bold; margin-top: 0; margin-bottom: 8px; font-size: 14px;">
    🚀 Auto-Fill Copilot සුපිරි වාසි:
  </p>
  <ul style="color: #e2e8f0; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
    <li>⚡ <strong>Instant Form Filling:</strong> LinkedIn Easy Apply සහ Career Portals වල තත්පරයෙන් auto-fill වීම.</li>
    <li>📄 <strong>Role-Targeted CV Re-Tailor:</strong> අදාළ Job Description එකට හරියන ලෙස ඔබේ CV එක තත්පර 10න් Re-tailor වීම.</li>
    <li>⏰ <strong>Save 10+ Hours Every Week:</strong> සාමාන්‍යයෙන් දින ගණන් ගතවන අයදුම් කිරීමේ ක්‍රියාවලිය මිනිත්තු කිහිපයකින් නිම කිරීම.</li>
  </ul>
</div>
<p style="font-size: 13px; color: #cbd5e1;">අදම Copilot සමඟ ඔබේ රැකියා සෙවීම 10x වේගවත් කරගන්න!</p>
"""
                },
                {
                    "subject": "📄 {name}, අදාළ Job එකට හරියන විදියට ඔබේ CV එක තත්පර 10න් Re-tailor කරගන්න!",
                    "headline": "⚡ 1-Click Copilot & Auto-Fill for LinkedIn Easy Apply & Global Vacancies",
                    "cta_text": "📄 Re-Tailor My CV Now →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>එකම generic CV එක හැම job එකටම යවන්න එපා. DreemFolio Copilot මඟින් ඉල්ලුම් කරන job එකේ keywords වලට තත්පර 10න් ඔබේ CV එක re-target කරගන්න.</p>
"""
                },
                {
                    "subject": "🛑 Stop Wasting Hours on Manual Job Applications: {name}, Let Copilot Apply for You",
                    "headline": "🚀 1-Click Easy Apply & Auto-Form Filling with DreemFolio AI",
                    "cta_text": "🛑 Try 1-Click Apply →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>ආයුබෝවන් <strong>{name}</strong>,</p>
<p>DreemFolio AI Copilot සක්‍රිය කර රැකියා අයදුම් කිරීමේ සම්පූර්ණ ක්‍රියාවලිය ස්වයංක්‍රීය කරගන්න.</p>
"""
                }
            ]
        },
        "en": {
            "variants": [
                {
                    "subject": "⚡ {name}, Stop Filling Repetitive Job Forms: Meet 1-Click Application Copilot",
                    "headline": "🤖 Auto-Fill Enabled: Apply to 50+ Global Vacancies in Minutes",
                    "cta_text": "Enable 1-Click Copilot →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Tired of re-typing your work history into every single company ATS portal? DreemFolio Copilot auto-fills your applications and re-tailors your CV on the fly.</p>
"""
                },
                {
                    "subject": "📄 {name}, Re-Tailor Your CV for Any Job in Under 10 Seconds",
                    "headline": "⚡ 1-Click Application Copilot: Auto-Fill & Instant Role Targeting",
                    "cta_text": "Re-Tailor My Resume →",
                    "cta_url": "https://www.dreemfolio.com/dashboard",
                    "body": """
<p>Hi <strong>{name}</strong>,</p>
<p>Match exact job descriptions with one click and beat ATS algorithms effortlessly.</p>
"""
                }
            ]
        },
        "ta": {
            "variants": [
                {
                    "subject": "⚡ {name}, மீண்டும் மீண்டும் படிவங்களை நிரப்புவதை நிறுத்துங்கள்: 1-Click Copilot-ஐப் பயன்படுத்துங்கள்!",
                    "headline": "🤖 தானியங்கி வேலை விண்ணப்பங்கள்: நிமிடங்களில் 50+ வேலைகளுக்கு விண்ணப்பியுங்கள்!",
                    "cta_text": "Copilot-ஐத் தொடங்குங்கள் →",
                    "cta_url": "https://www.dreemfolio.com/job-hunter",
                    "body": """
<p>வணக்கம் <strong>{name}</strong>,</p>
<p>DreemFolio Auto-Fill Application Copilot மூலம் நேரத்தை மிச்சப்படுத்தி விரைவாக வேலைகளுக்கு விண்ணப்பியுங்கள்.</p>
"""
                }
            ]
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

        # Segment assignment priority across all 6 growth boosters
        if resume_count == 0 or (u.lifetime_ats_downloads_count == 0):
            segment = "ats_resume" if (u.id % 2 == 0) else "application_copilot"
        elif resume_count > 0 and ref_count == 0:
            segment = "affiliate_earning" if (u.id % 2 == 0) else "portfolio_launch"
        else:
            # Active users: rotate between Job Hunter vacancies and Mock Interview coach
            segment = "job_hunter_matches" if (u.id % 2 == 0) else "mock_interview"

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
        lead_segments = ["ats_resume", "job_hunter_matches", "application_copilot"]
        lead_seg = lead_segments[(l.id or 0) % len(lead_segments)]
        candidates.append({
            "source_type": "marketing_lead",
            "id": l.id,
            "email": l.email,
            "name": l.name or "Candidate",
            "segment": lead_seg,
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
    window_info = get_prime_window_info(cfg)

    # Audit inspects fresh opportunities (12h window) to give admin full visibility
    eligible = research_system_candidates(db, limit=150, force_fresh=True)
    by_segment = {
        "affiliate_earning": 0,
        "ats_resume": 0,
        "portfolio_launch": 0,
        "job_hunter_matches": 0,
        "mock_interview": 0,
        "application_copilot": 0
    }
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
        f"({by_segment['affiliate_earning']} Affiliate, {by_segment['ats_resume']} ATS CV, "
        f"{by_segment['portfolio_launch']} Portfolio, {by_segment['job_hunter_matches']} Job Hunter, "
        f"{by_segment['mock_interview']} Mock Interview, {by_segment['application_copilot']} Copilot). "
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
    window_info = get_prime_window_info(cfg)

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
        if seg == "job_hunter_matches" and not getattr(cfg, "enable_job_hunter_booster", True):
            continue
        if seg == "mock_interview" and not getattr(cfg, "enable_interview_booster", True):
            continue
        if seg == "application_copilot" and not getattr(cfg, "enable_copilot_booster", True):
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
        tpl_group = templates_for_seg.get(target_lang, templates_for_seg.get("en", {}))
        if isinstance(tpl_group, dict) and "variants" in tpl_group and tpl_group["variants"]:
            v_idx = (cand.get("id") or 0) % len(tpl_group["variants"])
            tpl = tpl_group["variants"][v_idx]
        else:
            tpl = tpl_group

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
                    w_info = get_prime_window_info(cfg)
                    if not w_info["is_prime"]:
                        return
                    execute_growth_bot_cycle(db, force_now=False, max_to_send=5)

            await asyncio.to_thread(_run_tick)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in growth bot background daemon loop: %s", e)
            await asyncio.sleep(60)
