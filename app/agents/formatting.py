"""Turn tool results into readable markdown answers."""


def format_search(results: list[dict]) -> str:
    lines = []
    for r in results:
        lines.append(f"**{r['name']}** (candidate {r['candidate_id']}) - relevance {r['score']}, "
                     f"{r['experience_years'] or 'n/a'} yrs\n  Skills: {', '.join(r['skills']) or 'n/a'}\n"
                     f"  > {r['snippets'][0][:220]}...")
    return "\n\n".join(lines)


def format_result(tool: str, result: dict) -> str:
    data, text = result["data"], result.get("text")
    if tool == "get_candidate_details":
        return (f"**{data['name']}** (candidate {data['id']})\n- Email: {data['email'] or 'n/a'}\n"
                f"- Phone: {data['phone'] or 'n/a'}\n- Experience: {data['experience_years'] or 'n/a'} years\n"
                f"- Skills: {', '.join(data['skills']) or 'n/a'}\n- File: {data['file_name']}")
    if tool == "match_candidate":
        return (f"**{data['candidate_name']}** vs **{data['job_title']}**: "
                f"**{data['match_score']}/100** ({data['rating']})\n"
                f"- Matched: {', '.join(data['matched_skills']) or 'none'}\n"
                f"- Missing: {', '.join(data['missing_skills']) or 'none'}\n\n{text}")
    if tool == "compare_candidates":
        rows = "\n".join(f"{r['rank']}. {r['name']} (id {r['candidate_id']}) - score {r['match_score']}, "
                         f"{r['experience_years']} yrs" for r in data["ranking"])
        return f"**Ranking**\n{rows}\n\n{text}"
    if tool == "analyze_job":
        return (f"**{data['title']}** - seniority: {data['seniority']}, min experience: "
                f"{data['min_years_experience'] or 'not stated'}\nSkills: {', '.join(data['required_skills']) or 'n/a'}\n\n{text}")
    return text or "Done."


HELP_TEXT = ("I can help with: searching candidates ('Find Python developers with Django'), candidate details "
             "('Show candidate 2'), job analysis ('Analyze job 1'), matching ('Match candidate 2 to job 1'), "
             "comparison ('Compare candidates 1 and 2 for job 1'), summaries and interview questions "
             "('Interview questions for candidate 1 for job 1').")
