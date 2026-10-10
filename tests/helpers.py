"""Test helper: build a tiny valid text PDF without extra libraries."""


def make_pdf(lines: list[str]) -> bytes:
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content = "BT /F1 11 Tf 50 780 Td 14 TL\n" + "".join(f"({esc(l)}) Tj T*\n" for l in lines) + "ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = "%PDF-1.4\n", []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return out.encode("latin-1")


PYTHON_RESUME = [
    "Priya Sharma",
    "priya.sharma@example.com | +91 98765 43210",
    "Backend Developer with 4 years of experience building REST APIs.",
    "Skills: Python, Django, Django REST Framework, PostgreSQL, Docker, Git",
    "Built scalable Django services at Acme Corp and deployed them with Docker on AWS.",
]
SECURITY_RESUME = [
    "Rahul Verma",
    "rahul.verma@example.com",
    "Cybersecurity analyst with 2 years of experience in VAPT.",
    "Skills: Nmap, Burp Suite, SQLMap, Nikto, Penetration Testing, OWASP, Linux",
    "Performed vulnerability assessment and penetration testing for web applications.",
]
JOB_TEXT = ("We are hiring a Backend Developer with Python, Django and PostgreSQL experience. "
            "Docker and AWS knowledge is a plus. 3+ years of experience required.")
