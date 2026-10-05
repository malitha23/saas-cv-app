"""
Authoritative Blog Database and SEO Content Catalog for DreemFolio AI.
Maintains structured blog metadata, publishing dates, author credentials,
categories, target search keywords, schema markup contexts, and multi-language
translations (English, Sinhala, Tamil) adhering to Google Multilingual SEO Guidelines.
"""

from typing import Dict, Any, List, Optional

BLOG_DATABASE: Dict[str, Dict[str, Any]] = {
    "how-to-write-an-ats-friendly-cv": {
        "slug": "how-to-write-an-ats-friendly-cv",
        "title": "How to Write an ATS-Friendly Resume in 2026",
        "subtitle": "Step-by-step blueprint to pass modern Applicant Tracking Systems (Workday, Greenhouse, Lever) with 95%+ match scores.",
        "description": "Learn step-by-step how to write an ATS-friendly CV that passes Applicant Tracking Systems. Discover formatting rules, keyword optimization, and free ATS checkers.",
        "template": "blogs/ats_cv_guide.html",
        "published_date": "2026-10-05",
        "modified_date": "2026-10-05",
        "author": {
            "name": "DreemFolio AI Career Team",
            "role": "Senior Talent Acquisition & Resume Strategists",
            "avatar": "/static/images/logo.png"
        },
        "reading_time": "7 min read",
        "category": "ATS Resume Guide",
        "badge": "Top Recruiter Pick",
        "priority": "0.9",
        "target_keywords": [
            "ATS friendly CV",
            "pass ATS scanner",
            "free ATS checker",
            "ATS resume format 2026",
            "Applicant Tracking System resume",
            "ATS score check"
        ],
        "og_image": "https://www.dreemfolio.com/static/images/hero_showcase.jpg",
        "translations": {
            "si": {
                "title": "2026 දී ATS-Friendly CV එකක් සාදාගන්නේ කෙසේද? (සම්පූර්ණ මඟපෙන්වීම)",
                "subtitle": "Workday, Greenhouse සහ Lever වැනි ATS පද්ධති වලින් 95%+ ලකුණු ලබාගනිමින් Pass වන CV එකක් හදන නිවැරදි ක්‍රමය.",
                "description": "Applicant Tracking Systems (ATS) හරහා පහසුවෙන්ම Pass වන ATS-friendly CV එකක් සාදන ආකාරය, formatting නීති, සහ නොමිලේ ATS score පරීක්ෂා කරන හැටි.",
                "category": "ATS CV මඟපෙන්වීම",
                "badge": "ප්‍රමුඛ මාර්ගෝපදේශය",
                "reading_time": "විනාඩි 7ක කියවීමක්",
                "target_keywords": [
                    "ATS friendly CV සිංහලෙන්",
                    "CV හදන හැටි",
                    "ATS resume format sinhala",
                    "pass ATS scanner",
                    "free ATS checker",
                    "CV eka hadana widiya"
                ]
            },
            "ta": {
                "title": "2026 இல் ATS-நட்பு CV எழுதுவது எப்படி? (முழு வழிகாட்டி)",
                "subtitle": "Workday, Greenhouse மற்றும் Lever போன்ற ATS அமைப்புகளில் 95%+ மதிப்பெண்களுடன் தேர்ச்சி பெறுவதற்கான வழிகாட்டி.",
                "description": "Applicant Tracking Systems (ATS) இல் எளிதாக தேர்ச்சி பெறும் ATS-நட்பு CV எழுதுவது எப்படி, வடிவமைப்பு விதிகள் மற்றும் இலவச ATS சரிபார்ப்பு.",
                "category": "ATS CV வழிகாட்டி",
                "badge": "சிறந்த வழிகாட்டி",
                "reading_time": "7 நிமிட வாசிப்பு",
                "target_keywords": [
                    "ATS friendly CV tamil",
                    "CV தயார் செய்வது எப்படி",
                    "ATS resume format tamil",
                    "pass ATS scanner",
                    "tech resume tamil"
                ]
            }
        }
    },
    "top-10-resume-errors-that-cause-rejection": {
        "slug": "top-10-resume-errors-that-cause-rejection",
        "title": "Top 10 Resume Errors That Cause Rejection (And How to Fix Them)",
        "subtitle": "The critical formatting, typography, and keyword mistakes that trigger instant rejection in 2026 recruiting funnels.",
        "description": "Discover the top 10 resume errors that cause instant ATS and recruiter rejection. Learn how to fix formatting traps, missing metrics, and keyword mistakes.",
        "template": "blogs/resume_errors_guide.html",
        "published_date": "2026-10-05",
        "modified_date": "2026-10-05",
        "author": {
            "name": "DreemFolio AI Career Team",
            "role": "Recruitment Operations & Career Mentors",
            "avatar": "/static/images/logo.png"
        },
        "reading_time": "8 min read",
        "category": "Resume Optimization",
        "badge": "Essential Reading",
        "priority": "0.85",
        "target_keywords": [
            "resume formatting mistakes",
            "CV rejection reasons",
            "ATS parsing errors",
            "why resumes get rejected",
            "resume red flags",
            "fix resume errors"
        ],
        "og_image": "https://www.dreemfolio.com/static/images/hero_showcase.jpg",
        "translations": {
            "si": {
                "title": "CV එකක් Reject වීමට බලපාන ප්‍රධාන වැරදි 10ක් (සහ ඒවා නිවැරදි කරගන්නා ආකාරය)",
                "subtitle": "බොහෝ දෙනෙකුගේ CV පළමු තත්පර 6 තුළ Reject වීමට හේතුවන Formatting, Typography සහ Keyword දෝෂ 10ක්.",
                "description": "ATS පද්ධති සහ Recruiters ලා අතින් CV Reject වීමට හේතුවන ප්‍රධාන වැරදි 10ක් සහ DreemFolio AI මඟින් ඒවා නිවැරදි කරගන්නා ආකාරය.",
                "category": "CV නිවැරදි කිරීම",
                "badge": "අත්‍යවශ්‍ය කියවීමක්",
                "reading_time": "විනාඩි 8ක කියවීමක්",
                "target_keywords": [
                    "CV rejection reasons sinhala",
                    "resume mistakes sinhala",
                    "CV eke waradi",
                    "ATS parsing errors",
                    "CV hadana widiya"
                ]
            },
            "ta": {
                "title": "CV நிராகரிக்கப்படுவதற்கு வழிவகுக்கும் முதல் 10 தவறுகள் (மற்றும் தீர்வுகள்)",
                "subtitle": "2026 ஆட்சேர்ப்பு சுழற்சியில் உடனடி நிராகரிப்பைத் தூண்டும் வடிவமைப்பு மற்றும் முக்கிய வார்த்தை தவறுகள்.",
                "description": "ATS மற்றும் ஆட்சேர்ப்பாளர்களால் CV நிராகரிக்கப்படுவதற்கான முதல் 10 காரணங்கள் மற்றும் அவற்றை AI மூலம் எவ்வாறு சரிசெய்வது.",
                "category": "CV தேர்வுமுறை",
                "badge": "முக்கிய வாசிப்பு",
                "reading_time": "8 நிமிட வாசிப்பு",
                "target_keywords": [
                    "CV rejection reasons tamil",
                    "resume mistakes tamil",
                    "ATS parsing errors tamil",
                    "how to fix CV errors"
                ]
            }
        }
    },
    "tailor-cv-for-remote-jobs": {
        "slug": "tailor-cv-for-remote-jobs",
        "title": "How to Tailor Your CV for Remote Tech Jobs",
        "subtitle": "Proven tactics to stand out among 1,000+ global applicants for remote software engineer and engineering roles.",
        "description": "Optimize your resume specifically for remote software engineer and tech roles. Highlight async communication, remote tech stacks, and live portfolios.",
        "template": "blogs/remote_cv_guide.html",
        "published_date": "2026-10-05",
        "modified_date": "2026-10-05",
        "author": {
            "name": "DreemFolio AI Career Team",
            "role": "Global Tech Hiring Advisors",
            "avatar": "/static/images/logo.png"
        },
        "reading_time": "6 min read",
        "category": "Remote Tech Jobs",
        "badge": "Tech Special",
        "priority": "0.85",
        "target_keywords": [
            "remote job CV",
            "tech resume template",
            "software engineer ATS resume",
            "remote developer resume",
            "global tech jobs CV",
            "remote work resume tailoring"
        ],
        "og_image": "https://www.dreemfolio.com/static/images/hero_showcase.jpg",
        "translations": {
            "si": {
                "title": "විදේශීය සහ Remote Tech රැකියා සඳහා CV එක සකස් කරගන්නේ කෙසේද?",
                "subtitle": "ගෝලීය තරඟකරුවන් 1,000ක් අභිබවා Software Engineer සහ Tech රැකියා දිනාගැනීමට සාර්ථක උපක්‍රම.",
                "description": "Remote Software Engineer සහ Developer රැකියා සඳහා CV එක Optimize කරගන්නා ආකාරය. Async communication, remote tech stacks සහ Live Web Portfolio භාවිතය.",
                "category": "Remote රැකියා මඟපෙන්වීම",
                "badge": "Tech විශේෂාංගය",
                "reading_time": "විනාඩි 6ක කියවීමක්",
                "target_keywords": [
                    "remote job CV sinhala",
                    "software engineer resume sinhala",
                    "foreign jobs CV",
                    "remote developer resume",
                    "work from home tech jobs"
                ]
            },
            "ta": {
                "title": "ரிமோட் டெக் வேலைகளுக்கு உங்கள் CV ஐ எவ்வாறு வடிவமைப்பது",
                "subtitle": "ரிமோட் சாப்ட்வேர் இன்ஜினியர் பணிகளுக்கு 1,000+ சர்வதேச விண்ணப்பதாரர்களிடையே தனித்து நிற்க நிரூபிக்கப்பட்ட உத்திகள்.",
                "description": "ரிமோட் சாப்ட்வேர் இன்ஜினியர் பணிகளுக்கு உங்கள் விண்ணப்பத்தை எவ்வாறு மேம்படுத்துவது. Async தொடர்பு, ரிமோட் தொழில்நுட்பங்கள் மற்றும் நேரடி போர்ட்ஃபோலியோ.",
                "category": "ரிமோட் டெக் வேலைகள்",
                "badge": "டெக் சிறப்பு",
                "reading_time": "6 நிமிட வாசிப்பு",
                "target_keywords": [
                    "remote job CV tamil",
                    "software engineer resume tamil",
                    "global tech jobs tamil",
                    "remote work CV"
                ]
            }
        }
    }
}


def get_localized_blog_post(slug: str, lang: str = "en") -> Optional[Dict[str, Any]]:
    """Retrieve single blog post metadata localized for specified language (en, si, ta)."""
    post = BLOG_DATABASE.get(slug)
    if not post:
        return None
    res = dict(post)
    translations = post.get("translations", {})
    if lang in translations:
        res.update(translations[lang])
    res["current_lang"] = lang
    return res


def get_all_blog_posts(lang: str = "en") -> List[Dict[str, Any]]:
    """Return all blog posts localized and sorted by published date (newest first)."""
    posts = [get_localized_blog_post(slug, lang) for slug in BLOG_DATABASE.keys()]
    posts.sort(key=lambda p: p.get("published_date", ""), reverse=True)
    return posts


def get_blog_post(slug: str) -> Optional[Dict[str, Any]]:
    """Backward compatible helper returning default English post."""
    return get_localized_blog_post(slug, "en")
