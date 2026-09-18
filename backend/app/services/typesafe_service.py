import logging
import os
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("ai_ensemble.typesafe")

TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone"


def get_typesafe_api_key() -> str:
    return settings.typesafe_api_key or os.getenv("TYPESAFE_API_KEY", "")


async def evaluate_system_one(
    state: Any,
    questions: Dict[str, Any],
    model: str = "jev-latest",
    api_key: Optional[str] = None,
    timeout: float = 8.0,
) -> Optional[Dict[str, Any]]:
    """Evaluate state against typed questions using TypeSafe System One (Jev)."""
    key = api_key or get_typesafe_api_key()
    if not key:
        logger.debug("TypeSafe API key not configured; skipping System One evaluation")
        return None

    payload = {
        "state": state,
        "model": model,
        "questions": questions,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(TYPESAFE_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning(f"TypeSafe System One evaluation failed: {exc}")
        return None


async def should_search_web(prompt: str) -> bool:
    """Use TypeSafe Jev to evaluate whether a prompt requires live web search in ~50ms.
    
    Returns True if confidence/probability >= 0.65, or falls back to True on error.
    """
    key = get_typesafe_api_key()
    if not key:
        return True

    res = await evaluate_system_one(
        state=prompt,
        questions={
            "needs_web_search": {
                "type": "noul",
                "instructions": (
                    "Does this user prompt require searching the live web for recent events, "
                    "current facts, live data, or up-to-date documentation?"
                ),
                "criteria": {
                    "true": "Needs real-time or external live web search",
                    "false": "General knowledge, coding, creative writing, or self-contained logic",
                },
            }
        },
    )
    if not res:
        return True

    noul = res.get("answers", {}).get("needs_web_search", {}).get("noul")
    if noul is not None:
        logger.info(f"[TypeSafe] Web search necessity probability: {noul:.2f}")
        return noul >= 0.65
    return True


async def classify_oauth_error(provider: str, raw_error: str) -> dict:
    """Use TypeSafe Jev to classify an OAuth/upstream error into user-actionable diagnostics."""
    key = get_typesafe_api_key()
    if not key or not raw_error:
        return {"category": "unknown", "actionable_hint": raw_error}

    res = await evaluate_system_one(
        state={"provider": provider, "error": raw_error},
        questions={
            "category": {
                "type": "choice",
                "instructions": "Classify the root cause of this OAuth or API authorization error.",
                "choices": ["rate_limit", "expired", "access_denied", "subscription_required", "network_failure", "other"],
            },
            "user_action": {
                "type": "choice",
                "instructions": "What should the user do to resolve this error?",
                "choices": ["wait_and_retry", "restart_login", "check_subscription", "contact_admin"],
            },
        },
    )
    if not res:
        return {"category": "unknown", "actionable_hint": raw_error}

    answers = res.get("answers", {})
    cat = answers.get("category", {}).get("choice", "other")
    action = answers.get("user_action", {}).get("choice", "restart_login")
    return {
        "category": cat,
        "action": action,
        "actionable_hint": f"{cat}: {action}",
    }
