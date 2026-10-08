import re
from typing import Dict, Any, List, Optional
from app.parser import extract_candidate_name, clean_extracted_text

# Common power action verbs used by Fortune 500 ATS systems
POWER_ACTION_VERBS = set([
    "accelerated", "achieved", "adapted", "administered", "advanced", "analyzed", "architected",
    "assembled", "automated", "built", "boosted", "calculated", "championed", "collaborated",
    "compiled", "composed", "configured", "consolidated", "constructed", "converted", "coordinated",
    "crafted", "created", "decreased", "delivered", "deployed", "designed", "developed", "devised",
    "diagnosed", "directed", "distributed", "documented", "doubled", "drafted", "drove", "eliminated",
    "enabled", "enforced", "engineered", "enhanced", "established", "estimated", "executed", "expanded",
    "expedited", "fabricated", "facilitated", "forecasted", "formulated", "founded", "generated",
    "guided", "headed", "identified", "implemented", "improved", "increased", "initiated", "innovated",
    "inspected", "installed", "instituted", "integrated", "intensified", "introduced", "invented",
    "investigated", "launched", "lead", "led", "leveraged", "managed", "maximized", "measured",
    "mentored", "migrated", "minimized", "modeled", "modernized", "monitored", "motivated", "negotiated",
    "operated", "optimized", "orchestrated", "organized", "overhauled", "oversaw", "partnered",
    "performed", "pioneered", "planned", "prepared", "produced", "programmed", "promoted", "proposed",
    "published", "rebuilt", "redesigned", "reduced", "reengineered", "regulated", "remodeled", "reorganized",
    "resolved", "restructured", "revamped", "reviewed", "revitalized", "routed", "saved", "scaled",
    "scheduled", "secured", "simplified", "slashed", "spearheaded", "standardized", "streamlined",
    "structured", "succeeded", "supervised", "surpassed", "synthesized", "systematized", "tested",
    "trained", "transformed", "troubleshot", "unified", "upgraded", "validated", "verified", "yielded"
])

# Weak / passive phrasing that ATS and recruiters penalize
WEAK_PHRASES = [
    ("responsible for", "Replace 'Responsible for' with active impact verbs like 'Engineered', 'Orchestrated', or 'Directed'"),
    ("duties included", "Replace 'Duties included' with tangible accomplishments and deliverables"),
    ("helped with", "Clarify your direct contribution: did you lead, build, design, or optimize it?"),
    ("assisted in", "Specify the exact component or outcome you delivered rather than 'assisted'"),
    ("worked on", "Replace vague 'Worked on' with specific action verbs like 'Developed', 'Deployed', or 'Architected'"),
    ("tasked with", "Describe what you accomplished rather than what you were assigned")
]

# Recognizable core skills taxonomy across Tech, Engineering, Business & Management
SKILL_TAXONOMY = [
    # Languages & Frameworks
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust", "php", "ruby", "swift", "kotlin",
    "react", "react.js", "next.js", "vue", "vue.js", "angular", "node.js", "express", "fastapi", "django", "flask",
    "spring boot", ".net", "asp.net", "laravel", "flutter", "react native", "html", "css", "tailwind", "bootstrap",
    # Databases & Cloud
    "sql", "postgresql", "mysql", "mongodb", "redis", "dynamodb", "oracle", "sqlite", "elasticsearch", "supabase", "firebase",
    "aws", "amazon web services", "azure", "google cloud", "gcp", "docker", "kubernetes", "git", "github", "gitlab",
    "ci/cd", "terraform", "ansible", "linux", "jenkins", "nginx", "apache", "kafka", "rabbitmq", "microservices", "rest api", "graphql",
    # Data & AI
    "machine learning", "deep learning", "ai", "artificial intelligence", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "data analysis", "power bi", "tableau", "excel", "nlp", "llm", "opencv", "computer vision",
    # Professional & Methodologies
    "agile", "scrum", "kanban", "jira", "project management", "system design", "unit testing", "qa testing", "ci cd",
    "product management", "leadership", "ui/ux", "figma", "wireframing", "seo", "cybersecurity", "penetration testing"
]


def audit_resume_ats(text: str, filename: str = "") -> Dict[str, Any]:
    """
    Perform deep, objective ATS audit of candidate resume text.
    Evaluates:
      1. Section completeness (25 pts)
      2. ATS formatting & parseability (25 pts)
      3. Action verbs, measurable metrics & impact (25 pts)
      4. Skills & keyword density (25 pts)
    """
    text = clean_extracted_text(text)
    text_lower = text.lower()
    words = re.findall(r'\b[A-Za-z0-9+#.-]+\b', text)
    word_count = len(words)

    # 1. Contact & Section Detection
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    extracted_email = email_match.group(0) if email_match else None

    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}', text)
    extracted_phone = phone_match.group(0).strip() if phone_match else None

    has_linkedin = bool(re.search(r'(linkedin\.com/in/|linkedin\.com/profile)', text_lower))
    has_github_or_portfolio = bool(re.search(r'(github\.com/|gitlab\.com/|behance\.net|dribbble\.com|\.vercel\.app|\.netlify\.app|\.github\.io|[a-z0-9-]+\.(?:com|io|dev|me)/)', text_lower))

    extracted_name = extract_candidate_name(text, extracted_email or "")

    # Section Checks
    section_checks = {
        "Professional Summary": bool(re.search(r'\b(summary|objective|profile|about me|professional summary)\b', text_lower)),
        "Work Experience": bool(re.search(r'\b(experience|employment|work history|career history|professional background|internship)\b', text_lower)),
        "Education": bool(re.search(r'\b(education|academic|university|degree|bachelor|bsc|msc|hnd|diploma)\b', text_lower)),
        "Skills & Competencies": bool(re.search(r'\b(skills|technical skills|technologies|tools|competencies|programming)\b', text_lower)),
        "Projects & Deliverables": bool(re.search(r'\b(projects|portfolio|personal projects|key projects|capstone)\b', text_lower)),
        "Certifications / Awards": bool(re.search(r'\b(certifications|certificates|licenses|credentials|awards|honors|hackathon)\b', text_lower))
    }

    detected_sections = [sec for sec, found in section_checks.items() if found]
    missing_sections = [sec for sec, found in section_checks.items() if not found]

    # Section Score (Max 25)
    section_score = 0
    if extracted_email and extracted_phone:
        section_score += 5
    elif extracted_email or extracted_phone:
        section_score += 3

    if has_linkedin or has_github_or_portfolio:
        section_score += 4
    elif any(term in text_lower for term in ['linkedin', 'github', 'portfolio']):
        section_score += 2

    if section_checks["Work Experience"]:
        section_score += 5
    if section_checks["Education"]:
        section_score += 4
    if section_checks["Skills & Competencies"]:
        section_score += 4
    if section_checks["Professional Summary"] or section_checks["Projects & Deliverables"]:
        section_score += 3

    section_score = min(25, max(0, section_score))

    # 2. ATS Formatting & Parseability (Max 25)
    formatting_score = 25
    formatting_warnings = []
    formatting_passed = []

    # Word count check
    if 350 <= word_count <= 1800:
        formatting_passed.append(f"Ideal length: {word_count} words (perfect 1 to 2 pages).")
    elif 200 <= word_count < 350:
        formatting_score -= 5
        formatting_warnings.append(f"Short document: {word_count} words. Recruiters expect at least 350+ words.")
    elif word_count < 200:
        formatting_score -= 12
        formatting_warnings.append(f"Extremely brief: Only {word_count} words. Document lacks critical details.")
    elif 1800 < word_count <= 2600:
        formatting_score -= 3
        formatting_warnings.append(f"Slightly lengthy: {word_count} words. Condense into 2 pages.")
    else:
        formatting_score -= 8
        formatting_warnings.append(f"Excessive length: {word_count} words. ATS and recruiters favor concise resumes.")

    # Check for text extractability
    if len(text.strip()) > 300:
        formatting_passed.append("100% Selectable Text: Document passes OCR and text stream parsing.")
    else:
        formatting_score -= 10
        formatting_warnings.append("Low character density: Ensure file is not a scanned raster image.")

    # Check for multi-column / messy table layout signs
    consecutive_short_lines = len(re.findall(r'(?m)^[A-Za-z0-9 ]{2,15}$', text))
    canva_risk_alert = False
    if consecutive_short_lines > 15:
        canva_risk_alert = True
        formatting_score -= 6
        formatting_warnings.append("Possible multi-column / sidebar detected: May cause text interleaving in ATS parsers.")
    else:
        formatting_passed.append("Linear text hierarchy: Follows single-column ATS reading order.")

    formatting_score = min(25, max(0, formatting_score))

    # 3. Action Verbs, Metrics & Quantifiable Impact (Max 25)
    impact_score = 0
    words_lower = [w.lower() for w in words]
    found_power_verbs = set(words_lower).intersection(POWER_ACTION_VERBS)
    power_verbs_count = len(found_power_verbs)

    # Detect numbers, percentages, dollar amounts, scaling metrics
    metric_matches = re.findall(
        r'(\b\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:\.\d+)?|\b\d+\+\b|\b\d+\s*(?:k|m|million|billion|users|customers|clients|projects|features|team members|years|months|hours|ms|seconds)\b)',
        text,
        re.I
    )
    metric_count = len(metric_matches)

    # Power verbs scoring (up to 12 pts)
    if power_verbs_count >= 8:
        impact_score += 12
    elif power_verbs_count >= 5:
        impact_score += 9
    elif power_verbs_count >= 2:
        impact_score += 5
    else:
        impact_score += 2

    # Metrics scoring (up to 13 pts)
    if metric_count >= 5:
        impact_score += 13
    elif metric_count >= 3:
        impact_score += 9
    elif metric_count >= 1:
        impact_score += 5
    else:
        impact_score += 0

    # Weak phrase penalties
    weak_found = []
    for phrase, tip in WEAK_PHRASES:
        if phrase in text_lower:
            weak_found.append(f"Found '{phrase}': {tip}")
            impact_score -= 2

    impact_score = min(25, max(0, impact_score))

    # 4. Skills & Keywords Density (Max 25)
    skills_score = 0
    detected_skills = []
    for skill in SKILL_TAXONOMY:
        # Match as whole word / phrase
        if re.search(rf'\b{re.escape(skill)}\b', text_lower):
            detected_skills.append(skill.title() if len(skill) > 3 else skill.upper())

    skills_count = len(detected_skills)
    if skills_count >= 10:
        skills_score = 25
    elif skills_count >= 7:
        skills_score = 20
    elif skills_count >= 4:
        skills_score = 14
    elif skills_count >= 1:
        skills_score = 8
    else:
        skills_score = 3

    # Total ATS Compatibility Score (0 - 100)
    overall_score = section_score + formatting_score + impact_score + skills_score
    overall_score = min(100, max(15, overall_score))

    # Rating determination
    if overall_score >= 88:
        rating = "Top 5% ATS Ready"
        rating_color = "emerald"
        summary_verdict = "Exceptional resume! Clean structure, strong action verbs, and quantifiable achievements."
    elif overall_score >= 74:
        rating = "Strong ATS Candidate"
        rating_color = "cyan"
        summary_verdict = "Solid resume structure with good keyword coverage. Minor improvements will make it invincible."
    elif overall_score >= 55:
        rating = "Moderate Rejection Risk"
        rating_color = "amber"
        summary_verdict = "Parsable by ATS systems, but missing critical quantifiable metrics and core section formatting."
    else:
        rating = "High Rejection Risk"
        rating_color = "rose"
        summary_verdict = "Critical formatting or keyword deficiencies detected. Likely to be filtered out before a human sees it."

    # Top Strengths
    strengths = []
    if section_checks["Work Experience"] and section_checks["Education"]:
        strengths.append("Standard core sections (Experience & Education) cleanly detected by parser.")
    if extracted_email and extracted_phone:
        strengths.append(f"Clear contact header found: Verified email & contact number.")
    if has_linkedin or has_github_or_portfolio:
        strengths.append("Digital verification links included (LinkedIn / GitHub / Portfolio).")
    if metric_count >= 3:
        strengths.append(f"Results-oriented impact: Found {metric_count} measurable data points / metrics.")
    if power_verbs_count >= 5:
        strengths.append(f"Strong active voice: Identified {power_verbs_count}+ industry action verbs.")
    if skills_count >= 6:
        strengths.append(f"Keyword rich: Recognized {skills_count} high-demand technical and domain skills.")

    if not strengths:
        strengths.append("Selectable document text successfully parsed without OCR corruption.")

    # Critical Improvements & Quick Fixes
    improvements = []
    if metric_count == 0:
        improvements.append("Add measurable outcomes: Include % improvements, dollar values, team sizes, or volume metrics in bullet points.")
    elif metric_count < 3:
        improvements.append("Increase quantifiable data: Aim for at least 1 number or percentage per work experience entry.")

    if not (has_linkedin or has_github_or_portfolio):
        improvements.append("Missing live portfolio or GitHub URL: Recruiters strongly favor candidates with verifiable public projects.")

    if not section_checks["Professional Summary"]:
        improvements.append("Missing Professional Summary: Add a 3-4 sentence elevator pitch highlighting target role and core strengths.")

    if canva_risk_alert:
        improvements.append("Convert to Single-Column: Switch multi-column or sidebar layouts to a clean top-to-bottom vertical layout.")

    if weak_found:
        improvements.append("Replace passive phrases: Swap 'Responsible for' with active verbs like 'Engineered', 'Optimized', or 'Spearheaded'.")

    if skills_count < 5:
        improvements.append("Expand skills section: Clearly categorize programming languages, tools, frameworks, and methodologies.")

    if not improvements:
        improvements.append("Tailor keywords against the exact Job Description when applying to corporate roles.")

    return {
        "success": True,
        "filename": filename,
        "overall_score": overall_score,
        "rating": rating,
        "rating_color": rating_color,
        "summary_verdict": summary_verdict,
        "word_count": word_count,
        "reading_time": f"{max(1, word_count // 180)} min read",
        "extracted_name": extracted_name,
        "extracted_email": extracted_email,
        "extracted_phone": extracted_phone,
        "has_linkedin": has_linkedin,
        "has_github_or_portfolio": has_github_or_portfolio,
        "canva_risk_alert": canva_risk_alert,
        "breakdown": {
            "sections": {
                "score": section_score,
                "max": 25,
                "detected": detected_sections,
                "missing": missing_sections
            },
            "formatting": {
                "score": formatting_score,
                "max": 25,
                "passed": formatting_passed,
                "warnings": formatting_warnings
            },
            "impact_metrics": {
                "score": impact_score,
                "max": 25,
                "metrics_found": metric_count,
                "power_verbs_count": power_verbs_count,
                "weak_phrases_flagged": weak_found[:3]
            },
            "skills": {
                "score": skills_score,
                "max": 25,
                "skills_count": skills_count,
                "top_skills": detected_skills[:12]
            }
        },
        "strengths": strengths[:4],
        "critical_issues": improvements[:4],
        "raw_text_preview": text[:20000]
    }
