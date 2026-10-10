"""Thin client for any OpenAI-compatible chat-completions API.

The key comes from the environment and is never logged or put in error messages.
"""
import logging

import requests

from app.config import settings
from app.exceptions import LLMUnavailableError

logger = logging.getLogger(__name__)


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 900) -> str:
    if not settings.llm_api_key:
        raise LLMUnavailableError("The LLM is not configured (LLM_API_KEY is missing).")
    try:
        resp = requests.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}",
                     "Content-Type": "application/json"},
            json={"model": settings.llm_model, "temperature": temperature, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system_prompt},
                               {"role": "user", "content": user_prompt}]},
            timeout=settings.llm_timeout,
        )
    except requests.RequestException as exc:
        logger.error("LLM request failed: %s", type(exc).__name__)
        raise LLMUnavailableError("Could not reach the LLM service.") from exc
    if resp.status_code != 200:
        logger.error("LLM returned HTTP %s", resp.status_code)
        raise LLMUnavailableError(f"The LLM service returned HTTP {resp.status_code}.")
    try:
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMUnavailableError("The LLM returned an unexpected response.") from exc


def ask_llm_or_fallback(system_prompt: str, user_prompt: str, fallback_text: str) -> tuple[str, bool]:
    """Try the LLM; if it is unavailable return (fallback_text, False). Never silent: callers add a warning."""
    try:
        return call_llm(system_prompt, user_prompt), True
    except LLMUnavailableError as exc:
        logger.warning("LLM unavailable, using fallback: %s", exc.message)
        return fallback_text, False
