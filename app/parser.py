import io
import re
from typing import Tuple, List, Dict, Any
from pypdf import PdfReader
from docx import Document


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file stream using pypdf."""
    reader = PdfReader(io.BytesIO(file_bytes))
    extracted_pages = []
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            extracted_pages.append(text.strip())
            
    full_text = "\n\n".join(extracted_pages)
    return clean_extracted_text(full_text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a DOCX file stream using python-docx."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    # Also extract text inside tables if any
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
            if row_text:
                paragraphs.append(row_text)
                
    full_text = "\n".join(paragraphs)
    return clean_extracted_text(full_text)


def clean_extracted_text(text: str) -> str:
    """Normalize whitespace, remove non-printable chars, and standardize bullets."""
    if not text:
        return ""
    # Strip unprintable or odd control chars like \x7f and unicode squares
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Replace weird unicode bullets with standard dashes
    text = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219\u25A0\u25AA\u25AB\u25CF\u25CB\u25BA\u25B6\uF0B7■▪●•]', '\n- ', text)
    # Standardize multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove excessive horizontal whitespace
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def detect_sections(text: str) -> List[str]:
    """Detect presence of common standard resume sections."""
    detected = []
    text_lower = text.lower()
    
    section_patterns = [
        ("Summary / Objective", r"(summary|objective|profile|about me)"),
        ("Work Experience", r"(experience|employment|work history|career history|professional background|work experience)"),
        ("Education", r"(education|academic background|degrees|university|college|bsc|hnd)"),
        ("Skills & Technologies", r"(skills|technical skills|competencies|technologies|programming languages|frameworks)"),
        ("Projects & Works", r"(projects|portfolio|personal projects|key projects|projects and my works)"),
        ("Certifications & Awards", r"(certifications|certificates|licenses|credentials|awards)")
    ]
    
    for label, pattern in section_patterns:
        if re.search(pattern, text_lower):
            detected.append(label)
            
    return detected


NAME_BLACKLIST = set([
    'university', 'college', 'institute', 'academy', 'school', 'polytechnic', 'campus', 'faculty', 'department',
    'pvt', 'ltd', 'inc', 'llc', 'corp', 'corporation', 'company', 'systems', 'technologies', 'services', 'solutions',
    'road', 'street', 'avenue', 'lane', 'drive', 'boulevard', 'city', 'state', 'country', 'sri lanka', 'colombo', 'beliatta',
    'resume', 'curriculum', 'vitae', 'cv', 'page', 'objective', 'summary', 'profile', 'education', 'experience', 'skills',
    'personal', 'contact', 'nationality', 'gender', 'dob', 'date', 'birth', 'passport', 'nic', 'qualifications', 'references',
    'projects', 'works', 'portfolio', 'languages', 'frameworks', 'database', 'certifications', 'awards', 'links', 'socials',
    'engineer', 'developer', 'manager', 'analyst', 'designer', 'architect', 'consultant', 'technician', 'electrician',
    'painter', 'specialist', 'executive', 'officer', 'director', 'intern', 'associate', 'lead', 'founder', 'freelance',
    'bsc', 'bachelor', 'master', 'msc', 'phd', 'diploma', 'hnd', 'nvq', 'degree', 'cardiff', 'metropolitan', 'nibm',
    'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
    'present', 'year', 'years', 'month', 'months', 'repository', 'website', 'application', 'applications', 'tools', 'database',
    'surface', 'preparation', 'sanding', 'coating', 'primer', 'polishing', 'diagnostics', 'inspection', 'wiring', 'repairs',
    'assembly', 'welding', 'fabrication', 'finishes', 'harnesses', 'lighting', 'alternator', 'testing', 'sensor', 'charging',
    'technical', 'competencies', 'responsibilities', 'duties', 'achievements', 'hardware', 'troubleshooting', 'safety'
])


def extract_candidate_name(text: str, email: str = "") -> str:
    """Intelligently extract the candidate's actual full name from text with confidence scoring."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return "Candidate Name"

    email_user = email.split('@')[0].lower() if email else ''
    candidates = []

    for i, line in enumerate(lines):
        # Ignore lines with obvious non-name symbols
        if any(c in line for c in [':', '|', '@', '/', '\\', '=', '+', ';', '#', '(', ')', '{', '}', '[', ']']):
            continue
        if re.search(r'\d', line):
            continue

        cleaned = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = cleaned.split()
        if not (2 <= len(words) <= 6):
            continue
        # Each word must start with an uppercase letter and consist only of letters
        if not all(w.isalpha() and w[0].isupper() for w in words):
            continue

        line_lower = line.lower()
        # Strictly reject if any blacklisted keyword exists as a word or substring
        if any(re.search(rf'\b{re.escape(b)}\b', line_lower) for b in NAME_BLACKLIST):
            continue
        if any(b in line_lower for b in ['university', 'college', 'institute', 'school', 'cardiff', 'nibm', 'pvt', 'ltd', 'road', 'street']):
            continue

        score = 10
        # Positional priority - first 3 lines are overwhelmingly candidate names
        if i == 0:
            score += 60
        elif i == 1:
            score += 45
        elif i < 5:
            score += 25
        elif i < 15:
            score += 15
        elif i < 80:
            score += 5

        # Adjacent title boost (e.g. line right after is 'Automotive Technician' or 'Software Engineer')
        if i + 1 < len(lines):
            next_line = lines[i+1].lower()
            if any(t in next_line for t in ['engineer', 'developer', 'manager', 'specialist', 'consultant', 'technician', 'lead', 'architect', 'painter', 'electrician', 'mechanic', 'officer']):
                score += 80

        # Email match boost (e.g. 'isuranga' in 'lghisuranga@gmail.com')
        for w in words:
            w_low = w.lower()
            if len(w_low) >= 3 and (w_low in email_user or email_user in w_low or (len(w_low) >= 4 and w_low[:4] in email_user)):
                score += 90

        candidates.append((score, cleaned, i))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # Email username fallback
    if email_user:
        name_parts = re.findall(r'[A-Za-z]+', email_user)
        if name_parts and len(name_parts) >= 2:
            return " ".join([p.capitalize() for p in name_parts])
        elif name_parts and len(name_parts[0]) >= 3:
            return name_parts[0].capitalize()

    return "Candidate Name"


def parse_resume_file(filename: str, file_bytes: bytes) -> Tuple[str, List[str]]:
    """Parse resume file based on extension and return (text, detected_sections)."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        text = extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith(('.docx', '.doc')):
        text = extract_text_from_docx(file_bytes)
    elif filename_lower.endswith('.txt'):
        try:
            text = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            text = file_bytes.decode('latin-1', errors='ignore')
        text = clean_extracted_text(text)
    else:
        raise ValueError(f"Unsupported file format: {filename}. Please upload a PDF, DOCX, or TXT file.")
        
    detected = detect_sections(text)
    return text, detected
