from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SocialLink(BaseModel):
    name: str = Field(..., description="Name of the platform (e.g. 'GitHub', 'LinkedIn', 'Twitter/X', 'Instagram', 'Portfolio', 'Calendly', 'WhatsApp')")
    url: str = Field(..., description="Target URL or handle")
    icon: str = Field(default="globe", description="Lucide icon name: github, linkedin, twitter, instagram, youtube, mail, globe, calendar, message-circle")
    enabled: bool = Field(default=True, description="Whether to display this link on the portfolio")


class PersonalInfo(BaseModel):
    full_name: str = Field(..., description="Full candidate name")
    email: str = Field(..., description="Professional email address")
    phone: str = Field(..., description="Phone number formatted cleanly")
    location: str = Field(..., description="City, State/Country e.g. 'San Francisco, CA' or 'Sri Lanka'")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL or handle")
    portfolio: Optional[str] = Field(None, description="Portfolio website URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    avatar_url: Optional[str] = Field(None, description="Candidate profile photo or avatar URL")
    hero_headline: Optional[str] = Field(None, description="Custom hero headline or tagline")
    availability_badge: Optional[str] = Field(
        default="Available for High-Impact Roles & Consulting",
        description="Availability status badge text"
    )
    custom_domain: Optional[str] = Field(None, description="Custom private domain e.g. 'malitha.dev'")
    social_links: List[SocialLink] = Field(default_factory=list, description="Dynamic list of social media and custom links")


class SkillCategory(BaseModel):
    category_name: str = Field(..., description="Category name (e.g. 'Languages & Frameworks', 'Mobile Development', 'Databases & Tools')")
    skills: List[str] = Field(default_factory=list, description="List of matched hard/soft skills")
    skill_levels: Dict[str, int] = Field(default_factory=dict, description="Skill name to percentage (10 to 100)")


class WorkExperienceItem(BaseModel):
    job_title: str = Field(..., description="Official job title")
    company: str = Field(..., description="Company or organization name")
    location: Optional[str] = Field(None, description="City, State or 'Remote'")
    start_date: str = Field(..., description="Start date (e.g. 'Nov 2024')")
    end_date: str = Field(..., description="End date (e.g. 'Present' or 'May 2024')")
    bullet_points: List[str] = Field(
        default_factory=list,
        description="High-impact bullet points rewritten with strong action verbs, quantifiable metrics, and JD keyword alignment."
    )


class EducationItem(BaseModel):
    degree: str = Field(..., description="Degree and major (e.g. 'BSc in Software Engineering')")
    institution: str = Field(..., description="University / College name")
    location: Optional[str] = Field(None, description="City, State or Country")
    graduation_year: str = Field(..., description="Graduation year (e.g. '2023 - 2025')")
    details: Optional[str] = Field(None, description="GPA, Honors, or notable coursework")


class ProjectItem(BaseModel):
    name: str = Field(..., description="Project name")
    technologies: List[str] = Field(default_factory=list, description="Technologies & frameworks used")
    link: Optional[str] = Field(None, description="GitHub repo link or primary URL")
    demo_url: Optional[str] = Field(None, description="Live preview / deployed app URL")
    description_bullets: List[str] = Field(
        default_factory=list,
        description="Bullet points explaining scope, architecture, and measurable outcome"
    )


class CertificationItem(BaseModel):
    name: str = Field(..., description="Certification title or award")
    issuer: str = Field(..., description="Issuing organization")
    year: Optional[str] = Field(None, description="Year awarded")


class KeywordDetail(BaseModel):
    keyword: str
    frequency: int = 1
    found_in_resume: bool = True
    importance: str = "high"


class ATSAnalysis(BaseModel):
    overall_score: int = Field(..., description="ATS Match Score from 0 to 100")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords found in both JD and candidate profile")
    missing_keywords: List[str] = Field(default_factory=list, description="Target JD keywords recommended to incorporate")
    formatting_score: int = Field(default=100, description="ATS structural formatting compliance score (0-100)")
    impact_quantification_score: int = Field(default=92, description="Metric and active verb impact score (0-100)")
    contact_score: int = Field(default=100, description="Contact details completeness (0-100)")
    experience_score: int = Field(default=95, description="Work experience alignment score (0-100)")
    skills_score: int = Field(default=92, description="Skills alignment score (0-100)")
    action_verbs_count: int = Field(default=14, description="Number of strong action verbs identified")
    metrics_quantified_count: int = Field(default=8, description="Number of quantifiable metrics (% or $) included")
    summary_feedback: str = Field(..., description="Quick executive assessment of ATS readiness")
    recommendations: List[str] = Field(default_factory=list, description="Actionable suggestions to improve interview conversion")


class CoverLetter(BaseModel):
    recipient_name: str = Field(default="Hiring Team", description="Name or 'Hiring Manager'")
    recipient_title: Optional[str] = Field(default="Talent Acquisition Team", description="Title")
    company_name: str = Field(..., description="Target company name")
    company_address: Optional[str] = Field(None, description="Company address or location")
    salutation: str = Field(default="Dear Hiring Manager,", description="Salutation")
    opening_paragraph: str = Field(..., description="Compelling hook expressing enthusiasm for the exact role and company")
    body_paragraph: str = Field(..., description="Evidence of relevant past achievements directly solving JD requirements")
    closing_paragraph: str = Field(..., description="Call to action, availability for interview, and appreciation")
    sign_off: str = Field(default="Sincerely,", description="Formal sign-off")
    tone: str = Field(default="professional", description="Tone: professional, assertive, enthusiastic, or executive")
    letter_date: Optional[str] = Field(default=None, description="Formal letter date e.g. 'September 3, 2026'")
    reference_subject: Optional[str] = Field(default=None, description="Subject or Reference line e.g. 'Application for Senior Software Engineer'")
    signature_mode: str = Field(default="script", description="Signature mode: 'script', 'draw', 'upload', or 'none'")
    signature_style: str = Field(default="script_1", description="Script calligraphy style: 'script_1', 'script_2', 'script_3'")
    signature_image_data: Optional[str] = Field(default=None, description="Base64 PNG of drawn or uploaded signature")
    sign_off_title: Optional[str] = Field(default=None, description="Signer designation/title below name e.g. 'Software Engineer'")
    postscript: Optional[str] = Field(default=None, description="Optional P.S. note at the bottom")
    enclosure: Optional[str] = Field(default=None, description="Optional Enclosure/Attachment note e.g. 'Enclosure: Resume & Portfolio'")
    layout_style: str = Field(default="modern_banner", description="Layout style: 'modern_banner', 'classic_corporate', 'minimal_clean'")
    full_text: Optional[str] = Field(None, description="Complete formatted text representation")


class MatchedJobOpportunity(BaseModel):
    title: str = Field(..., description="Job title of matching role")
    company_type: str = Field(default="Tech / SaaS / Enterprise", description="Target industry or company tier e.g. 'Cloud SaaS / Global Remote'")
    match_score: int = Field(default=95, description="Calculated candidate match score (0-100)")
    match_reason: str = Field(..., description="Why the candidate is a strong fit based on their verified skills & experience")
    key_skills: List[str] = Field(default_factory=list, description="Key overlapping skills")
    work_mode: str = Field(default="Remote", description="Work mode: 'Remote', 'Hybrid', or 'On-site'")
    experience_level: str = Field(default="Mid-Senior", description="Experience level e.g. 'Entry-Level', 'Mid-Level', 'Senior', 'Lead'")
    estimated_salary: Optional[str] = Field(default=None, description="Market salary estimate e.g. '$95k - $125k / yr'")
    search_keywords: str = Field(..., description="Concise keywords for live job search queries")


class TailoredResume(BaseModel):
    personal_info: PersonalInfo
    target_job_title: str = Field(..., description="Target job title matching the JD")
    target_company: Optional[str] = Field(None, description="Target company name")
    professional_summary: str = Field(
        ...,
        description="3-4 sentence professional summary tightly tailored to target role with matched keywords"
    )
    template_style: str = Field(default="classic", description="Template style: 'classic', 'modern', 'minimal'")
    font_size_scale: str = Field(default="standard", description="Font scaling: 'compact', 'standard', 'spacious'")
    font_family: str = Field(default="Helvetica", description="Font family: 'Helvetica', 'Times-Roman', 'Courier'")
    custom_accent_color: Optional[str] = Field(default=None, description="Custom hex accent color e.g. '#1E3A8A'")
    show_photo: bool = Field(default=False, description="Show/Hide Profile Photo in Visual Resumes")
    show_skill_bars: bool = Field(default=True, description="Show progress bars for skills in visual formats")
    skill_bar_style: str = Field(default="sleek", description="Progress bar style: 'sleek', 'segmented', 'badge'")
    show_summary: bool = Field(default=True, description="Show/Hide Professional Summary")
    show_skills: bool = Field(default=True, description="Show/Hide Technical Skills")
    show_experience: bool = Field(default=True, description="Show/Hide Work Experience")
    show_projects: bool = Field(default=True, description="Show/Hide Key Projects")
    show_education: bool = Field(default=True, description="Show/Hide Education")
    show_certifications: bool = Field(default=True, description="Show/Hide Certifications")
    role_archetype: str = Field(
        default="general_professional",
        description="Role blueprint: 'software_engineering', 'trade_technical', 'management_executive', 'healthcare_medical', 'general_professional'"
    )
    section_order: List[str] = Field(
        default_factory=lambda: ["summary", "skills", "experience", "projects", "education", "certifications"],
        description="Display order of resume sections"
    )
    skill_categories: List[SkillCategory] = Field(default_factory=list)
    work_experience: List[WorkExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    ats_analysis: ATSAnalysis
    cover_letter: CoverLetter

    # Recommended Career Opportunities
    matched_jobs: List[MatchedJobOpportunity] = Field(
        default_factory=list,
        description="Similar high-match job opportunities tailored to candidate's profile"
    )

    # Full Portfolio Web Customization Suite
    portfolio_theme: str = Field(default="bento_grid", description="Portfolio layout: 'bento_grid', 'split_sidebar', 'terminal_dev', 'editorial_swiss', 'neon_glass'")
    portfolio_accent_color: Optional[str] = Field(default=None, description="Custom accent hex color for portfolio")
    portfolio_font: str = Field(default="Inter", description="Portfolio font family: 'Inter', 'JetBrains Mono', 'Outfit', 'Playfair Display', 'Plus Jakarta Sans', 'Fira Code'")
    portfolio_show_bio: bool = Field(default=True, description="Show/Hide Bio section")
    portfolio_show_skills: bool = Field(default=True, description="Show/Hide Skills section")
    portfolio_show_experience: bool = Field(default=True, description="Show/Hide Work Experience section")
    portfolio_show_projects: bool = Field(default=True, description="Show/Hide Key Projects section")
    portfolio_show_education: bool = Field(default=True, description="Show/Hide Education section")
    portfolio_show_resume_download: bool = Field(default=True, description="Show direct ATS Resume download button on portfolio")
    portfolio_cta_text: str = Field(default="Get in Touch", description="Primary call-to-action button text")
    portfolio_cta_url: Optional[str] = Field(default=None, description="Primary call-to-action URL or mailto")
    portfolio_metrics: List[Dict[str, str]] = Field(default_factory=list, description="Custom stat counter highlights (label & value)")


class TailorRequest(BaseModel):
    resume_text: str = Field(..., description="Raw text of the candidate's existing resume")
    job_description: str = Field(..., description="Target Job Description text")
    job_title: Optional[str] = Field(None, description="Optional target job title override")
    company_name: Optional[str] = Field(None, description="Optional target company override")
    role_archetype: Optional[str] = Field(
        "auto",
        description="Role blueprint: 'auto', 'software_engineering', 'trade_technical', 'management_executive', 'healthcare_medical', 'general_professional'"
    )
    template_style: Optional[str] = Field("classic", description="Template: classic, modern, minimal")
    cover_letter_tone: Optional[str] = Field("professional", description="Tone of cover letter")
    api_key: Optional[str] = Field(None, description="User-provided Gemini API key (optional)")


class ParseResponse(BaseModel):
    success: bool
    text: str
    filename: Optional[str] = None
    character_count: int
    detected_sections: List[str] = Field(default_factory=list)
    extracted_name: Optional[str] = None
    extracted_email: Optional[str] = None
    extracted_phone: Optional[str] = None
    message: Optional[str] = None


class DomainVerifyRequest(BaseModel):
    domain: str = Field(..., description="Custom domain name e.g. 'malitha.dev'")
    slug: str = Field(..., description="Portfolio user slug")


class CheckoutRequest(BaseModel):
    tier: str = Field(..., description="'single' ($3), 'monthly' ($9), or 'lifetime' ($29)")
    email: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# SAAS AUTHENTICATION & PERSISTENCE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, description="Password (at least 6 characters)")
    full_name: str = Field(default="Candidate", description="User's full name")


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    plan_tier: str
    created_at: str
    is_admin: bool = False
    subscription_status: str = "active"
    subscription_started_at: Optional[str] = None
    subscription_expires_at: Optional[str] = None
    subscription_days_remaining: Optional[int] = None
    subscription_validity_label: str = "Lifetime Free"
    daily_ai_generations_count: int = 0
    daily_generations_remaining: Optional[int] = None
    daily_pdf_downloads_count: int = 0
    daily_pdf_downloads_remaining: Optional[int] = None
    daily_cover_letter_downloads_count: int = 0
    daily_cover_letter_downloads_remaining: Optional[int] = None
    # Career Features Daily Quotas
    daily_copilot_kits_count: int = 0
    daily_copilot_kits_remaining: Optional[int] = 1
    daily_chat_count: int = 0
    daily_chat_remaining: Optional[int] = 3
    # Strategic Lifetime Quotas
    lifetime_ats_downloads_count: int = 0
    lifetime_ats_downloads_remaining: Optional[int] = 2
    lifetime_visual_downloads_count: int = 0
    lifetime_visual_downloads_remaining: Optional[int] = 1
    lifetime_cover_letter_downloads_count: int = 0
    lifetime_cover_letter_downloads_remaining: Optional[int] = 3
    # Google OAuth2 Fields
    avatar_url: Optional[str] = None
    auth_provider: str = "email"
    google_id: Optional[str] = None

    class Config:
        from_attributes = True


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., description="Google ID Token JWT returned by Google Identity Services")
    client_id: Optional[str] = Field(None, description="Optional Client ID for audience verification")


class GoogleConfigResponse(BaseModel):
    client_id: Optional[str] = Field(None, description="Active Google OAuth 2.0 Client ID")
    is_enabled: bool = Field(default=False, description="Whether Google Sign-In is configured and active")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SubscriptionUpgradeRequest(BaseModel):
    plan_tier: str = Field(..., description="'pro' or 'elite' or 'sprint'")
    duration_months: int = Field(default=1, description="Duration in months (1, 3, or 12)")
    payment_method: Optional[str] = Field(default="card", description="Payment method: card, payhere, stripe, simulation")


class SubscriptionStatusResponse(BaseModel):
    plan_tier: str
    subscription_status: str
    is_active: bool
    subscription_started_at: Optional[str]
    subscription_expires_at: Optional[str]
    subscription_days_remaining: Optional[int]
    subscription_validity_label: str
    daily_ai_generations_count: int
    daily_generations_limit: Optional[int]
    daily_generations_remaining: Optional[int]
    daily_pdf_downloads_count: int = 0
    daily_pdf_downloads_limit: Optional[int] = 1
    daily_pdf_downloads_remaining: Optional[int] = None
    lifetime_ats_downloads_count: int = 0
    lifetime_ats_downloads_limit: Optional[int] = 2
    lifetime_ats_downloads_remaining: Optional[int] = None
    lifetime_visual_downloads_count: int = 0
    lifetime_visual_downloads_limit: Optional[int] = 1
    lifetime_visual_downloads_remaining: Optional[int] = None
    lifetime_cover_letter_downloads_count: int = 0
    lifetime_cover_letter_downloads_limit: Optional[int] = 3
    lifetime_cover_letter_downloads_remaining: Optional[int] = None
    features: Dict[str, Any]


class CountryPricingConfig(BaseModel):
    country_code: str = Field(..., description="2-letter ISO code e.g. 'LK', 'US', 'IN', or 'DEFAULT'")
    country_name: str = Field(..., description="Country name e.g. 'Sri Lanka'")
    currency_code: str = Field(..., description="'LKR', 'USD', 'INR', 'EUR'")
    currency_symbol: str = Field(..., description="'Rs.', '$', '₹', '€'")
    sprint_price: str = Field(..., description="7-Day Sprint Pass price e.g. 'Rs. 490' or '$4.99'")
    plans: List["PlanItemConfig"]


class CountryPricingResponse(BaseModel):
    country_code: Optional[str] = None
    detected_country: str
    currency: Optional[str] = None
    active_currency: str
    currency_symbol: Optional[str] = None
    active_currency_symbol: str
    sprint_price: str
    plans: List["PlanItemConfig"]
    available_countries: List[Dict[str, str]]


class AdminUpdateCountryPricingRequest(BaseModel):
    country_code: str
    country_name: str
    currency_code: str
    currency_symbol: str
    sprint_price: str
    plans: List["PlanItemConfig"]



class AdminOverviewResponse(BaseModel):
    total_users: int
    free_users: int
    pro_users: int
    elite_users: int
    admin_users: int
    estimated_mrr_usd: float
    total_saved_resumes: int


class AdminUserListItem(BaseModel):
    id: int
    email: str
    full_name: str
    plan_tier: str
    subscription_status: str
    is_admin: bool
    subscription_started_at: Optional[str]
    subscription_expires_at: Optional[str]
    subscription_days_remaining: Optional[int]
    daily_ai_generations_count: int
    daily_pdf_downloads_count: int
    created_at: str


class AdminUpdateUserPlanRequest(BaseModel):
    plan_tier: str = Field(..., description="'free', 'pro', 'elite'")
    duration_days: int = Field(default=30, description="Validity extension days")
    is_admin: Optional[bool] = None


class AdminSettingItem(BaseModel):
    key: str
    value: str
    description: str


class AdminUpdateSettingsRequest(BaseModel):
    settings: Dict[str, str] = Field(..., description="Key-value mapping of updated SaaS settings")


class SaveResumeRequest(BaseModel):
    resume_id: Optional[int] = Field(default=None, description="Existing resume ID to update, or None to create new")
    title: str = Field(default="My Professional Resume", description="Saved resume title")
    resume_data: TailoredResume = Field(..., description="Complete tailored resume state")


class SavedResumeListItem(BaseModel):
    id: int
    title: str
    target_role: Optional[str] = None
    template_style: str
    updated_at: str


class PlanItemConfig(BaseModel):
    plan_key: str = Field(..., description="'free', 'pro', 'elite'")
    title: str = Field(..., description="Display title of the plan")
    badge: Optional[str] = Field(None, description="Badge tag, e.g. 'Freemium', '🔥 Best Seller'")
    price_display: str = Field(..., description="Price display, e.g. '$0', '$9'")
    period_display: str = Field(..., description="Period display, e.g. '/ forever', '/ month'")
    sub_billing_text: Optional[str] = Field("", description="Sub-billing line, e.g. 'or $19 for 3-Month Pass'")
    description: str = Field(..., description="Short marketing description")
    features: List[str] = Field(default_factory=list, description="Bullet points of plan features")
    is_popular: bool = Field(default=False, description="Highlight card style")
    button_text: str = Field(default="Select Plan", description="CTA button label")


class PlansConfigResponse(BaseModel):
    plans: List[PlanItemConfig]


class UpdatePlansConfigRequest(BaseModel):
    plans: List[PlanItemConfig]


# ═══════════════════════════════════════════════════════════════════
# AI Job Hunter, 1-Click Application Copilot & Tracker Schemas
# ═══════════════════════════════════════════════════════════════════

class JobSearchRequest(BaseModel):
    keywords: str = Field(..., description="Job role keywords or technology e.g. 'Senior Frontend Engineer'")
    location: Optional[str] = Field(default="Remote", description="Location or 'Remote'")
    work_mode: Optional[str] = Field(default="all", description="'all', 'remote', 'hybrid', 'onsite'")
    experience_level: Optional[str] = Field(default="all", description="'all', 'entry', 'mid', 'senior', 'lead'")
    limit: int = Field(default=8, ge=1, le=25)


class JobSearchResultItem(BaseModel):
    id: str
    title: str
    company: str
    location: str
    work_mode: str
    salary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    match_score: int = 95
    match_reason: str = "High alignment with candidate core technical stack."
    apply_url: str
    easy_apply_url: str
    posted_time: Optional[str] = "Recently active"


class JobSearchResponse(BaseModel):
    query: str
    location: str
    total_results: int
    results: List[JobSearchResultItem]


class ApplicationKitRequest(BaseModel):
    job_title: str
    company_name: str
    job_description: Optional[str] = None
    work_mode: Optional[str] = "Remote"
    salary_range: Optional[str] = None
    resume_data: Optional[Dict[str, Any]] = None


class ApplicationKitResponse(BaseModel):
    job_title: str
    company_name: str
    elevator_pitch: str = Field(..., description="30-second authentic professional intro")
    why_company: str = Field(..., description="Compelling, tailored reason for applying to this company & role")
    key_achievement: str = Field(..., description="Top quantifiable achievement proving candidate's capability")
    salary_expectation_answer: str = Field(..., description="Tactful, market-rate salary negotiation response")
    availability_notice_answer: str = Field(..., description="Direct availability and notice period statement")
    strengths_summary: List[str] = Field(default_factory=list)
    recommended_custom_qa: List[Dict[str, str]] = Field(default_factory=list)


class TrackedJobCreate(BaseModel):
    job_title: str
    company_name: str = "Target Company"
    location: str = "Remote"
    work_mode: str = "Remote"
    salary_range: Optional[str] = None
    match_score: int = 95
    job_url: Optional[str] = None
    status: str = "wishlist"
    notes: Optional[str] = None
    application_kit_json: Optional[str] = None


class TrackedJobUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    applied_date: Optional[str] = None
    salary_range: Optional[str] = None
    application_kit_json: Optional[str] = None


class TrackedJobResponse(BaseModel):
    id: int
    job_title: str
    company_name: str
    location: str
    work_mode: str
    salary_range: Optional[str] = None
    match_score: int
    job_url: Optional[str] = None
    status: str
    applied_date: Optional[str] = None
    notes: Optional[str] = None
    has_application_kit: bool = False
    created_at: str
    updated_at: str


# ═══════════════════════════════════════════════════════════════════
# AI Career Copilot Chatbot Schemas
# ═══════════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")
    timestamp: Optional[str] = None


class ChatCopilotRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Conversation message history")
    resume_context: Optional[Dict[str, Any]] = Field(default=None, description="Active candidate CV data")
    target_job_title: Optional[str] = Field(default=None, description="Target job title")
    company_name: Optional[str] = Field(default=None, description="Target company name")


class ChatCopilotResponse(BaseModel):
    reply: str = Field(..., description="AI Career Copilot assistant response in markdown format")
    suggested_prompts: List[str] = Field(default_factory=list, description="Follow-up suggested quick actions or questions")
    action_trigger: Optional[Dict[str, Any]] = Field(default=None, description="Optional interactive action trigger")


# ═══════════════════════════════════════════════════════════════════
# AI Voice Mock Interview Simulator Schemas
# ═══════════════════════════════════════════════════════════════════

class InterviewQuestion(BaseModel):
    id: int = Field(..., description="Question index starting at 1")
    category: str = Field(..., description="Category e.g. 'STAR Behavioral', 'Technical Architecture', 'Conflict Resolution'")
    question_text: str = Field(..., description="The spoken interview question")
    interviewer_cue: str = Field(default="Focus on your specific role and measurable impact.", description="Tip/cue for candidate")
    expected_competencies: List[str] = Field(default_factory=list, description="Key skills and criteria evaluated")


class MockInterviewStartRequest(BaseModel):
    target_role: str = Field(default="Professional", description="Target job title")
    target_company: Optional[str] = Field(default=None, description="Target company or organization")
    interview_type: str = Field(default="behavioral", description="'behavioral', 'technical', or 'situational'")
    difficulty: str = Field(default="standard", description="'friendly', 'standard', or 'executive'")
    question_count: int = Field(default=3, ge=1, le=8, description="Number of questions in session")
    resume_context: Optional[Dict[str, Any]] = Field(default=None, description="Active candidate CV data")


class MockInterviewStartResponse(BaseModel):
    session_id: str
    target_role: str
    target_company: Optional[str] = None
    interview_type: str
    difficulty: str
    questions: List[InterviewQuestion]


class EvaluateAnswerRequest(BaseModel):
    session_id: str
    question_id: int
    question_text: str
    candidate_answer_transcript: str
    duration_seconds: int = Field(default=45, ge=1, description="Time in seconds taken to answer")
    target_role: str = "Professional"
    interview_type: str = "behavioral"


class AnswerEvaluationResponse(BaseModel):
    question_id: int
    score: int = Field(..., ge=0, le=100, description="Readiness score for this question")
    star_breakdown: Dict[str, str] = Field(default_factory=dict, description="Evaluation of Situation, Task, Action, Result")
    filler_words_detected: List[str] = Field(default_factory=list)
    filler_words_count: int = 0
    words_per_minute: float = 0.0
    pacing_feedback: str = "Good speaking pace"
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    exemplary_answer: str = Field(..., description="High-impact model answer script")


class FinalInterviewReportRequest(BaseModel):
    session_id: str
    target_role: str
    interview_type: str
    evaluations: List[AnswerEvaluationResponse]


class FinalInterviewReportResponse(BaseModel):
    session_id: str
    overall_score: int = Field(..., ge=0, le=100)
    hiring_verdict: str = Field(..., description="'Strong Hire', 'Hire', 'Borderline', or 'Needs Improvement'")
    verdict_color: str = "emerald"
    competency_scores: Dict[str, int] = Field(default_factory=dict)
    total_filler_words: int = 0
    average_wpm: float = 0.0
    top_strengths: List[str] = Field(default_factory=list)
    critical_gaps: List[str] = Field(default_factory=list)
    actionable_recommendations: List[str] = Field(default_factory=list)
    executive_summary: str


# ═══════════════════════════════════════════════════════════════════
# Real-Time AI Video Conference & Live Mistake Coaching Schemas
# ═══════════════════════════════════════════════════════════════════

class MistakeItem(BaseModel):
    type: str = Field(default="technical_vagueness", description="'technical_vagueness', 'filler_words', 'pacing', 'structure_star', or 'grammar'")
    severity: str = Field(default="warning", description="'tip', 'warning', or 'critical'")
    label: str = Field(..., description="Short mistake headline (e.g. 'Missing Diagnostic Tool Name')")
    explanation: str = Field(..., description="Why this weakens the interview response")
    suggestion: str = Field(..., description="How to rephrase or correct it")


class ConferenceTurnRequest(BaseModel):
    session_id: str
    candidate_transcript: str = Field(..., description="Spoken speech transcribed live from candidate")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    target_role: str = "Automotive Technician"
    target_company: Optional[str] = None
    speaking_duration_seconds: int = 15


class ConferenceTurnResponse(BaseModel):
    interviewer_reply: str = Field(..., description="Spoken verbal reply from AI interviewer")
    live_coaching_nudge: Optional[str] = Field(default=None, description="Floating HUD coaching alert on video")
    mistakes_detected: List[MistakeItem] = Field(default_factory=list)
    words_per_minute: float = 0.0
    filler_words_count: int = 0
    filler_words: List[str] = Field(default_factory=list)
    turn_score: int = Field(default=80, ge=0, le=100)
    is_interview_complete: bool = False


class ConferenceDebriefRequest(BaseModel):
    session_id: str
    target_role: str = "Professional"
    target_company: Optional[str] = None
    turns_history: List[Dict[str, Any]] = Field(default_factory=list)
    all_mistakes: List[Dict[str, Any]] = Field(default_factory=list)


class ConferenceDebriefResponse(BaseModel):
    session_id: str
    overall_score: int = Field(..., ge=0, le=100)
    hiring_verdict: str = Field(..., description="'Strong Hire', 'Hire', 'Borderline', or 'Needs Improvement'")
    verdict_color: str = "emerald"
    total_turns: int = 0
    total_mistakes_count: int = 0
    top_mistakes_corrected: List[MistakeItem] = Field(default_factory=list)
    key_strengths: List[str] = Field(default_factory=list)
    action_plan: List[str] = Field(default_factory=list)
    executive_summary: str




