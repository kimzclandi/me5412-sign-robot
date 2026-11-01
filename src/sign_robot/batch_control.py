"""Soft budgets, single-writer locks and resource records for batched development runs.

Budgets are checked only at immutable breakpoints (between pairs, between
candidate reviews, between sequence attempts); a started step is never killed,
so a stop is soft and may overrun by one step. Nothing here changes planning.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import resource
import shutil
import time

from sign_robot.pair_contract import inside, file_hash, json_bytes, read_json
from sign_robot.pair_runner_v2 import VerificationPaused

GIB = 1024 ** 3
MAX_PAIRS_PER_BATCH = 16


class BatchControlError(RuntimeError):
    def __init__(self, code, details=None):
        super().__init__(f"{code}: {details}")
        self.code, self.details = code, details


class SingleWriterLock:
    """Exclusive advisory lock kept outside the run directory; the kernel releases it on exit."""

    def __init__(self, path):
        self.path = Path(path)
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = open(self.path, "a+")
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            stream.close()
            raise BatchControlError("RUN_LOCKED_BY_ANOTHER_WRITER", str(self.path)) from exc
        stream.seek(0)
        stream.truncate()
        stream.write(f"pid {os.getpid()} since {utc_now()}\n")
        stream.flush()
        self.stream = stream
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        self.stream.close()
        self.stream = None
        return False


class SoftBudget:
    """Wall-clock, free-disk and operator-stop limits, consulted only at saved breakpoints.

    An operator stops a run gracefully by creating ``stop_file`` (or sending
    SIGTERM when the caller wires ``requested`` to a signal flag). ``drift``
    returns a reason when code or inputs no longer match the run identity, so a
    mid-run edit stops the run instead of saving ERROR reviews.
    """

    def __init__(self, wall_time_s, min_free_bytes, disk_path, *, stop_file=None, requested=None, drift=None,
                 clock=time.monotonic, disk_usage=shutil.disk_usage):
        if not wall_time_s > 0 or not min_free_bytes >= 0:
            raise BatchControlError("INVALID_BUDGET", {"wall_time_s": wall_time_s, "min_free_bytes": min_free_bytes})
        self.wall_time_s, self.min_free_bytes, self.disk_path = wall_time_s, min_free_bytes, Path(disk_path)
        self.stop_file = None if stop_file is None else Path(stop_file)
        self.requested = requested or (lambda: False)
        self.drift = drift or (lambda: None)
        self.clock, self.disk_usage = clock, disk_usage
        self.started = clock()

    def stop_reason(self):
        if self.requested() or (self.stop_file is not None and self.stop_file.exists()):
            return "STOP_REQUESTED"
        if self.clock() - self.started >= self.wall_time_s:
            return "SOFT_WALL_TIME_REACHED"
        if self.disk_usage(self.disk_path).free < self.min_free_bytes:
            return "DISK_FREE_BELOW_FLOOR"
        return self.drift()

    def record(self):
        return {"wall_time_s": self.wall_time_s, "min_free_bytes": self.min_free_bytes,
                "elapsed_s": self.clock() - self.started, "hard_real_time_abort": False}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resource_record(path):
    usage = resource.getrusage(resource.RUSAGE_SELF)
    disk = shutil.disk_usage(path)
    return {"time_utc": utc_now(), "load_average": list(os.getloadavg()), "cpu_count": os.cpu_count(),
            "disk_free_bytes": disk.free, "disk_total_bytes": disk.total, "max_rss_kib": usage.ru_maxrss,
            "user_cpu_s": usage.ru_utime, "system_cpu_s": usage.ru_stime}


def write_new_log(directory, value):
    """Append-only invocation logs: a new numbered file each time, never an overwrite."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for number in range(1, 10_000):
        path = directory / f"invocation_{number:03d}.json"
        try:
            with open(path, "xb") as stream:
                stream.write(json_bytes(value))
            return path
        except FileExistsError:
            continue
    raise BatchControlError("TOO_MANY_INVOCATION_LOGS", str(directory))


def load_batch_manifest(root, path, expected_sha256, universe_ids, policy_path):
    """Hash-bound frozen batches: mutually exclusive, each at most 16 pairs, union equal to the universe."""
    root = Path(root).resolve()
    manifest_path = inside(root, path)
    if file_hash(manifest_path) != expected_sha256:
        raise BatchControlError("BATCH_MANIFEST_HASH_MISMATCH", path)
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1 or manifest.get("kind") != "hospital35_pair_batches_v1":
        raise BatchControlError("BATCH_MANIFEST_VERSION", path)
    if (manifest["policy"]["path"] != str(policy_path)
            or file_hash(inside(root, manifest["policy"]["path"])) != manifest["policy"]["sha256"]):
        raise BatchControlError("BATCH_POLICY_MISMATCH", manifest["policy"])
    batches, seen = {}, set()
    for entry in manifest["batches"]:
        batch_path = inside(root, entry["file"])
        if file_hash(batch_path) != entry["sha256"]:
            raise BatchControlError("BATCH_FILE_HASH_MISMATCH", entry["batch_id"])
        pairs = read_json(batch_path)["pair_ids"]
        if (not pairs or len(pairs) > MAX_PAIRS_PER_BATCH or len(set(pairs)) != len(pairs)
                or len(pairs) != entry["pair_count"] or not set(pairs) <= set(universe_ids)):
            raise BatchControlError("INVALID_BATCH", entry["batch_id"])
        if seen & set(pairs) or entry["batch_id"] in batches:
            raise BatchControlError("BATCHES_OVERLAP", entry["batch_id"])
        seen |= set(pairs)
        batches[entry["batch_id"]] = {**entry, "pair_ids": pairs}
    if seen != set(universe_ids) or manifest["order"] != list(batches):
        raise BatchControlError("BATCHES_DO_NOT_COVER_UNIVERSE_IN_ORDER", len(seen))
    return manifest, batches


def _pair_state(store, pair_id):
    record = store._head_record(pair_id)
    if record is None:
        return {"pair_id": pair_id, "status": "NOT_RUN", "planning_state": None, "verification_state": None}
    numerical = sum(v["numerical_checks_passed"] for v in record.get("verifications", []))
    return {"pair_id": pair_id, "status": record["status"], "reason_codes": record["reason_codes"],
            "planning_state": record["planning_state"], "verification_state": record["verification_state"],
            "attempt_count": len(record["attempts"]), "candidate_count": record["candidate_count"],
            "reviewed_candidates": len(record.get("verifications", [])), "numerical_pass_candidates": numerical,
            "selected_candidate_id": record["selected_candidate_id"]}


def verification_backlog(store, exclude=()):
    """Planned pairs outside ``exclude`` whose planning or independent review is unfinished."""
    backlog = []
    for pair_id in store.manifest["heads"]:
        record = store._head_record(pair_id)
        if pair_id not in exclude and (not record["completed"] or record["verification_state"] == "NOT_RUN"):
            backlog.append(pair_id)
    return sorted(backlog)


def run_pair_batch(store, context, batch, *, budget, seed_base):
    """Plan, then independently review, one frozen batch; stop softly at saved breakpoints."""
    universe = {p["pair_id"]: (index, p) for index, p in enumerate(store.universe())}
    pairs = sorted(batch["pair_ids"], key=lambda pair_id: universe[pair_id][0])
    backlog = verification_backlog(store, exclude=set(pairs))
    if backlog:
        return {"stop_reason": "BACKLOG_NOT_CLEARED", "backlog": backlog, "pairs": [_pair_state(store, p) for p in pairs]}
    stop = None
    for pair_id in pairs:
        record = store._head_record(pair_id)
        if record is not None and record["completed"]:
            continue
        stop = budget.stop_reason()
        if stop:
            break
        index, pair = universe[pair_id]
        store.run_pair(pair["source_gloss"], pair["target_gloss"], context, seed=seed_base + index)
    if stop is None:
        for pair_id in pairs:
            record = store._head_record(pair_id)
            if not record["completed"] or record["verification_state"] != "NOT_RUN":
                continue
            stop = budget.stop_reason()
            if stop:
                break
            try:
                store.verify_pair(pair_id, should_stop=budget.stop_reason)
            except VerificationPaused as exc:
                stop = exc.reason
                break
    states = [_pair_state(store, p) for p in pairs]
    complete = all(s["planning_state"] == "COMPLETE" and s["verification_state"] in ("COMPLETE", "DIAGNOSIS_ONLY")
                   for s in states)
    return {"stop_reason": stop or ("BATCH_COMPLETE" if complete else "BATCH_INCOMPLETE"), "pairs": states,
            "backlog_after": verification_backlog(store)}
