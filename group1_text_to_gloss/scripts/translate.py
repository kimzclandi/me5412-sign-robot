"""Command-line entry point for English-to-ASL-gloss conversion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sign_robot.gloss import text_to_gloss  # noqa: E402


EXIT_COMMANDS = {"exit", "quit"}


def _configure_utf8_output() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def render_interactive(result: dict[str, Any]) -> str:
    """Render a safe, human-readable view of one unchanged result."""

    status = result.get("status")
    latency = result.get("latency_ms")
    if status == "ok":
        glosses = result.get("glosses", [])
        lines = [" ".join(glosses), "status=ok"]
        lines.append(f"question={str(result.get('question')).lower()}")
        lines.append(f"latency_ms={latency}")
        return "\n".join(lines)
    if status == "unsupported":
        unknown = result.get("unknown", [])
        return "\n".join(
            [
                "unsupported",
                "status=unsupported",
                f"question={str(result.get('question')).lower()}",
                "unknown=" + ", ".join(unknown),
                f"latency_ms={latency}",
            ]
        )

    safe_fields = [f"status={status or 'error'}", f"reason={result.get('reason', 'unknown_error')}"]
    for name in ("error_category", "http_status", "validation_detail"):
        if result.get(name) is not None:
            safe_fields.append(f"{name}={result[name]}")
    safe_fields.append(f"latency_ms={latency}")
    return "\n".join(safe_fields)


def interactive_loop(
    *,
    demo_only: bool,
    converter: Callable[[str, bool], dict[str, Any]] = text_to_gloss,
    input_func: Callable[[str], str] = input,
) -> int:
    while True:
        try:
            sentence = input_func("English> ")
        except EOFError:
            return 0
        stripped = sentence.strip()
        if stripped.lower() in EXIT_COMMANDS:
            return 0
        if not stripped:
            print("请输入非空英文句子；未发送 API 请求。")
            continue
        result = converter(stripped, demo_only)
        print(render_interactive(result))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sentence", nargs="?", help="English sentence; omit for interactive mode.")
    parser.add_argument(
        "--demo-only",
        action="store_true",
        help="Allow only glosses whose motion_ready value is true.",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    converter: Callable[[str, bool], dict[str, Any]] = text_to_gloss,
    input_func: Callable[[str], str] = input,
) -> int:
    _configure_utf8_output()
    args = parse_args(argv)
    if args.sentence is None:
        return interactive_loop(
            demo_only=args.demo_only,
            converter=converter,
            input_func=input_func,
        )
    sentence = args.sentence.strip()
    if not sentence:
        print("输入不能为空；未发送 API 请求。", file=sys.stderr)
        return 2
    result = converter(sentence, args.demo_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"ok", "unsupported"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
