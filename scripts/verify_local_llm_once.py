#!/usr/bin/env python3
"""One immutable development feasibility attempt; never reads final evaluation."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from sign_robot import llm
from sign_robot.contracts import ROOT
from sign_robot.language import select_action


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-mode", choices=["json", "label"], default="json")
    args = parser.parse_args()
    version = "v1" if args.output_mode == "json" else "v2_label"
    output = ROOT / f"config/llm_local_feasibility_{version}.json"
    if output.exists():
        raise SystemExit("The first feasibility record already exists; this script refuses to rerun or overwrite it.")
    captured = []
    original_root, original_builder = llm.ROOT, llm.build_opener

    class RecordingOpener:
        def __init__(self, opener):
            self.opener = opener

        def open(self, request, timeout):
            record = {"request_sha256": hashlib.sha256(request.data).hexdigest(),
                      "request": json.loads(request.data)}
            record["prompt_prefix_sha256"] = hashlib.sha256(json.dumps(
                record["request"]["messages"][:-1], ensure_ascii=False,
                sort_keys=True).encode("utf-8")).hexdigest()
            captured.append(record)
            response = self.opener.open(request, timeout=timeout)

            class RecordingResponse:
                def __enter__(self): return self
                def __exit__(self, *args): response.close()
                def read(self, size):
                    raw = response.read(size)
                    record["response_sha256"] = hashlib.sha256(raw).hexdigest()
                    record["response_utf8"] = raw.decode("utf-8", errors="replace")
                    return raw

            return RecordingResponse()

    report = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "attempt": 1, "cases": [], "scope": "Three developer positive examples only; no test-set use or prompt tuning.",
              "output_mode": args.output_mode,
              "development_change": ("Explicit label schema with three positive and one unsupported public few-shot example; authorized after v1 invalid-JSON failure, no held-out tuning." if args.output_mode == "label" else "Original JSON mode."),
              "server_json_mode": "MLX-LM 0.26.3 ignores response_format; strict client parsing only.",
              "source_hashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                for p in ["src/sign_robot/language.py", "src/sign_robot/llm.py", "data/catalog.json"]}}
    try:
        with tempfile.TemporaryDirectory(prefix="me5412-local-llm-") as temporary:
            llm.ROOT = Path(temporary)
            (llm.ROOT / "config").mkdir()
            (llm.ROOT / "config/llm.json").write_text(json.dumps({
                "endpoint": "http://127.0.0.1:5413/v1/chat/completions",
                "model": "default_model", "timeout_s": 10,
                "output_mode": args.output_mode}), encoding="utf-8")
            llm.build_opener = lambda *handlers: RecordingOpener(original_builder(*handlers))
            for text, expected in [("Hello", "HELLO"), ("Thank you", "THANK_YOU"), ("Please wait", "PLEASE_WAIT")]:
                result = select_action(text, method="llm")
                case = {"text": text, "expected_action_id": expected, "actual": result,
                        "correct": result["status"] == "execute" and result["action_id"] == expected}
                report["cases"].append(case)
                print(json.dumps(case, ensure_ascii=False), flush=True)
    finally:
        llm.ROOT, llm.build_opener = original_root, original_builder
        report["http_records"] = captured
        report["all_three_correct"] = len(report["cases"]) == 3 and all(case["correct"] for case in report["cases"])
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Preserved single-attempt record: {output}", flush=True)


if __name__ == "__main__":
    main()
