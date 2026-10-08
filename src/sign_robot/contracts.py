"""Shared IDs and serialization contracts. No inference or motion side effects."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUSES = {"execute", "clarify", "unsupported", "error"}


def load_catalog(path: str | Path | None = None) -> list[dict]:
    data = json.loads(Path(path or ROOT / "data/catalog.json").read_text(encoding="utf-8"))
    actions = data["actions"]
    ids = [a["action_id"] for a in actions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate action IDs")
    return actions


def validate_selection(value: dict, catalog: list[dict]) -> dict:
    if not isinstance(value, dict) or value.get("status") not in STATUSES:
        raise ValueError("Invalid selection status")
    aid = value.get("action_id")
    if value["status"] == "execute":
        if aid not in {a["action_id"] for a in catalog}:
            raise ValueError("Unknown action ID")
    elif aid is not None:
        raise ValueError("Non-execute selections must have a null action_id")
    return value
