"""Rule-based extraction of basic resume fields (no LLM, so it is fast and predictable)."""
import re
from pathlib import Path

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust", "php", "kotlin",
    "sql", "mysql", "postgresql", "mongodb", "sqlite", "redis", "kafka",
    "django", "django rest framework", "flask", "fastapi", "spring boot", "node.js", "express",
    "react", "angular", "vue", "html", "css",
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "linux", "jenkins", "ci/cd", "terraform",
    "rest api", "graphql", "microservices",
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow", "scikit-learn",
    "pandas", "numpy", "langchain", "langgraph", "rag", "data analysis", "tableau", "power bi",
    "excel", "agile", "scrum", "communication", "leadership",
    "nmap", "burp suite", "sqlmap", "nikto", "metasploit", "wireshark",
    "penetration testing", "vapt", "owasp", "cybersecurity", "networking", "vulnerability assessment",
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s\-().]{8,16}\d)(?!\d)")
YEARS_RE = re.compile(r"(\d{1,2})(?:\.\d)?\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def extract_skills(text: str) -> list[str]:
    """Find known skills in text (whole-word match, case-insensitive)."""
    lowered = (text or "").lower()
    found = []
    for skill in SKILL_KEYWORDS:
        pattern = r"(?<![\w+#])" + re.escape(skill) + r"(?![\w+#])"
        if re.search(pattern, lowered):
            found.append(skill)
    # drop "rest api"-style duplicates of longer names (e.g. keep "django rest framework")
    return found


def _guess_name(text: str) -> str:
    for line in text.splitlines()[:6]:
        line = line.strip()
        words = line.split()
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z.'-]+", w) for w in words):
            return line.title() if line.isupper() else line
    return ""


def parse_resume(text: str, file_name: str = "") -> dict:
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    years = [int(m) for m in YEARS_RE.findall(text) if int(m) <= 45]
    name = _guess_name(text) or (Path(file_name).stem.replace("_", " ").title() if file_name else "Unknown Candidate")
    return {
        "name": name,
        "email": email.group(0).lower() if email else None,
        "phone": phone.group(1).strip() if phone else None,
        "skills": extract_skills(text),
        "experience_years": float(max(years)) if years else 0.0,
    }
