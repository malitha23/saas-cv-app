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
    # Replace weird unicode bullets with standard dashes
    text = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u25CF\u25CB\u25BA\u25B6]', '\n- ', text)
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


def extract_candidate_name(text: str, email: str = "") -> str:
    """Intelligently extract the candidate's actual full name from text."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Look for name near title or standalone line
    candidates = []
    for line in lines:
        # Ignore lines with email, phone numbers, urls, dates, or standard headings
        if "@" in line or "http" in line or "linkedin" in line or "github" in line:
            continue
        if re.search(r'\b(resume|curriculum vitae|cv|page \d|objective|summary|education|experience|skills)\b', line, re.IGNORECASE):
            continue
        if re.search(r'\d{4}', line) or re.search(r'\+\d+', line):
            continue
        
        # Check if line looks like a proper name (2 to 4 capitalized words)
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
            # Filter out generic titles like "Software Engineer"
            if not re.search(r'\b(Engineer|Developer|Manager|Analyst|Designer|Architect|Consultant)\b', line, re.IGNORECASE):
                candidates.append(line)
            elif len(words) >= 3 and not words[0] in ["Senior", "Lead", "Associate", "Staff", "Principal", "Junior"]:
                candidates.append(line)
                
    if candidates:
        return candidates[0]
        
    # Fallback to first non-empty line
    for line in lines[:5]:
        if "@" not in line and not re.search(r'\b(resume|cv|objective)\b', line, re.IGNORECASE):
            cleaned = re.sub(r'[^a-zA-Z\s]', '', line).strip()
            if len(cleaned.split()) >= 2:
                return cleaned
                
    # If all else fails, use email username nicely formatted
    if email and "@" in email:
        username = email.split("@")[0]
        name_parts = re.findall(r'[A-Za-z]+', username)
        if name_parts:
            return " ".join([p.capitalize() for p in name_parts])
            
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
