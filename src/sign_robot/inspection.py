"""Read-only access to named, locally generated trajectory inspection artifacts."""
from pathlib import Path
import json
import re

from .contracts import ROOT
from .motion import ACTION_IDS

VIEWS = ("front", "right_side")


def artifact_path(relative: str, root=ROOT, *, suffix: str) -> Path:
    root = Path(root).resolve()
    base = (root / "results/inspection").resolve()
    path = (root / relative).resolve()
    if (not base.is_relative_to(root) or not path.is_relative_to(base)
            or path.suffix != suffix or not path.is_file()):
        raise ValueError("Inspection artifact is missing or outside its allowed directory")
    return path


def manifest(root=ROOT) -> dict:
    path = Path(root) / "results/inspection/manifest.json"
    if not path.is_file():
        return {"schema_version": 1, "actions": {}, "runs": []}
    path = artifact_path("results/inspection/manifest.json", root, suffix=".json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value.get("schema_version") != 1 or not isinstance(value.get("actions"), dict)
            or not isinstance(value.get("runs"), list)):
        raise ValueError("Invalid inspection manifest")
    return value


def action_entry(action_id: str, root=ROOT, *, run_id: str | None = None) -> dict:
    if action_id not in ACTION_IDS:
        raise ValueError("Unknown action ID")
    records = manifest(root)
    if run_id is None:
        latest = records["actions"].get(action_id)
        if not isinstance(latest, dict):
            raise FileNotFoundError("Inspection has not been generated for this action")
        run_id = latest.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{16}", run_id):
        raise ValueError("Invalid inspection run ID")
    matches = [entry for entry in records["runs"] if isinstance(entry, dict)
               and entry.get("action_id") == action_id and entry.get("run_id") == run_id]
    if len(matches) != 1:
        raise FileNotFoundError("Inspection run is missing or ambiguous")
    return matches[0]


def run_artifact(entry: dict, relative: str, root=ROOT, *, suffix: str) -> Path:
    path = artifact_path(relative, root, suffix=suffix)
    directory = Path(root).resolve() / "results/inspection" / entry["action_id"] / entry["run_id"]
    if not path.is_relative_to(directory):
        raise ValueError("Inspection artifact belongs to another action or run")
    return path


def inventory(root=ROOT) -> dict:
    result = {"schema_version": 1, "actions": {}, "execution": "prerendered_kinematic_inspection"}
    for action_id in ACTION_IDS:
        try:
            entry = action_entry(action_id, root)
        except FileNotFoundError:
            continue
        run_id = entry["run_id"]
        run_artifact(entry, entry["telemetry"], root, suffix=".json")
        views = {}
        for view in VIEWS:
            if view not in entry["views"]:
                continue
            for ext in ("mp4", "png"):
                run_artifact(entry, entry["views"][view][ext], root, suffix="." + ext)
            views[view] = {"video_url": f"/inspection-media/{action_id}/{run_id}/{view}.mp4",
                           "poster_url": f"/inspection-media/{action_id}/{run_id}/{view}.png"}
        result["actions"][action_id] = {"telemetry_url": f"/api/inspection/{action_id}/{run_id}",
                                        "trajectory_sha256": entry["trajectory_sha256"],
                                        "run_id": entry["run_id"], "views": views}
    return result


def telemetry(action_id: str, root=ROOT, *, run_id: str) -> dict:
    entry = action_entry(action_id, root, run_id=run_id)
    path = run_artifact(entry, entry["telemetry"], root, suffix=".json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("action_id") != action_id or data.get("trajectory_sha256") != entry["trajectory_sha256"]
            or data.get("run_id", run_id) != run_id):
        raise ValueError("Inspection identity does not match its manifest")
    return {**data, "run_id": run_id}


def media(action_id: str, view: str, extension: str, root=ROOT, *, run_id: str) -> Path:
    if view not in VIEWS or extension not in {"mp4", "png"}:
        raise ValueError("Unknown inspection media")
    entry = action_entry(action_id, root, run_id=run_id)
    return run_artifact(entry, entry["views"][view][extension], root, suffix="." + extension)
