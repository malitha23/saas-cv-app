# 📘 DreemFolio AI — Complete User Guide & Operational Manual
**Version 2.3.0 • Enterprise Edition**
*Comprehensive step-by-step guide for new users & administrators covering 100% of platform features, registration, login, validations, ATS optimization, and AI engines.*

---

## 📑 Table of Contents
1. [Platform Overview & System Architecture](#1-platform-overview--system-architecture)
2. [New User Onboarding & Quick Start Journey](#2-new-user-onboarding--quick-start-journey)
3. [Authentication, Registration & Login Workflows](#3-authentication-registration--login-workflows)
   - [Registration Workflow & Form Validations](#registration-workflow--form-validations)
   - [Sign-In / Login Workflow & Security](#sign-in--login-workflow--security)
   - [Google 1-Tap / OAuth2 Native Sign-In](#google-1-tap--oauth2-native-sign-in)
   - [Session Management & JWT Storage](#session-management--jwt-storage)
   - [Password Rules & Anti-Bruteforce Protection](#password-rules--anti-bruteforce-protection)
4. [SaaS Plan Tiers, Quotas & Dynamic Currency Billing](#4-saas-plan-tiers-quotas--dynamic-currency-billing)
5. [AI Resume Architect & 100% ATS Optimizer](#5-ai-resume-architect--100-ats-optimizer)
   - [File Upload, Magic-Bytes Validation & Parsing](#file-upload-magic-bytes-validation--parsing)
   - [Job Description Matching & Role Archetypes](#job-description-matching--role-archetypes)
   - [Google XYZ Formula & Active Verb Optimization](#google-xyz-formula--active-verb-optimization)
   - [Live Real-Time ATS Audit Checklist](#live-real-time-ats-audit-checklist)
6. [Dual PDF Generation Engine (Classic ATS vs Modern Visual Photo CV)](#6-dual-pdf-generation-engine-classic-ats-vs-modern-visual-photo-cv)
7. [AI Cover Letter Studio & Digital Signatures](#7-ai-cover-letter-studio--digital-signatures)
8. [Interactive Developer Portfolio Studio & Custom Domains](#8-interactive-developer-portfolio-studio--custom-domains)
9. [QR Smart Card, Digital vCard & 4-Digit Encrypted PIN System](#9-qr-smart-card-digital-vcard--4-digit-encrypted-pin-system)
10. [AI Job Hunter, Application Copilot & Kanban Tracker](#10-ai-job-hunter-application-copilot--kanban-tracker)
11. [24/7 AI Career Copilot Chatbot](#11-247-ai-career-copilot-chatbot)
12. [AI Spoken Voice Mock Interview Studio](#12-ai-spoken-voice-mock-interview-studio)
13. [Real-Time Gemini Live Video Conference & Mistake HUD Studio](#13-real-time-gemini-live-video-conference--mistake-hud-studio)
14. [MySQL Cloud Auto-Save & Revision Persistence](#14-mysql-cloud-auto-save--revision-persistence)
15. [Super Admin Command Center (/paneladmin)](#15-super-admin-command-center-paneladmin)
16. [Comprehensive System Validations, Error Codes & Rate Limits](#16-comprehensive-system-validations-error-codes--rate-limits)
17. [Troubleshooting & Frequently Asked Questions (FAQ)](#17-troubleshooting--frequently-asked-questions-faq)

---

## 1. Platform Overview & System Architecture

**DreemFolio AI** is an enterprise micro-SaaS career acceleration ecosystem. It bridges the gap between candidate qualifications and corporate recruitment algorithms (Applicant Tracking Systems - ATS) while providing live multimodal AI preparation tools.

### Core Architectural Pillars
- **Backend**: FastAPI (Python 3.12/3.14) with asynchronous endpoints, WebSockets, and SQLAlchemy ORM (MySQL persistence).
- **Frontend**: Lightweight Alpine.js reactive state machine, Tailwind CSS, Lucide icons, and responsive split-pane UI.
- **AI Intelligence**: Google Gemini 2.5 Flash API for high-speed resume tailoring, STAR scoring, job kits, and live voice synthesis.
- **Multimodal Video Call**: Direct bi-directional WebSockets (`/ws/conference/live`) streaming 24kHz raw PCM audio with Google Gemini Live.
- **PDF Vector Engine**: Dual-layer generation using ReportLab for pixel-perfect single-column ATS vector compliance and HTML5 A4 print styling.

---

## 2. New User Onboarding & Quick Start Journey

When a new user visits DreemFolio AI for the first time, follow this 4-step quick start path:

1. **Sign Up / Sign In**: Create an account via email or Google to enable cloud saving and PDF downloads.
2. **Upload Existing CV or Select Sample**: Upload a PDF/Word file or click one of the pre-built sample personas.
3. **Paste Job Description & Tailor**: Paste the target job description and click **"Optimize & Tailor for Job"**.
4. **Export & Prepare**: Download your 100% ATS PDF, publish your hosted portfolio, and launch an AI Mock Video Interview.

### Navigating the Workspaces
- **Header Bar**: Displays current plan badge, real-time quota counters, theme selector, quick navigation tabs (`Resume`, `Cover Letter`, `Portfolio`, `Raw Text`, `Job Hunter`), and interview launch buttons (`🎤 Voice Interview`, `📹 AI Conference`).
- **Left Panel (Inputs & Form Editors)**: File upload dropzone, target job description textarea, archetype selector, and expandable accordion editors for Personal Info, Experience, Education, Projects, and Skills.
- **Right Panel (Live Interactive Workspace)**: Instant live preview with zoom controls, template selector, ATS scoring meters, and one-click PDF download buttons.
- **Floating Controls**: 24/7 AI Career Copilot floating orb on the bottom-right corner.

---

## 3. Authentication, Registration & Login Workflows

DreemFolio AI provides enterprise-grade authentication with multi-method flexibility, secure password hashing, and anti-abuse safeguards.

### Registration Workflow & Form Validations
To create a new account:
1. Click the **"Sign In / Register"** button in the header or on the guest banner.
2. Select the **"Register"** tab in the modal.
3. Fill in the registration form fields:

| Field Name | Rules & Validations | Error Behavior if Invalid |
| :--- | :--- | :--- |
| **Full Name** | String, max 100 characters. Defaults to "Candidate" if omitted. | Trimmed of whitespace; safe for display. |
| **Email Address** | Must be a valid email format (`user@domain.com`). Converted automatically to lowercase. | Shows alert: *"Please enter a valid email address."* Returns HTTP 422 if invalid. |
| **Password** | **Minimum 6 characters** length required. Encrypted using industry-standard `bcrypt`. | Shows alert: *"Password must be at least 6 characters long."* |

4. **Duplicate Email Prevention**: If the email is already registered, the system displays:
   > ⚠️ *"An account with this email address already exists. Please log in."* (HTTP 400).
5. **Auto-Login on Register**: Upon successful registration, the backend automatically issues a secure JWT bearer token and logs the user in immediately.

### Sign-In / Login Workflow & Security
To log into an existing account:
1. Click **"Sign In"** in the top navigation.
2. Enter your registered email address and password.
3. Click **"Sign In"**.
4. **Validation & Security Checks**:
   - Incorrect password or non-existent email displays: *"Invalid email or password. Please check your credentials."* (HTTP 401).
   - Deactivated accounts display: *"Your account has been deactivated."* (HTTP 403).
   - Once authenticated, the JWT access token is stored in the browser's `localStorage` under `saas_auth_token`.

### Google 1-Tap / OAuth2 Native Sign-In
1. Click the **"Continue with Google"** / **"Sign up with Google"** button in the authentication modal.
2. A native, secure Google authentication popup opens.
3. Select your Google account.
4. Google returns an identity token verified securely on the server via `verify_google_credential_token`.
5. If you are a new Google user, an account is created instantly with your Google profile avatar and full name.

### Session Management & JWT Storage
- The token is passed as `Authorization: Bearer <token>` in the HTTP headers for all protected requests.
- When you click **"Log Out"**, the token is purged from `localStorage`, and the application cleanly resets all user state to guest mode.

### Password Rules & Anti-Bruteforce Protection
- **Rate Limit**: Maximum **5 registration attempts** per minute per IP, and maximum **10 login attempts** per minute per IP.
- If exceeded, the server returns HTTP 429 with the exact seconds remaining before retry (`Retry-After`).

---

## 4. SaaS Plan Tiers, Quotas & Dynamic Currency Billing

DreemFolio AI features automated daily quota resets and localized purchasing power parity:

| Feature / Quota | Free Starter Tier | Pro Career ($9 / Rs. 990 / mo) | Elite Lifetime ($29 / Rs. 3,200) |
| :--- | :--- | :--- | :--- |
| **Daily AI Tailoring Runs** | 5 runs / day | **Unlimited** | **Unlimited** |
| **Classic ATS PDF Downloads** | 2 Lifetime downloads free | **Unlimited** | **Unlimited** |
| **Visual Photo CV Downloads** | 1 Lifetime download free | **Unlimited** | **Unlimited** |
| **AI Cover Letter Exports** | 3 Lifetime (1st unwatermarked) | **Unlimited (Clean)** | **Unlimited (Clean)** |
| **Cloud Auto-Save Resumes** | 3 saved resumes | **Unlimited** | **Unlimited** |
| **Hosted Web Portfolios** | Preview only | 1 Active Live Site (`/p/{slug}`) | Unlimited Sites + Custom Domain |
| **AI Job Hunter & Copilot** | 4 vacancies / 1 kit per day | **Unlimited kits & search** | **Unlimited** |
| **Voice Mock Interview** | 1 session / day | **Unlimited practice** | **Unlimited** |
| **Gemini Live Conference** | 1 session / day | **Unlimited live calls** | **Unlimited** |

---

## 5. AI Resume Architect & 100% ATS Optimizer

### File Upload, Magic-Bytes Validation & Parsing
1. In the **Step 1 (Upload)** section on the left panel, drag and drop your existing resume or click to browse.
2. **Strict Validations**:
   - **Supported Extensions**: `.pdf`, `.docx`, `.txt`.
   - **File Size Limit**: Strict **10 MB maximum** (HTTP 413 if exceeded).
   - **Magic Header Verification**: PDF files must start with the authentic `%PDF-` byte header to block disguised executables.
3. **Automatic Extraction**: The system parses candidate name, email, phone number, work history, education, and technical skills into editable fields.

### Job Description Matching & Role Archetypes
1. In **Step 2 (Target Job Description)**, paste the complete job posting text.
2. Specify the **Target Job Title** and **Target Company**.
3. Select an **Archetype**:
   - `Auto-Detect`: Let AI determine the best approach.
   - `Software Engineering / DevOps`: Highlights system architecture, concurrency, CI/CD, and scale.
   - `QA & Test Automation`: Emphasizes test frameworks, defect density reduction, and reliability.
   - `Automotive / Engineering Technician`: Focuses on OEM diagnostics, electrical schematics, and repairs.
   - `Data Science & AI`: Focuses on machine learning models, ETL pipelines, and business metrics.
   - `Product / Executive Management`: Focuses on stakeholder leadership, P&L, and product roadmaps.

### Google XYZ Formula & Active Verb Optimization
Click **"⚡ Optimize & Tailor for Job"**. Gemini transforms ordinary experience bullet points into high-impact accomplishments using the formula:
> *"Accomplished [X], as measured by [Y], by doing [Z]"*

*Example:* *"Accelerated API throughput by 42% (Y) by refactoring microservice database queries and implementing Redis caching (Z), supporting 10,000+ daily active users (X)."*

### Live Real-Time ATS Audit Checklist
The right panel displays a comprehensive ATS score audit:
- **Overall ATS Score (0 - 100)**: Calculated by keyword density and semantic relevance.
- **Keyword Alignment**: Matched keywords (green badges) vs missing critical JD keywords (red recommendations).
- **Action Verbs Count**: Verifies dynamic words (*Engineered, Architected, Spearheaded, Diagnosed*).
- **Impact Quantification**: Flags whether numbers, dollar amounts, or percentages are present.

---

## 6. Dual PDF Generation Engine (Classic ATS vs Modern Visual Photo CV)

DreemFolio provides two distinct export engines designed for different hiring stages:

### 1. Classic Single-Column ATS Format (ReportLab Vector Engine)
- **Best For**: Submitting to enterprise ATS portals (Workday, Taleo, Greenhouse, Lever, iCIMS).
- **Characteristics**: Single-column linear layout, standard fonts (Helvetica), strict black-and-white high-contrast text, machine-readable tables, no graphics or multi-column layouts that can confuse parsers.
- **Export**: Click **"Download ATS PDF"** in the top action bar.

### 2. Modern Visual Photo CV Format
- **Best For**: Direct email to recruiters, networking, LinkedIn messaging, or creative/executive positions.
- **Themes**:
  - `Indigo Banner`: Corporate executive with styled headers.
  - `Visual Sidebar`: Two-column layout with photo and skills progress bars.
  - `Emerald Prestige`: Luxurious emerald accents for management roles.
  - `Tech Noir`: Sleek dark-mode aesthetic for software developers.
- **Export**: Toggle template style to your preferred visual format and click **"Download Visual CV"**.

---

## 7. AI Cover Letter Studio & Digital Signatures

1. Switch to the **Cover Letter** tab in the top navigation.
2. Select your desired tone:
   - `Professional`: Balanced, formal, and authoritative.
   - `Confident & Assertive`: High-energy, achievement-driven tone.
   - `Enthusiastic`: Passionate and company culture-focused.
   - `Executive`: High-level leadership and strategic alignment.
3. **Digital Signature Integration**:
   - Choose between **Script Calligraphy** (3 cursive styles), **Draw Signature** (interactive canvas pad), or **Upload PNG**.
4. **Export Options**: Download as a formatted PDF or copy raw text with 1 click.

---

## 8. Interactive Developer Portfolio Studio & Custom Domains

Every resume can instantly become a live, hosted web portfolio:

1. Switch to the **Portfolio** tab.
2. Select a layout theme:
   - `Bento Grid`: Modern Apple/Linear style cards.
   - `Split Sidebar`: Left fixed profile with right scrolling showcase.
   - `Terminal Dev`: Cyberpunk / CLI dark mode for developers.
   - `Editorial Swiss`: High-typography minimalist magazine style.
   - `Neon Glass`: Glassmorphism with glowing gradients.
3. Configure **Contact Form**, **Project Showcases**, and **Proof-of-Work galleries**.
4. **Publishing**: Click **"Publish Portfolio"** to get an instant public URL (`http://localhost:8000/portfolio/<slug>`).
5. **Custom Domain**: Connect your personal domain (e.g. `yourname.com`) by creating a CNAME DNS record and verifying it in the Domain modal.

---

## 9. QR Smart Card, Digital vCard & 4-Digit Encrypted PIN System

DreemFolio bridges offline and online networking:

1. Click **"📱 QR Smart Card"** in the workspace.
2. **Offline Contact QR Code**:
   - Generates a dynamic QR code encoding full `.vcf` contact data.
   - When a recruiter scans it with their phone camera, it immediately prompts them to save your contact information into their mobile phonebook with 1 tap.
3. **4-Digit Encrypted PIN Security**:
   - Protect your sensitive personal phone number and address from internet web scrapers.
   - Enable PIN protection in portfolio settings (e.g. PIN: `1234`).
   - Visitors must enter the 4-digit PIN to reveal protected contact cards.
   - Built-in rate limiting locks out attackers after 10 failed PIN attempts.

---

## 10. AI Job Hunter, Application Copilot & Kanban Tracker

1. Switch to the **Job Hunter** workspace.
2. Enter your desired **Job Title** and **Location** (e.g., *"Full Stack Developer"*, *"Remote"* or *"Colombo, Sri Lanka"*).
3. The AI scans real-time listings and scores each opportunity against your uploaded resume.
4. **Generate Application Kit**:
   - 1-Click generates a customized outreach message, elevator pitch, and tailored cover letter specifically tailored for that specific job posting.
5. **Kanban Status Tracking**:
   - Move jobs across columns: `Saved` ➔ `Applied` ➔ `Interviewing` ➔ `Offered` ➔ `Archived`.

---

## 11. 24/7 AI Career Copilot Chatbot

Click the glowing floating icon in the bottom-right corner:
- **Pre-Built Strategy Chips**:
  - *"Conduct a quick behavioral mock interview for my role"*
  - *"Critique my resume bullets with the Google XYZ formula"*
  - *"Draft a high-converting LinkedIn message to a recruiter"*
  - *"Give me a salary negotiation script for an offer of $95,000"*
- Context-Aware: The copilot automatically references your active resume data to give personalized answers.

---

## 12. AI Spoken Voice Mock Interview Studio

1. Click **"🎤 Voice Interview"** in the header.
2. Choose your role, target company, and question count (3 to 5 questions).
3. Select the interview style: `Behavioral (STAR)`, `Technical Deep-Dive`, or `Executive Leadership`.
4. Click **"Start Voice Interview"**.
5. **How to Use**:
   - The AI interviewer reads the question aloud using voice synthesis.
   - Click the microphone icon and speak your answer.
   - The engine transcribes your spoken words in real time.
6. **Instant Answer Audit**:
   - **STAR Compliance**: Grades your Situation, Task, Action, and Result coverage.
   - **Pacing Metrics**: Measures your Words-Per-Minute (WPM).
   - **Filler-Word Detection**: Flags excessive use of *"um"*, *"like"*, *"you know"*.
7. Download an executive **Interview Performance PDF Dossier** at the conclusion.

---

## 13. Real-Time Gemini Live Video Conference & Mistake HUD Studio

The pinnacle of DreemFolio AI — a real-time, zero-latency technical video interview with Google Gemini Live:

### Architecture & Audio Setup
- **Endpoint**: WebSocket at `ws://localhost:8000/ws/conference/live`.
- **Latency**: Sub-second (**< 800ms**) voice-to-voice streaming with 24,000Hz raw PCM audio.
- **Voices**: Choose between 5 distinctive personas:
  - ⚡ **Alex** (`Puck` — Direct, Energetic Male)
  - ⚡ **Aoede** (`Aoede` — Expressive, Warm Female)
  - ⚡ **Charon** (`Charon` — Deep, Authoritative Male)
  - ⚡ **Kore** (`Kore` — Natural, Conversational Female)
  - ⚡ **Fenrir** (`Fenrir` — Executive, Structured Male)

### Starting a Live Conference
1. Click **"📹 AI Conference"** in the header.
2. Confirm your target role and company.
3. Grant camera and microphone permissions when prompted by your browser.
4. **Mobile Users**: Tap the **"🔊 Tap to Hear / Replay"** button once upon joining to unlock your mobile browser's Web Audio API.

### Live Mistake Interventions ("Waradi Kiyala Denna")
- As you explain technical concepts, the AI listens actively.
- If you state an incorrect specification, miss a critical step, or explain a bug incorrectly, a **Floating HUD Alert** drops down on your screen in real time:
  > *"💡 Technical Intervention: You recommended replacing the motor controller without verifying the CAN-Bus termination resistor! Mention signal integrity checking first."*

---

## 14. MySQL Cloud Auto-Save & Revision Persistence

Never lose your work:
1. When logged in, click the **"💾 Save to Cloud"** button in the header.
2. Give your resume version a title (e.g. *"Google Senior QA Tailor - V2"*).
3. The full structured state, theme preferences, and ATS scores are stored in MySQL.
4. Click **"📁 My Resumes"** to view your saved history, restore past versions, or delete obsolete drafts.

---

## 15. Super Admin Command Center (/paneladmin)

For administrators and platform managers:
1. Log in with an administrative account (`is_admin: true`).
2. Navigate to: `http://localhost:8000/paneladmin`.
3. **Core Controls**:
   - **User Manager**: Search users by name/email, inspect account creation dates, and view plan statuses.
   - **Instant Plan Upgrades**: Override any user's tier to `free`, `pro`, `sprint_pass`, or `lifetime` with 1 click.
   - **System Performance Analytics**: Real-time counters for generated resumes, PDF downloads, and active live conference sessions.
   - **Country Pricing Matrix**: Set localized pricing per country (e.g., configure Sri Lanka LKR rates, US Dollar rates, Euro rates).
   - **SaaS Quota Controls**: Adjust free daily limits for AI tailoring runs and PDF downloads system-wide.

---

## 16. Comprehensive System Validations, Error Codes & Rate Limits

| Endpoint / Operation | Rule / Validation | Error Code & User Message |
| :--- | :--- | :--- |
| **User Registration** | Valid email format, min 6-char password | `400 Bad Request`: Email already exists.<br>`422 Unprocessable`: Password too short. |
| **User Login** | Valid credentials & active account | `401 Unauthorized`: Invalid email or password.<br>`403 Forbidden`: Account deactivated. |
| **File Upload** | Max 10MB, `.pdf`, `.docx`, `.txt`, valid magic bytes | `413 Payload Too Large`: File exceeds 10MB.<br>`400 Bad Request`: Invalid PDF header. |
| **AI Resume Tailoring** | Non-empty resume text and job description | `400 Bad Request`: Resume or JD cannot be empty.<br>`402 Payment Required`: Daily AI quota reached. |
| **Portfolio PIN Verification** | Max 10 attempts per minute | `429 Too Many Requests`: Too many PIN attempts.<br>`401 Unauthorized`: Invalid 4-digit PIN. |
| **Direct PDF Download** | Verified tier or remaining free quota | `401 Unauthorized`: Sign in to download.<br>`402 Payment Required`: Quota exhausted. |
| **Live WebSockets** | Valid Gemini API credentials | Code 1000 on clean disconnect; Code 1006 on network disruption. |

---

## 17. Troubleshooting & Frequently Asked Questions (FAQ)

### Q: I cannot hear sound on my smartphone during the AI Conference.
**A:** iOS Safari and Android Chrome require an explicit user touch gesture before playing streaming audio. Tap the **"🔊 Tap to Hear / Replay"** button on the conference screen to unlock the audio context.

### Q: Why did the PDF preview show a blank screen?
**A:** Click the **"Image Mode"** toggle in the preview toolbar to switch from HTML5 Canvas to direct PNG rendering.

### Q: Can I practice in Sinhala or other languages?
**A:** While the user manual and core prompts are optimized for English technical terms, Gemini can understand and respond in multiple languages if prompted in the AI Career Copilot!

---

*DreemFolio AI — Empowering Global Professionals with High-Impact Agentic Careers.*
