"""
DreemFolio AI - Dynamic Support, Feature & Quota Guide Service
Provides real-time, database-driven documentation, how-to-use workflows,
and feature-by-feature quota limits without hardcoded values.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.auth import (
    get_saas_setting,
    DEFAULT_FREE_DAILY_AI_LIMIT,
    DEFAULT_FREE_LIFETIME_ATS_LIMIT,
    DEFAULT_FREE_LIFETIME_VISUAL_LIMIT,
    DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT,
    DEFAULT_FREE_DAILY_COPILOT_KITS_LIMIT,
    DEFAULT_FREE_MAX_TRACKED_JOBS,
    DEFAULT_FREE_DAILY_CHAT_LIMIT,
    DEFAULT_FREE_DAILY_INTERVIEW_LIMIT,
)
from app.pricing import _get_country_pricing_dict


def get_dynamic_guide_catalog(db: Session, country_code: str = "LK") -> Dict[str, Any]:
    """
    Builds a fully dynamic guide & quota catalog for the given country.
    Pulls live subscription prices and plan descriptions from the database,
    and binds current SaaS quota thresholds directly from saas_settings.
    """
    # 1. Fetch live country pricing & plans configuration
    country_pricing_dict = _get_country_pricing_dict(db)
    selected_country_data = country_pricing_dict.get(country_code) or country_pricing_dict.get("DEFAULT")
    if not selected_country_data:
        # Fallback to first available country entry
        selected_country_data = next(iter(country_pricing_dict.values()))

    currency_symbol = selected_country_data.get("currency_symbol", "Rs.")
    currency_code = selected_country_data.get("currency_code", "LKR")
    plans = selected_country_data.get("plans", [])

    # Map plans by key for quick lookup
    plans_by_key = {p["plan_key"]: p for p in plans}

    # 2. Fetch live quota limits from database saas_settings
    def _int_setting(key: str, default: int) -> int:
        val = get_saas_setting(db, key, str(default))
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    free_daily_ai = _int_setting("free_daily_ai_limit", DEFAULT_FREE_DAILY_AI_LIMIT)
    free_lifetime_ats = _int_setting("free_lifetime_ats_limit", DEFAULT_FREE_LIFETIME_ATS_LIMIT)
    free_lifetime_visual = _int_setting("free_lifetime_visual_limit", DEFAULT_FREE_LIFETIME_VISUAL_LIMIT)
    free_lifetime_cover_letter = _int_setting("free_lifetime_cover_letter_limit", DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT)
    free_daily_copilot_kits = _int_setting("free_daily_copilot_kits_limit", DEFAULT_FREE_DAILY_COPILOT_KITS_LIMIT)
    free_max_tracked_jobs = _int_setting("free_max_tracked_jobs", DEFAULT_FREE_MAX_TRACKED_JOBS)
    free_daily_chat = _int_setting("free_daily_chat_limit", DEFAULT_FREE_DAILY_CHAT_LIMIT)
    free_daily_interview = _int_setting("free_daily_interview_limit", DEFAULT_FREE_DAILY_INTERVIEW_LIMIT)

    quotas_summary = {
        "free_daily_ai": free_daily_ai,
        "free_lifetime_ats": free_lifetime_ats,
        "free_lifetime_visual": free_lifetime_visual,
        "free_lifetime_cover_letter": free_lifetime_cover_letter,
        "free_daily_copilot_kits": free_daily_copilot_kits,
        "free_max_tracked_jobs": free_max_tracked_jobs,
        "free_daily_chat": free_daily_chat,
        "free_daily_interview": free_daily_interview,
    }

    # 3. Define logical categories (inspired by Google Cloud / Stripe documentation)
    categories = [
        {
            "id": "resume_ats",
            "name": "ATS Resume Intelligence",
            "icon": "file-text",
            "description": "AI resume keyword optimization, STAR-method bullet tailoring, and ATS-safe PDF compilation."
        },
        {
            "id": "cover_letter",
            "name": "Cover Letters & Application Kits",
            "icon": "mail",
            "description": "Tailored cover letters and 1-click screening questionnaire responses matching target job descriptions."
        },
        {
            "id": "job_hunter",
            "name": "Job Discovery & Pipeline Tracking",
            "icon": "briefcase",
            "description": "AI job recommendations, LinkedIn Easy Apply search, and Kanban application lifecycle tracking."
        },
        {
            "id": "interview_copilot",
            "name": "Interview Simulator & Voice Coaching",
            "icon": "mic",
            "description": "24/7 AI career coaching, voice mock interviews, and real-time video conference HUD mistake feedback."
        },
        {
            "id": "portfolio",
            "name": "Hosted Web Portfolio Studio",
            "icon": "globe",
            "description": "Live developer & executive portfolios hosted on subdomains or custom domains with automated SSL."
        },
        {
            "id": "cloud_security",
            "name": "Cloud Persistence & Enterprise Security",
            "icon": "shield-check",
            "description": "Real-time cloud auto-save, multi-device sync, version rollbacks, and zero data training."
        }
    ]

    # 4. Define structured feature guides with step-by-step instructions & dynamic quotas
    feature_guides = [
        {
            "id": "ai-tailoring",
            "category_id": "resume_ats",
            "category_name": "ATS Resume Intelligence",
            "title": "AI Resume Keyword Tailoring & ATS Scoring",
            "tagline": "Semantically optimize your work history against any job description with instant 0-100 match scoring.",
            "badge": "Core AI",
            "min_plan": "free",
            "icon": "sparkles",
            "quotas": {
                "free": f"{free_daily_ai} Tailored runs per day (Resets at 00:00 UTC)",
                "pro": "Unlimited AI Tailoring runs (Zero daily throttles)",
                "elite": "Unlimited + Priority AI Queue (Sub-second processing)"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Enter or Load Resume Information",
                    "instruction": "Open the Resume Builder at /app and enter your work experience, education, and technical skills, or click 'Demo: Full Stack' to load a sample."
                },
                {
                    "step": 2,
                    "title": "Paste the Target Job Description",
                    "instruction": "Click the 'AI Tailoring' tab on the left sidebar and paste the full job post (responsibilities, required skills, and qualifications)."
                },
                {
                    "step": 3,
                    "title": "Run AI Tailoring",
                    "instruction": "Click 'Tailor with AI'. The Google Gemini Flash model extracts high-yield keywords, calculates semantic density, and restructures bullet points using the STAR methodology."
                },
                {
                    "step": 4,
                    "title": "Inspect ATS Match Score & Keyword Density",
                    "instruction": "Review the computed 0–100 ATS Match Score. Green badges indicate verified keyword matches, while amber badges highlight suggested terms to add."
                }
            ],
            "backend_enforcement": "Enforced server-side via `check_daily_ai_quota` in FastAPI. Excess requests return HTTP 402 with upgrade details.",
            "security_privacy": "Zero Retention: Resume text and job descriptions are processed in memory and never used to train foundational AI models.",
            "pro_tip": "Paste the entire job post including soft skills. The model balances technical keywords with leadership action verbs for optimal ATS passing.",
            "action_url": "/app",
            "action_label": "Open Resume Builder"
        },
        {
            "id": "classic-ats-pdf",
            "category_id": "resume_ats",
            "category_name": "ATS Resume Intelligence",
            "title": "Classic ATS PDF Engine (ReportLab Vector Rendering)",
            "tagline": "Strictly formatted single/multi-page PDFs guaranteed to parse cleanly on Taleo, Workday, Greenhouse & Lever.",
            "badge": "ATS Guaranteed",
            "min_plan": "free",
            "icon": "file-text",
            "quotas": {
                "free": f"{free_lifetime_ats} Lifetime Downloads (+1 clean download per referred friend)",
                "pro": "Unlimited Classic ATS PDF Downloads",
                "elite": "Unlimited Classic ATS PDF Downloads"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Verify Profile Content",
                    "instruction": "Ensure your contact info, experience dates, and bullet points are finalized in the editor."
                },
                {
                    "step": 2,
                    "title": "Select Classic ATS Format",
                    "instruction": "Click the 'Classic ATS PDF' button in the top download toolbar."
                },
                {
                    "step": 3,
                    "title": "Instant Vector Compilation",
                    "instruction": "The ReportLab backend compiles a standards-compliant PDF with single-column layout, standard typography, and clean text streams with no tables or graphics that confuse ATS crawlers."
                },
                {
                    "step": 4,
                    "title": "Direct Submission",
                    "instruction": "Upload your generated PDF directly to company career portals with 100% confidence."
                }
            ],
            "backend_enforcement": "Enforced by `check_ats_pdf_quota`. Tracks user lifetime download count in MySQL. Free users can earn bonus downloads via referral links.",
            "security_privacy": "PDFs are assembled in isolated server RAM and streamed directly to the browser; no documents remain on unencrypted storage.",
            "pro_tip": "Keep resume length to 1 page for less than 5 years of experience, and 2 pages for 5+ years. Classic ATS format auto-paginates cleanly.",
            "action_url": "/app",
            "action_label": "Generate ATS PDF"
        },
        {
            "id": "visual-photo-cv",
            "category_id": "resume_ats",
            "category_name": "ATS Resume Intelligence",
            "title": "Visual Photo CV & Modern Design Studio",
            "tagline": "Eye-catching two-column layout with professional headshot, custom accent palettes, and digital signature.",
            "badge": "Visual Format",
            "min_plan": "free",
            "icon": "camera",
            "quotas": {
                "free": f"{free_lifetime_visual} Lifetime Download",
                "pro": "Unlimited Visual Photo CV Downloads",
                "elite": "Unlimited Visual Photo CV Downloads"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Enable Photo CV Layout",
                    "instruction": "Toggle the 'Visual Photo CV' layout switch in the design settings panel."
                },
                {
                    "step": 2,
                    "title": "Upload Professional Headshot",
                    "instruction": "Upload a clean portrait photo (JPG/PNG). Crop and preview the circular or rounded avatar directly."
                },
                {
                    "step": 3,
                    "title": "Customize Branding & Signature",
                    "instruction": "Pick an accent color (Indigo, Emerald, Violet, Rose) and draw or upload your digital signature."
                },
                {
                    "step": 4,
                    "title": "Export High-Res PDF",
                    "instruction": "Download high-resolution print-ready PDF for email applications, agency recruiters, and networking."
                }
            ],
            "backend_enforcement": "Enforced by `check_visual_pdf_quota`. Blocks secondary downloads on free accounts until upgrade.",
            "security_privacy": "Uploaded photos are stored with cryptographic UUID tokens accessible only through your authenticated session.",
            "pro_tip": "Visual photo resumes are ideal for direct executive emails, networking on LinkedIn, and hiring in regions where candidate photos are expected.",
            "action_url": "/app",
            "action_label": "Design Photo CV"
        },
        {
            "id": "ai-cover-letter",
            "category_id": "cover_letter",
            "category_name": "Cover Letters & Application Kits",
            "title": "AI Tailored Cover Letter Generator",
            "tagline": "Compelling, role-specific cover letters linking your proven accomplishments directly to employer needs.",
            "badge": "High Conversion",
            "min_plan": "free",
            "icon": "mail",
            "quotas": {
                "free": f"{free_lifetime_cover_letter} Lifetime Downloads (1st download 100% clean, 2nd & 3rd watermarked)",
                "pro": "Unlimited 100% Clean & Watermark-Free Cover Letters",
                "elite": "Unlimited 100% Clean & Watermark-Free Cover Letters"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Select Target Position",
                    "instruction": "Click 'Cover Letter' in the left menu. Select which resume version to reference."
                },
                {
                    "step": 2,
                    "title": "Provide Company & Role Context",
                    "instruction": "Input the hiring manager's name (optional), target company name, and job posting text."
                },
                {
                    "step": 3,
                    "title": "Generate Tailored Draft",
                    "instruction": "Click 'Draft with AI'. Gemini synthesizes your strongest metrics into a coherent 3-paragraph narrative."
                },
                {
                    "step": 4,
                    "title": "Edit & Download",
                    "instruction": "Fine-tune any sentences in the live rich text editor, then download in PDF or copy to clipboard."
                }
            ],
            "backend_enforcement": "Enforced by `check_daily_cover_letter_quota`. Pro subscribers enjoy unlimited watermark-free PDF exports.",
            "security_privacy": "Cover letters are saved securely in your private cloud profile.",
            "pro_tip": "Specify 1 or 2 core achievements you're proudest of. The AI weaves them into the opening paragraph as an immediate hook.",
            "action_url": "/app",
            "action_label": "Draft Cover Letter"
        },
        {
            "id": "copilot-kit",
            "category_id": "cover_letter",
            "category_name": "Cover Letters & Application Kits",
            "title": "1-Click Application Screening Copilot",
            "tagline": "Generate tailored answers for tough employer screening questions in seconds.",
            "badge": "Time Saver",
            "min_plan": "free",
            "icon": "check-circle",
            "quotas": {
                "free": f"{free_daily_copilot_kits} Screening Kit per day",
                "pro": "Unlimited Application Screening Kits",
                "elite": "Unlimited Application Screening Kits"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Copy Screening Questions",
                    "instruction": "When applying on LinkedIn, Greenhouse, or Workday, copy the employer's supplemental questions."
                },
                {
                    "step": 2,
                    "title": "Paste into Copilot",
                    "instruction": "Open 'Application Copilot' in DreemFolio and paste the questions."
                },
                {
                    "step": 3,
                    "title": "Generate STAR Answers",
                    "instruction": "Click 'Generate Answers'. AI aligns your actual experience with the required competencies."
                },
                {
                    "step": 4,
                    "title": "Review & Paste",
                    "instruction": "Copy the polished answers straight into the job application form."
                }
            ],
            "backend_enforcement": "Guarded by `check_copilot_kit_quota` with daily reset.",
            "security_privacy": "Prompt data is ephemeral and never saved to shared caches.",
            "pro_tip": "Great for questions like 'Describe a time you dealt with ambiguity' or 'Why are you leaving your current role?'",
            "action_url": "/app",
            "action_label": "Launch Copilot"
        },
        {
            "id": "job-recommendations",
            "category_id": "job_hunter",
            "category_name": "Job Discovery & Pipeline Tracking",
            "title": "AI Job Recommendations & Market Match",
            "tagline": "Discover high-overlap job roles, seniority brackets, and salary benchmarks matched to your CV.",
            "badge": "Career Growth",
            "min_plan": "free",
            "icon": "target",
            "quotas": {
                "free": "Top 3 Roles Preview",
                "pro": "Unlimited AI Job Recommendations & Re-Tailoring",
                "elite": "Unlimited AI Job Recommendations & Re-Tailoring"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Run Profile Analysis",
                    "instruction": "Open the 'Job Recommendations' panel and click 'Analyze My Resume'."
                },
                {
                    "step": 2,
                    "title": "Explore Recommended Positions",
                    "instruction": "Review top matched titles, required skills gap analysis, and estimated salary bands."
                },
                {
                    "step": 3,
                    "title": "1-Click Resume Re-Tailoring",
                    "instruction": "Click 'Tailor For This Role' on any recommendation to auto-align your resume for that exact job title."
                }
            ],
            "backend_enforcement": "Capped on free accounts via API response filtering; fully unlocked for Pro and Elite.",
            "security_privacy": "Calculated dynamically without transmitting identity to third parties.",
            "pro_tip": "Use this feature before making a career transition to see which of your existing skills transfer into higher-paying specialties.",
            "action_url": "/app",
            "action_label": "View Recommendations"
        },
        {
            "id": "job-hunter",
            "category_id": "job_hunter",
            "category_name": "Job Discovery & Pipeline Tracking",
            "title": "AI Job Hunter & LinkedIn Easy Apply Search",
            "tagline": "Search live job vacancies across top portals with remote filtering and direct application shortcuts.",
            "badge": "Discovery",
            "min_plan": "free",
            "icon": "search",
            "quotas": {
                "free": "Basic Search (up to 4 Vacancies)",
                "pro": "Unlimited Search & Filtering with Direct Apply Links",
                "elite": "Unlimited Search & VIP Priority Sourcing"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Enter Search Criteria",
                    "instruction": "Specify target title (e.g. 'Backend Engineer', 'DevOps Specialist') and preferred location or 'Remote'."
                },
                {
                    "step": 2,
                    "title": "Run Live Vacancy Search",
                    "instruction": "Click 'Search Vacancies'. The engine aggregates open opportunities from major job networks."
                },
                {
                    "step": 3,
                    "title": "Save to Application Pipeline",
                    "instruction": "Click 'Add to Tracker' to immediately route promising leads into your Kanban pipeline."
                }
            ],
            "backend_enforcement": "Free searches limited to 4 results; Pro & Elite unlock unrestricted global querying.",
            "security_privacy": "Search queries are anonymous and never shared with employers.",
            "pro_tip": "Filter by 'Remote' to uncover international USD-compensated remote positions open to global applicants.",
            "action_url": "/app",
            "action_label": "Search Jobs"
        },
        {
            "id": "job-tracker",
            "category_id": "job_hunter",
            "category_name": "Job Discovery & Pipeline Tracking",
            "title": "Kanban Job Application Tracker & Cloud Sync",
            "tagline": "Organize your job search visually from initial submission to final compensation negotiation.",
            "badge": "Productivity",
            "min_plan": "free",
            "icon": "layout",
            "quotas": {
                "free": f"Track up to {free_max_tracked_jobs} active job applications",
                "pro": "Unlimited Tracked Applications + Full Cloud History",
                "elite": "Unlimited Tracked Applications + Full Cloud History"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Create a Job Card",
                    "instruction": "Click '+ Add Job' and input company, role, salary range, and application date."
                },
                {
                    "step": 2,
                    "title": "Drag Across Pipeline Stages",
                    "instruction": "Move cards between 'Wishlist', 'Applied', 'Screening', 'Interviewing', 'Offer', and 'Archived'."
                },
                {
                    "step": 3,
                    "title": "Record Notes & Follow-ups",
                    "instruction": "Add interview rounds, interviewer names, and key talking points inside each card."
                }
            ],
            "backend_enforcement": "Enforced by `check_job_tracker_quota`. Free accounts can track up to the configured limit.",
            "security_privacy": "Job details and salary notes are private to your authenticated account.",
            "pro_tip": "Record the names of people who interviewed you. You can ask the AI Career Copilot to generate customized post-interview thank you emails.",
            "action_url": "/app",
            "action_label": "Open Job Tracker"
        },
        {
            "id": "career-copilot-chat",
            "category_id": "interview_copilot",
            "category_name": "Interview Simulator & Voice Coaching",
            "title": "24/7 AI Career Copilot Chatbot",
            "tagline": "Your personal career advisor for resume critiques, career pivoting strategies, and salary negotiations.",
            "badge": "Interactive",
            "min_plan": "free",
            "icon": "message-square",
            "quotas": {
                "free": f"{free_daily_chat} Free prompts / day",
                "pro": "Unlimited 24/7 Career Coaching & Resume Critiques",
                "elite": "Unlimited + Dedicated Executive Advisory Prompt Mode"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Open Career Copilot",
                    "instruction": "Click the floating AI Chat icon in the bottom right corner of the screen."
                },
                {
                    "step": 2,
                    "title": "Ask Specific Career Questions",
                    "instruction": "Ask about career gaps, phrasing achievements, countering job offers, or preparing for behavioral questions."
                },
                {
                    "step": 3,
                    "title": "Receive Contextual Feedback",
                    "instruction": "The Copilot evaluates your query against your live resume and returns structured, actionable advice."
                }
            ],
            "backend_enforcement": "Enforced by `check_chat_copilot_quota` with daily reset.",
            "security_privacy": "Chat history is private and never accessible to other platform users.",
            "pro_tip": "Ask: 'Simulate a tough salary negotiation call for an offer of Rs. 350,000 where I want Rs. 450,000'. The AI will roleplay as the HR manager.",
            "action_url": "/app",
            "action_label": "Start Chat"
        },
        {
            "id": "video-conference-coaching",
            "category_id": "interview_copilot",
            "category_name": "Interview Simulator & Voice Coaching",
            "title": "Real-Time AI Video Conference & Live Mistake Coaching (Real-Time Error Detection)",
            "tagline": "Practice in a realistic video call room with real-time HUD feedback highlighting mistakes as you speak.",
            "badge": "Game Changer",
            "min_plan": "free",
            "icon": "video",
            "quotas": {
                "free": f"{free_daily_interview} Practice session / day",
                "pro": "Unlimited Live Video Conference Sessions with Real-Time HUD Coaching",
                "elite": "Unlimited + Executive C-Level Boardroom Simulation"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Enter the Video Conference Studio",
                    "instruction": "Navigate to the 'AI Video Studio' and enable microphone and camera permissions."
                },
                {
                    "step": 2,
                    "title": "Configure Interview Scenario",
                    "instruction": "Choose your target role, difficulty level, and whether you want technical or behavioral questions."
                },
                {
                    "step": 3,
                    "title": "Engage in Live Video Dialogue",
                    "instruction": "The AI avatar asks questions. As you speak, the live HUD monitors filler words, rambling, metric citations, and pace in real-time."
                },
                {
                    "step": 4,
                    "title": "Review Mistake & Correction Breakdown",
                    "instruction": "After the session, receive an in-depth scorecard highlighting your exact phrasing mistakes, missing STAR components, and suggested ideal answers."
                }
            ],
            "backend_enforcement": "Enforced by `check_conference_quota`. Free accounts receive 1 session daily.",
            "security_privacy": "Audio and video streams are processed in memory for live inference; no camera recordings are saved.",
            "pro_tip": "Keep an eye on the STAR Indicator on your HUD. It turns green once you successfully state your measurable results.",
            "action_url": "/app",
            "action_label": "Enter Video Studio"
        },
        {
            "id": "voice-interview-simulator",
            "category_id": "interview_copilot",
            "category_name": "Interview Simulator & Voice Coaching",
            "title": "AI Voice Mock Interview Simulator",
            "tagline": "Realistic spoken mock interviews with dynamic follow-up questions and audio feedback.",
            "badge": "Voice AI",
            "min_plan": "free",
            "icon": "mic-2",
            "quotas": {
                "free": f"{free_daily_interview} Practice session / day (3 questions)",
                "pro": "Unlimited Full-Length Voice Mock Interviews",
                "elite": "Unlimited + Executive Leadership Scenarios"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Launch Voice Simulator",
                    "instruction": "Click 'Voice Interview' and choose your target company or domain."
                },
                {
                    "step": 2,
                    "title": "Listen & Speak Answers",
                    "instruction": "The AI interviewer articulates questions through realistic speech synthesis. Respond naturally via your microphone."
                },
                {
                    "step": 3,
                    "title": "Receive Instant Scoring",
                    "instruction": "The model evaluates your answer's structure, technical accuracy, and conciseness, then asks a follow-up probing question."
                }
            ],
            "backend_enforcement": "Enforced by `check_voice_interview_quota`.",
            "security_privacy": "Voice transcription uses high-speed streaming without storing audio files on external servers.",
            "pro_tip": "Practice with your headset microphone in a quiet room to simulate realistic remote video interview conditions.",
            "action_url": "/app",
            "action_label": "Start Voice Practice"
        },
        {
            "id": "portfolio-studio",
            "category_id": "portfolio",
            "category_name": "Hosted Web Portfolio Studio",
            "title": "Hosted Web Portfolio Studio (8 Architectures & Subdomain)",
            "tagline": "Turn your resume into a stunning, responsive personal website live on username.dreemfolio.com.",
            "badge": "Personal Brand",
            "min_plan": "free",
            "icon": "globe",
            "quotas": {
                "free": "Live Studio Preview (Publishing requires Pro / Elite)",
                "pro": "Hosted Live Portfolio on username.dreemfolio.com with Automated SSL",
                "elite": "Hosted Live Portfolio + Custom Domain + HTML Static Export"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Select Web Architecture",
                    "instruction": "Choose from 8 distinct layout architectures (Minimalist, Terminal Dev, Creative Grid, Executive, Clean Modern, etc.)."
                },
                {
                    "step": 2,
                    "title": "Auto-Populate Projects & Bio",
                    "instruction": "Your projects, work history, skills, and social handles automatically sync from your resume."
                },
                {
                    "step": 3,
                    "title": "Choose Subdomain Name",
                    "instruction": "Claim your unique web address (e.g. `malith.dreemfolio.com`) with automated SSL."
                },
                {
                    "step": 4,
                    "title": "Publish Worldwide",
                    "instruction": "Click 'Publish Portfolio'. Your website is deployed across global CDN edge nodes instantly."
                }
            ],
            "backend_enforcement": "Live subdomain routing and hosting guarded via `require_tier('pro')`.",
            "security_privacy": "Automated SSL certificates, DDoS mitigation, and global Edge caching.",
            "pro_tip": "Include live project URLs and GitHub links; hiring managers who visit portfolios are 60% more likely to advance candidates to interview rounds.",
            "action_url": "/app",
            "action_label": "Build Portfolio"
        },
        {
            "id": "cloud-autosave",
            "category_id": "cloud_security",
            "category_name": "Cloud Persistence & Enterprise Security",
            "title": "Real-Time Cloud Auto-Save & Instant Version Restore",
            "tagline": "Continuous cloud backup prevents work loss with multi-device synchronization and rollback capability.",
            "badge": "Cloud Sync",
            "min_plan": "free",
            "icon": "cloud",
            "quotas": {
                "free": "Continuous Cloud Auto-Save (Restoring previous drafts requires Pro)",
                "pro": "Unlimited Cloud Saves & Instant 1-Click Version History Restore",
                "elite": "Unlimited Cloud Saves & Instant 1-Click Version History Restore"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Automatic Real-Time Sync",
                    "instruction": "Every change you make in the editor is automatically saved to the database in the background."
                },
                {
                    "step": 2,
                    "title": "Multi-Device Continuity",
                    "instruction": "Switch between your workstation, laptop, or mobile phone seamlessly without losing changes."
                },
                {
                    "step": 3,
                    "title": "1-Click Version Restore (Pro)",
                    "instruction": "Open the Version History modal to view previously saved snapshots and restore any draft with a single click."
                }
            ],
            "backend_enforcement": "Restore endpoint verified by `free_allow_cloud_restore` SaaS setting in `app/routers/resume.py`.",
            "security_privacy": "Encrypted at rest using AES-256 database storage with user-isolated tenancy.",
            "pro_tip": "Create different targeted versions for various roles (e.g. 'Frontend Engineer' vs. 'Solutions Architect') and switch between them anytime.",
            "action_url": "/app",
            "action_label": "View Saved Resumes"
        },
        {
            "id": "custom-domain",
            "category_id": "portfolio",
            "category_name": "Hosted Web Portfolio Studio",
            "title": "Custom Private Domain & SSL Binding",
            "tagline": "Connect your own private domain (e.g. yourname.com or yourname.dev) with automated HTTPS.",
            "badge": "Executive Elite",
            "min_plan": "elite",
            "icon": "link-2",
            "quotas": {
                "free": "Not Included",
                "pro": "Not Included (Hosted on .dreemfolio.com)",
                "elite": "Included (Connect any custom apex domain or subdomain with auto-SSL)"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Add Domain Name",
                    "instruction": "In Portfolio Studio settings, enter your registered domain name (e.g. `alexsilva.dev`)."
                },
                {
                    "step": 2,
                    "title": "Configure CNAME DNS Record",
                    "instruction": "Add the designated CNAME record in your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.)."
                },
                {
                    "step": 3,
                    "title": "Verify & Launch",
                    "instruction": "Click 'Verify Domain'. Our edge routing immediately issues a zero-configuration SSL certificate."
                }
            ],
            "backend_enforcement": "Enforced server-side via `require_tier('elite')`.",
            "security_privacy": "Automated Let's Encrypt TLS encryption with automatic 90-day renewal.",
            "pro_tip": "A custom .dev or .com domain gives you the highest level of professional credibility for senior and executive roles.",
            "action_url": "/app",
            "action_label": "Connect Custom Domain"
        },
        {
            "id": "html-export",
            "category_id": "portfolio",
            "category_name": "Hosted Web Portfolio Studio",
            "title": "Standalone Website HTML Export (Zero Vendor Lock-in)",
            "tagline": "Download your portfolio as clean, static HTML/CSS/JS ready to deploy to GitHub Pages, Vercel, or your own server.",
            "badge": "Executive Elite",
            "min_plan": "elite",
            "icon": "code-2",
            "quotas": {
                "free": "Not Included",
                "pro": "Not Included",
                "elite": "Included (Unlimited Standalone Code Exports)"
            },
            "how_to_use": [
                {
                    "step": 1,
                    "title": "Open Portfolio Studio",
                    "instruction": "Verify your portfolio styling, projects, and bio in the preview window."
                },
                {
                    "step": 2,
                    "title": "Click Export Code",
                    "instruction": "Select 'Export Static ZIP' in the top action bar."
                },
                {
                    "step": 3,
                    "title": "Deploy Anywhere",
                    "instruction": "Extract the ZIP and host it on GitHub Pages, Netlify, Vercel, AWS S3, or any private VPS with zero recurring fees."
                }
            ],
            "backend_enforcement": "Enforced server-side via `require_tier('elite')`.",
            "security_privacy": "Clean static code with zero external telemetry or tracking scripts.",
            "pro_tip": "Deploy your exported bundle to GitHub Pages for completely free, permanent lifetime hosting with your own Git repository.",
            "action_url": "/app",
            "action_label": "Export Code Bundle"
        }
    ]

    # 5. Build dynamic comparison matrix mapping directly from current DB data
    comparison_matrix = [
        {
            "feature": "AI Resume Keyword Tailoring Runs",
            "free": f"{free_daily_ai} runs / day",
            "pro": "Unlimited Runs",
            "elite": "Unlimited + Priority Queue",
            "highlight": True
        },
        {
            "feature": "ATS Keyword Match & Score (0–100)",
            "free": "Included",
            "pro": "Included",
            "elite": "Included",
            "highlight": False
        },
        {
            "feature": "Classic ATS PDF Downloads",
            "free": f"{free_lifetime_ats} Lifetime (+1 per referral)",
            "pro": "Unlimited Downloads",
            "elite": "Unlimited Downloads",
            "highlight": True
        },
        {
            "feature": "Visual Photo CV Downloads",
            "free": f"{free_lifetime_visual} Lifetime Download",
            "pro": "Unlimited Downloads",
            "elite": "Unlimited Downloads",
            "highlight": False
        },
        {
            "feature": "AI Cover Letters",
            "free": f"{free_lifetime_cover_letter} Lifetime (1st Clean, 2 Watermarked)",
            "pro": "Unlimited 100% Clean & Watermark-Free",
            "elite": "Unlimited 100% Clean & Watermark-Free",
            "highlight": True
        },
        {
            "feature": "1-Click Application Copilot Screening Kits",
            "free": f"{free_daily_copilot_kits} Kit / day",
            "pro": "Unlimited Kits",
            "elite": "Unlimited Kits",
            "highlight": False
        },
        {
            "feature": "AI Job Recommendations & Re-Tailoring",
            "free": "Top 3 Roles Preview",
            "pro": "Unlimited Roles & Re-Tailor",
            "elite": "Unlimited Roles & Re-Tailor",
            "highlight": False
        },
        {
            "feature": "AI Job Hunter Vacancy Search",
            "free": "Up to 4 Vacancies",
            "pro": "Unlimited Search & Filtering",
            "elite": "Unlimited + VIP Sourcing",
            "highlight": False
        },
        {
            "feature": "Kanban Job Application Tracker",
            "free": f"Up to {free_max_tracked_jobs} Jobs Tracked",
            "pro": "Unlimited Jobs + Cloud History",
            "elite": "Unlimited Jobs + Cloud History",
            "highlight": True
        },
        {
            "feature": "24/7 AI Career Copilot Chatbot",
            "free": f"{free_daily_chat} Prompts / day",
            "pro": "Unlimited 24/7 Coaching",
            "elite": "Unlimited + Executive Mode",
            "highlight": False
        },
        {
            "feature": "Real-Time AI Video Conference Mistake Coaching",
            "free": f"{free_daily_interview} Session / day",
            "pro": "Unlimited Live Video Practice",
            "elite": "Unlimited + Boardroom Scenarios",
            "highlight": True
        },
        {
            "feature": "AI Voice Mock Interview Simulator",
            "free": f"{free_daily_interview} Session / day",
            "pro": "Unlimited Voice Interviews",
            "elite": "Unlimited Voice Interviews",
            "highlight": False
        },
        {
            "feature": "Hosted Web Portfolio Studio",
            "free": "Live Studio Preview",
            "pro": "Live Subdomain (.dreemfolio.com)",
            "elite": "Live Subdomain + All 8 Layouts",
            "highlight": True
        },
        {
            "feature": "Connect Custom Private Domain & SSL",
            "free": "—",
            "pro": "—",
            "elite": "Included (Custom Apex/Subdomain)",
            "highlight": True
        },
        {
            "feature": "Standalone Website HTML Code Export",
            "free": "—",
            "pro": "—",
            "elite": "Included (Full ZIP Bundle)",
            "highlight": True
        },
        {
            "feature": "Real-Time Cloud Auto-Save & Version Restore",
            "free": "Auto-Save Active (Restore requires Pro)",
            "pro": "Instant 1-Click Version Restore",
            "elite": "Instant 1-Click Version Restore",
            "highlight": False
        },
        {
            "feature": "Priority AI Processing Queue",
            "free": "Standard Queue",
            "pro": "Fast Queue",
            "elite": "Ultra-Fast Priority Queue",
            "highlight": False
        }
    ]

    return {
        "country_code": country_code,
        "currency_symbol": currency_symbol,
        "currency_code": currency_code,
        "plans": plans,
        "plans_by_key": plans_by_key,
        "quotas": quotas_summary,
        "categories": categories,
        "feature_guides": feature_guides,
        "comparison_matrix": comparison_matrix,
        "total_features": len(feature_guides)
    }
