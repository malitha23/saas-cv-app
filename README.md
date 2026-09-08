# 🚀 DreemFolio AI - ATS-Friendly AI Resume & Cover Letter SaaS

A production-ready Micro-SaaS platform that transforms resumes into 100% ATS-compliant single-column PDF resumes and tailored cover letters in under 10 seconds using Google Gemini Flash.

---

## 🌟 Key Features

- **⚡ Client/Server Resume Parsing:** Extracts clean text from `.pdf`, `.docx`, and `.txt` files without external binary dependencies.
- **🤖 Gemini Flash Structured Engine:** Enforces strict Pydantic JSON schema with constraint prompting:
  - Rewrites bullet points into `[Strong Action Verb] + [Context/Task] + [Measurable Business Metric/Impact]`.
  - Injects target Job Description keywords naturally.
  - **Zero Hallucination:** Only reframes and highlights real candidate achievements.
- **📄 100% ATS-Compliant PDF Generation:**
  - Strict single-column layout powered by **ReportLab**.
  - Standard Helvetica typography and 0.5-inch margins.
  - Guaranteed parsing on **Workday, Taleo, Greenhouse, and Lever**.
- **✉️ Tailored Cover Letter Generator:** Drafts a persuasive, customized 3-paragraph letter matching the hiring company and role.
- **📊 Live ATS Score & Intelligence:**
  - Real-time ATS match score (0-100%).
  - Matched vs. Missing keyword breakdown.
  - Actionable improvement recommendations.
- **✍️ Real-Time Fine-Tuning Editor:** Edit generated bullets, summary, and skills with instant live PDF preview re-rendering.
- **💰 Monetization Ready:** Integrated Lemon Squeezy payment flows ($3 single download / $9 monthly pass).

---

## 🛠️ Tech Stack (No Node.js Required)

- **Backend:** FastAPI + Uvicorn (Python 3.10+)
- **AI Model:** Google Gemini 1.5 / 2.5 Flash (`google-genai` / `google-generative-ai`)
- **PDF Engine:** ReportLab
- **Parsing:** PyPDF + python-docx
- **Frontend:** Modern HTML5 + Tailwind CSS + Alpine.js + Lucide Icons

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure Gemini API Key
Copy `.env.example` to `.env` and set your key from [Google AI Studio](https://aistudio.google.com/):
```env
GEMINI_API_KEY=your_gemini_api_key_here
PORT=8000
```
*(Note: If no API key is provided, the platform automatically runs its built-in deterministic ATS engine for seamless offline demo testing).*

### 3. Run the SaaS Server
```bash
python run.py
```
Open your browser at **[http://localhost:8000](http://localhost:8000)**.

---

## 📁 Project Structure

```
cv-app/
├── app/
│   ├── static/
│   │   ├── app.js            # Reactive Alpine.js SaaS frontend logic
│   │   └── index.html        # Modern split-screen dashboard UI
│   ├── ai_engine.py          # Gemini Flash structured engine & ATS prompt
│   ├── main.py               # FastAPI REST API endpoints & static serving
│   ├── parser.py             # Robust PDF/DOCX/TXT resume text extractor
│   ├── pdf_generator.py      # ReportLab 100% ATS Single-Column PDF engine
│   ├── sample_data.py        # Realistic demo CVs & Job Descriptions
│   └── schemas.py            # Pydantic structured schemas
├── .env.example              # Environment variable template
├── requirements.txt          # Python dependencies
├── run.py                    # Server entrypoint
└── README.md
```

---

## 🚢 Deployment

### Render / Railway / Fly.io
Deploy with a single command or GitHub connect. Set start command to:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
