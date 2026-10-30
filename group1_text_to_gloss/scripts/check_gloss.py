"""Evaluate English-to-ASL-gloss conversion with explicit API safeguards."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
CSV_PATH = PROJECT_ROOT / "data" / "gloss_eval" / "gloss_test.csv"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results" / "gloss_check"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sign_robot.gloss import text_to_gloss  # noqa: E402
from sign_robot.llm import DEFAULT_MODEL  # noqa: E402


CATEGORIES = ("脚本原句", "换说法", "词库外")
CATEGORY_ALIASES = {"库外": "词库外"}
STOP_ERROR_CATEGORIES = {"rate_limit", "authentication", "server_error", "configuration"}
RETRYABLE_HTTP = {500, 502, 503, 504}
RETRYABLE_CATEGORIES = {"timeout", "connection"}
FATAL_HTTP = {401, 403, 404, 429}


def effective_model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def test_data_hash(path: Path = CSV_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def load_cases(path: Path = CSV_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"id", "type", "sentence", "expected", "question"}
    cases: list[dict[str, Any]] = []
    for row in rows:
        if not required.issubset(row):
            raise ValueError("CSV is missing required columns.")
        question_text = row["question"].strip().lower()
        if question_text not in {"true", "false"}:
            raise ValueError(f"Invalid question value for {row['id']}.")
        expected_text = row["expected"].strip()
        category = row["type"].strip()
        category = CATEGORY_ALIASES.get(category, category)
        if category not in CATEGORIES:
            raise ValueError(f"Unknown test category for {row['id']}: {category}")
        cases.append(
            {
                "id": row["id"].strip(),
                "type": category,
                "sentence": row["sentence"],
                "expected": expected_text,
                "expected_options": (
                    [] if expected_text == "unsupported" else expected_text.split("|")
                ),
                "expected_question": question_text == "true",
            }
        )
    return cases


def select_ids(cases: list[dict[str, Any]], requested: list[str] | None) -> list[str]:
    """Validate IDs and preserve the user's order without duplicate execution."""

    available = {case["id"] for case in cases}
    if requested is None:
        return [case["id"] for case in cases]
    duplicates = []
    seen = set()
    for test_id in requested:
        if test_id in seen and test_id not in duplicates:
            duplicates.append(test_id)
        seen.add(test_id)
    if duplicates:
        raise ValueError("Duplicate test ID(s): " + ", ".join(duplicates))
    unknown = [test_id for test_id in requested if test_id not in available]
    if unknown:
        raise ValueError("Unknown test ID(s): " + ", ".join(unknown))
    return list(requested)


def judge(case: dict[str, Any], model_result: dict[str, Any]) -> tuple[bool, bool, str]:
    status = model_result.get("status")
    glosses = model_result.get("glosses")
    if case["expected"] == "unsupported":
        passed = status == "unsupported" and glosses == []
        actual = "unsupported" if passed else " ".join(glosses or [])
    else:
        actual = " ".join(glosses) if isinstance(glosses, list) else ""
        passed = status == "ok" and actual in case["expected_options"]
    question_correct = model_result.get("question") == case["expected_question"]
    return passed, question_correct, actual


def _not_run(case: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "id": case["id"],
        "type": case["type"],
        "sentence": case["sentence"],
        "expected": case["expected"],
        "expected_question": case["expected_question"],
        "execution": "not_run",
        "not_run_reason": reason,
        "verdict": "NOT_RUN",
        "question_correct": None,
        "latency_ms": None,
        "attempts": [],
        "model_result": None,
    }


def _executed(
    case: dict[str, Any],
    model_result: dict[str, Any],
    attempts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    passed, question_correct, actual = judge(case, model_result)
    return {
        "id": case["id"],
        "type": case["type"],
        "sentence": case["sentence"],
        "expected": case["expected"],
        "expected_question": case["expected_question"],
        "execution": "completed",
        "verdict": "PASS" if passed else "FAIL",
        "question_correct": question_correct,
        "actual": actual,
        "latency_ms": model_result.get("latency_ms"),
        "reason": model_result.get("reason"),
        "validation_detail": model_result.get("validation_detail"),
        "attempts": attempts or [],
        "model_result": model_result,
    }


def _api_failed(
    case: dict[str, Any], model_result: dict[str, Any], attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    record = _not_run(case, "api_failed")
    record.update(
        {
            "execution": "api_failed",
            "verdict": "API_FAILURE",
            "latency_ms": model_result.get("latency_ms"),
            "reason": model_result.get("reason"),
            "attempts": attempts,
            "model_result": model_result,
        }
    )
    return record


def _attempt(number: int, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt": number,
        "status": result.get("status"),
        "reason": result.get("reason"),
        "validation_detail": result.get("validation_detail"),
        "error_category": result.get("error_category"),
        "http_status": result.get("http_status"),
        "retry_after_seconds": result.get("retry_after_seconds"),
        "latency_ms": result.get("latency_ms"),
    }


def _is_api_failure(result: dict[str, Any]) -> bool:
    return result.get("status") == "error" and result.get("reason") == "llm_unavailable"


def _is_retryable(result: dict[str, Any]) -> bool:
    return (
        result.get("http_status") in RETRYABLE_HTTP
        or result.get("error_category") in RETRYABLE_CATEGORIES
    )


def _retry_wait(index: int, base: float, jitter: float, rng: random.Random) -> float:
    return base * (2**index) + rng.uniform(0.0, jitter)


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [record for record in records if record["execution"] == "completed"]
    passed = [record for record in completed if record["verdict"] == "PASS"]
    failed = [record for record in completed if record["verdict"] == "FAIL"]
    api_failed = [record for record in records if record["execution"] == "api_failed"]
    not_run = [record for record in records if record["execution"] == "not_run"]
    attempts = [attempt for record in records for attempt in record.get("attempts", [])]
    validation_details = [
        attempt["validation_detail"]
        for attempt in attempts
        if isinstance(attempt.get("validation_detail"), str)
    ]
    validation_detail_counts = {
        detail: validation_details.count(detail) for detail in sorted(set(validation_details))
    }
    latencies = [
        float(attempt["latency_ms"])
        for attempt in attempts
        if isinstance(attempt.get("latency_ms"), (int, float))
    ]
    by_category = {}
    for category in CATEGORIES:
        category_records = [record for record in records if record["type"] == category]
        by_category[category] = {
            "total": len(category_records),
            "completed": sum(record["execution"] == "completed" for record in category_records),
            "correct": sum(record["verdict"] == "PASS" for record in category_records),
            "api_failed": sum(record["execution"] == "api_failed" for record in category_records),
            "not_run": sum(record["execution"] == "not_run" for record in category_records),
        }
    total = len(records)
    return {
        "by_category": by_category,
        "total_cases": total,
        "completed_cases": len(completed),
        "correct_conversions": len(passed),
        "incorrect_conversions": len(failed),
        "api_failures": len(api_failed),
        "api_total_requests": len(attempts),
        "retry_count": sum(max(0, len(record.get("attempts", [])) - 1) for record in records),
        "validation_detail_counts": validation_detail_counts,
        "average_response_ms": (sum(latencies) / len(latencies)) if latencies else None,
        "slowest_response_ms": max(latencies) if latencies else None,
        "not_run_cases": len(not_run),
        "effective_accuracy": len(passed) / len(completed) if completed else None,
        "end_to_end_success_rate": len(passed) / total if total else None,
        "question_correct": sum(record["question_correct"] is True for record in completed),
        "conversion_failures": failed,
        "api_failure_details": api_failed,
    }


def evaluate(
    cases: list[dict[str, Any]],
    *,
    live: bool,
    max_requests: int,
    delay: float,
    max_retries: int = 2,
    backoff_base: float = 2.0,
    jitter: float = 1.0,
    converter: Callable[[str, bool], dict[str, Any]] = text_to_gloss,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    run_kind: str | None = None,
    resumed_records: dict[str, dict[str, Any]] | None = None,
    checkpoint: Callable[[dict[str, Any]], None] | None = None,
    resumed_from: str | None = None,
    selected_ids: list[str] | None = None,
) -> dict[str, Any]:
    mode = run_kind or ("live" if live else "dry_run")
    selected_ids = select_ids(cases, selected_ids)
    selected_set = set(selected_ids)
    records = [
        _not_run(
            case,
            ("pending" if live else "dry_run") if case["id"] in selected_set else "not_selected",
        )
        for case in cases
    ]
    report = {
        "schema_version": 2,
        "simulated": mode == "simulated",
        "mode": mode,
        "model": effective_model(),
        "test_time": datetime.now().astimezone().isoformat(),
        "source_csv": str(CSV_PATH),
        "test_data_sha256": test_data_hash(),
        "selected_ids": selected_ids,
        "resumed_from": resumed_from,
        "settings": {
            "max_requests": max_requests,
            "delay_seconds": delay,
            "max_retries": max_retries,
            "backoff_base_seconds": backoff_base,
            "jitter_seconds": jitter,
        },
        "api_requests_this_run": 0,
        "stop_reason": None,
        "summary": summarize(records),
        "tests": records,
    }
    attempted = 0
    rng = rng or random.Random()
    resumed_records = resumed_records or {}

    def update(index: int, record: dict[str, Any]) -> None:
        records[index] = record
        report["api_requests_this_run"] = attempted
        report["summary"] = summarize(records)
        if checkpoint:
            checkpoint(report)

    if checkpoint:
        checkpoint(report)

    case_by_id = {case["id"]: (index, case) for index, case in enumerate(cases)}
    for selected_id in selected_ids:
        index, case = case_by_id[selected_id]
        if case["id"] in resumed_records:
            update(index, resumed_records[case["id"]])
            continue
        if not live:
            update(index, _not_run(case, "dry_run"))
            continue
        if report["stop_reason"]:
            update(index, _not_run(case, report["stop_reason"]))
            continue

        attempts: list[dict[str, Any]] = []
        result: dict[str, Any] | None = None
        for retry_index in range(max_retries + 1):
            if attempted >= max_requests:
                report["stop_reason"] = "max_requests_reached"
                break
            wait = delay if attempted > 0 else 0.0
            if retry_index > 0:
                wait = max(wait, _retry_wait(retry_index - 1, backoff_base, jitter, rng))
            if wait > 0:
                sleep(wait)
            attempted += 1
            result = converter(case["sentence"], False)
            attempts.append(_attempt(len(attempts) + 1, result))
            if not _is_api_failure(result):
                break
            status = result.get("http_status")
            if status == 429:
                report["stop_reason"] = "stopped_after_rate_limit"
                break
            if not _is_retryable(result):
                if status in FATAL_HTTP or result.get("error_category") in {
                    "authentication",
                    "configuration",
                }:
                    report["stop_reason"] = "stopped_after_non_retryable_api_error"
                break
            if retry_index >= max_retries:
                report["stop_reason"] = "stopped_after_retry_exhausted"
                break

        if result is None:
            update(index, _not_run(case, report["stop_reason"] or "max_requests_reached"))
        elif _is_api_failure(result):
            update(index, _api_failed(case, result, attempts))
        else:
            update(index, _executed(case, result, attempts))

    report["api_requests_this_run"] = attempted
    report["summary"] = summarize(records)
    if checkpoint:
        checkpoint(report)
    return report


def create_report_path(directory: Path = DEFAULT_RESULTS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S_%f%z")
    return directory / f"{stamp}.json"


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(path)


def save_report(report: dict[str, Any], directory: Path = DEFAULT_RESULTS_DIR) -> Path:
    """Compatibility helper that always creates a new report file."""

    path = create_report_path(directory)
    write_report(path, report)
    return path


def _signature(item: dict[str, Any]) -> tuple[Any, ...]:
    return item.get("id"), item.get("sentence"), item.get("expected"), item.get("expected_question")


def load_resume(
    path: Path, cases: list[dict[str, Any]], selected_ids: list[str]
) -> dict[str, dict[str, Any]]:
    previous = json.loads(path.read_text(encoding="utf-8"))
    if previous.get("simulated") or previous.get("mode") != "live":
        raise ValueError("Cannot resume from a simulated or non-live report.")
    if previous.get("model") != effective_model():
        raise ValueError("Resume model does not match the current model.")
    if previous.get("test_data_sha256") != test_data_hash():
        raise ValueError("Resume test data does not match the current CSV.")
    previous_selected = previous.get("selected_ids")
    if previous_selected is None:
        previous_selected = [case["id"] for case in cases]
    if previous_selected != selected_ids:
        raise ValueError("Resume selected IDs do not match the current --ids selection.")
    current_signatures = {
        (case["id"], case["sentence"], case["expected"], case["expected_question"])
        for case in cases
    }
    previous_signatures = {_signature(record) for record in previous.get("tests", [])}
    if current_signatures != previous_signatures:
        raise ValueError("Resume records do not match the current CSV.")
    return {
        record["id"]: record
        for record in previous["tests"]
        if record.get("execution") == "completed"
    }


def print_report(report: dict[str, Any]) -> None:
    for record in report["tests"]:
        print(f"[{record['id']}] {record['verdict']} | {record['sentence']}")
        print(f"  output={json.dumps(record['model_result'], ensure_ascii=False)}")
        print(f"  expected={record['expected']}")
        print(f"  question_correct={record['question_correct']} latency_ms={record['latency_ms']}")
    summary = report["summary"]
    print(f"Completed: {summary['completed_cases']}/{summary['total_cases']}")
    print(f"Correct: {summary['correct_conversions']} Incorrect: {summary['incorrect_conversions']}")
    print(f"API failures: {summary['api_failures']} Not run: {summary['not_run_cases']}")
    print(f"API requests: {summary['api_total_requests']} Retries: {summary['retry_count']}")
    print(f"Average latency: {summary['average_response_ms']} ms")
    print(f"Slowest latency: {summary['slowest_response_ms']} ms")
    print(f"Effective accuracy: {summary['effective_accuracy']}")
    print(f"End-to-end success rate: {summary['end_to_end_success_rate']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow real Gemini API calls.")
    parser.add_argument("--max-requests", type=_nonnegative_int, default=2)
    parser.add_argument("--delay", type=_nonnegative_float, default=5.0)
    parser.add_argument("--max-retries", type=_nonnegative_int, default=2)
    parser.add_argument("--backoff-base", type=_nonnegative_float, default=2.0)
    parser.add_argument("--jitter", type=_nonnegative_float, default=1.0)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--ids", nargs="+", metavar="ID", help="Run only the selected test IDs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cases = load_cases()
    try:
        selected_ids = select_ids(cases, args.ids)
        resumed = load_resume(args.resume, cases, selected_ids) if args.resume else None
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Selection/resume error: {exc}", file=sys.stderr)
        return 2
    output_path = create_report_path()
    last_report: dict[str, Any] | None = None

    def checkpoint(report: dict[str, Any]) -> None:
        nonlocal last_report
        last_report = report
        write_report(output_path, report)

    try:
        report = evaluate(
            cases,
            live=args.live,
            max_requests=args.max_requests,
            delay=args.delay,
            max_retries=args.max_retries,
            backoff_base=args.backoff_base,
            jitter=args.jitter,
            resumed_records=resumed,
            checkpoint=checkpoint,
            resumed_from=str(args.resume.resolve()) if args.resume else None,
            selected_ids=selected_ids,
        )
    except KeyboardInterrupt:
        if last_report is not None:
            last_report["stop_reason"] = "keyboard_interrupt"
            last_report["summary"] = summarize(last_report["tests"])
            write_report(output_path, last_report)
        print(f"Interrupted; progress saved to: {output_path}", file=sys.stderr)
        return 130
    print_report(report)
    print(f"Saved report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
