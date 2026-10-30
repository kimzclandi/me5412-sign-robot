import importlib.util
import json

import numpy as np
import pytest
from sign_robot.motion import ROOT, validate_motion

spec = importlib.util.spec_from_file_location("hospital_demo", ROOT / "scripts/demo/hospital_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_offline_cache_covers_scripted_lines_with_ready_motions():
    lines = demo.cached_lines()
    assert [l["id"] for l in lines] == [f"s{k}" for k in range(1, 10)]
    ready = {g["gloss"] for g in json.loads(demo.HOSPITAL.read_text())["glosses"] if g["motion_ready"]}
    for line in lines:
        assert line["glosses"] and set(line["glosses"]) <= ready, line["id"]


def test_cache_matches_id_and_sentence_ignoring_case_and_punctuation():
    assert demo.from_cache("S4")["glosses"] == ["YOU", "HURT", "WHERE"]
    assert demo.from_cache("where does it hurt")["id"] == "s4"
    assert demo.from_cache("Is the pain bad?") is None
    with pytest.raises(SystemExit):
        demo.resolve("Is the pain bad?", use_live=False)


def test_build_writes_valid_motion_with_ordered_word_spans(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "OUT", tmp_path)
    line = demo.from_cache("s7")
    motion, meta = demo.build(line, 0.5)
    validate_motion(motion)
    assert [w["gloss"] for w in meta["words"]] == line["glosses"]
    spans = [w["frames"] for w in meta["words"]]
    assert spans[0][0] == 0 and spans[-1][1] == len(motion["positions"]) - 1
    assert all(a[1] < b[0] for a, b in zip(spans, spans[1:]))
    assert meta["gloss_source"] == "offline_cache"
    assert {w["library"] for w in meta["words"]} <= {"motions/studio_galt_v1", "motions/wlasl_video_v1"}
    saved = np.load(tmp_path / "s7.npz")
    assert np.array_equal(saved["positions"], motion["positions"])


def test_live_result_is_used_rejection_plays_nothing_and_failure_falls_back(monkeypatch):
    monkeypatch.setattr(demo, "live", lambda s: {"status": "ok", "glosses": ["HURT", "WHERE"], "question": True})
    assert demo.resolve("Where is the pain?", use_live=True)["gloss_source"] == "live_gemini"
    monkeypatch.setattr(demo, "live", lambda s: {"status": "unsupported", "unknown": ["insurance"]})
    with pytest.raises(SystemExit):
        demo.resolve("Show me your insurance card.", use_live=True)
    monkeypatch.setattr(demo, "live", lambda s: {"status": "error", "reason": "llm_unavailable"})
    assert demo.resolve("Do you understand?", use_live=True)["gloss_source"] == "offline_cache_after_live_failure"
    with pytest.raises(SystemExit):
        demo.resolve("Is the pain bad?", use_live=True)


def test_demo_acts_cover_every_scripted_line_once_in_order():
    ids = [key for act in demo.ACTS.values() for key in act]
    assert ids == [l["id"] for l in demo.cached_lines()]
    assert list(demo.ACTS) == ["act1_registration", "act2_consultation", "act3_treatment", "act4_discharge"]
