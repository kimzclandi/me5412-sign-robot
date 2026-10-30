"""Minimal Google Gemini connectivity client.

This module only checks the OpenAI-compatible API connection. It contains no
ASL conversion or prompt logic.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-3.1-flash-lite"
REQUEST_TIMEOUT_SECONDS = 45.0


def load_project_environment(env_path: Path = ENV_PATH) -> bool:
    """Load project-local configuration without replacing system variables."""

    return load_dotenv(dotenv_path=env_path, override=False)


load_project_environment()


class ConfigurationError(RuntimeError):
    """Raised when the Gemini API configuration is invalid or incomplete."""


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    base_url: str
    model: str

    @classmethod
    def from_environment(cls) -> "GeminiConfig":
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        base_url = (
            os.environ.get("GEMINI_BASE_URL", DEFAULT_BASE_URL).strip()
            or DEFAULT_BASE_URL
        )
        model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

        missing = []
        if not api_key:
            missing.append("GEMINI_API_KEY")
        if missing:
            raise ConfigurationError(
                "Missing required environment variable(s): " + ", ".join(missing)
            )

        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigurationError("GEMINI_BASE_URL must be a complete HTTP(S) URL.")
        if "{" in base_url or "}" in base_url:
            raise ConfigurationError(
                "GEMINI_BASE_URL still contains a placeholder."
            )

        return cls(api_key=api_key, base_url=base_url, model=model)


def safe_configuration_summary() -> dict[str, object]:
    """Return non-secret effective settings without making an API request."""

    config = GeminiConfig.from_environment()
    return {
        "base_url": config.base_url,
        "model": config.model,
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "max_retries": 0,
    }


def chat_completion(messages: list[dict[str, str]]) -> tuple[str, float]:
    """Send chat messages and return the text reply and elapsed seconds."""
    config = GeminiConfig.from_environment()
    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )
    started_at = time.perf_counter()
    try:
        completion = client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=0,
        )
    finally:
        elapsed_seconds = time.perf_counter() - started_at
    if not completion.choices:
        raise OpenAIError("The API returned no choices.")
    reply = completion.choices[0].message.content
    if not isinstance(reply, str) or not reply.strip():
        raise OpenAIError("The API returned an empty text reply.")
    return reply.strip(), elapsed_seconds


def connectivity_test(prompt: str = "Hello") -> tuple[str, float]:
    """Send one minimal connectivity request."""

    return chat_completion([{"role": "user", "content": prompt}])


def main() -> int:
    try:
        reply, elapsed_seconds = connectivity_test("Hello")
        print(reply)
        print(f"Request elapsed: {elapsed_seconds:.3f} seconds")
        return 0
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except AuthenticationError:
        print("Authentication failed. Check GEMINI_API_KEY.", file=sys.stderr)
        return 3
    except APITimeoutError:
        print(
            f"API request timed out after {REQUEST_TIMEOUT_SECONDS:.0f} seconds.",
            file=sys.stderr,
        )
        return 3
    except APIConnectionError:
        print("Could not connect to the configured Gemini base URL.", file=sys.stderr)
        return 3
    except APIStatusError as exc:
        print(f"API returned HTTP status {exc.status_code}.", file=sys.stderr)
        return 3
    except OpenAIError as exc:
        print(f"OpenAI-compatible API error: {type(exc).__name__}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
