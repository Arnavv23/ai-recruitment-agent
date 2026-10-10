"""Streamlit dashboard. Talks to the FastAPI backend only (never to the database directly).

Run:  streamlit run streamlit_app.py
Theme: place .streamlit/config.toml next to this file (forces the light theme the CSS is designed for).
"""
import html
import inspect
import os

import requests
import streamlit as st
from dotenv import load_dotenv
from sympy import python

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="AI Recruitment Agent",
    page_icon="🧑‍💼",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------- Streamlit version compatibility ----------------
def _stretch(fn):
    """Full-width kwargs that work on both old (use_container_width) and new (width='stretch') Streamlit."""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return {}
    if "width" in params:
        return {"width": "stretch"}
    if "use_container_width" in params:
        return {"use_container_width": True}
    return {}


BTN_FULL = _stretch(st.button)
FORM_FULL = _stretch(st.form_submit_button)
TABLE_FULL = _stretch(st.dataframe)


# ---------------- Page names (used for navigation) ----------------
NAV_DASH = "📊  Dashboard"
NAV_JOBS = "💼  Jobs"
NAV_UPLOAD = "📄  Upload Resume"
NAV_CANDS = "👥  Candidates"
NAV_ANALYSIS = "🎯  Candidate Analysis"
NAV_ASSISTANT = "💬  AI Assistant"
NAV_ADMIN = "🛡️  Admin"


# ---------------- Theme (CSS + animations) ----------------
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
  --ink: #0F1B2D;
  --ink-2: #182B45;
  --bg: #F3F6FA;
  --card: #FFFFFF;
  --line: #E2E8F0;
  --text: #1A2434;
  --muted: #5B6879;
  --brand: #0E9F8E;
  --brand-dark: #0A7C70;
  --brand-soft: #DFF5F2;
  --good: #168A4A;
  --good-soft: #DDF4E6;
  --warn: #A9640B;
  --warn-soft: #FDF0D5;
  --bad: #C0392B;
  --bad-soft: #FBE4E1;
  --shadow: 0 1px 2px rgba(15,27,45,.06), 0 6px 18px rgba(15,27,45,.06);
  color-scheme: light;
}

html, body, .stApp, p, label, li, h1, h2, h3, h4, h5, h6, button, input, textarea,
[data-testid="stMarkdownContainer"] {
  font-family: 'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp { background: var(--bg); color: var(--text); }
.block-container { padding-top: 2rem; padding-bottom: 5rem; max-width: 1180px; }
h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.01em; }
h3 { font-weight: 700; }

/* hide default chrome */
#MainMenu, footer, .stAppDeployButton, [data-testid="stToolbar"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 999999 !important;
}

/* keep content crisp while the app reruns */
[data-stale="true"] { opacity: 1 !important; }

/* ---------- keyframes ---------- */
@keyframes fadeUp   { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
@keyframes fadeIn   { from { opacity: 0; } to { opacity: 1; } }
@keyframes grow     { from { width: 0; } }
@keyframes drift    { 0%,100% { transform: translate(0,0); } 50% { transform: translate(18px,-22px); } }
@keyframes gradient { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, var(--ink) 0%, #0A1322 100%);
  border-right: none;
}
[data-testid="stSidebar"] * { color: #D5DEEA; }
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"] { padding-top: 1.2rem; }

.brand { display: flex; align-items: center; gap: .75rem; padding: .2rem .4rem 1.2rem; }
.brand-mark {
  width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-size: 1.3rem;
  background: linear-gradient(135deg, var(--brand), #0B6E8A); box-shadow: 0 6px 16px rgba(14,159,142,.35);
}
.brand-name { color: #fff !important; font-weight: 800; font-size: 1.05rem; line-height: 1.1; }
.brand-sub  { color: #8FA3BB !important; font-size: .78rem; }

[data-testid="stSidebar"] div[role="radiogroup"] { gap: .2rem; }
[data-testid="stSidebar"] div[role="radiogroup"] > label {
  width: 100%; padding: .62rem .85rem; border-radius: 10px; cursor: pointer;
  border-left: 3px solid transparent;
  transition: background .2s ease, transform .2s ease, border-color .2s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background: rgba(255,255,255,.07); transform: translateX(3px); }
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
  background: rgba(14,159,142,.24); border-left-color: #2DD4BF;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * { color: #fff; font-weight: 700; }

.user-card {
  display: flex; align-items: center; gap: .7rem; padding: .8rem; margin: 1.4rem 0 .8rem;
  border-radius: 12px; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
}
.avatar {
  width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; font-weight: 800;
  background: linear-gradient(135deg, #2DD4BF, #0E9F8E); color: #06231F !important;
}
.user-name { color: #fff !important; font-weight: 700; font-size: .92rem; line-height: 1.1; }
.user-role { font-size: .76rem; color: #8FA3BB !important; }

[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.16); color: #fff;
}
[data-testid="stSidebar"] .stButton > button * { color: #fff; }
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,.14); border-color: #2DD4BF; }

/* ---------- page header ---------- */
.page-head { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; animation: fadeUp .45s ease both; }
.page-icon {
  width: 54px; height: 54px; border-radius: 15px; display: grid; place-items: center; font-size: 1.55rem; flex: none;
  background: linear-gradient(135deg, var(--brand), #0B6E8A); box-shadow: 0 8px 18px rgba(14,159,142,.28);
}
.page-head h1 { margin: 0; padding: 0; font-size: 1.75rem; font-weight: 800; line-height: 1.15; }
.page-head p  { margin: .2rem 0 0; color: var(--muted); font-size: .96rem; }
.section-title { font-weight: 700; color: var(--ink); font-size: 1.05rem; margin: 1.6rem 0 .7rem; }

/* ---------- buttons ---------- */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
  border-radius: 10px; border: 1px solid var(--line); background: #fff; color: var(--ink);
  font-weight: 600; padding: .55rem 1.1rem;
  transition: transform .15s ease, box-shadow .2s ease, background .2s ease, border-color .2s ease, color .2s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: var(--brand); color: var(--brand-dark); transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(15,27,45,.10);
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(0) scale(.98); box-shadow: none; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-dark) 100%); color: #fff; border: none;
  box-shadow: 0 6px 16px rgba(14,159,142,.30);
}
.stButton > button[kind="primary"] *, [data-testid="stBaseButton-primary"] *,
[data-testid="stBaseButton-primaryFormSubmit"] * { color: #fff; }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  color: #fff; box-shadow: 0 10px 22px rgba(14,159,142,.38); filter: brightness(1.05);
}
.stButton > button:disabled { opacity: .45; transform: none; box-shadow: none; }

/* ---------- inputs ---------- */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  border-radius: 10px !important; transition: box-shadow .2s ease, border-color .2s ease;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"]:focus-within > div {
  box-shadow: 0 0 0 3px rgba(14,159,142,.22);
}
[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed #B6C3D4; border-radius: 16px; background: #fff; padding: 1.6rem;
  transition: border-color .2s ease, background .2s ease, transform .2s ease;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--brand); background: var(--brand-soft); transform: translateY(-1px); }

/* ---------- surfaces ---------- */
[data-testid="stForm"] {
  border: 1px solid var(--line); border-radius: 16px; background: #fff; padding: 1.4rem; box-shadow: var(--shadow);
}
[data-testid="stExpander"] {
  border: 1px solid var(--line); border-radius: 12px; background: #fff; box-shadow: var(--shadow);
  overflow: hidden; transition: border-color .2s ease, box-shadow .2s ease; margin-bottom: .55rem;
}
[data-testid="stExpander"]:hover { border-color: #9CD9D1; box-shadow: 0 8px 22px rgba(15,27,45,.09); }
[data-testid="stExpander"] details[open] > summary ~ * { animation: fadeIn .3s ease both; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; border-color: var(--line); background: #fff; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; box-shadow: var(--shadow); }
[data-testid="stAlert"] { border-radius: 12px; animation: fadeUp .3s ease both; }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
  padding: .6rem 1.05rem; font-weight: 600; color: var(--muted); border-radius: 8px 8px 0 0;
  transition: color .2s ease, background .2s ease;
}
.stTabs [data-baseweb="tab"]:hover { background: rgba(14,159,142,.08); color: var(--brand-dark); }
.stTabs [aria-selected="true"] { color: var(--brand-dark); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--brand); height: 3px; border-radius: 3px; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.2rem; animation: fadeUp .35s ease both; }

/* ---------- stat cards ---------- */
.stat {
  display: flex; align-items: center; gap: 1rem; padding: 1.25rem 1.4rem; background: #fff;
  border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow);
  transition: transform .2s ease, box-shadow .2s ease; animation: fadeUp .5s ease both;
}
.stat:hover { transform: translateY(-3px); box-shadow: 0 14px 30px rgba(15,27,45,.12); }
.stat-ico { width: 52px; height: 52px; border-radius: 14px; display: grid; place-items: center; font-size: 1.5rem; background: var(--brand-soft); }
.stat-val { font-size: 2.1rem; font-weight: 800; color: var(--ink); line-height: 1; }
.stat-lbl { color: var(--muted); font-weight: 600; margin-top: .3rem; font-size: .9rem; }

/* ---------- chips, badges ---------- */
.chip-row { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; margin: .45rem 0; }
.chip-label { font-weight: 700; color: var(--ink); min-width: 78px; font-size: .9rem; }
.chip {
  display: inline-block; padding: .2rem .7rem; border-radius: 999px; font-size: .82rem; font-weight: 600;
  animation: fadeIn .4s ease both;
}
.chip-neutral { background: #E8EDF4; color: #2B3A52; }
.chip-good { background: var(--good-soft); color: var(--good); }
.chip-bad  { background: var(--bad-soft);  color: var(--bad); }
.muted { color: var(--muted); font-size: .9rem; }
.badge { display: inline-block; padding: .25rem .8rem; border-radius: 999px; font-weight: 700; font-size: .82rem; }
.badge-good { background: var(--good-soft); color: var(--good); }
.badge-mid  { background: var(--warn-soft); color: var(--warn); }
.badge-low  { background: var(--bad-soft);  color: var(--bad); }
.badge-brand { background: var(--brand-soft); color: var(--brand-dark); }

/* ---------- score card ---------- */
.score-card { background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 1.3rem 1.5rem; box-shadow: var(--shadow); animation: fadeUp .4s ease both; margin-bottom: 1rem; }
.score-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: .8rem; }
.score-num { font-size: 2.4rem; font-weight: 800; color: var(--ink); line-height: 1; }
.score-num span { font-size: 1rem; color: var(--muted); font-weight: 600; margin-left: .2rem; }
.bar { height: 12px; border-radius: 999px; background: #E8EDF4; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; animation: grow 1.1s cubic-bezier(.22,.8,.3,1) both; }
.bar-good { background: linear-gradient(90deg, #22A867, #168A4A); }
.bar-mid  { background: linear-gradient(90deg, #F2B84B, #D58A12); }
.bar-low  { background: linear-gradient(90deg, #E5705F, #C0392B); }

/* ---------- empty / welcome states ---------- */
.empty {
  text-align: center; padding: 2.6rem 1rem; border: 2px dashed #C9D4E2; border-radius: 16px;
  background: #fff; animation: fadeUp .45s ease both; margin-bottom: 1rem;
}
.empty-ico { font-size: 2.2rem; }
.empty-title { font-weight: 800; color: var(--ink); margin-top: .4rem; }
.empty-text { color: var(--muted); margin-top: .2rem; }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {
  background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.1rem;
  box-shadow: var(--shadow); animation: fadeUp .35s ease both;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { background: var(--brand-soft); border-color: #BFE7E1; }
[data-testid="stChatInput"] { border-radius: 14px; }

/* ---------- login hero ---------- */
.hero {
  position: relative; overflow: hidden; border-radius: 22px; padding: 2.8rem 2.5rem; min-height: 440px; color: #fff;
  background: linear-gradient(135deg, #0F1B2D 0%, #12365A 55%, #0E7F78 100%); background-size: 220% 220%;
  animation: gradient 16s ease infinite, fadeUp .6s ease both;
}
.hero::before, .hero::after { content: ""; position: absolute; border-radius: 50%; animation: drift 10s ease-in-out infinite; }
.hero::before { width: 280px; height: 280px; right: -80px; top: -80px; background: rgba(45,212,191,.16); }
.hero::after  { width: 200px; height: 200px; left: -60px; bottom: -70px; background: rgba(99,179,237,.15); animation-delay: -5s; }
.hero * { position: relative; z-index: 1; color: #fff; }
.hero h2 { color: #fff; font-size: 2.1rem; font-weight: 800; line-height: 1.15; margin: 1.2rem 0 .8rem; }
.hero p { color: #C9D8EA; font-size: 1.02rem; max-width: 460px; }
.hero ul { list-style: none; padding: 0; margin: 1.6rem 0 0; }
.hero li { display: flex; align-items: center; gap: .7rem; margin: .7rem 0; color: #E4EDF8; font-weight: 600; animation: fadeUp .6s ease both; }
.hero li:nth-child(1) { animation-delay: .15s; } .hero li:nth-child(2) { animation-delay: .27s; }
.hero li:nth-child(3) { animation-delay: .39s; } .hero li:nth-child(4) { animation-delay: .51s; }
.hero .tick { width: 28px; height: 28px; border-radius: 8px; background: rgba(255,255,255,.14); display: grid; place-items: center; font-size: .95rem; }
.login-head h2 { margin: .4rem 0 .2rem; font-size: 1.6rem; font-weight: 800; }
.login-head p { color: var(--muted); margin-bottom: 1rem; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
"""


HIDE_SIDEBAR_CSS = """
[data-testid="stSidebar"] {
    display: none !important;
}
"""


def inject_css(hide_sidebar: bool = False):
    css = BASE_CSS + (HIDE_SIDEBAR_CSS if hide_sidebar else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ---------------- UI helpers ----------------
def page_header(icon: str, title: str, subtitle: str):
    st.markdown(
        f'<div class="page-head"><div class="page-icon">{icon}</div>'
        f'<div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div></div>',
        unsafe_allow_html=True,
    )


def section_title(text: str):
    st.markdown(f'<div class="section-title">{html.escape(text)}</div>', unsafe_allow_html=True)


def stat_card(icon: str, label: str, value, delay: float = 0.0):
    st.markdown(
        f'<div class="stat" style="animation-delay:{delay}s"><div class="stat-ico">{icon}</div>'
        f'<div><div class="stat-val">{html.escape(str(value))}</div>'
        f'<div class="stat-lbl">{html.escape(label)}</div></div></div>',
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, text: str):
    st.markdown(
        f'<div class="empty"><div class="empty-ico">{icon}</div>'
        f'<div class="empty-title">{html.escape(title)}</div>'
        f'<div class="empty-text">{html.escape(text)}</div></div>',
        unsafe_allow_html=True,
    )


def chips(items, kind: str = "neutral") -> str:
    if not items:
        return '<span class="muted">None</span>'
    return "".join(f'<span class="chip chip-{kind}">{html.escape(str(i))}</span>' for i in items)


def labeled_chips(label: str, items, kind: str = "neutral"):
    st.markdown(
        f'<div class="chip-row"><div class="chip-label">{html.escape(label)}</div>{chips(items, kind)}</div>',
        unsafe_allow_html=True,
    )


def score_card(score, rating):
    try:
        value = max(0.0, min(100.0, float(score)))
    except (TypeError, ValueError):
        value = 0.0
    tone = "good" if value >= 70 else "mid" if value >= 40 else "low"
    st.markdown(
        f'<div class="score-card"><div class="score-top">'
        f'<div class="score-num">{value:g}<span>/ 100</span></div>'
        f'<div class="badge badge-{tone}">{html.escape(str(rating))}</div></div>'
        f'<div class="bar"><div class="bar-fill bar-{tone}" style="width:{value}%"></div></div></div>',
        unsafe_allow_html=True,
    )


def go(page: str):
    """Button callback: jump to another page."""
    st.session_state["nav"] = page


# ---------------- API helper ----------------
def api(method: str, path: str, **kwargs):
    """Call the backend. Returns (data, error_message). Errors are always shown to the user."""
    headers = {}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state['token']}"
    try:
        resp = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=120, **kwargs)
    except requests.RequestException:
        return None, f"Cannot reach the API at {API_URL}. Is the backend running?"
    if resp.status_code == 401 and st.session_state.get("token"):
        st.session_state.pop("token", None)
        st.session_state.pop("user", None)
        st.session_state["flash"] = "Your session expired. Please log in again."
        st.rerun()
    if resp.ok:
        return resp.json(), None
    try:
        detail = resp.json().get("detail", resp.text[:200])
    except ValueError:
        detail = resp.text[:200]
    if isinstance(detail, list):  # FastAPI validation errors
        detail = "; ".join(str(d.get("msg", d)) for d in detail)
    return None, str(detail)


def show_error(err: str):
    st.error(err)


def show_warnings(warnings):
    for w in warnings or []:
        st.warning(w)


# ---------------- login ----------------
def login_view():
    flash = st.session_state.pop("flash", None)
    left, right = st.columns([1.25, 1], gap="large")
    with left:
        st.markdown(
            '<div class="hero">'
            '<div class="brand"><div class="brand-mark">🧑‍💼</div>'
            '<div><div class="brand-name">AI Recruiter</div><div class="brand-sub">Candidate screening agent</div></div></div>'
            '<h2>Screen candidates in minutes, not days.</h2>'
            '<p>Upload resumes, search by meaning, score matches against a job and ask the assistant anything about your talent pool.</p>'
            '<ul>'
            '<li><span class="tick">📄</span>Resumes parsed into skills and experience</li>'
            '<li><span class="tick">🔎</span>Search candidates by meaning, not keywords</li>'
            '<li><span class="tick">🎯</span>Match scores with matched and missing skills</li>'
            '<li><span class="tick">💬</span>Ask questions in plain English</li>'
            '</ul></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="login-head"><h2>Welcome back</h2><p>Log in to manage candidates and jobs.</p></div>',
            unsafe_allow_html=True,
        )
        if flash:
            st.warning(flash)
        with st.form("login"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Log in", type="primary", **FORM_FULL)
        if submitted:
            if not username or not password:
                st.error("Enter both your username and password.")
            else:
                with st.spinner("Signing in..."):
                    data, err = api("POST", "/auth/login", json={"username": username, "password": password})
                if err:
                    show_error(err)
                else:
                    st.session_state["token"], st.session_state["user"] = data["access_token"], data["user"]
                    st.rerun()


def sidebar(pages: dict) -> str:
    user = st.session_state["user"]
    name = str(user["username"])
    st.sidebar.markdown(
        '<div class="brand"><div class="brand-mark">🧑‍💼</div>'
        '<div><div class="brand-name">AI Recruiter</div><div class="brand-sub">Screening agent</div></div></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.get("nav") not in pages:
        st.session_state["nav"] = NAV_DASH
    choice = st.sidebar.radio("Navigate", list(pages), key="nav", label_visibility="collapsed")
    st.sidebar.markdown(
        f'<div class="user-card"><div class="avatar">{html.escape(name[:1].upper())}</div>'
        f'<div><div class="user-name">{html.escape(name)}</div>'
        f'<div class="user-role">{html.escape(str(user["role"]).title())}</div></div></div>',
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Log out", **BTN_FULL):
        st.session_state.clear()
        st.rerun()
    return choice


# ---------------- pages ----------------
def page_dashboard():
    page_header("📊", "Dashboard", "A quick look at your talent pool and open roles.")
    stats, err = api("GET", "/dashboard/stats")
    if err:
        return show_error(err)
    c1, c2 = st.columns(2)
    with c1:
        stat_card("👥", "Candidates", stats["candidates"])
    with c2:
        stat_card("💼", "Open jobs", stats["jobs"], 0.08)

    section_title("Quick actions")
    a1, a2, a3, a4 = st.columns(4)
    a1.button("📄 Upload resumes", on_click=go, args=(NAV_UPLOAD,), **BTN_FULL)
    a2.button("💼 Create a job", on_click=go, args=(NAV_JOBS,), **BTN_FULL)
    a3.button("🔎 Search candidates", on_click=go, args=(NAV_CANDS,), **BTN_FULL)
    a4.button("💬 Ask the assistant", on_click=go, args=(NAV_ASSISTANT,), **BTN_FULL)

    section_title("Most common skills")
    with st.container(border=True):
        if stats["top_skills"]:
            st.bar_chart(stats["top_skills"])
        else:
            empty_state("📈", "No skill data yet", "Upload resumes to see which skills show up most.")


def page_jobs():
    page_header("💼", "Jobs", "Create roles and keep track of what you are hiring for.")
    is_admin = st.session_state["user"]["role"] == "admin"
    tab_list, tab_new, tab_file = st.tabs(["All jobs", "Create job", "Upload job description"])

    with tab_list:
        jobs, err = api("GET", "/jobs")
        if err:
            return show_error(err)
        if not jobs:
            empty_state("💼", "No jobs yet", "Create a job in the next tab, or upload a job description file.")
        else:
            term = st.text_input("Search jobs", placeholder="Filter by title or skill", key="job_filter",
                                 label_visibility="collapsed").strip().lower()
            shown = [j for j in jobs if not term
                     or term in j["title"].lower()
                     or any(term in str(s).lower() for s in j["required_skills"])]
            st.caption(f"Showing {len(shown)} of {len(jobs)} jobs")
            if not shown:
                st.info("No jobs match that search.")
            for job in shown:
                with st.expander(f"#{job['id']}  ·  {job['title']}"):
                    st.write(job["description"])
                    labeled_chips("Skills", job["required_skills"], "neutral")
                    if is_admin:
                        with st.popover("🗑️ Delete job"):
                            st.write("This permanently removes the job.")
                            if st.button("Yes, delete it", key=f"dj{job['id']}", type="primary"):
                                _, err = api("DELETE", f"/jobs/{job['id']}")
                                show_error(err) if err else st.rerun()

    with tab_new:
        with st.form("new_job"):
            title = st.text_input("Job title", placeholder="e.g. Backend Developer")
            desc = st.text_area("Job description", height=200, placeholder="Describe the role, responsibilities and requirements")
            skills = st.text_input("Required skills (optional)", placeholder="python, django, docker",
                                   help="Comma separated. Leave empty to detect skills automatically.")
            submitted = st.form_submit_button("Create job", type="primary")
        if submitted:
            if not title.strip() or not desc.strip():
                st.warning("Add a job title and description first.")
            else:
                body = {"title": title, "description": desc,
                        "required_skills": [s.strip() for s in skills.split(",") if s.strip()] or None}
                data, err = api("POST", "/jobs", json=body)
                if err:
                    show_error(err)
                else:
                    st.success(f"Job created (id {data['id']}).")
                    st.toast("Job created", icon="✅")

    with tab_file:
        title = st.text_input("Title for uploaded job", key="job_file_title", placeholder="e.g. Security Analyst")
        file = st.file_uploader("Drop a PDF or TXT file here", type=["pdf", "txt"], key="job_file")
        if st.button("Upload job description", type="primary", disabled=file is None):
            data, err = api("POST", "/jobs/upload", data={"title": title},
                            files={"file": (file.name, file.getvalue())})
            if err:
                show_error(err)
            else:
                st.success(f"Job created (id {data['id']}).")
                st.toast("Job created", icon="✅")


def page_upload():
    page_header("📄", "Upload Resume", "Add resumes and let the agent extract skills and experience.")
    files = st.file_uploader("Drop resume PDFs here, or click to browse", type=["pdf"], accept_multiple_files=True)
    if files:
        st.caption(f"{len(files)} file{'s' if len(files) != 1 else ''} ready to process")
    if st.button("Process resumes", type="primary", disabled=not files):
        bar = st.progress(0.0, text="Starting...")
        saved, results = 0, []
        for i, f in enumerate(files, 1):
            bar.progress((i - 1) / len(files), text=f"Processing {f.name} ({i} of {len(files)})")
            data, err = api("POST", "/candidates/upload", files={"file": (f.name, f.getvalue(), "application/pdf")})
            if err:
                results.append((False, f"{f.name}: {err}"))
            else:
                saved += 1
                results.append((True, f"{f.name}: saved as candidate {data['id']} - {data['name']} "
                                      f"({len(data['skills'])} skills found)"))
        bar.progress(1.0, text="Done")
        for ok, msg in results:
            st.success(msg) if ok else st.error(msg)
        if saved:
            st.toast(f"{saved} resume{'s' if saved != 1 else ''} processed", icon="✅")
            st.button("View candidates", on_click=go, args=(NAV_CANDS,))


def page_candidates():
    page_header("👥", "Candidates", "Search by meaning or browse everyone in your pool.")
    tab_search, tab_all = st.tabs(["Search by meaning", "All candidates"])

    with tab_search:
        query = st.text_input("Describe who you are looking for",
                              placeholder="e.g. backend developer with Django and Docker experience")
        if st.button("Search", type="primary", disabled=not query.strip()):
            with st.spinner("Searching..."):
                data, err = api("POST", "/candidates/search", json={"query": query, "top_k": 5})
            if err:
                show_error(err)
            elif not data["results"]:
                st.info(data["message"])
            else:
                for idx, r in enumerate(data["results"]):
                    with st.expander(f"{r['name']}  ·  id {r['candidate_id']}  ·  relevance {r['score']}", expanded=idx == 0):
                        labeled_chips("Skills", r["skills"], "neutral")
                        for snip in r["snippets"]:
                            st.caption(snip[:300] + "...")

    with tab_all:
        skill = st.text_input("Filter by skill", placeholder="e.g. python")
        cands, err = api("GET", "/candidates", params={"skill": skill} if skill else None)
        if err:
            return show_error(err)
        if not cands:
            return empty_state("👥", "No candidates found",
                               "Try a different skill filter, or upload resumes to build your pool.")
        st.caption(f"Showing {len(cands)} candidate{'s' if len(cands) != 1 else ''}")
        st.dataframe([{"ID": c["id"], "Name": c["name"], "Email": c["email"], "Experience (yrs)": c["experience_years"],
                       "Skills": ", ".join(c["skills"])} for c in cands], hide_index=True, **TABLE_FULL)
        if st.session_state["user"]["role"] == "admin":
            st.caption("Admins can delete candidates in the Admin section.")


def _pick(label, items, name_key):
    options = {f"#{i['id']} - {i[name_key]}": i["id"] for i in items}
    choice = st.selectbox(label, list(options)) if options else None
    return options.get(choice)


def page_analysis():
    page_header("🎯", "Candidate Analysis", "Score, summarise and compare candidates against a job.")
    cands, err1 = api("GET", "/candidates")
    jobs, err2 = api("GET", "/jobs")
    if err1 or err2:
        return show_error(err1 or err2)
    if not cands:
        empty_state("📄", "No candidates yet", "Upload at least one resume to start analysing.")
        st.button("Go to Upload Resume", on_click=go, args=(NAV_UPLOAD,), type="primary")
        return

    job_options = {"No specific job": None, **{f"#{j['id']} - {j['title']}": j["id"] for j in jobs}}
    with st.container(border=True):
        jid = job_options[st.selectbox("Target job (optional)", list(job_options),
                                       help="Pick a job to enable match scores and job-specific summaries.")]

    tab_one, tab_cmp = st.tabs(["Evaluate one candidate", "Compare candidates"])

    with tab_one:
        cid = _pick("Candidate", cands, "name")
        if jid is None:
            st.caption("Select a target job above to enable the match score.")
        c1, c2, c3 = st.columns(3)
        if c1.button("🎯 Match score", type="primary", disabled=jid is None, **BTN_FULL):
            with st.spinner("Analysing..."):
                data, err = api("POST", "/analysis/match", json={"candidate_id": cid, "job_id": jid})
            if err:
                show_error(err)
            else:
                score_card(data["match_score"], data["rating"])
                labeled_chips("Matched", data["matched_skills"], "good")
                labeled_chips("Missing", data["missing_skills"], "bad")
                st.write(data["explanation"])
                show_warnings(data["warnings"])
        if c2.button("📝 AI summary", **BTN_FULL):
            with st.spinner("Writing summary..."):
                data, err = api("POST", "/analysis/summary", json={"candidate_id": cid, "job_id": jid})
            if err:
                show_error(err)
            else:
                with st.container(border=True):
                    st.write(data["summary"])
                show_warnings(data["warnings"])
        if c3.button("❓ Interview questions", **BTN_FULL):
            with st.spinner("Generating questions..."):
                data, err = api("POST", "/analysis/questions", json={"candidate_id": cid, "job_id": jid})
            if err:
                show_error(err)
            else:
                with st.container(border=True):
                    st.write(data["questions"])
                show_warnings(data["warnings"])

    with tab_cmp:
        chosen = st.multiselect("Pick 2-5 candidates", [f"#{c['id']} - {c['name']}" for c in cands])
        if st.button("Compare", type="primary", disabled=len(chosen) < 2):
            if len(chosen) > 5:
                st.warning("Pick at most 5 candidates to compare.")
            else:
                ids = [int(c.split(" ")[0][1:]) for c in chosen]
                with st.spinner("Comparing..."):
                    data, err = api("POST", "/analysis/compare", json={"candidate_ids": ids, "job_id": jid})
                if err:
                    show_error(err)
                else:
                    st.dataframe([{"Rank": r["rank"], "Name": r["name"], "Score": r["match_score"],
                                   "Experience": r["experience_years"], "Skills": ", ".join(r["skills"])}
                                  for r in data["ranking"]], hide_index=True, **TABLE_FULL)
                    with st.container(border=True):
                        st.write(data["comparison"])
                    show_warnings(data["warnings"])
        elif len(chosen) < 2:
            st.caption("Select at least two candidates to compare.")


EXAMPLE_QUESTIONS = [
    "Find backend developers with Django and Docker experience",
    "Show candidate 1",
    "Analyze job 1",
    "Match candidate 1 to job 1",
    "Compare candidates 1 and 2 for job 1",
    "Interview questions for candidate 1 for job 1",
]


def set_question(q: str):
    st.session_state["pending_q"] = q


def page_assistant():
    page_header("💬", "AI Recruitment Assistant", "Ask about candidates and jobs in plain English.")
    history = st.session_state.setdefault("chat", [])
    typed = st.chat_input("Ask about candidates or jobs...")
    question = typed or st.session_state.pop("pending_q", None)

    if not history and not question:
        empty_state("💬", "Ask your first question", "Try one of these, or type your own below.")
        cols = st.columns(2)
        for i, q in enumerate(EXAMPLE_QUESTIONS):
            cols[i % 2].button(q, key=f"ex{i}", on_click=set_question, args=(q,), **BTN_FULL)
    elif history:
        if st.button("🧹 Clear chat"):
            st.session_state["chat"] = []
            st.rerun()

    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if question:
        history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                data, err = api("POST", "/agent/query", json={"query": question})
            if err:
                answer = f"⚠️ {err}"
                st.error(err)
            else:
                answer = data["answer"]
                st.markdown(answer)
                show_warnings(data["warnings"])
                with st.expander("How the agent got this answer"):
                    st.write(f"Tool: `{data['tool_used']}`")
                    st.write(" → ".join(data["steps"]))
        history.append({"role": "assistant", "content": answer})


def page_admin():
    page_header("🛡️", "Admin", "Manage users, candidate data and review the audit trail.")
    if st.session_state["user"]["role"] != "admin":
        return st.error("Admins only.")
    tab_users, tab_cands, tab_audit = st.tabs(["Users", "Candidates", "Audit log"])

    with tab_users:
        users, err = api("GET", "/admin/users")
        if err:
            show_error(err)
        else:
            st.dataframe(users, hide_index=True, **TABLE_FULL)
            left, right = st.columns(2, gap="large")
            with left:
                with st.form("new_user"):
                    st.subheader("Create user")
                    u = st.text_input("Username")
                    p = st.text_input("Password (min 8 chars)", type="password")
                    role = st.selectbox("Role", ["recruiter", "admin"])
                    submitted = st.form_submit_button("Create user", type="primary")
                if submitted:
                    _, err = api("POST", "/admin/users", json={"username": u, "password": p, "role": role})
                    if err:
                        show_error(err)
                    else:
                        st.success("User created.")
                        st.toast("User created", icon="✅")
            with right:
                with st.container(border=True):
                    st.subheader("Delete user")
                    options = {f"{x['username']} (id {x['id']})": x["id"] for x in users}
                    target = st.selectbox("User", list(options)) if options else None
                    if target:
                        with st.popover("🗑️ Delete selected user"):
                            st.write(f"Delete **{target}**? This cannot be undone.")
                            if st.button("Yes, delete user", type="primary", key="confirm_del_user"):
                                _, err = api("DELETE", f"/admin/users/{options[target]}")
                                if err:
                                    show_error(err)
                                else:
                                    st.success("User deleted.")
                                    st.toast("User deleted", icon="🗑️")

    with tab_cands:
        cands, err = api("GET", "/candidates")
        if err:
            show_error(err)
        elif not cands:
            empty_state("👥", "No candidates", "Candidates you upload will show up here.")
        else:
            with st.container(border=True):
                st.subheader("Delete candidate")
                options = {f"{c['name']} (id {c['id']})": c["id"] for c in cands}
                target = st.selectbox("Candidate", list(options))
                with st.popover("🗑️ Delete selected candidate"):
                    st.write(f"Delete **{target}** and their resume data? This cannot be undone.")
                    if st.button("Yes, delete candidate", type="primary", key="confirm_del_cand"):
                        _, err = api("DELETE", f"/candidates/{options[target]}")
                        if err:
                            show_error(err)
                        else:
                            st.success("Candidate and resume data deleted.")
                            st.toast("Candidate deleted", icon="🗑️")

    with tab_audit:
        log, err = api("GET", "/admin/audit")
        show_error(err) if err else st.dataframe(log, hide_index=True, **TABLE_FULL)


# ---------------- main ----------------
logged_in = bool(st.session_state.get("token"))
inject_css(hide_sidebar=not logged_in)

if logged_in:
    pages = {NAV_DASH: page_dashboard, NAV_JOBS: page_jobs, NAV_UPLOAD: page_upload,
             NAV_CANDS: page_candidates, NAV_ANALYSIS: page_analysis, NAV_ASSISTANT: page_assistant}
    if st.session_state["user"]["role"] == "admin":
        pages[NAV_ADMIN] = page_admin
    pages[sidebar(pages)]()
else:
    login_view()
