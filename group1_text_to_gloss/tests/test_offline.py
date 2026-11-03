"""Offline regression tests. These tests must never contact Gemini."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sign_robot.gloss import text_to_gloss
from sign_robot.llm import load_project_environment


def _load_translate_module():
    path = PROJECT_ROOT / "scripts" / "translate.py"
    spec = importlib.util.spec_from_file_location("translate_for_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scripts/translate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


translate = _load_translate_module()


def _ok_result() -> dict[str, object]:
    return {
        "status": "ok",
        "glosses": ["YOU", "HURT", "WHERE"],
        "question": True,
        "dropped": ["does", "it"],
        "unknown": [],
        "latency_ms": 1.0,
    }


class GlossOfflineTests(unittest.TestCase):
    def test_empty_input_is_rejected_without_llm_call(self) -> None:
        with patch("sign_robot.gloss.chat_completion") as mocked:
            result = text_to_gloss("   ")
        mocked.assert_not_called()
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["glosses"], [])

    def test_valid_mocked_response_is_parsed(self) -> None:
        raw = json.dumps(
            {
                "status": "ok",
                "glosses": ["YOU", "HURT", "WHERE"],
                "question": True,
                "dropped": ["does", "it"],
                "unknown": [],
            }
        )
        with patch("sign_robot.gloss.chat_completion", return_value=(raw, 0.01)):
            result = text_to_gloss("Where does it hurt?")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["glosses"], ["YOU", "HURT", "WHERE"])

    def test_unknown_gloss_is_not_executable(self) -> None:
        raw = json.dumps(
            {
                "status": "ok",
                "glosses": ["XRAY"],
                "question": False,
                "dropped": [],
                "unknown": [],
            }
        )
        with patch("sign_robot.gloss.chat_completion", return_value=(raw, 0.01)):
            result = text_to_gloss("X-ray")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "unknown_gloss")
        self.assertEqual(result["glosses"], [])


class EnvironmentOfflineTests(unittest.TestCase):
    def test_dotenv_loads_missing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "GEMINI_API_KEY=simulated-file-key\n"
                "GEMINI_MODEL=gemini-3.1-flash-lite\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                loaded = load_project_environment(env_path)
                self.assertTrue(loaded)
                self.assertEqual(os.environ["GEMINI_API_KEY"], "simulated-file-key")
                self.assertEqual(os.environ["GEMINI_MODEL"], "gemini-3.1-flash-lite")

    def test_system_environment_has_priority_over_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "GEMINI_API_KEY=simulated-file-key\n"
                "GEMINI_MODEL=file-model\n",
                encoding="utf-8",
            )
            existing = {
                "GEMINI_API_KEY": "simulated-system-key",
                "GEMINI_MODEL": "system-model",
            }
            with patch.dict(os.environ, existing, clear=True):
                load_project_environment(env_path)
                self.assertEqual(os.environ["GEMINI_API_KEY"], "simulated-system-key")
                self.assertEqual(os.environ["GEMINI_MODEL"], "system-model")


class TranslateOfflineTests(unittest.TestCase):
    def test_direct_mode_prints_complete_json(self) -> None:
        calls: list[tuple[str, bool]] = []

        def converter(sentence: str, demo_only: bool):
            calls.append((sentence, demo_only))
            return _ok_result()

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = translate.main(
                ["--demo-only", "Where does it hurt?"], converter=converter
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [("Where does it hurt?", True)])
        self.assertEqual(json.loads(stdout.getvalue()), _ok_result())

    def test_interactive_empty_input_and_exit_do_not_call_converter(self) -> None:
        calls = 0

        def converter(_sentence: str, _demo_only: bool):
            nonlocal calls
            calls += 1
            return _ok_result()

        answers = iter(["", "exit"])
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = translate.interactive_loop(
                demo_only=False,
                converter=converter,
                input_func=lambda _prompt: next(answers),
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, 0)


if __name__ == "__main__":
    unittest.main()
