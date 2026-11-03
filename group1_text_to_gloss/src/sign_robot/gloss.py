"""Convert short hospital English sentences to validated ASL gloss sequences."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAIError,
)

try:
    from .llm import ConfigurationError, chat_completion
except ImportError:  # Allow direct execution: python src/sign_robot/gloss.py
    from llm import ConfigurationError, chat_completion


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VOCAB_PATH = PROJECT_ROOT / "data" / "vocab" / "hospital_v1.json"
MAX_INPUT_LENGTH = 200
MAX_GLOSSES = 10
REQUIRED_FIELDS = {"status", "glosses", "question", "dropped", "unknown"}

PROMPT_TEMPLATE = """You are an American Sign Language (ASL) conversion assistant in a hospital. A hearing medical worker types an English sentence; you convert its meaning into ASL glosses for a robot to sign to a Deaf patient.

You may ONLY use these currently allowed glosses (gloss: English meanings it covers):
{vocab}

Rules:
1. Translate the meaning, not word by word. Map English synonyms to a listed gloss.
2. Drop English function words that ASL does not need, including: a, an, the, is, are, am, be, do, does, did, will, would, can, could, to, it, this, that, of, at, in, on, for, and.
3. Use the scope of a time expression to place it without changing meaning. A time that frames the whole sentence, such as NOW or TOMORROW, may go at the start. A relative time such as SOON or LATER that directly modifies one action should stay in the same semantic unit as that action, normally after the action. When a concrete object such as MEDICINE is clearly the topic of an instruction, the object topic may come before recurring times such as MORNING and NIGHT, followed by the action. Do not move a time gloss across clause boundaries or change which action it modifies merely to put time first.
4. Use topic first and comment afterward (Topic-Comment). Example: MEDICINE MORNING NIGHT TAKE. When HAVE means possessing or having something, keep the explicit possessor pronoun, make the possessed thing the topic, and put HAVE after it: possessor pronoun + possessed thing + HAVE. Apply this only to possessive HAVE; do not move other verbs such as NEED, UNDERSTAND, or COME, and do not treat the English phrase "have to" as possessive HAVE. For an input with multiple clauses, preserve each clause as a semantic unit and keep its action, object, and local modifiers together; do not move an action such as WAIT into another clause merely to satisfy a time or topic ordering rule.
5. Put a question gloss such as WHERE at the end, but use WHERE only when the English actually asks about a place or location. Never add WHERE merely because the sentence is a question or ends with a question mark. For a yes/no question, set "question" to true without adding WHERE or another question gloss unless that meaning is present in the English.
6. Put NOT after the verb. Example: ME UNDERSTAND NOT.
7. Express subject pronouns such as YOU and ME explicitly. Use YOUR when ownership is important for contrast, identification, or safety. In a routine instruction spoken directly to the patient, YOUR may be omitted when ownership of the patient's medicine or body is already unambiguous from context. Never delete YOUR when doing so would change, blur, or remove important meaning; do not apply this as a rule to remove every YOUR.
8. If important meaning cannot be expressed using the allowed glosses, return unsupported. List the unexpressible words or phrases in unknown. Never guess, substitute, or omit important medical information. For an unsupported result, glosses MUST be exactly an empty list, unknown MUST be a list of strings naming the important unexpressible information, dropped MUST be a list of strings, and question MUST be the boolean that matches the actual input. Never return partial executable glosses together with status "unsupported". Do not avoid unsupported by deleting or guessing important information such as an exact time, insurance information, or a medication allergy.
9. Every output gloss must have a semantic basis in the English input. Do not invent substantive meaning or add extra glosses merely to make the output look complete. Before returning, check each proposed gloss against the input meaning; if it has no basis, do not include it.
10. Use no gloss outside the allowed list and output at most 10 glosses.
11. Return ONLY one JSON object. Do not return Markdown, explanations, or any other text.

Required JSON format:
{{"status": "ok", "glosses": ["YOU", "HURT", "WHERE"], "question": true, "dropped": ["does", "it"], "unknown": []}}

Unsupported JSON structure for a non-question (use question=true instead when the input is a question):
{{"status": "unsupported", "glosses": [], "question": false, "dropped": [], "unknown": ["unexpressible important information"]}}

Examples:
Input: Where does it hurt?
Output: {{"status": "ok", "glosses": ["YOU", "HURT", "WHERE"], "question": true, "dropped": ["does", "it"], "unknown": []}}

Input: Take this medicine in the morning and at night.
Output: {{"status": "ok", "glosses": ["MEDICINE", "MORNING", "NIGHT", "TAKE"], "question": false, "dropped": ["this", "in", "the", "and", "at"], "unknown": []}}

Input: The nurse will draw your blood now.
Output: {{"status": "ok", "glosses": ["NOW", "NURSE", "BLOOD-DRAW"], "question": false, "dropped": ["the", "will", "your"], "unknown": []}}

Input: Sorry, I don't understand.
Output: {{"status": "ok", "glosses": ["SORRY", "ME", "UNDERSTAND", "NOT"], "question": false, "dropped": [], "unknown": []}}

Input: Do you need an X-ray?
Output: {{"status": "unsupported", "glosses": [], "question": true, "dropped": [], "unknown": ["X-ray"]}}
"""


def _unsupported(latency_ms: float = 0.0) -> dict[str, Any]:
    return {
        "status": "unsupported",
        "glosses": [],
        "question": False,
        "dropped": [],
        "unknown": [],
        "latency_ms": latency_ms,
    }


def _error(
    reason: str,
    latency_ms: float,
    *,
    error_category: str | None = None,
    http_status: int | None = None,
    retry_after_seconds: float | None = None,
    validation_detail: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "error",
        "reason": reason,
        "glosses": [],
        "latency_ms": latency_ms,
    }
    if error_category is not None:
        result["error_category"] = error_category
    if http_status is not None:
        result["http_status"] = http_status
    if retry_after_seconds is not None:
        result["retry_after_seconds"] = retry_after_seconds
    if validation_detail is not None:
        result["validation_detail"] = validation_detail
    return result


def _classify_llm_exception(exc: Exception) -> tuple[str, int | None]:
    """Return a safe category and status without exposing request details."""

    if isinstance(exc, ConfigurationError):
        return "configuration", None
    if isinstance(exc, AuthenticationError):
        return "authentication", getattr(exc, "status_code", 401)
    if isinstance(exc, APITimeoutError):
        return "timeout", None
    if isinstance(exc, APIConnectionError):
        return "connection", None
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        if status == 400:
            return "bad_request", status
        if status == 429:
            return "rate_limit", status
        if isinstance(status, int) and status >= 500:
            return "server_error", status
        return "api_status", status
    if isinstance(exc, OSError):
        return "local_io", None
    return "openai_error", None


def _safe_google_error_code(exc: Exception) -> str | None:
    """Extract Google's structured status token, never its free-text message."""

    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None
    error = body.get("error", body)
    if not isinstance(error, dict):
        return None
    code = error.get("status")
    if not isinstance(code, str):
        return None
    normalized = code.strip().upper()
    if not normalized or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_" for char in normalized):
        return None
    return normalized[:64]


def _safe_retry_after_seconds(exc: Exception) -> float | None:
    """Extract a bounded Retry-After delay without exposing response headers."""

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    value = headers.get("retry-after")
    if not isinstance(value, str):
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            seconds = (when - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return None
    if seconds < 0 or seconds > 3600:
        return None
    return round(seconds, 3)


def _debug_llm_exception(exc: Exception) -> None:
    """Print only non-sensitive diagnostics when explicitly enabled."""

    enabled = os.environ.get("SIGN_ROBOT_DEBUG", "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return
    category, status = _classify_llm_exception(exc)
    fields = [f"type={type(exc).__name__}", f"category={category}"]
    if status is not None:
        fields.append(f"http_status={status}")
    google_code = _safe_google_error_code(exc)
    if google_code is not None:
        fields.append(f"google_code={google_code}")
    print("LLM debug: " + " ".join(fields), file=sys.stderr)


def _load_vocab(demo_only: bool) -> list[dict[str, Any]]:
    with VOCAB_PATH.open(encoding="utf-8") as handle:
        vocab = json.load(handle)
    if not isinstance(vocab, list):
        raise ValueError("Vocabulary root must be a list.")
    selected = [entry for entry in vocab if not demo_only or entry.get("motion_ready") is True]
    if not selected:
        raise ValueError("No glosses are available in the selected mode.")
    return selected


def _build_prompt(vocab: list[dict[str, Any]]) -> str:
    lines = []
    for entry in vocab:
        gloss = entry.get("gloss")
        english = entry.get("english")
        if not isinstance(gloss, str) or not isinstance(english, list) or not all(
            isinstance(item, str) for item in english
        ):
            raise ValueError("Invalid vocabulary entry.")
        lines.append(f"{gloss}: {', '.join(english)}")
    return PROMPT_TEMPLATE.format(vocab="\n".join(lines))


def _parse_and_validate(
    raw_response: str, allowed_glosses: set[str], latency_ms: float
) -> dict[str, Any]:
    try:
        result = json.loads(raw_response)
    except (json.JSONDecodeError, TypeError):
        return _error("invalid_json", latency_ms)

    if not isinstance(result, dict) or not REQUIRED_FIELDS.issubset(result):
        return _error("invalid_json", latency_ms)
    if result["status"] not in {"ok", "unsupported"}:
        return _error(
            "validation_error", latency_ms, validation_detail="invalid_status"
        )
    if not isinstance(result["question"], bool):
        return _error(
            "validation_error", latency_ms, validation_detail="question_not_bool"
        )
    for field in ("glosses", "dropped", "unknown"):
        value = result[field]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return _error(
                "validation_error",
                latency_ms,
                validation_detail="field_not_string_list",
            )

    glosses = result["glosses"]
    if result["status"] == "ok":
        if not glosses:
            return _error(
                "validation_error",
                latency_ms,
                validation_detail="ok_empty_glosses",
            )
        if len(glosses) > MAX_GLOSSES:
            return _error(
                "validation_error",
                latency_ms,
                validation_detail="too_many_glosses",
            )
        if any(gloss not in allowed_glosses for gloss in glosses):
            return _error("unknown_gloss", latency_ms)
    elif glosses:
        return _error(
            "validation_error",
            latency_ms,
            validation_detail="unsupported_nonempty_glosses",
        )

    return {
        "status": result["status"],
        "glosses": glosses,
        "question": result["question"],
        "dropped": result["dropped"],
        "unknown": result["unknown"],
        "latency_ms": latency_ms,
    }


def text_to_gloss(sentence: str, demo_only: bool = False) -> dict[str, Any]:
    """Convert English to a strictly validated ASL gloss result."""

    if not isinstance(sentence, str) or not sentence.strip() or len(sentence) > MAX_INPUT_LENGTH:
        return _unsupported()

    started_at = time.perf_counter()
    try:
        vocab = _load_vocab(demo_only)
        prompt = _build_prompt(vocab)
        allowed_glosses = {entry["gloss"] for entry in vocab}
        raw_response, _ = chat_completion(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": sentence.strip()},
            ]
        )
    except (ConfigurationError, OpenAIError) as exc:
        _debug_llm_exception(exc)
        error_category, http_status = _classify_llm_exception(exc)
        retry_after_seconds = _safe_retry_after_seconds(exc)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 3)
        return _error(
            "llm_unavailable",
            latency_ms,
            error_category=error_category,
            http_status=http_status,
            retry_after_seconds=retry_after_seconds,
        )
    except OSError as exc:
        _debug_llm_exception(exc)
        error_category, http_status = _classify_llm_exception(exc)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 3)
        return _error(
            "llm_unavailable",
            latency_ms,
            error_category=error_category,
            http_status=http_status,
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        latency_ms = round((time.perf_counter() - started_at) * 1000, 3)
        return _error("validation_error", latency_ms)

    latency_ms = round((time.perf_counter() - started_at) * 1000, 3)
    return _parse_and_validate(raw_response, allowed_glosses, latency_ms)


def main() -> int:
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        print("GEMINI_API_KEY is not configured; no API requests were sent.")
        return 0

    for sentence in ("Where does it hurt?", "Do you need an X-ray?"):
        result = text_to_gloss(sentence)
        print(json.dumps({"input": sentence, "result": result}, ensure_ascii=False))
        if result["status"] == "error":
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
