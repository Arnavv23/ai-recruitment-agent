"""Candidate analysis: match score, summary, interview questions, comparison, job analysis.

Division of labour:
* Python computes anything numeric (skill overlap, scores, ranking).
* The LLM only writes natural-language explanations from the facts we give it.
* If the LLM is unavailable a plain-text fallback is returned and a warning is added.
"""
import logging
import re

from app.rag import vector_store
from app.exceptions import ValidationError, VectorStoreError
from app.services import candidate_service, job_service, llm_service
from app.services.prompt_safety import GROUNDING_RULES, neutralize_injection, wrap_untrusted

logger = logging.getLogger(__name__)
LLM_WARNING = "The LLM is unavailable, so a basic (non-AI) result is shown."


# ---------- helpers ----------
def _facts(candidate: dict) -> str:
    return (f"Name: {candidate['name']}\n"
            f"Skills found in resume: {', '.join(candidate['skills']) or 'none detected'}\n"
            f"Years of experience mentioned: {candidate['experience_years'] or 'not stated'}")


def _resume_context(candidate: dict, job: dict | None, warnings: list[str]) -> str:
    """RAG: with a job, retrieve the resume chunks most relevant to it; otherwise use the resume start."""
    text = ""
    if job:
        try:
            hits = vector_store.search_chunks(job["description"][:1500], top_k=4, candidate_ids=[candidate["id"]])
            text = "\n...\n".join(h["text"] for h in hits)
        except VectorStoreError:
            warnings.append("Vector search unavailable; used the beginning of the resume instead.")
    if not text:
        full = candidate_service.get_candidate(candidate["id"], include_text=True)["resume_text"]
        text = full[:3500]
    clean, _ = neutralize_injection(text)
    return wrap_untrusted("RESUME_EXCERPTS", clean)


def _rating(score: float | None) -> str:
    if score is None:
        return "Not rated"
    return "Strong match" if score >= 75 else "Moderate match" if score >= 50 else "Weak match"


# ---------- match ----------
def match_candidate(candidate_id: int, job_id: int) -> dict:
    cand = candidate_service.get_candidate(candidate_id)
    job = job_service.get_job(job_id)
    warnings: list[str] = []
    required = [s.lower() for s in job["required_skills"]]
    have = {s.lower() for s in cand["skills"]}
    matched = [s for s in required if s in have]
    missing = [s for s in required if s not in have]
    skill_score = round(len(matched) / len(required) * 100, 1) if required else None

    semantic = None
    try:
        hits = vector_store.search_chunks(job["description"][:1500], top_k=3, candidate_ids=[candidate_id])
        if hits:
            semantic = round(sum(h["score"] for h in hits) / len(hits), 3)
    except VectorStoreError:
        warnings.append("Semantic similarity unavailable (vector database error).")

    if skill_score is not None and semantic is not None:
        score = round(0.7 * skill_score + 0.3 * semantic * 100, 1)
    elif skill_score is not None:
        score = skill_score
    elif semantic is not None:
        score = round(semantic * 100, 1)
    else:
        score = None
    if not required:
        warnings.append("The job lists no recognised required skills; score uses text similarity only.")

    fallback = (f"{cand['name']} matches {len(matched)} of {len(required)} required skills "
                f"({', '.join(matched) or 'none'}). Missing: {', '.join(missing) or 'none'}.")
    context = _resume_context(cand, job, warnings)
    prompt = (f"JOB TITLE: {job['title']}\nREQUIRED SKILLS: {', '.join(required) or 'not specified'}\n\n"
              f"CONTEXT (candidate facts):\n{_facts(cand)}\n"
              f"Matched skills: {', '.join(matched) or 'none'}\nMissing skills: {', '.join(missing) or 'none'}\n"
              f"Computed match score: {score}/100 (do not change it)\n\n{context}\n\n"
              "Write a short (4-6 sentences) explanation of how well the candidate fits, citing only the context.")
    explanation, used = llm_service.ask_llm_or_fallback(GROUNDING_RULES, prompt, fallback)
    if not used:
        warnings.append(LLM_WARNING)
    return {"candidate_id": candidate_id, "candidate_name": cand["name"], "job_id": job_id,
            "job_title": job["title"], "match_score": score, "rating": _rating(score),
            "skill_score": skill_score, "semantic_similarity": semantic,
            "matched_skills": matched, "missing_skills": missing,
            "experience_years": cand["experience_years"],
            "explanation": explanation, "llm_used": used, "warnings": warnings}


# ---------- summary ----------
def summarize_candidate(candidate_id: int, job_id: int | None = None) -> dict:
    cand = candidate_service.get_candidate(candidate_id)
    job = job_service.get_job(job_id) if job_id else None
    warnings: list[str] = []
    context = _resume_context(cand, job, warnings)
    fallback = (f"{cand['name']} - {cand['experience_years'] or 'unstated'} years of experience. "
                f"Skills: {', '.join(cand['skills']) or 'none detected'}.")
    prompt = (f"CONTEXT (candidate facts):\n{_facts(cand)}\n\n{context}\n\n"
              + (f"The recruiter is hiring for: {job['title']}.\n" if job else "")
              + "Write a recruiter-friendly summary: 1) one-sentence overview, 2) key strengths, "
                "3) possible gaps or things to verify. Use only the context; say 'Not found in the resume' when unsure.")
    summary, used = llm_service.ask_llm_or_fallback(GROUNDING_RULES, prompt, fallback)
    if not used:
        warnings.append(LLM_WARNING)
    return {"candidate_id": candidate_id, "candidate_name": cand["name"], "job_id": job_id,
            "summary": summary, "llm_used": used, "warnings": warnings}


# ---------- interview questions ----------
def generate_interview_questions(candidate_id: int, job_id: int | None = None, num_questions: int = 8) -> dict:
    if not 3 <= num_questions <= 15:
        raise ValidationError("num_questions must be between 3 and 15.")
    cand = candidate_service.get_candidate(candidate_id)
    job = job_service.get_job(job_id) if job_id else None
    warnings: list[str] = []
    required = [s.lower() for s in job["required_skills"]] if job else []
    have = {s.lower() for s in cand["skills"]}
    missing = [s for s in required if s not in have]

    fallback_qs = [f"Walk me through a project where you used {s}. What was your role?" for s in cand["skills"][:4]]
    fallback_qs += [f"The role needs {s}, which is not on your resume. How would you get up to speed?" for s in missing[:3]]
    fallback_qs += ["Describe the most challenging technical problem you solved and how.",
                    "Tell me about a time you disagreed with a teammate. What happened?",
                    "How do you keep your skills current?"]
    fallback = "\n".join(f"{i}. {q}" for i, q in enumerate(fallback_qs[:num_questions], 1))

    context = _resume_context(cand, job, warnings)
    prompt = (f"CONTEXT (candidate facts):\n{_facts(cand)}\n\n{context}\n\n"
              + (f"JOB TITLE: {job['title']}\nREQUIRED SKILLS: {', '.join(required)}\n"
                 f"Skills the resume does not show: {', '.join(missing) or 'none'}\n" if job else "")
              + f"Write {num_questions} interview questions as a numbered list: a mix of technical questions "
                "tied to the candidate's real experience, questions probing missing skills, and behavioural questions. "
                "Do not assume experience that is not in the context.")
    text, used = llm_service.ask_llm_or_fallback(GROUNDING_RULES, prompt, fallback)
    if not used:
        warnings.append(LLM_WARNING)
    return {"candidate_id": candidate_id, "candidate_name": cand["name"], "job_id": job_id,
            "questions": text, "llm_used": used, "warnings": warnings}


# ---------- comparison ----------
def compare_candidates(candidate_ids: list[int], job_id: int | None = None) -> dict:
    ids = list(dict.fromkeys(candidate_ids))  # remove duplicates, keep order
    if not 2 <= len(ids) <= 5:
        raise ValidationError("Provide between 2 and 5 different candidate IDs to compare.")
    warnings: list[str] = []
    rows = []
    for cid in ids:
        cand = candidate_service.get_candidate(cid)
        row = {"candidate_id": cid, "name": cand["name"], "skills": cand["skills"],
               "experience_years": cand["experience_years"], "match_score": None}
        if job_id:
            result = match_candidate(cid, job_id)
            row.update(match_score=result["match_score"], missing_skills=result["missing_skills"])
        rows.append(row)
    rows.sort(key=lambda r: ((r["match_score"] or 0), r["experience_years"], len(r["skills"])), reverse=True)
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank

    job = job_service.get_job(job_id) if job_id else None
    table = "\n".join(
        f"#{r['rank']} {r['name']} (id {r['candidate_id']}): score={r['match_score']}, "
        f"experience={r['experience_years']} yrs, skills={', '.join(r['skills']) or 'none'}" for r in rows)
    fallback = "Ranking (computed from skill overlap and experience):\n" + table
    prompt = (f"CONTEXT (computed facts):\n{table}\n"
              + (f"Job: {job['title']}; required skills: {', '.join(job['required_skills'])}\n" if job else "")
              + "\nWrite a short comparison (strengths and gaps of each candidate, then a suggested order to "
                "interview them). Use only the context. The ranking above is computed; do not change it.")
    narrative, used = llm_service.ask_llm_or_fallback(GROUNDING_RULES, prompt, fallback)
    if not used:
        warnings.append(LLM_WARNING)
    return {"job_id": job_id, "ranking": rows, "comparison": narrative, "llm_used": used, "warnings": warnings}


# ---------- job analysis ----------
def analyze_job(job_id: int) -> dict:
    job = job_service.get_job(job_id)
    text = f"{job['title']} {job['description']}".lower()
    level = next((lvl for lvl, pat in [("senior", r"\bsenior|\blead\b|\bprincipal"), ("junior", r"\bjunior|\bentry|\bintern|\bfresher"),
                                       ("mid", r"\bmid[- ]level")] if re.search(pat, text)), "not specified")
    years = [int(y) for y in re.findall(r"(\d{1,2})\+?\s*(?:years|yrs)", text) if int(y) <= 45]
    fallback = (f"{job['title']}: seniority {level}; minimum experience "
                f"{min(years) if years else 'not stated'} years; key skills: {', '.join(job['required_skills']) or 'none detected'}.")
    clean, _ = neutralize_injection(job["description"][:4000])
    prompt = (f"CONTEXT:\nTitle: {job['title']}\nDetected skills: {', '.join(job['required_skills'])}\n"
              f"{wrap_untrusted('JOB_DESCRIPTION', clean)}\n\n"
              "Summarise the role: main responsibilities, must-have vs nice-to-have requirements, and what an ideal candidate looks like. "
              "Use only the job description.")
    summary, used = llm_service.ask_llm_or_fallback(GROUNDING_RULES, prompt, fallback)
    return {"job_id": job_id, "title": job["title"], "required_skills": job["required_skills"],
            "seniority": level, "min_years_experience": min(years) if years else None,
            "summary": summary, "llm_used": used, "warnings": [] if used else [LLM_WARNING]}
