"""LangGraph workflow:

 understand_request -> select_tool -> run_tool (retrieve / RAG) -> analyze_results -> generate_response

Any node can set `answer` or `error`; the conditional edges then jump straight to
generate_response. Authorization is enforced in select_tool and again in execute_tool.
"""
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents import formatting, router
from app.auth.permissions import check_permission
from app.exceptions import AppError
from app.services import llm_service
from app.services.prompt_safety import (GROUNDING_RULES, clean_user_text, detect_prompt_injection,
                                        neutralize_injection, redact_secrets, wrap_untrusted)
from app.tools.recruitment_tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

BLOCKED_MESSAGE = ("I can't act on that request because it looks like an attempt to change my instructions "
                   "or access protected information. Please ask a recruitment-related question.")


class AgentState(TypedDict, total=False):
    user: dict
    query: str
    ids: dict
    tool: str
    args: dict
    tool_result: dict
    answer: str
    error: str
    blocked: bool
    warnings: list
    steps: list


def _step(state: AgentState, name: str) -> list:
    return state.get("steps", []) + [name]


# ---------- nodes ----------
def understand_request(state: AgentState) -> dict:
    query = clean_user_text(state.get("query", ""))
    if not query:
        return {"error": "Please type a question.", "steps": _step(state, "understand_request")}
    if detect_prompt_injection(query):
        logger.warning("Blocked suspicious agent query from user '%s'.", state["user"].get("username"))
        return {"blocked": True, "answer": BLOCKED_MESSAGE, "query": query,
                "steps": _step(state, "understand_request:blocked")}
    ids = router.extract_ids(query)
    tool, llm_used = router.route_request(query, ids)
    return {"query": query, "ids": ids, "tool": tool,
            "steps": _step(state, f"understand_request:{tool}{' (llm)' if llm_used else ' (rules)'}")}


def select_tool(state: AgentState) -> dict:
    tool = state["tool"]
    if tool == "none" or tool not in TOOLS:
        return {"answer": formatting.HELP_TEXT, "steps": _step(state, "select_tool:none")}
    args, missing = router.build_args(tool, state["query"], state["ids"])
    if missing:
        return {"answer": missing, "steps": _step(state, "select_tool:needs_info")}
    try:
        check_permission(state["user"], TOOLS[tool].permission)  # deterministic authorization
    except AppError as exc:
        return {"error": exc.message, "steps": _step(state, "select_tool:denied")}
    return {"args": args, "steps": _step(state, f"select_tool:{tool}")}


def run_tool(state: AgentState) -> dict:
    """Retrieval step: database lookups and RAG searches happen inside the tool."""
    try:
        result = execute_tool(state["tool"], state["user"], state["args"])
    except AppError as exc:
        return {"error": exc.message, "steps": _step(state, "run_tool:error")}
    except Exception:
        logger.exception("Unexpected tool failure")
        return {"error": "An unexpected error occurred while running the tool.",
                "steps": _step(state, "run_tool:error")}
    return {"tool_result": result, "steps": _step(state, "run_tool")}


def analyze_results(state: AgentState) -> dict:
    """For candidate search, the LLM writes a grounded answer from the retrieved resume chunks."""
    steps = _step(state, "analyze_results")
    result = state["tool_result"]
    if state["tool"] != "search_candidates":
        return {"steps": steps}
    hits = result["data"]
    if not hits:
        return {"answer": "No matching candidates were found. Try different keywords or upload more resumes.",
                "steps": steps}
    context = "\n\n".join(
        wrap_untrusted(f"CANDIDATE {h['candidate_id']} ({h['name']})",
                       neutralize_injection("\n".join(h["snippets"]))[0]) for h in hits)
    prompt = (f"{wrap_untrusted('RECRUITER_QUESTION', state['query'])}\n\nCONTEXT (retrieved resume excerpts):\n{context}\n\n"
              "Answer the question using ONLY the excerpts. Mention candidate IDs, explain briefly why each fits, "
              "and say clearly if the evidence is weak or missing.")
    text, used = llm_service.ask_llm_or_fallback(GROUNDING_RULES, prompt, formatting.format_search(hits))
    warnings = state.get("warnings", [])
    if not used:
        warnings = warnings + ["The LLM is unavailable, so raw search results are shown."]
    return {"answer": text if used else formatting.format_search(hits), "warnings": warnings, "steps": steps}


def generate_response(state: AgentState) -> dict:
    answer = state.get("answer")
    if state.get("error"):
        answer = f"Sorry, I couldn't complete that: {state['error']}"
    elif not answer and state.get("tool_result"):
        answer = formatting.format_result(state["tool"], state["tool_result"])
        if state["tool_result"].get("data") and isinstance(state["tool_result"]["data"], dict):
            warnings = state["tool_result"]["data"].get("warnings") or []
            if warnings:
                return {"answer": redact_secrets(answer), "warnings": state.get("warnings", []) + warnings,
                        "steps": _step(state, "generate_response")}
    return {"answer": redact_secrets(answer or "Sorry, I have no answer for that."),
            "steps": _step(state, "generate_response")}


# ---------- graph wiring ----------
def _next_or_respond(state: AgentState) -> str:
    return "respond" if (state.get("answer") or state.get("error") or state.get("blocked")) else "next"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("understand_request", understand_request)
    graph.add_node("select_tool", select_tool)
    graph.add_node("run_tool", run_tool)
    graph.add_node("analyze_results", analyze_results)
    graph.add_node("generate_response", generate_response)
    graph.set_entry_point("understand_request")
    graph.add_conditional_edges("understand_request", _next_or_respond,
                                {"next": "select_tool", "respond": "generate_response"})
    graph.add_conditional_edges("select_tool", _next_or_respond,
                                {"next": "run_tool", "respond": "generate_response"})
    graph.add_conditional_edges("run_tool", _next_or_respond,
                                {"next": "analyze_results", "respond": "generate_response"})
    graph.add_edge("analyze_results", "generate_response")
    graph.add_edge("generate_response", END)
    return graph.compile()


_compiled = build_graph()


def run_agent(user: dict, query: str) -> dict:
    """Entry point used by the API. `user` must come from verified authentication."""
    final = _compiled.invoke({"user": user, "query": query, "warnings": [], "steps": []})
    data = (final.get("tool_result") or {}).get("data")
    return {"answer": final.get("answer", ""), "tool_used": final.get("tool") if final.get("tool_result") else None,
            "data": data, "steps": final.get("steps", []), "warnings": final.get("warnings", []),
            "blocked": bool(final.get("blocked")), "error": bool(final.get("error"))}
