"""One call to the Gemini REST API.

Deliberately no retry logic: this makes a single attempt and raises a
classified `LLMError`. Every decision about what to try next belongs to
`chain.py`, which is what makes both halves testable in isolation.

The REST endpoint is used rather than the `google-genai` SDK because the
failover design turns entirely on HTTP status classification, and reading the
status directly is more precise than mapping SDK exception types. It also
keeps the dependency to `httpx`, which is already present.
"""
import logging

import httpx

from backend.llm.base import FailureKind, LLMError, LLMReply

logger = logging.getLogger(__name__)

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"

#: Statuses that mean the credential is fine but the request could not be
#: served now. Anything else is classified explicitly below.
_TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})


def _classify(status: int, body: str) -> LLMError:
    if status == 429:
        return LLMError(FailureKind.RATE_LIMITED, f"quota or rate limit: {body[:200]}")
    if status in (401, 403):
        return LLMError(FailureKind.INVALID_CREDENTIAL, f"key rejected: {body[:200]}")
    if status in _TRANSIENT_STATUSES:
        return LLMError(FailureKind.TRANSIENT, f"upstream {status}: {body[:200]}")
    if status == 400:
        # Ours to fix. The chain must not advance on this.
        return LLMError(FailureKind.BAD_REQUEST, f"malformed request: {body[:200]}")
    if status == 404:
        # The model id is wrong, retired, or not enabled for this account.
        # Trying it with another key cannot help.
        return LLMError(FailureKind.MODEL_UNAVAILABLE, f"model not found: {body[:200]}")
    return LLMError(FailureKind.TRANSIENT, f"unexpected status {status}: {body[:200]}")


def _extract_text(payload: dict) -> str:
    """Pull the reply text out of a generateContent response.

    Returns an empty string when the model produced nothing, which the caller
    turns into NO_CONTENT -- a safety block and an empty candidate list look
    the same from here and are handled the same way.
    """
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""

    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts).strip()


def generate(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float,
    max_output_tokens: int = 400,
    temperature: float = 0.4,
) -> LLMReply:
    """Make exactly one generation attempt. Raises `LLMError` on any failure."""
    url = f"{API_ROOT}/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            # Header rather than a ?key= query parameter, so the credential
            # does not end up in proxy logs or error messages containing URLs.
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise LLMError(FailureKind.TRANSIENT, f"timed out after {timeout}s") from exc
    except httpx.HTTPError as exc:
        raise LLMError(FailureKind.TRANSIENT, f"transport error: {exc}") from exc

    if response.status_code != 200:
        error = _classify(response.status_code, response.text)
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                error.retry_after = float(retry_after)
            except ValueError:
                pass
        raise error

    try:
        body = response.json()
    except ValueError as exc:
        raise LLMError(FailureKind.TRANSIENT, "response was not JSON") from exc

    # A prompt rejected before generation reports the reason here.
    block_reason = (body.get("promptFeedback") or {}).get("blockReason")
    if block_reason:
        raise LLMError(FailureKind.NO_CONTENT, f"prompt blocked: {block_reason}")

    text = _extract_text(body)
    if not text:
        raise LLMError(FailureKind.NO_CONTENT, "model returned no text")

    return LLMReply(text=text, model=model)
