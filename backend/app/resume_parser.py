"""Resume parsing: extract name, skills, projects, and experience signals
from PDF or plain-text resumes. Pure local processing, no external calls."""
import io
import re

SKILL_LEXICON = [
    "Python", "SQL", "Machine Learning", "Deep Learning", "NLP",
    "Computer Vision", "TensorFlow", "PyTorch", "Keras", "Scikit-learn",
    "Pandas", "NumPy", "LangChain", "LangGraph", "RAG", "LLM",
    "Prompt Engineering", "Transformers", "Hugging Face", "FastAPI",
    "Flask", "Django", "Docker", "Kubernetes", "Git", "GitHub",
    "AWS", "GCP", "Azure", "React", "JavaScript", "TypeScript",
    "Node.js", "PostgreSQL", "MySQL", "MongoDB", "ChromaDB",
    "Vector Databases", "Data Analysis", "Statistics", "A/B Testing",
    "Tableau", "Power BI", "Spark", "Airflow", "MLOps", "OpenCV",
    "Embeddings", "Fine-tuning", "REST APIs", "Linux", "Excel",
    "Matplotlib", "Seaborn", "XGBoost", "Neural Networks",
    "Reinforcement Learning", "Speech Recognition", "OCR",
]

SECTION_HEADERS = {
    "projects": ["projects", "key projects", "personal projects"],
    "experience": ["experience", "work experience", "employment"],
    "skills": ["skills", "technical skills", "tech stack"],
    "education": ["education", "academics"],
}


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract raw text from a PDF upload or a plain-text file."""
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return file_bytes.decode("utf-8", errors="ignore")


def _find_sections(text: str) -> dict:
    """Split resume text into rough sections by header lines."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    sections = {"header": []}
    current = "header"
    for ln in lines:
        low = ln.strip().lower().rstrip(":")
        matched = None
        for name, variants in SECTION_HEADERS.items():
            if low in variants:
                matched = name
                break
        if matched:
            current = matched
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(ln)
    return sections


def extract_skills(text: str) -> list:
    found = []
    low = text.lower()
    for skill in SKILL_LEXICON:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, low):
            found.append(skill)
    return found


def extract_projects(sections: dict) -> list:
    """Heuristic: within the Projects section, short non-bullet lines that
    are followed by content are treated as project titles."""
    projects = []
    lines = [ln for ln in sections.get("projects", []) if ln.strip()]
    for i, ln in enumerate(lines):
        s = ln.strip()
        is_bullet = s.startswith(("-", "•", "*", "·"))
        if is_bullet or len(s) > 70 or len(s) < 3:
            continue
        # Skip PDF line-wrap fragments: continuations start lowercase, or
        # follow a line ending in a comma / conjunction / hyphen. A line
        # carrying a repo link is a title even if the name is lowercase.
        if s[0].islower() and "github.com" not in s and " — " not in s:
            continue
        if i > 0:
            prev = lines[i - 1].strip()
            if prev.endswith((",", "-", "and", "or")):
                continue
        # A title line is usually followed by a description/bullet line.
        if i + 1 < len(lines):
            title = re.split(r"\s{2,}|\||—|–", s)[0].strip()
            title = re.sub(r"\s+\d{4}$", "", title)
            projects.append(title)
    # De-duplicate, keep order, cap at 6.
    seen, out = set(), []
    for p in projects:
        if p.lower() not in seen and len(p) >= 3:
            seen.add(p.lower())
            out.append(p)
    return out[:6]


def extract_experience_years(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?experience",
                  text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    text = extract_text(file_bytes, filename)
    sections = _find_sections(text)
    header_lines = [ln.strip() for ln in sections.get("header", [])
                    if ln.strip()]
    name = header_lines[0] if header_lines else "Candidate"
    email_m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    return {
        "name": name,
        "email": email_m.group(0) if email_m else None,
        "skills": extract_skills(text),
        "projects": extract_projects(sections),
        "experience_years": extract_experience_years(text),
        "char_count": len(text),
        "raw_text": text,
    }
