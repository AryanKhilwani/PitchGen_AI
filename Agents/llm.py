"""
Shared LLM interface for all agents.

Uses Gemini 2.0 Flash via google-genai (same as RAG engine).
Handles rate limiting with exponential backoff.
Swappable to any LangChain-compatible model later.
"""

import os
import re
import time

from google import genai
from dotenv import load_dotenv

load_dotenv()
# Also try RAG/.env and Agents/.env if key not found
if not os.getenv("GEMINI_API_KEY"):
    _base = os.path.join(os.path.dirname(__file__), "..")
    for _env in [
        os.path.join(_base, "RAG", ".env"),
        os.path.join(_base, "Agents", ".env"),
    ]:
        if os.path.exists(_env):
            load_dotenv(_env)

_client = None

MODEL = os.getenv("AGENT_LLM_MODEL", "gemini-2.0-flash")
MAX_RETRIES = 10
API_CALL_DELAY = 3  # seconds between calls for free tier


def _get_client():
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set. Add it to .env or export it.")
        _client = genai.Client(api_key=api_key)
    return _client


# Error patterns that are transient and worth retrying
_RETRIABLE_PATTERNS = (
    "429",
    "RESOURCE_EXHAUSTED",
    "503",
    "UNAVAILABLE",
    "500",
    "INTERNAL",
    "DEADLINE_EXCEEDED",
    "overloaded",
    "high demand",
    "temporarily",
    "try again",
)


def _is_retriable(error_str: str) -> bool:
    """Check if an error message matches a transient/retriable pattern."""
    lower = error_str.lower()
    return any(p.lower() in lower for p in _RETRIABLE_PATTERNS)


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Call the LLM with a system + user prompt. Returns the response text.
    Handles transient errors (429, 503, 500) with exponential backoff.
    """
    combined = f"{system_prompt}\n\n{user_prompt}"

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                time.sleep(API_CALL_DELAY)

            response = _get_client().models.generate_content(
                model=MODEL,
                contents=[combined],
                config={"temperature": temperature},
            )
            return response.text.strip()

        except Exception as e:
            error_str = str(e)
            if _is_retriable(error_str):
                # Parse explicit retry delay from error if present
                wait_time = min(
                    30 * (2**attempt), 300
                )  # exponential: 30, 60, 120, 240, 300
                match = re.search(r"retryDelay': '(\d+)s", error_str)
                if match:
                    wait_time = max(int(match.group(1)), wait_time)
                print(
                    f"  ⏳ Transient error (attempt {attempt+1}/{MAX_RETRIES}): "
                    f"{error_str[:100]}..."
                )
                print(f"     Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            # Non-retriable error — fail immediately
            print(f"  ❌ LLM error (non-retriable): {e}")
            raise

    raise RuntimeError(f"Failed to get LLM response after {MAX_RETRIES} retries.")
