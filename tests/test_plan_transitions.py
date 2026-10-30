"""Transition contract checks, separate from source-clip quality/ASL review."""

import importlib.util
import json
import math

import numpy as np
import pytest

import sign_robot.transitions as transitions
from sign_robot.motion import ROOT, apply_frame, load_model, validate_motion
from sign_robot.transitions import (
    FPS,
    CLEARANCE_DISPLAY_CAP_M,
    ENDPOINT_NEAR_M,
    PENETRATION_TOLERANCE_M,
    SOURCE_END_FRAME_OVERRIDES,
    TARGET_START_FRAME_OVERRIDES,
    TRIM_CAP_EXCEPTIONS,
    VIA_DIRECTIONS,
    VIA_DISPLACEMENT_M,
    ClearanceResult,
    MujocoClearance,
    build_retract_approach_route,
    clearance_is_capped,
    derive_static_body_pairs,
    format_clearance_mm,
    ik_via_candidates,
    ik_dual_via_candidates,
    joint_rate_limits,
    minimum_jerk_blend,
    neutral_pose,
    plan_sentence,
    plan_transition,
    source_end_frame,
    target_start_frame,
    timescale_to_rate_limits,
)


SENTENCES = (
    ("HELLO", "YOU", "APPOINTMENT", "HAVE"),
    ("MEDICINE", "MORNING", "NIGHT", "TAKE"),
    ("NOW", "NURSE", "BLOOD-DRAW"),
    ("PLEASE", "WAIT", "DOCTOR", "COME", "SOON"),
    ("YOU", "BUY", "BOOK"),
    ("YOU", "HURT", "WHERE"),
    ("YOU", "NEED", "INTERPRETER"),
    ("YOU", "UNDERSTAND"),
    ("BREATHE-DEEP",),
    ("THANK-YOU",),
)


def distance_result(distance, positions, frame=0):
    contact = {"bodies": ["torso_link", "right_wrist_yaw_link"],
               "geoms": ["torso_geom", "wrist_geom"],
               "distance_m": distance, "frame": frame,
               "location": "start_endpoint" if frame == 0 else "interior"}
    violations = [contact] if distance < PENETRATION_TOLERANCE_M else []
    return ClearanceResult(not violations, distance, violations, len(positions),
                           [contact] if distance < ENDPOINT_NEAR_M else [], contact,
                           frame_clearances_m=[distance] * len(positions))


def clear(positions):
    return distance_result(0.01, positions)


@pytest.fixture(scope="module")
def words():
    # Resolve independently of the planner: hospital-ready clips take precedence.
    entries = {
        row["gloss"]: row
        for row in json.loads((ROOT / "motions/hospital_v1_motions.json").read_text())["glosses"]
        if row["motion_ready"]
    }
    for library in ("studio_galt_v1", "wlasl_video_v1"):
        for row in json.loads((ROOT / "motions" / library / "index.json").read_text())["words"]:
            if row["robot_status"] != "poor":
                entries.setdefault(row["gloss"], row)
    return entries


@pytest.fixture
def temporary_departure_overrides(words):
    # Test-only one-frame trims from current metadata, not collision candidates.
    return {gloss: words[gloss]["sign_frames"][1] - 1 for gloss in ("NURSE", "DOCTOR")}


@pytest.fixture(scope="module")
def evaluation_script():
    spec = importlib.util.spec_from_file_location(
        "evaluate_planned_transitions", ROOT / "scripts/evaluate_planned_transitions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_joint_rate_limits_match_library_categories():
    names = np.array([
        "left_shoulder_pitch_joint", "right_elbow_joint", "right_wrist_pitch_joint",
        "L_thumb_distal_joint", "R_index_proximal_joint", "waist_yaw_joint",
    ])
    limits = joint_rate_limits(names)
    np.testing.assert_array_equal(limits[:5], [15, 15, 15, 10, 10])
    assert np.isinf(limits[5])


def test_quintic_uses_shortest_continuously_rate_safe_integer_duration():
    names = np.array(["left_shoulder_pitch_joint", "R_thumb_distal_joint"])
    start = np.zeros(2)
    end = np.array([1.6, 2.7])
    positions = minimum_jerk_blend(start, end, names)
    intervals = len(positions) - 1
    limits = np.array([15.0, 10.0])
    # The derivative of 10u^3 - 15u^4 + 6u^5 peaks at 15/8.
    peak_rates = 1.875 * np.abs(end - start) * FPS / intervals
    assert np.all(peak_rates <= limits + 1e-12)
    assert intervals / FPS >= 0.3
    assert np.any(1.875 * np.abs(end - start) * FPS / (intervals - 1) > limits)
    u = np.linspace(0.0, 1.0, len(positions))[:, None]
    expected = start + (10 * u**3 - 15 * u**4 + 6 * u**5) * (end - start)
    np.testing.assert_allclose(positions, expected, atol=1e-12)
    np.testing.assert_array_equal(positions[[0, -1]], np.stack([start, end]))
    assert np.all(np.abs(np.diff(positions, axis=0)) * FPS <= limits + 1e-12)


def test_stationary_blend_keeps_minimum_duration():
    pose = np.array([0.2, 0.6])
    positions = minimum_jerk_blend(pose, pose, ["right_elbow_joint", "L_index_proximal_joint"])
    assert (len(positions) - 1) / FPS == 0.3
    np.testing.assert_array_equal(positions, np.broadcast_to(pose, positions.shape))


def test_tiny_joint_delta_still_takes_point_three_seconds():
    positions = minimum_jerk_blend(np.zeros(2), np.full(2, 1e-8),
                                   ["right_elbow_joint", "L_index_proximal_joint"])
    assert len(positions) - 1 == 9
    assert (len(positions) - 1) / FPS >= 0.3


@pytest.mark.parametrize("glosses", SENTENCES, ids=lambda seq: "_".join(seq))
def test_sentence_boundaries_rates_and_source_frames(glosses, words):
    motion, report = plan_sentence(glosses, clearance=clear)
    assert report["source_end_frame_overrides"] == SOURCE_END_FRAME_OVERRIDES
    assert report["target_start_frame_overrides"] == TARGET_START_FRAME_OVERRIDES
    assert report["rrt_override"]["pairs"] == [["MEDICINE", "MORNING"], ["NURSE", "BLOOD-DRAW"]]
    validate_motion(motion)
    positions = motion["positions"]
    names = motion["joint_names"]
    np.testing.assert_allclose(np.diff(motion["timestamps_s"]), 1 / FPS)
    assert len(report["transitions"]) == len(glosses) - 1
    limits = joint_rate_limits(names)

    for previous, following, segment in zip(glosses, glosses[1:], report["transitions"]):
        assert segment["from_gloss"] == previous
        assert segment["to_gloss"] == following
        assert segment["method"] == "direct"
        assert segment["status"] == "PASS" and not segment["source_near"]
        assert isinstance(segment["min_clearance_mm"], (int, float))
        assert math.isfinite(segment["min_clearance_mm"])
        assert segment["min_clearance_mm"] == 10.0
        assert segment["endpoint_clearances_mm"] == [10.0, 10.0]
        assert segment["closest_pair"]["bodies"] == ["torso_link", "right_wrist_yaw_link"]
        start_frame, end_frame = segment["start_frame"], segment["end_frame"]
        assert (end_frame - start_frame) / FPS >= 0.3
        transition = positions[start_frame:end_frame + 1]
        with np.load(ROOT / words[previous]["motion"]) as source:
            np.testing.assert_array_equal(names, source["joint_names"])
            departure = SOURCE_END_FRAME_OVERRIDES.get(previous, words[previous]["sign_frames"][1])
            assert segment["source_start_frame"] == departure
            np.testing.assert_array_equal(transition[0], source["positions"][departure])
        with np.load(ROOT / words[following]["motion"]) as target:
            arrival = TARGET_START_FRAME_OVERRIDES.get(following, words[following]["sign_frames"][0])
            assert segment["target_start_frame"] == arrival
            np.testing.assert_array_equal(transition[-1], target["positions"][arrival])
        assert np.all(np.abs(np.diff(transition, axis=0)) * FPS <= limits + 1e-10)

    assert len(report["word_segments"]) == len(glosses)
    for index, (gloss, segment) in enumerate(zip(glosses, report["word_segments"])):
        assert segment["gloss"] == gloss
        with np.load(ROOT / words[gloss]["motion"]) as clip:
            expected_start = (0 if index == 0 else
                              TARGET_START_FRAME_OVERRIDES.get(gloss, words[gloss]["sign_frames"][0]))
            expected_end = (len(clip["positions"]) - 1 if index == len(glosses) - 1 else
                            SOURCE_END_FRAME_OVERRIDES.get(gloss, words[gloss]["sign_frames"][1]))
            assert segment["source_start_frame"] == expected_start
            assert segment["source_end_frame"] == expected_end
            np.testing.assert_array_equal(
                positions[segment["start_frame"]:segment["end_frame"] + 1],
                clip["positions"][expected_start:expected_end + 1],
            )


def test_round13c_default_departures_keep_doctor_and_need_sign_ends(words):
    assert SOURCE_END_FRAME_OVERRIDES == {"MEDICINE": 73, "NIGHT": 61, "HURT": 66, "NURSE": 80}
    assert TRIM_CAP_EXCEPTIONS == {"NURSE": 80}
    for gloss in ("DOCTOR", "NEED"):
        assert source_end_frame(words[gloss]) == words[gloss]["sign_frames"][1]


@pytest.mark.parametrize("gloss", ["MEDICINE", "NIGHT", "HURT"])
def test_round13_default_departure_is_inside_sign_core_and_trims_at_most_ten_percent(gloss):
    assert gloss not in TRIM_CAP_EXCEPTIONS
    library = json.loads((ROOT / "motions/hospital_v1_motions.json").read_text())
    word = next(row for row in library["glosses"] if row["gloss"] == gloss)
    sign_start, sign_end = word["sign_frames"]
    core_start, core_end = word["core_frames"]
    departure = source_end_frame(word)
    assert departure == SOURCE_END_FRAME_OVERRIDES[gloss]
    assert max(core_start, sign_start) <= departure <= min(core_end, sign_end)
    trim_frames = sign_end - departure
    core_len = core_end - core_start + 1
    assert 0 < trim_frames / core_len <= 0.10


def test_round13c_nurse_total_trim_keeps_arrival_and_uses_exact_exception(words):
    word = words["NURSE"]
    assert word["sign_frames"] == [24, 88] and word["core_frames"] == [24, 102]
    core_len = word["core_frames"][1] - word["core_frames"][0] + 1
    arrival, departure = target_start_frame(word), source_end_frame(word)
    assert arrival == 24 and departure == 80
    assert "NURSE" not in TARGET_START_FRAME_OVERRIDES
    assert max(word["core_frames"][0], word["sign_frames"][0]) <= departure <= min(
        word["core_frames"][1], word["sign_frames"][1])
    total_trim = arrival - word["sign_frames"][0] + word["sign_frames"][1] - departure
    assert total_trim == 8 and core_len == 79
    assert total_trim / core_len == pytest.approx(8 / 79)
    assert 100 * total_trim / core_len == pytest.approx(10.126582278481013)
    assert total_trim / core_len > 0.10
    assert math.floor(0.10 * core_len) == 7 < total_trim
    assert TRIM_CAP_EXCEPTIONS == {"NURSE": departure}


@pytest.mark.parametrize("gloss", ["MEDICINE", "NIGHT", "HURT", "DOCTOR"])
def test_nonexception_departure_rejects_trim_above_strict_ten_percent(gloss, words):
    assert gloss not in TRIM_CAP_EXCEPTIONS
    word = words[gloss]
    core_len = word["core_frames"][1] - word["core_frames"][0] + 1
    frame = word["sign_frames"][1] - math.floor(0.10 * core_len) - 1
    with pytest.raises(ValueError, match="source-end override exceeds strict 10% trim cap"):
        source_end_frame(word, overrides={gloss: frame})


@pytest.mark.parametrize("exceptions", [{}, {"NURSE": 81}])
def test_nurse_f80_requires_matching_exception(exceptions, words, monkeypatch):
    monkeypatch.setattr(transitions, "TRIM_CAP_EXCEPTIONS", exceptions)
    for overrides in (None, {"NURSE": 80}):
        with pytest.raises(ValueError, match="source-end override exceeds strict 10% trim cap"):
            source_end_frame(words["NURSE"], overrides=overrides)
    with pytest.raises(ValueError, match="source-end override exceeds strict 10% trim cap"):
        plan_sentence(["NOW", "NURSE", "BLOOD-DRAW"], clearance=clear)
    # The strict floor still permits f81 without an exception.
    assert source_end_frame(words["NURSE"], overrides={"NURSE": 81}) == 81


def test_nurse_exception_does_not_allow_another_over_budget_frame(words):
    assert source_end_frame(words["NURSE"], overrides={"NURSE": 80}) == 80
    with pytest.raises(ValueError, match="source-end override exceeds strict 10% trim cap"):
        source_end_frame(words["NURSE"], overrides={"NURSE": 79})


def test_round13b_default_arrival_trims_interpreter_at_most_ten_percent(words):
    assert TARGET_START_FRAME_OVERRIDES == {"INTERPRETER": 25}
    word = words["INTERPRETER"]
    sign_start, sign_end = word["sign_frames"]
    core_start, core_end = word["core_frames"]
    arrival = target_start_frame(word)
    assert arrival == 25
    assert max(core_start, sign_start) <= arrival <= min(core_end, sign_end)
    assert sign_start == 24 and arrival > sign_start
    trim_fraction = (arrival - sign_start) / (core_end - core_start + 1)
    assert trim_fraction == pytest.approx(1 / 54)
    assert 0 < trim_fraction <= 0.10
    for gloss in ("BLOOD-DRAW", "COME", "MORNING"):
        assert target_start_frame(words[gloss]) == words[gloss]["sign_frames"][0]


@pytest.mark.parametrize("glosses", [
    ("NEED", "INTERPRETER"), ("YOU", "NEED", "INTERPRETER"),
    ("NEED", "INTERPRETER", "COME"),
])
@pytest.mark.parametrize("override_mode", ["default", "replace", "patched_default", "disable"])
def test_arrival_override_trims_target_only_and_knob_works(glosses, override_mode, words, monkeypatch):
    gloss = "INTERPRETER"
    library_start, library_end = words[gloss]["sign_frames"]
    patched = {gloss: library_start + 3}
    if override_mode != "default":
        monkeypatch.setattr(transitions, "TARGET_START_FRAME_OVERRIDES", patched)
    overrides = {"default": None, "replace": {gloss: library_start + 2},
                 "patched_default": None, "disable": {}}[override_mode]
    expected_overrides = {"default": TARGET_START_FRAME_OVERRIDES,
                          "replace": {gloss: library_start + 2},
                          "patched_default": patched, "disable": {}}[override_mode]
    expected = expected_overrides.get(gloss, library_start)
    assert target_start_frame(words[gloss], overrides=overrides) == expected
    motion, report = plan_sentence(glosses, clearance=clear, target_start_frame_overrides=overrides)
    assert report["target_start_frame_overrides"] == expected_overrides
    assert report["source_end_frame_overrides"] == SOURCE_END_FRAME_OVERRIDES
    word = next(s for s in report["word_segments"] if s["gloss"] == gloss)
    arrival = next(s for s in report["transitions"] if s["to_gloss"] == gloss)
    assert word["source_start_frame"] == arrival["target_start_frame"] == expected
    assert words[gloss]["sign_frames"] == transitions.lookup_words()[gloss]["sign_frames"] == [library_start, library_end]
    with np.load(ROOT / words[gloss]["motion"], allow_pickle=False) as target:
        end = len(target["positions"]) - 1 if glosses[-1] == gloss else library_end
        assert word["source_end_frame"] == end
        np.testing.assert_array_equal(
            motion["positions"][word["start_frame"]:word["end_frame"] + 1],
            target["positions"][expected:end + 1])
        np.testing.assert_array_equal(motion["positions"][arrival["end_frame"]],
                                      target["positions"][expected])
    source_word = words[arrival["from_gloss"]]
    departure = source_word["sign_frames"][1]
    assert arrival["source_start_frame"] == departure
    with np.load(ROOT / source_word["motion"], allow_pickle=False) as source:
        np.testing.assert_array_equal(motion["positions"][arrival["start_frame"]],
                                      source["positions"][departure])


@pytest.mark.parametrize("glosses", [("INTERPRETER",), ("INTERPRETER", "COME")])
def test_arrival_override_keeps_first_word_rise_and_singleton(glosses, words):
    motion, report = plan_sentence(glosses, clearance=clear)
    word = report["word_segments"][0]
    assert word["source_start_frame"] == 0
    with np.load(ROOT / words["INTERPRETER"]["motion"], allow_pickle=False) as clip:
        end = len(clip["positions"]) - 1 if len(glosses) == 1 else words["INTERPRETER"]["sign_frames"][1]
        assert word["source_end_frame"] == end
        np.testing.assert_array_equal(motion["positions"][:word["end_frame"] + 1],
                                      clip["positions"][:end + 1])


@pytest.mark.parametrize("invalid_kind", [
    "before_start", "sign_start", "after_core", "after_sign", "fractional", "boolean", "numpy_boolean",
])
def test_arrival_override_rejects_out_of_core_or_non_trim_frames(invalid_kind, words):
    word = words["INTERPRETER"]
    sign_start, sign_end = word["sign_frames"]
    frame = {"before_start": sign_start - 1, "sign_start": sign_start,
             "after_core": word["core_frames"][1] + 1, "after_sign": sign_end + 1,
             "fractional": sign_start + 1.5, "boolean": True,
             "numpy_boolean": np.bool_(True)}[invalid_kind]
    with pytest.raises(ValueError, match="target-start override.*inside core_frames/sign_frames"):
        target_start_frame(word, overrides={"INTERPRETER": frame})
    with pytest.raises(ValueError, match="target-start override.*inside core_frames/sign_frames"):
        plan_sentence(["NEED", "INTERPRETER"], clearance=clear,
                      target_start_frame_overrides={"INTERPRETER": frame})


@pytest.mark.parametrize("sign_frames,core_frames,valid_frame,invalid_frame", [
    ([2, 8], [4, 20], 4, 3),  # Core start is the lower bound.
    ([4, 8], [2, 20], 5, 4),  # Arrival must be strictly after sign start.
    ([2, 20], [2, 8], 8, 9),  # Core end is the upper bound.
    ([2, 8], [2, 20], 8, 9),  # Sign end is the upper bound.
])
def test_arrival_override_is_general_and_honors_core_and_sign_boundaries(
        sign_frames, core_frames, valid_frame, invalid_frame):
    word = {"gloss": "TEST", "sign_frames": sign_frames, "core_frames": core_frames}
    assert target_start_frame(word, overrides={"TEST": np.int64(valid_frame)}) == valid_frame
    assert target_start_frame(word, overrides={}) == sign_frames[0]
    assert target_start_frame(word) == sign_frames[0]
    with pytest.raises(ValueError, match="target-start override"):
        target_start_frame(word, overrides={"TEST": invalid_frame})


def test_arrival_override_requires_core_metadata_only_for_overridden_gloss():
    word = {"gloss": "TEST", "sign_frames": [2, 8]}
    assert target_start_frame(word, overrides={}) == 2
    with pytest.raises(ValueError, match="target-start override"):
        target_start_frame(word, overrides={"TEST": 3})


@pytest.mark.parametrize("override_mode", ["default", "replace", "patched_default", "disable"])
def test_verifier_rechecks_recorded_arrival_policy_and_rejects_false_arrival(
        override_mode, words, monkeypatch, tmp_path, evaluation_script):
    gloss = "INTERPRETER"
    library_start = words[gloss]["sign_frames"][0]
    if override_mode != "default":
        monkeypatch.setattr(transitions, "TARGET_START_FRAME_OVERRIDES", {gloss: library_start + 3})
    overrides = {"default": None, "replace": {gloss: library_start + 2},
                 "patched_default": None, "disable": {}}[override_mode]
    motion, report = plan_sentence(["NEED", gloss], clearance=clear,
                                   target_start_frame_overrides=overrides)
    path = tmp_path / "arrival.npz"
    np.savez_compressed(path, **motion)
    report["output_npz"] = str(path)
    monkeypatch.setattr(evaluation_script, "MujocoClearance", lambda *args: clear)
    monkeypatch.setattr(transitions, "TARGET_START_FRAME_OVERRIDES", {gloss: library_start + 4})
    assert evaluation_script.verify_saved_sentence(report, None)["passed"]
    trimmed = gloss in report["target_start_frame_overrides"]
    if not report["target_start_frame_overrides"]:
        del report["target_start_frame_overrides"]  # Legacy reports used library arrivals.
        assert evaluation_script.verify_saved_sentence(report, None)["passed"]
    segment, = report["transitions"]
    segment["target_start_frame"] = library_start if trimmed else library_start + 1
    with pytest.raises(AssertionError):
        evaluation_script.verify_saved_sentence(report, None)


def test_arrival_override_approach_and_handoff_use_trimmed_frame(
        words, monkeypatch, tmp_path, evaluation_script):
    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))
    checked = []

    def clearance(q):
        checked.append(q.copy())
        return distance_result(0.001 if len(q) == 1 else -0.01, q)

    motion, report = plan_sentence(["NEED", "INTERPRETER"], clearance=clearance)
    segment, = report["transitions"]
    assert segment["status"] == "FAILED" and segment["method"] == "retract_approach"
    assert segment["target_start_frame"] == 25
    assert segment["target_approach_frames"] == [0, 25]
    assert not segment["rrt_attempted"]
    assert any(hit["word"] == "INTERPRETER" and hit["frame"] == 25
               for hit in report["source_near_handoff"])
    with np.load(ROOT / words["INTERPRETER"]["motion"], allow_pickle=False) as target:
        assert any(np.array_equal(q, target["positions"][:26]) for q in checked)
    assert words["INTERPRETER"]["sign_frames"][0] == 24
    path = tmp_path / "trimmed_approach.npz"
    np.savez_compressed(path, **motion)
    report["output_npz"] = str(path)
    monkeypatch.setattr(evaluation_script, "MujocoClearance", lambda *args: clearance)
    assert evaluation_script.verify_saved_sentence(report, None)["passed"]


@pytest.mark.parametrize("glosses,gloss", [
    (("MEDICINE", "MORNING"), "MEDICINE"),
    (("MEDICINE", "MORNING", "NIGHT", "TAKE"), "NIGHT"),
    (("YOU", "HURT", "WHERE"), "HURT"),
    (("NURSE", "BLOOD-DRAW"), "NURSE"),
    (("NOW", "NURSE", "BLOOD-DRAW"), "NURSE"),
    (("DOCTOR", "COME"), "DOCTOR"),
    (("PLEASE", "WAIT", "DOCTOR", "COME", "SOON"), "DOCTOR"),
])
@pytest.mark.parametrize("override_mode", ["default", "replace", "patched_default", "disable"])
def test_departure_override_trims_source_only_and_knob_works(
        glosses, gloss, override_mode, words, temporary_departure_overrides, monkeypatch):
    library_start, library_end = words[gloss]["sign_frames"]
    replacement_end = library_end - 2
    if override_mode != "default":
        monkeypatch.setattr(transitions, "SOURCE_END_FRAME_OVERRIDES", temporary_departure_overrides)
    overrides = {"default": None, "replace": {gloss: replacement_end},
                 "patched_default": None, "disable": {}}[override_mode]
    expected_overrides = {
        "default": SOURCE_END_FRAME_OVERRIDES,
        "replace": {gloss: replacement_end},
        "patched_default": temporary_departure_overrides,
        "disable": {},
    }[override_mode]
    expected = expected_overrides.get(gloss, library_end)
    motion, report = plan_sentence(glosses, clearance=clear, source_end_frame_overrides=overrides)
    assert report["source_end_frame_overrides"] == expected_overrides
    word = next(s for s in report["word_segments"] if s["gloss"] == gloss)
    transition = next(s for s in report["transitions"] if s["from_gloss"] == gloss)
    assert words[gloss]["sign_frames"] == [library_start, library_end]
    assert word["source_end_frame"] == transition["source_start_frame"] == expected
    if expected != library_end:
        core_start, core_end = words[gloss]["core_frames"]
        assert max(core_start, library_start) <= expected <= core_end
        assert expected < library_end
        trim_fraction = (library_end - expected) / (core_end - core_start + 1)
        if gloss == "NURSE" and expected == 80:
            assert TRIM_CAP_EXCEPTIONS == {"NURSE": expected}
            assert trim_fraction == pytest.approx(8 / 79) and trim_fraction > 0.10
        else:
            assert 0 < trim_fraction <= 0.10
    with np.load(ROOT / words[gloss]["motion"], allow_pickle=False) as source:
        start = 0 if glosses[0] == gloss else library_start
        assert word["source_start_frame"] == start
        np.testing.assert_array_equal(
            motion["positions"][word["start_frame"]:word["end_frame"] + 1],
            source["positions"][start:expected + 1])
        np.testing.assert_array_equal(motion["positions"][transition["start_frame"]],
                                      source["positions"][expected])
        if glosses[0] != gloss:
            arrival = next(s for s in report["transitions"] if s["to_gloss"] == gloss)
            assert arrival["target_start_frame"] == library_start
            np.testing.assert_array_equal(motion["positions"][arrival["end_frame"]],
                                          source["positions"][library_start])
    target_word = words[transition["to_gloss"]]
    target_start = target_word["sign_frames"][0]
    assert transition["target_start_frame"] == target_start
    with np.load(ROOT / target_word["motion"], allow_pickle=False) as target:
        np.testing.assert_array_equal(motion["positions"][transition["end_frame"]],
                                      target["positions"][target_start])


@pytest.mark.parametrize("glosses", [("NURSE",), ("NOW", "NURSE"), ("DOCTOR",), ("WAIT", "DOCTOR")])
def test_departure_override_keeps_final_return_and_singleton(
        glosses, words, temporary_departure_overrides):
    motion, report = plan_sentence(glosses, clearance=clear,
                                   source_end_frame_overrides=temporary_departure_overrides)
    word = report["word_segments"][-1]
    with np.load(ROOT / words[glosses[-1]]["motion"], allow_pickle=False) as source:
        assert word["source_end_frame"] == len(source["positions"]) - 1
        np.testing.assert_array_equal(motion["positions"][word["start_frame"]:],
                                      source["positions"][word["source_start_frame"]:])


@pytest.mark.parametrize("gloss,target", [("NURSE", "BLOOD-DRAW"), ("DOCTOR", "COME")])
@pytest.mark.parametrize("invalid_kind", ["before_start", "sign_end", "after_core", "fractional", "boolean"])
def test_departure_override_rejects_out_of_core_or_non_trim_frames(
        gloss, target, invalid_kind, words):
    sign_start, sign_end = words[gloss]["sign_frames"]
    core_start, core_end = words[gloss]["core_frames"]
    frame = {"before_start": max(core_start, sign_start) - 1, "sign_end": sign_end,
             "after_core": core_end + 1, "fractional": sign_end - 0.5,
             "boolean": True}[invalid_kind]
    with pytest.raises(ValueError, match="source-end override.*inside core_frames/sign_frames"):
        plan_sentence([gloss, target], clearance=clear,
                      source_end_frame_overrides={gloss: frame})


def test_doctor_departure_trim_stays_within_ten_percent_core(words, monkeypatch):
    word = words["DOCTOR"]
    core_len = word["core_frames"][1] - word["core_frames"][0] + 1
    max_trim_frames = core_len // 10
    # Exercise the largest whole-frame trim allowed by policy, using current
    # metadata only. This test override is not a proposed collision repair.
    frame = word["sign_frames"][1] - max_trim_frames
    monkeypatch.setattr(transitions, "SOURCE_END_FRAME_OVERRIDES", {"DOCTOR": frame})
    departure = source_end_frame(word)
    assert departure == frame
    assert max(word["core_frames"][0], word["sign_frames"][0]) <= departure <= word["core_frames"][1]
    trim_frames = word["sign_frames"][1] - departure
    assert trim_frames == max_trim_frames
    assert 0 < trim_frames / core_len <= 0.10
    assert (trim_frames + 1) / core_len > 0.10


@pytest.mark.parametrize("sign_frames,core_frames,valid_frame,invalid_frame", [
    ([2, 8], [3, 52], 3, 2),  # Core start is the lower bound; trim is exactly 10%.
    ([3, 8], [2, 51], 3, 2),  # Sign start is the lower bound.
    ([2, 52], [3, 50], 50, 51),  # Core end is the upper bound.
])
def test_departure_override_is_general_and_honors_core_boundary(
        sign_frames, core_frames, valid_frame, invalid_frame):
    word = {"gloss": "TEST", "sign_frames": sign_frames, "core_frames": core_frames}
    assert source_end_frame(word, overrides={"TEST": valid_frame}) == valid_frame
    assert source_end_frame(word, overrides={}) == sign_frames[1]
    assert (sign_frames[1] - valid_frame) / (core_frames[1] - core_frames[0] + 1) <= 0.10
    with pytest.raises(ValueError, match="source-end override"):
        source_end_frame(word, overrides={"TEST": invalid_frame})


@pytest.mark.parametrize("glosses,gloss", [
    (("NOW", "NURSE", "BLOOD-DRAW"), "NURSE"),
    (("PLEASE", "WAIT", "DOCTOR", "COME", "SOON"), "DOCTOR"),
])
@pytest.mark.parametrize("override_mode", ["default", "replace", "patched_default", "disable"])
def test_verifier_rechecks_departure_policy_and_rejects_false_departure(
        glosses, gloss, override_mode, words, temporary_departure_overrides,
        tmp_path, monkeypatch, evaluation_script):
    if override_mode != "default":
        monkeypatch.setattr(transitions, "SOURCE_END_FRAME_OVERRIDES", temporary_departure_overrides)
    overrides = {"default": None, "replace": {gloss: words[gloss]["sign_frames"][1] - 2},
                 "patched_default": None, "disable": {}}[override_mode]
    motion, report = plan_sentence(glosses, clearance=clear,
                                   source_end_frame_overrides=overrides)
    path = tmp_path / "departure.npz"
    np.savez_compressed(path, **motion)
    report["output_npz"] = str(path)
    monkeypatch.setattr(evaluation_script, "MujocoClearance", lambda *args: clear)
    # Rechecking uses the recorded policy even if the current default changes.
    monkeypatch.setattr(transitions, "SOURCE_END_FRAME_OVERRIDES", {
        name: end - 2 for name, end in temporary_departure_overrides.items()})
    assert evaluation_script.verify_saved_sentence(report, None)["passed"]
    trimmed = gloss in report["source_end_frame_overrides"]
    if not report["source_end_frame_overrides"]:
        del report["source_end_frame_overrides"]  # Legacy report: no departure trim.
        assert evaluation_script.verify_saved_sentence(report, None)["passed"]
    segment = next(s for s in report["transitions"] if s["from_gloss"] == gloss)
    segment["source_start_frame"] = (words[gloss]["sign_frames"][1] if trimmed
                                     else temporary_departure_overrides[gloss])
    with pytest.raises(AssertionError):
        evaluation_script.verify_saved_sentence(report, None)


def test_departure_override_retract_and_handoff_use_trimmed_frame(
        words, temporary_departure_overrides, monkeypatch, tmp_path, evaluation_script):
    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))
    # NURSE→BLOOD-DRAW now gets its single RRT attempt after slice failure.
    # Keep this departure/handoff regression bounded and deterministic.
    monkeypatch.setattr(transitions, "rrt_connect", lambda *args, **kwargs: transitions.RRTResult(
        None, None, {"rrt_seed": transitions.RRT_SEED, "rrt_budget_s": transitions.RRT_BUDGET_S,
                     "rrt_nodes": 0, "rrt_runtime_s": 0.0, "rrt_found": False,
                     "smoothed": False, "rrt_outcome": "timeout"}))
    checked = []

    def clearance(q):
        checked.append(q.copy())
        return distance_result(0.001 if len(q) == 1 else -0.01, q, frame=0)

    departure = temporary_departure_overrides["NURSE"]
    motion, report = plan_sentence(["NURSE", "BLOOD-DRAW"], clearance=clearance,
                                   source_end_frame_overrides=temporary_departure_overrides)
    segment, = report["transitions"]
    assert segment["status"] == "needs_group2_fix" and segment["method"] == "rrt_connect"
    assert segment["diagnostic_method"] == "retract_approach"
    assert segment["target_approach_frames"] == [0, words["BLOOD-DRAW"]["sign_frames"][0]]
    assert segment["rrt_attempted"]
    assert sum(a["kind"] == "rrt_connect" for a in segment["attempts"]) == 1
    assert any(hit["word"] == "NURSE" and hit["frame"] == departure
               for hit in report["source_near_handoff"])
    with np.load(ROOT / words["NURSE"]["motion"], allow_pickle=False) as source:
        assert segment["source_retract_frames"] == [departure, len(source["positions"]) - 1]
        assert any(np.array_equal(q, source["positions"][departure:]) for q in checked)
    path = tmp_path / "trimmed_retract.npz"
    np.savez_compressed(path, **motion)
    report["output_npz"] = str(path)
    monkeypatch.setattr(evaluation_script, "MujocoClearance", lambda *args: clearance)
    assert evaluation_script.verify_saved_sentence(report, None)["passed"]


def collision_result(distance, positions, frame=0):
    return distance_result(distance, positions, frame)


def test_collision_tries_named_vias_and_preserves_endpoints():
    names = np.array(["left_shoulder_pitch_joint", "right_elbow_joint", "R_index_proximal_joint"])
    start, end = np.zeros(3), np.array([0.7, 0.9, 1.5])
    via = (start + end) / 2 + np.array([-0.25, 0.3, 0.0])
    checks, vias, duals = [], [], []

    def clearance(positions):
        checks.append(positions.copy())
        if len(positions) == 1 or len(positions) > 10:
            return clear(positions)
        return collision_result(-0.01, positions, 3)

    def via_factory(a, b, joint_names):
        vias.append((a.copy(), b.copy()))
        np.testing.assert_array_equal(joint_names, names)
        return [("up", via)]

    def dual_factory(a, b, joint_names):
        duals.append((a.copy(), b.copy()))
        return [(["out", "out"], [via, via + [0.1, 0, 0]])]

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=via_factory, via2_factory=dual_factory)
    assert len(checks) == 5 and len(vias) == len(duals) == 1
    assert plan.status == "PASS" and plan.used_via
    assert plan.method == "via1" and plan.via_direction == "up"
    assert [a["kind"] for a in plan.attempts] == ["direct", "via1", "via2"]
    for attempt in plan.attempts[1:]:
        assert all(leg / FPS >= 0.3 for leg in attempt["leg_intervals"])
    np.testing.assert_array_equal(plan.positions[0], start)
    np.testing.assert_array_equal(plan.positions[-1], end)
    assert any(np.array_equal(row, via) for row in plan.positions)
    assert np.all(np.abs(np.diff(plan.positions, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


@pytest.mark.parametrize("margins,chosen", [
    ([-0.004, 0.002, 0.001], 1),  # Only one direction passes the +2 mm line.
    ([0.003, 0.005, 0.004], 1),  # Select best, not first passing direction.
    ([0.003, 0.02, 0.004], 1),  # Separated candidates rank by numeric distance.
])
def test_multi_candidate_selects_largest_passing_clearance(margins, chosen):
    names = ["right_shoulder_pitch_joint", "right_elbow_joint"]
    start, end = np.zeros(2), np.array([0.6, 0.9])
    directions = ["out", "up", "forward"]
    vias = [(direction, (start + end) / 2 + [0, i + 1])
            for i, direction in enumerate(directions)]
    whole_paths = []

    def clearance(positions):
        if len(positions) == 1:
            return clear(positions)
        whole_paths.append(positions.copy())
        if len(whole_paths) == 1:
            return collision_result(-0.01, positions, 3)
        distance = margins[len(whole_paths) - 2]
        return distance_result(distance, positions, 3)

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda *args: vias, via2_factory=lambda *args: [])
    assert len(whole_paths) == 4
    assert plan.status == "PASS" and plan.via_direction == directions[chosen]
    np.testing.assert_array_equal(plan.positions, whole_paths[chosen + 1])
    assert plan.attempts[plan.selected_attempt]["clearance"]["min_distance_m"] == margins[chosen]
    for path in whole_paths:
        np.testing.assert_array_equal(path[[0, -1]], np.stack([start, end]))
        assert np.all(np.abs(np.diff(path, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


@pytest.mark.parametrize("single_margin,dual_margin,method", [
    (0.003, 0.005, "via2"), (0.005, 0.003, "via1"),
    (0.001, 0.01, "via2"), (0.003, -0.004, "via1"),
])
def test_via1_and_via2_compete_on_whole_path_clearance(single_margin, dual_margin, method):
    names = ["right_shoulder_pitch_joint", "R_index_proximal_joint"]
    start, end = np.zeros(2), np.array([0.8, 1.2])
    via1, via2 = np.array([-0.4, 0.4]), np.array([-0.2, 0.8])
    paths = []

    def clearance(positions):
        if len(positions) == 1:
            return clear(positions)
        paths.append(positions.copy())
        distance = [-0.01, single_margin, dual_margin][len(paths) - 1]
        return distance_result(distance, positions, 4)

    def unexpected_hub(*args):
        pytest.fail("Hub is a fallback after every via candidate fails")

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda *args: [("up", via1)],
                           via2_factory=lambda *args: [(["neutral_retreat", "out"], [via1, via2])],
                           hub_factory=unexpected_hub)
    assert len(paths) == 3
    assert plan.status == "PASS" and plan.method == method
    assert len(plan.attempts[2]["leg_intervals"]) == 3
    assert sum(plan.attempts[2]["leg_intervals"]) == len(paths[2]) - 1
    assert all(n / FPS >= 0.3 for n in plan.attempts[2]["leg_intervals"])
    for knot in (via1, via2):
        assert any(np.array_equal(row, knot) for row in paths[2])
    for path in paths:
        np.testing.assert_array_equal(path[[0, -1]], [start, end])
        assert np.all(np.abs(np.diff(path, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)
    if method == "via2":
        assert plan.via_direction is None
        assert plan.via_directions == ["neutral_retreat", "out"]
        np.testing.assert_array_equal(plan.positions, paths[2])


@pytest.mark.parametrize("pair,preferred_clearance,method", [
    (("NOW", "NURSE"), 0.003, "via2"),
    (("now", "nurse"), 0.003, "via2"),
    (("NOW", "NURSE"), 0.001, "via1"),  # An unsafe preferred route cannot win.
    (("NURSE", "NOW"), 0.003, "via1"),
    (("MEDICINE", "MORNING"), 0.003, "via1"),
    (("YOU", "BUY"), 0.003, "via1"),
])
def test_now_nurse_route_preference_is_pair_scoped_and_requires_passing_candidate(
        pair, preferred_clearance, method):
    names = ["right_shoulder_pitch_joint", "R_index_proximal_joint"]
    start, end = np.zeros(2), np.ones(2)
    checked = []

    def clearance(q):
        if len(q) == 1:
            return clear(q)
        checked.append(q.copy())
        return distance_result([-0.01, 0.01, preferred_clearance][len(checked) - 1], q)

    plan = plan_transition(
        start, end, names, clearance=clearance, from_gloss=pair[0], to_gloss=pair[1],
        via_factory=lambda *args: [("out+up", start + 0.4)],
        via2_factory=lambda *args: [(["out+up+forward", "out+up+forward"],
                                    [start + 0.2, start + 0.8])])
    assert plan.status == "PASS" and plan.method == method
    assert [a["kind"] for a in plan.attempts] == ["direct", "via1", "via2"]
    np.testing.assert_array_equal(plan.positions, checked[2 if method == "via2" else 1])
    np.testing.assert_array_equal(plan.positions[[0, -1]], [start, end])
    assert np.all(np.abs(np.diff(plan.positions, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


def test_hub_fallback_selected_only_after_mocked_vias_fail_and_both_legs_clear():
    names = ["right_shoulder_pitch_joint", "R_index_proximal_joint"]
    start, end, hub = np.zeros(2), np.ones(2), np.array([-0.6, -0.4])
    hub_paths = []

    def clearance(positions):
        if len(positions) == 1:
            return clear(positions)
        if any(np.array_equal(row, hub) for row in positions):
            hub_paths.append(positions.copy())
            return distance_result(0.003, positions)
        return collision_result(-0.01, positions, 4)

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda *args: [("out", np.full(2, 0.3))],
                           via2_factory=lambda *args: [(["out", "up"], [np.full(2, 0.2), np.full(2, 0.8)])],
                           hub_factory=lambda n: hub)
    assert plan.status == "PASS" and plan.method == "hub"
    assert [attempt["kind"] for attempt in plan.attempts] == ["direct", "via1", "via2", "hub"]
    assert plan.selected_attempt == 3
    assert len(hub_paths) == 3  # Complete path and both independently checked legs.
    chosen = plan.attempts[plan.selected_attempt]
    assert len(chosen["leg_clearance"]) == 2
    assert all(result["passed"] for result in chosen["leg_clearance"])
    assert all(n / FPS >= 0.3 for n in chosen["leg_intervals"])
    np.testing.assert_array_equal(plan.positions[[0, -1]], [start, end])
    assert np.all(np.abs(np.diff(plan.positions, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


def test_persistent_interior_collision_checks_hub_and_reports_worst_pair():
    names = np.array(["right_shoulder_pitch_joint", "L_index_proximal_joint"])
    calls = []

    def clearance(positions):
        calls.append(positions.copy())
        if len(positions) == 1:
            return clear(positions)
        result = collision_result(-0.01, positions, 4)
        result.collisions.append({"bodies": ["left_elbow_link", "right_elbow_link"],
                                  "distance_m": -0.005, "frame": 5, "location": "interior"})
        return result

    plan = plan_transition(np.zeros(2), np.ones(2), names, clearance=clearance,
                           via_factory=lambda a, b, n: [(d, (a + b) / 2) for d, _ in VIA_DIRECTIONS],
                           via2_factory=lambda a, b, n: [(["neutral_retreat", "out"], [a + 0.2, b + 0.2])],
                           hub_factory=lambda names: np.full(len(names), -0.3))
    assert len(calls) == 3 + len(VIA_DIRECTIONS) + 1 + 3  # Via2, hub whole path and both legs.
    assert plan.status == "FAILED" and plan.method == "direct"
    assert plan.attempts[-1]["kind"] == "hub"
    assert len(plan.attempts[-1]["leg_clearance"]) == 2
    assert plan.reasons
    worst = plan.attempts[plan.selected_attempt]["worst_collision"]
    assert worst["distance_m"] == -0.01 and "torso_link" in worst["bodies"]
    assert plan.positions.ndim == 2 and np.isfinite(plan.positions).all()


def test_unknown_gloss_rejected_before_planning():
    with pytest.raises((ValueError, SystemExit), match="UNKNOWN-GLOSS"):
        plan_sentence(["UNKNOWN-GLOSS"], clearance=clear)


def sphere_pair_model(first_body, second_body):
    """Two real collision geoms; the second sphere slides along their centres."""
    import mujoco

    return mujoco.MjModel.from_xml_string(f"""
        <mujoco>
          <option gravity="0 0 0"/>
          <worldbody>
            <body name="{first_body}">
              <geom type="sphere" size="0.01"/>
            </body>
            <body name="{second_body}" pos="0.02 0 0">
              <joint name="right_wrist_pitch_joint" type="slide" axis="1 0 0"/>
              <geom type="sphere" size="0.01"/>
            </body>
          </worldbody>
        </mujoco>
    """)


def test_static_body_pairs_are_computed_from_moving_ancestors_not_names():
    import mujoco

    model = mujoco.MjModel.from_xml_string("""
        <mujoco><worldbody>
          <body name="anchor"><geom type="sphere" size="0.01"/></body>
          <body name="branch_a" pos="0.1 0 0">
            <joint name="motor_a" type="slide" axis="1 0 0"/>
            <geom type="sphere" size="0.01"/>
            <body name="rigid_tip" pos="0.05 0 0">
              <geom type="sphere" size="0.01"/>
            </body>
          </body>
          <body name="branch_b" pos="0.3 0 0">
            <joint name="motor_b" type="slide" axis="1 0 0"/>
            <geom type="sphere" size="0.01"/>
          </body>
        </worldbody></mujoco>
    """)

    def pair(a, b):
        return tuple(sorted((model.body(a).id, model.body(b).id)))

    moving_a = derive_static_body_pairs(model, {model.joint("motor_a").id})
    moving_b = derive_static_body_pairs(model, {model.joint("motor_b").id})
    assert pair("anchor", "branch_b") in moving_a
    assert pair("anchor", "branch_a") not in moving_a
    assert pair("branch_a", "rigid_tip") in moving_a
    assert pair("anchor", "branch_a") in moving_b
    assert pair("anchor", "branch_b") not in moving_b
    assert moving_a != moving_b


def test_moving_joint_derivation_uses_aggregate_library_span_and_planner_ik(tmp_path):
    import mujoco

    model = mujoco.MjModel.from_xml_string("""
        <mujoco><worldbody>
          <body name="anchor"><geom type="sphere" size="0.01"/></body>
          <body name="between_clip_body" pos="0.1 0 0">
            <joint name="between_clip_joint" type="slide" axis="1 0 0"/>
            <geom type="sphere" size="0.01"/>
          </body>
          <body name="constant_body" pos="0.3 0 0">
            <joint name="constant_joint" type="slide" axis="1 0 0"/>
            <geom type="sphere" size="0.01"/>
          </body>
          <body name="ik_body" pos="0.5 0 0">
            <joint name="left_wrist_pitch_joint" type="slide" axis="1 0 0"/>
            <geom type="sphere" size="0.01"/>
          </body>
        </worldbody></mujoco>
    """)
    names = np.array(["between_clip_joint", "constant_joint", "left_wrist_pitch_joint"])
    folder = tmp_path / "motions"
    folder.mkdir()
    words = []
    # Every individual clip is stationary. Only the complete library reveals
    # that the first joint moves; the second is always the same nonzero value.
    for index, between_value in enumerate((0.0, 2e-9)):
        path = folder / f"clip_{index}.npz"
        np.savez(path, timestamps_s=np.array([0.0, 1 / FPS]), joint_names=names,
                 positions=np.tile([between_value, 0.0004, 0.0], (2, 1)))
        words.append({"gloss": f"CLIP-{index}", "motion_ready": True,
                      "motion": f"motions/{path.name}"})
    library_path = folder / "hospital_v1_motions.json"
    library_path.write_text(json.dumps({"glosses": words}))
    checker = MujocoClearance(model, names, library_path=library_path)

    assert checker.moving_joint_ids == frozenset({model.joint("between_clip_joint").id,
                                                 model.joint("left_wrist_pitch_joint").id})
    assert checker.derivation["library_words"] == 2
    assert checker.derivation["library_frames"] == 4
    anchor = model.body("anchor").id
    stationary_pair = tuple(sorted((anchor, model.body("constant_body").id)))
    moving_pair = tuple(sorted((anchor, model.body("between_clip_body").id)))
    ik_pair = tuple(sorted((anchor, model.body("ik_body").id)))
    assert stationary_pair in checker.static_body_pairs
    assert moving_pair not in checker.static_body_pairs
    assert ik_pair not in checker.static_body_pairs  # IK can move it despite constant source clips.


def test_library_static_pairs_include_mount_hips_and_exclude_arm_hand_bodies(words):
    model = load_model()
    with np.load(ROOT / words["YOU"]["motion"]) as source:
        checker = MujocoClearance(model, source["joint_names"])

    body_pairs = {
        tuple(sorted(model.body(body).name for body in pair))
        for pair in checker.static_body_pairs
    }
    assert len(checker.moving_joint_ids) == 38
    assert len(checker.moving_ancestor_joint_ids) == model.nbody
    for side in ("left", "right"):
        assert tuple(sorted(("fixed_mount", f"{side}_hip_pitch_link"))) in body_pairs
        assert tuple(sorted(("fixed_mount", f"{side}_wrist_yaw_link"))) not in body_pairs
        assert any(set(gap["bodies"]) == {"fixed_mount", f"{side}_hip_pitch_link"}
                   for gap in checker.vendor_structural_gaps)
    assert not any(
        body.startswith(("L_", "R_")) or
        any(part in body.lower() for part in ("arm", "hand", "finger", "wrist", "shoulder", "elbow"))
        for pair in body_pairs for body in pair
    )


def test_vendor_gap_is_reported_without_dominating_moving_minimum_or_source_near():
    import mujoco

    model = mujoco.MjModel.from_xml_string("""
        <mujoco><worldbody>
          <body name="fixed_mount">
            <geom name="mount_geom" type="sphere" size="0.01"/>
          </body>
          <body name="left_hip_pitch_link" pos="0.0195 0 0">
            <joint name="left_hip_pitch_joint" type="slide" axis="1 0 0"/>
            <geom name="hip_geom" type="sphere" size="0.01"/>
          </body>
          <body name="left_wrist_yaw_link" pos="0.2 0 0">
            <joint name="left_wrist_pitch_joint" type="slide" axis="1 0 0"/>
            <geom name="wrist_geom" type="sphere" size="0.01"/>
          </body>
        </worldbody></mujoco>
    """)
    names = ["left_hip_pitch_joint", "left_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)
    start, end = [0.0, 0.0], [0.0, 0.005]
    result = checker(np.array([start, end]))
    assert result.passed and result.min_distance_m > 0.002
    assert "left_wrist_yaw_link" in result.worst_contact["bodies"]
    assert not result.collisions and not result.near_contacts
    vendor = [gap for gap in result.vendor_structural_gaps
              if set(gap["bodies"]) == {"fixed_mount", "left_hip_pitch_link"}]
    assert vendor
    assert vendor[0]["distance_m"] == pytest.approx(-0.0005, abs=1e-10)
    assert vendor[0]["distance_mm"] == pytest.approx(-0.5, abs=1e-7)
    assert set(vendor[0]["geoms"]) == {"mount_geom", "hip_geom"}
    plan = plan_transition(start, end, names, clearance=checker)
    assert plan.status == "PASS" and not plan.source_near
    assert all(endpoint["min_distance_m"] > 0.002 for endpoint in plan.endpoint_clearance)
    assert all(endpoint["vendor_structural_gaps"] for endpoint in plan.endpoint_clearance)


@pytest.mark.parametrize("distance", [-0.003, 0.001])
def test_forced_left_wrist_mount_violation_still_blocks_normal_gate(distance):
    model = sphere_pair_model("fixed_mount", "left_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)
    wrist_mount = tuple(sorted((model.body("fixed_mount").id,
                               model.body("left_wrist_yaw_link").id)))
    assert wrist_mount not in checker.static_body_pairs

    def clearance(positions):
        forced = np.asarray(positions).copy()
        if len(forced) > 1:
            forced[len(forced) // 2, 0] = distance
        return checker(forced)

    plan = plan_transition([0.005], [0.01], names, clearance=clearance,
                           via_factory=lambda *args: [], via2_factory=lambda *args: [],
                           hub_factory=lambda *args: [0.02])
    assert plan.status == "FAILED" and not plan.source_near
    assert plan.attempts[-1]["kind"] == "hub"
    assert all(attempt["clearance"]["min_distance_m"] < 0.002 for attempt in plan.attempts)
    assert set(plan.attempts[plan.selected_attempt]["worst_collision"]["bodies"]) == {
        "fixed_mount", "left_wrist_yaw_link",
    }


@pytest.mark.parametrize("distance,passed", [(0.003, True), (0.0015, False), (-0.0015, False), (-0.0025, False)])
def test_real_mujoco_clearance_requires_positive_two_mm(distance, passed):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    checker = MujocoClearance(model, np.array(["right_wrist_pitch_joint"]))
    # Endpoints are separated; the middle sample determines signed clearance.
    result = checker(np.array([[0.005], [distance], [0.005]]))
    assert result.passed is passed
    assert result.sampled_frames == 3
    assert result.min_distance_m == pytest.approx(distance, abs=1e-10)
    if passed:
        assert result.collisions == []
    else:
        assert len(result.collisions) == 1
        collision = result.collisions[0]
        assert set(collision["bodies"]) == {"torso_link", "right_wrist_yaw_link"}
        assert collision["distance_m"] == pytest.approx(distance, abs=1e-10)
        assert collision["frame"] == 1 and collision["location"] == "interior"


@pytest.mark.parametrize("frame,location", [(0, "start_endpoint"), (2, "end_endpoint")])
def test_clearance_checks_both_transition_endpoints(frame, location):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    checker = MujocoClearance(model, ["right_wrist_pitch_joint"])
    positions = np.full((3, 1), 0.005)
    positions[frame] = -0.003
    result = checker(positions)
    assert not result.passed
    assert result.collisions[0]["frame"] == frame
    assert result.collisions[0]["location"] == location


@pytest.mark.parametrize("gap", [0.005, 1.2])
def test_separated_clearance_and_planned_pass_are_finite_with_closest_pair(gap):
    model = sphere_pair_model("fixed_mount", "right_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)
    margins, pair_margins = model.geom_margin.copy(), model.pair_margin.copy()
    masks = (model.geom_contype.copy(), model.geom_conaffinity.copy())
    apply_frame(model, checker.data, names, [gap])
    assert checker.data.ncon == 0  # No contacts with the original zero margins.
    result = checker(np.array([[gap], [gap + 0.005]]))
    assert isinstance(result.min_distance_m, (int, float)) and math.isfinite(result.min_distance_m)
    assert result.min_distance_m == pytest.approx(gap)
    assert result.passed and len(result.worst_contact["bodies"]) == 2
    assert "fixed_mount" in result.worst_contact["bodies"]
    assert len(result.worst_contact["geoms"]) == 2
    plan = plan_transition([gap], [gap + 0.005], names, clearance=checker)
    chosen = plan.attempts[plan.selected_attempt]
    assert plan.status == "PASS" and not plan.source_near
    assert math.isfinite(chosen["clearance"]["min_distance_m"])
    assert chosen["worst_collision"]["bodies"] == result.worst_contact["bodies"]
    np.testing.assert_array_equal(model.geom_margin, margins)
    np.testing.assert_array_equal(model.pair_margin, pair_margins)
    np.testing.assert_array_equal(model.geom_contype, masks[0])
    np.testing.assert_array_equal(model.geom_conaffinity, masks[1])


@pytest.mark.parametrize("distance", [-0.0008, 0.0, 0.001999999, 0.002, 0.003])
def test_normal_path_uses_absolute_positive_two_mm_floor(distance):
    def clearance(positions):
        return clear(positions) if len(positions) == 1 else distance_result(distance, positions, 4)

    plan = plan_transition([0.0], [0.5], ["right_elbow_joint"], clearance=clearance,
                           via_factory=lambda *args: [], via2_factory=lambda *args: [],
                           hub_factory=lambda *args: [-0.5])
    assert not plan.source_near and plan.endpoint_floor_m is None
    assert plan.status == ("PASS" if distance >= 0.002 else "FAILED")


@pytest.mark.parametrize("endpoint", [0, 1])
@pytest.mark.parametrize("distance", [-0.0008, -0.002, -0.004, 0.001])
def test_real_near_endpoint_direct_passes_only_at_relative_floor(endpoint, distance):
    model = sphere_pair_model("fixed_mount", "right_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)
    endpoints = [[0.005], [0.005]]
    endpoints[endpoint] = [distance]
    checks = []

    def clearance(positions):
        checks.append(positions.copy())
        return checker(positions)

    def unexpected_search(*args):
        pytest.fail("A direct path meeting the relative floor needs no escalation")

    plan = plan_transition(*endpoints, names, clearance=clearance,
                           via_factory=unexpected_search, via2_factory=unexpected_search,
                           hub_factory=unexpected_search)
    assert len(checks) == 3 and len(checks[0]) == len(checks[1]) == 1
    assert plan.status == "source_near" and plan.method == "direct" and not plan.used_via
    assert plan.source_near and plan.attempts[0]["relative_floor_passed"]
    assert plan.via_direction is None and plan.via_directions == []
    assert len(plan.attempts) == 1
    near = plan.endpoint_clearance[endpoint]
    assert near["min_distance_m"] == pytest.approx(distance)
    assert set(near["near_contacts"][0]["bodies"]) == {"fixed_mount", "right_wrist_yaw_link"}
    assert not near["passed"]  # Absolute clearance and relative acceptance are separate.
    np.testing.assert_array_equal(plan.positions[[0, -1]], endpoints)


@pytest.mark.parametrize("endpoint_distance,status", [
    (0.002, "PASS"), (0.003, "PASS"), (0.001999999, "source_near"), (0.001, "source_near"),
])
def test_endpoint_near_threshold_is_strict(endpoint_distance, status):
    assert ENDPOINT_NEAR_M == 0.002
    assert PENETRATION_TOLERANCE_M == 0.002

    def clearance(positions):
        return distance_result(endpoint_distance, positions)

    plan = plan_transition([0.0], [0.5], ["right_elbow_joint"], clearance=clearance)
    assert plan.status == status and plan.method == "direct"
    assert plan.endpoint_clearance[0]["min_distance_m"] == endpoint_distance


@pytest.mark.parametrize("start,end", [
    (-0.004, 0.005), (0.005, -0.004), (-0.004, -0.003), (-0.004, -0.004),
])
def test_real_source_near_no_worse_than_endpoints_is_accepted(start, end):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)

    def unexpected_via(*args):
        pytest.fail("An unchanged source collision should not need a via")

    plan = plan_transition([start], [end], names, clearance=checker, via_factory=unexpected_via)
    assert plan.status == "source_near" and not plan.used_via
    assert plan.reasons == []
    assert plan.endpoint_floor_m == pytest.approx(min(start, end))
    assert checker(plan.positions).min_distance_m >= plan.endpoint_floor_m


@pytest.mark.parametrize("floor", [-0.004, -0.0008, 0.001])
@pytest.mark.parametrize("worsening", [0.0, 1e-9, 0.056])
def test_source_near_relative_floor_escalates_all_candidates_before_failed(floor, worsening):
    names = ["right_shoulder_pitch_joint", "right_elbow_joint"]
    start, end = np.zeros(2), np.array([0.6, 0.9])
    full_paths, factories = [], []

    def clearance(positions):
        if len(positions) == 1:
            return distance_result(floor, positions)
        full_paths.append(positions.copy())
        return distance_result(floor - worsening, positions, 4)

    def vias(*args):
        factories.append("via1")
        return [("out", (start + end) / 2 + 0.1)]

    def duals(*args):
        factories.append("via2")
        return [(["neutral_retreat", "out"], [start + 0.2, end + 0.2])]

    def hub(*args):
        factories.append("hub")
        return np.full(2, -0.5)

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=vias, via2_factory=duals, hub_factory=hub)
    assert plan.source_near and plan.endpoint_floor_m == floor
    assert plan.status == ("FAILED" if worsening else "source_near")
    assert plan.method == "direct"  # Stable tie order, but FAILED never counts as accepted.
    assert factories == (["via1", "via2", "hub"] if worsening else [])
    assert len(full_paths) == (6 if worsening else 1)
    assert [a["kind"] for a in plan.attempts] == (["direct", "via1", "via2", "hub"] if worsening else ["direct"])
    assert plan.attempts[plan.selected_attempt]["relative_floor_passed"] is (not worsening)
    assert bool(plan.reasons) == bool(worsening)
    if worsening:
        assert plan.attempts[-1]["status"] == "FAILED"
        assert plan.attempts[plan.selected_attempt]["worst_collision"]["distance_m"] == floor - worsening


@pytest.mark.parametrize("method", ["via1", "via2", "hub"])
@pytest.mark.parametrize("endpoint", [0, 1])
@pytest.mark.parametrize("floor", [-0.0008, 0.001])
def test_source_near_search_accepts_route_at_worse_endpoint_floor(method, endpoint, floor):
    endpoint_calls, path_calls, factories = [], [], []
    endpoints = [0.006, 0.006]
    endpoints[endpoint] = floor

    def clearance(positions):
        if len(positions) == 1:
            distance = endpoints[len(endpoint_calls)]
            endpoint_calls.append(positions.copy())
        else:
            kind = ["direct", "via1", "via2", "hub", "hub", "hub"][len(path_calls)]
            path_calls.append(positions.copy())
            distance = floor if kind == method else -0.056
        return distance_result(distance, positions)

    def vias(*args):
        factories.append("via1")
        return [("out", [0.2])]

    def duals(*args):
        factories.append("via2")
        return [(["neutral_retreat", "out"], [[0.1], [0.4]])]

    def hub(*args):
        factories.append("hub")
        return [-0.5]

    plan = plan_transition([0.0], [0.5], ["right_elbow_joint"], clearance=clearance,
                           via_factory=vias, via2_factory=duals, hub_factory=hub)
    assert plan.status == "source_near" and plan.source_near
    assert plan.method == method and plan.used_via
    assert plan.endpoint_floor_m == floor
    assert factories == (["via1", "via2", "hub"] if method == "hub" else ["via1", "via2"])
    assert plan.attempts[0]["status"] == "FAILED"  # The -56 mm direct is never accepted.
    chosen = plan.attempts[plan.selected_attempt]
    assert chosen["relative_floor_passed"] and chosen["clearance"]["min_distance_m"] == floor
    if method == "hub":
        assert len(chosen["leg_clearance"]) == 2
        assert all(r["min_distance_m"] == floor for r in chosen["leg_clearance"])


def test_source_near_report_separates_counts_and_hands_off_source_frames(words):
    def clearance(positions):
        return collision_result(-0.004, positions)

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["transition_count"] == report["source_near_count"] == report["accepted_count"] == 1
    assert report["pass_count"] == report["failed_count"] == 0
    assert report["status"] == "source_near"
    assert {(row["word"], row["frame"]) for row in report["source_near_handoff"]} == {
        ("YOU", words["YOU"]["sign_frames"][1]), ("BUY", words["BUY"]["sign_frames"][0]),
    }
    assert all(row["distance_m"] == -0.004 and "torso_link" in row["bodies"]
               for row in report["source_near_handoff"])


@pytest.mark.parametrize("floor", [-0.0008, 0.001])
def test_failed_source_near_report_is_not_accepted_and_keeps_handoff(words, monkeypatch, floor):
    import sign_robot.transitions as transitions

    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))

    def clearance(positions):
        return distance_result(floor if len(positions) == 1 else -0.056, positions)

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["transition_count"] == report["failed_count"] == 1
    assert report["pass_count"] == report["source_near_count"] == report["accepted_count"] == 0
    transition, = report["transitions"]
    assert report["status"] == transition["status"] == "FAILED"
    assert transition["source_near"] and not transition["relative_floor_passed"]
    assert transition["min_clearance_mm"] == -56.0
    assert transition["closest_pair"]["distance_m"] == -0.056
    assert {(row["word"], row["frame"]) for row in report["source_near_handoff"]} == {
        ("YOU", words["YOU"]["sign_frames"][1]), ("BUY", words["BUY"]["sign_frames"][0]),
        ("BUY", 0),  # Approach slice now joins the existing endpoint handoff.
    }


@pytest.mark.parametrize("distance", [-0.0008, 0.001])
def test_mild_contacts_and_small_positive_gaps_are_in_source_near_handoff(words, distance):
    def clearance(positions):
        contact = {"bodies": ["fixed_mount", "right_wrist_yaw_link"],
                   "distance_m": distance, "frame": 0, "location": "start_endpoint"}
        return ClearanceResult(False, distance, sampled_frames=len(positions),
                               near_contacts=[contact], worst_contact=contact,
                               frame_clearances_m=[distance] * len(positions))

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["source_near_count"] == 1 and report["pass_count"] == 0
    transition, = report["transitions"]
    assert transition["method"] == "direct" and transition["status"] == "source_near"
    assert transition["source_near"] and not transition["used_via"]
    assert transition["min_clearance_mm"] == distance * 1000
    assert {(row["word"], row["frame"]) for row in report["source_near_handoff"]} == {
        ("YOU", words["YOU"]["sign_frames"][1]), ("BUY", words["BUY"]["sign_frames"][0]),
    }
    assert all(row["clearance_mm"] == distance * 1000 for row in report["source_near_handoff"])


def test_ik_vias_use_robot_axes_bounded_arms_and_convex_fingers(words, monkeypatch):
    import mujoco
    from sign_robot.retarget import G1Retargeter

    model = load_model()
    with np.load(ROOT / words["YOU"]["motion"]) as source:
        names = source["joint_names"].copy()
        start, end = source["positions"][[0, words["YOU"]["sign_frames"][1]]].copy()
    arm = np.array([any(part in str(n) for part in ("shoulder", "elbow", "wrist")) for n in names])
    for i, name in enumerate(names):
        if arm[i]:
            value = (-0.5 if "shoulder_pitch" in name else 0.8 if "elbow" in name else
                     0.2 if "left_shoulder_roll" in name else -0.2 if "right_shoulder_roll" in name else 0.0)
            start[i] = end[i] = value
    midpoint = (start + end) / 2
    data = mujoco.MjData(model)
    wrist_ids = [model.body(f"{side}_wrist_yaw_link").id for side in ("left", "right")]
    apply_frame(model, data, names, midpoint)
    wrists = data.xpos[wrist_ids].copy()
    # Existing model shoulder offsets confirm +Y is left; foot tips extend +X.
    assert data.xpos[model.body("left_shoulder_pitch_link").id, 1] > 0
    assert data.xpos[model.body("right_shoulder_pitch_link").id, 1] < 0
    goals_and_seeds = []
    solve = G1Retargeter.solve_arms

    def recorded_solve(self, q, sides, goals, previous, pairs):
        goals_and_seeds.append((goals, q.copy()))
        return solve(self, q, sides, goals, previous, pairs)

    monkeypatch.setattr(G1Retargeter, "solve_arms", recorded_solve)
    candidates = list(ik_via_candidates(start, end, names, model))
    assert [direction for direction, _ in candidates] == [direction for direction, _ in VIA_DIRECTIONS]
    ids = [model.joint(str(n)).id for n in names]
    for (direction, via), (_, vector), (goals, seed) in zip(candidates, VIA_DIRECTIONS, goals_and_seeds):
        np.testing.assert_array_equal(via[~arm], midpoint[~arm])
        np.testing.assert_array_equal(seed, midpoint)
        assert np.all(via >= model.jnt_range[ids, 0]) and np.all(via <= model.jnt_range[ids, 1])
        apply_frame(model, data, names, via)
        displacement = data.xpos[wrist_ids] - wrists
        target = VIA_DISPLACEMENT_M * np.asarray(vector) / np.linalg.norm(vector)
        expected = np.stack([target, target * [1, -1, 1]])
        # The requested target is exact; bounded IK may only partly reach it.
        requested = np.stack([goals[side][0] for side in ("left", "right")]) - wrists
        np.testing.assert_allclose(requested, expected, atol=1e-12, err_msg=direction)
        assert np.all(np.sum(displacement * expected, axis=1) > 0), direction


def test_dual_ik_family_uses_neutral_qpos0_arms_and_solves_every_knot(words, monkeypatch):
    from sign_robot.retarget import G1Retargeter

    model = load_model()
    with np.load(ROOT / words["YOU"]["motion"]) as source:
        names = source["joint_names"].copy()
        start, end = source["positions"][[words["YOU"]["sign_frames"][0],
                                           words["YOU"]["sign_frames"][1]]].copy()
    addresses = [int(model.joint(str(n)).qposadr[0]) for n in names]
    np.testing.assert_array_equal(neutral_pose(names, model), model.qpos0[addresses])
    arm = np.array([any(part in str(n) for part in ("shoulder", "elbow", "wrist")) for n in names])
    seeds = []
    solve = G1Retargeter.solve_arms

    def recorded_solve(self, q, sides, goals, previous, pairs):
        seeds.append(q.copy())
        return solve(self, q, sides, goals, previous, pairs)

    monkeypatch.setattr(G1Retargeter, "solve_arms", recorded_solve)
    candidates = list(ik_dual_via_candidates(start, end, names, model))
    assert len(candidates) == len(VIA_DIRECTIONS) + 3 + 6
    assert len(seeds) == 2 * len(VIA_DIRECTIONS) + 1 + 3 + 12
    ids = [model.joint(str(n)).id for n in names]
    for directions, knots in candidates:
        assert len(directions) == len(knots) == 2
        for knot in knots:
            assert np.isfinite(knot).all()
            assert np.all(knot >= model.jnt_range[ids, 0]) and np.all(knot <= model.jnt_range[ids, 1])
        if directions[0].startswith("neutral_retreat"):
            np.testing.assert_array_equal(knots[0][~arm], (start + (end - start) / 3)[~arm])
            np.testing.assert_array_equal(knots[1][~arm], (start + 2 * (end - start) / 3)[~arm])
        else:
            np.testing.assert_array_equal(knots[0][~arm], start[~arm])
            np.testing.assert_array_equal(knots[1][~arm], end[~arm])
    retreat_seed = seeds[2 * len(VIA_DIRECTIONS)][addresses]
    np.testing.assert_array_equal(retreat_seed[arm], neutral_pose(names, model)[arm])
    assert [d for d, _ in candidates[len(VIA_DIRECTIONS):len(VIA_DIRECTIONS) + 3]] == [
        ["neutral_retreat", "out"], ["neutral_retreat", "out+up"], ["neutral_retreat", "out+forward"],
    ]
    serialized_start = 2 * len(VIA_DIRECTIONS) + 1 + 3
    for parked_side, seed_offset in (("left", serialized_start), ("right", serialized_start + 6)):
        parked = arm & np.array([str(n).startswith(parked_side + "_") for n in names])
        moving = arm & ~parked
        for i in range(3):
            first, second = (seeds[seed_offset + 2 * i + j][addresses] for j in (0, 1))
            np.testing.assert_array_equal(first[parked], neutral_pose(names, model)[parked])
            np.testing.assert_array_equal(second[parked], neutral_pose(names, model)[parked])
            np.testing.assert_array_equal(first[moving], start[moving])
            np.testing.assert_array_equal(second[moving], end[moving])


@pytest.mark.parametrize("first,second,excluded", [
    ("R_index_proximal", "right_wrist_yaw_link", True),
    ("L_thumb_proximal", "L_index_proximal", True),
    ("R_index_proximal", "left_wrist_yaw_link", False),
    ("R_index_proximal", "right_elbow_link", False),
    ("fixed_mount", "right_wrist_yaw_link", False),
])
def test_real_contact_excludes_only_same_hand_adjacency(first, second, excluded):
    model = sphere_pair_model(first, second)
    if excluded:
        # Keep an eligible far pair so exclusion does not require a null or
        # invented clearance. The contacting hand pair must remain excluded.
        import mujoco
        xml = f"""
            <mujoco><worldbody>
              <body name="{first}"><geom type="sphere" size="0.01"/></body>
              <body name="{second}" pos="0.02 0 0">
                <joint name="right_wrist_pitch_joint" type="slide" axis="1 0 0"/>
                <geom type="sphere" size="0.01"/>
              </body>
              <body name="torso_link" pos="0.5 0 0"><geom type="sphere" size="0.01"/></body>
            </worldbody></mujoco>"""
        model = mujoco.MjModel.from_xml_string(xml)
    checker = MujocoClearance(model, ["right_wrist_pitch_joint"])
    result = checker(np.array([[-0.004], [-0.004]]))
    assert checker.data.ncon > 0  # Filtering, rather than missing contacts, explains PASS.
    assert result.passed is excluded
    if excluded:
        assert result.collisions == [] and math.isfinite(result.min_distance_m)
        assert result.min_distance_m > 0.002
        assert "torso_link" in result.worst_contact["bodies"]
    else:
        assert result.min_distance_m == pytest.approx(-0.004, abs=1e-10)
        assert result.collisions


def test_sag_guard_does_not_replace_a_clear_blend_with_colliding_via():
    names = np.array(["right_shoulder_pitch_joint", "right_elbow_joint"])
    start, end = np.zeros(2), np.array([0.6, 0.9])
    direct = minimum_jerk_blend(start, end, names)
    calls = []

    def clearance(positions):
        if len(positions) == 1:
            return clear(positions)
        calls.append(positions.copy())
        return ClearanceResult(len(calls) == 1, min_distance_m=0.01 if len(calls) == 1 else -0.01)

    def height_check(positions):
        return {"passed": len(calls) > 1}

    plan = plan_transition(start, end, names, clearance=clearance, height_check=height_check,
                           via_factory=lambda a, b, n: [("up", (a + b) / 2 + [0, 0.3])],
                           via2_factory=lambda *args: [])
    assert len(calls) == 2
    assert plan.status == "PASS" and not plan.used_via
    assert plan.warnings
    assert plan.attempts[1]["status"] == "FAILED"
    np.testing.assert_array_equal(plan.positions, direct)



def test_clearance_display_caps_at_nine_point_five_mm():
    assert CLEARANCE_DISPLAY_CAP_M == pytest.approx(0.0095)
    assert clearance_is_capped(0.0095)
    assert clearance_is_capped(0.00950015)
    assert clearance_is_capped(0.05)
    assert not clearance_is_capped(0.0094)
    assert not clearance_is_capped(-0.0008)
    assert format_clearance_mm(0.00950015) == ">=9.5"
    assert format_clearance_mm(0.0095) == ">=9.5"
    assert format_clearance_mm(0.003) == "3.000000"
    assert format_clearance_mm(-0.00080926) == "-0.809260"


def test_retract_approach_route_bridges_and_timescales():
    names = ["right_elbow_joint", "R_index_proximal_joint"]
    retract = np.array([[0.0, 0.0], [1.2, 0.9], [0.2, 0.0]])
    approach = np.array([[0.5, 0.0], [1.8, 0.8], [0.7, 0.0]])
    bridge = minimum_jerk_blend(retract[-1], approach[0], names)
    raw = np.vstack([retract, bridge[1:-1], approach])
    limits = joint_rate_limits(names)
    assert np.any(np.abs(np.diff(raw, axis=0)) * FPS > limits)
    route, info = build_retract_approach_route(retract, approach, names)
    assert info["bridge_intervals"] / FPS >= 0.3
    assert info["timed_frames"] > info["raw_frames"]
    np.testing.assert_array_equal(route[[0, -1]], raw[[0, -1]])
    assert np.all(np.abs(np.diff(route, axis=0)) * FPS <= limits + 1e-10)
    cursor = 0
    for knot in raw:
        matches = np.flatnonzero(np.all(route[cursor:] == knot, axis=1))
        assert len(matches), f"Original knot {knot} was lost or reordered"
        cursor += int(matches[0]) + 1


@pytest.mark.parametrize("name,jump", [("right_elbow_joint", 1.2), ("R_index_proximal_joint", 0.8)])
def test_timescale_stretches_rate_violations_and_preserves_every_knot(name, jump):
    raw = np.array([[0.0], [jump], [-jump], [0.0]])
    limit, = joint_rate_limits([name])
    assert (len(raw) - 1) / FPS < 0.3
    assert np.max(np.abs(np.diff(raw, axis=0))) * FPS > limit
    timed = timescale_to_rate_limits(raw, [name])
    assert len(timed) > len(raw) and (len(timed) - 1) / FPS >= 0.3
    assert np.all(np.abs(np.diff(timed, axis=0)) * FPS <= limit + 1e-10)
    np.testing.assert_array_equal(timed[[0, -1]], raw[[0, -1]])
    for knot in raw:
        assert np.any(np.all(timed == knot, axis=1))


def test_retract_approach_same_neutral_retains_corner_when_duration_stretches():
    retract = np.array([[1.0, 0.0], [0.0, 0.0]])
    approach = np.array([[0.0, 0.0], [0.0, 1.0]])
    route, info = build_retract_approach_route(
        retract, approach, ["right_elbow_joint", "right_wrist_pitch_joint"])
    assert info["bridge_intervals"] == 0
    assert info["timed_frames"] > info["raw_frames"]
    neutral, = np.flatnonzero(np.all(route == [0.0, 0.0], axis=1))
    np.testing.assert_array_equal(route[:neutral + 1, 1], 0.0)
    np.testing.assert_array_equal(route[neutral:, 0], 0.0)
    assert (len(route) - 1) / FPS >= 0.3


@pytest.mark.parametrize("floor", [-0.0008, 0.001, 0.008])
def test_retract_approach_accepts_when_prior_routes_fail(floor):
    names = ["right_elbow_joint"]
    a, b = np.array([0.0]), np.array([1.0])
    retract = np.vstack([a, [[0.2]], [[0.4]]])
    approach = np.vstack([[[0.6]], [[0.8]], [b]])
    multi = []

    def clearance(positions):
        if len(positions) == 1:
            return distance_result(floor, positions)
        multi.append(len(positions))
        # direct (1) + hub whole+2 legs (3) fail; then retract/approach slices + route pass.
        if len(multi) <= 4:
            return distance_result(-0.056, positions)
        return distance_result(floor, positions)

    plan = plan_transition(
        a, b, names, clearance=clearance,
        via_factory=lambda *args: [], via2_factory=lambda *args: [],
        hub_factory=lambda names: np.array([-0.5]),
        source_retract=retract, target_approach=approach,
        source_retract_frames=(10, 12), target_approach_frames=(0, 2))
    assert plan.status == ("source_near" if floor < ENDPOINT_NEAR_M else "PASS")
    assert plan.method == "retract_approach" and plan.used_via
    chosen = plan.attempts[plan.selected_attempt]
    assert chosen["kind"] == "retract_approach"
    assert not chosen["in_slice_collision"]
    assert chosen["source_retract_frames"] == [10, 12]
    assert chosen["target_approach_frames"] == [0, 2]
    assert chosen["clearance"]["min_distance_m"] == floor
    assert chosen["required_clearance_m"] == floor
    assert "retract_approach" in [a["kind"] for a in plan.attempts]
    assert any(a["kind"] == "hub" for a in plan.attempts)


def test_retract_approach_in_slice_collision_stops_without_rrt(floor=-0.0008):
    names = ["right_elbow_joint"]
    a, b = np.array([0.0]), np.array([1.0])
    retract = np.vstack([a, [[0.2]], [[0.4]]])
    approach = np.vstack([[[0.6]], [[0.8]], [b]])

    def clearance(positions):
        if len(positions) == 1:
            return distance_result(floor, positions)
        # Retract slice (3 frames starting at 0.0): collide. Approach OK at floor.
        if len(positions) == 3 and float(positions[0, 0]) == 0.0:
            return distance_result(-0.05, positions, frame=1)
        if len(positions) <= 4:
            return distance_result(floor, positions)
        return distance_result(-0.056, positions)

    plan = plan_transition(
        a, b, names, clearance=clearance,
        via_factory=lambda *args: [], via2_factory=lambda *args: [],
        hub_factory=lambda names: np.array([-0.5]),
        source_retract=retract, target_approach=approach,
        source_retract_frames=(10, 12), target_approach_frames=(0, 2))
    assert plan.status == "FAILED" and plan.method == "retract_approach"
    chosen = plan.attempts[plan.selected_attempt]
    assert chosen["in_slice_collision"] is True
    assert any(h["slice"] == "retract" and h["library_frame"] == 11
               for h in chosen["slice_collisions"])
    assert any("retract slice collision" in r for r in plan.reasons)
    # No RRT attempt is recorded when the slice itself collides.
    assert all(a["kind"] != "rrt" for a in plan.attempts)


def test_plan_sentence_escalation_includes_retract_approach(words, monkeypatch):
    import sign_robot.transitions as transitions
    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))

    def clearance(positions):
        # Endpoints near; every multi-frame path fails relative floor except we
        # still expect retract_approach to be attempted from library slices.
        if len(positions) == 1:
            return distance_result(-0.0008, positions)
        return distance_result(-0.056, positions)

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["escalation_order"][-2] == "source_retract_approach"
    transition, = report["transitions"]
    assert transition["retract_approach_attempted"]
    assert transition["method"] == "retract_approach"
    assert transition["in_slice_collision"]
    assert transition["source_retract_frames"][0] == words["YOU"]["sign_frames"][1]
    assert transition["target_approach_frames"][1] == words["BUY"]["sign_frames"][0]
    assert report["clearance_display_cap_m"] == CLEARANCE_DISPLAY_CAP_M


@pytest.mark.parametrize("dip_at", ["route", "retract", "approach"])
def test_clear_retract_approach_fails_below_worse_endpoint_even_above_two_mm(dip_at):
    path_calls = 0

    def clearance(q):
        nonlocal path_calls
        if len(q) == 1:
            return distance_result(0.008 if q[0, 0] == 0 else 0.012, q)
        path_calls += 1
        if path_calls <= 4:  # Direct, hub route and its two legs.
            return distance_result(-0.01, q)
        kind = {5: "retract", 6: "approach", 7: "route"}[path_calls]
        return distance_result(0.003 if kind == dip_at else 0.008, q, frame=1)

    plan = plan_transition(
        [0.0], [1.0], ["right_elbow_joint"], clearance=clearance,
        via_factory=lambda *args: [], via2_factory=lambda *args: [],
        hub_factory=lambda *args: [-0.5],
        source_retract=[[0.0], [0.2], [0.4]], target_approach=[[0.6], [0.8], [1.0]],
        source_retract_frames=(10, 12), target_approach_frames=(0, 2))
    assert plan.status == "FAILED" and not plan.source_near
    chosen = plan.attempts[plan.selected_attempt]
    assert chosen["kind"] == "retract_approach"
    assert chosen["required_clearance_m"] == 0.008
    assert chosen["in_slice_collision"] == (dip_at != "route")
    assert all(hit["required_clearance_m"] == 0.008 for hit in chosen["slice_collisions"])
    assert all(attempt["required_clearance_m"] == 0.002 for attempt in plan.attempts[:-1])


def test_slice_stop_selects_library_diagnostic_even_when_direct_has_greater_clearance():
    direct = minimum_jerk_blend([0.0], [1.0], ["right_elbow_joint"])

    def clearance(q):
        if len(q) == 1:
            return distance_result(0.008, q)
        return distance_result(-0.01 if np.array_equal(q, direct) else -0.02, q)

    plan = plan_transition(
        [0.0], [1.0], ["right_elbow_joint"], clearance=clearance,
        via_factory=lambda *args: [], via2_factory=lambda *args: [],
        hub_factory=lambda *args: [-0.5],
        source_retract=[[0.0], [0.2], [0.4]], target_approach=[[0.6], [0.8], [1.0]],
        source_retract_frames=(10, 12), target_approach_frames=(0, 2))
    assert plan.status == "FAILED" and plan.method == "retract_approach"
    assert plan.attempts[0]["clearance"]["min_distance_m"] > plan.attempts[-1]["clearance"]["min_distance_m"]
    assert plan.attempts[-1]["in_slice_collision"]


def test_verifier_keeps_failed_when_original_slice_fails_but_retimed_samples_pass(
        words, monkeypatch, tmp_path, evaluation_script):
    import sign_robot.transitions as transitions

    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))
    with np.load(ROOT / words["YOU"]["motion"]) as source:
        retract = source["positions"][words["YOU"]["sign_frames"][1]:].copy()
    # Emulate an older retimer that omitted original slice samples.
    def omitted_slice_route(retract, approach, names):
        q = minimum_jerk_blend(retract[0], approach[-1], names)
        return q, {"bridge_intervals": 0, "raw_frames": len(retract) + len(approach),
                   "timed_frames": len(q)}

    monkeypatch.setattr(transitions, "build_retract_approach_route", omitted_slice_route)
    calls = 0

    def recheck(q):
        return distance_result(-0.01 if np.array_equal(q, retract) else 0.001, q)

    def planning_check(q):
        nonlocal calls
        if len(q) > 1:
            calls += 1
            if calls <= 4:
                return distance_result(-0.056, q)
        return recheck(q)

    motion, report = plan_sentence(["YOU", "BUY"], clearance=planning_check)
    segment, = report["transitions"]
    assert segment["status"] == "FAILED" and segment["in_slice_collision"]
    assert segment["clearance"]["min_distance_m"] == segment["required_clearance_m"] == 0.001
    assert segment["slice_collisions"][0]["distance_m"] == -0.01
    output = tmp_path / "planned.npz"
    np.savez_compressed(output, **motion)
    report["output_npz"] = str(output)
    monkeypatch.setattr(evaluation_script, "MujocoClearance", lambda *args: recheck)
    assert evaluation_script.verify_saved_sentence(report, model=None)["passed"]
    # The same independent slice failure must reject a falsely passing report.
    segment["status"] = "source_near"
    with pytest.raises(AssertionError):
        evaluation_script.verify_saved_sentence(report, model=None)


def test_bilingual_tables_cap_endpoint_route_and_hub_without_changing_raw_json(
        monkeypatch, tmp_path, evaluation_script):
    distance = 0.009500006
    _, report = plan_sentence(["YOU", "BUY"], clearance=lambda q: distance_result(distance, q))
    transition, = report["transitions"]
    transition["attempts"].append({"kind": "hub", "status": "PASS",
                                   "clearance": {"min_distance_m": distance}})
    transition["hub_attempted"] = True
    report.update(baseline={"duration_s": report["duration_s"]}, duration_vs_baseline_s=0.0)
    raw_json = json.dumps(report, sort_keys=True)
    monkeypatch.setattr(evaluation_script, "OUT", tmp_path)
    evaluation_script.write_tables([report])
    for filename in ("report.md", "report.en.md"):
        content = (tmp_path / filename).read_text()
        row, = [line for line in content.splitlines() if "YOU → BUY" in line]
        assert row.count(">=9.5") == 4  # Two endpoints, full route, hub.
        assert "9.500006" not in content
        assert "clearance_capped=true" in content and "JSON" in content
        assert "RRT_PAIRS" in content
        assert "MEDICINE→MORNING" in content and "NURSE→BLOOD-DRAW" in content
        assert "minimum-jerk edges" in content if filename.endswith(".en.md") else "逐边最小跃度" in content
    assert json.dumps(report, sort_keys=True) == raw_json


@pytest.mark.parametrize("minimum_jerk_edges", [False, True])
def test_verifier_rechecks_nurse_rrt_timing_and_preserves_legacy_linear_reports(
        minimum_jerk_edges, monkeypatch, tmp_path, evaluation_script):
    # Mock geometry to isolate saved timing/metadata verification. Actual f80
    # moving-pair clearance is checked separately by the focused smoke run.
    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))

    def search(a, b, names, **kwargs):
        assert kwargs["minimum_jerk_edges"] is True  # Only the new planner dispatch.
        knots = np.stack([a, b])
        q = (transitions.minimum_jerk_rrt_path(knots, names) if minimum_jerk_edges else
             timescale_to_rate_limits(knots, names))
        info = {"rrt_seed": transitions.RRT_SEED, "rrt_budget_s": transitions.RRT_BUDGET_S,
                "rrt_nodes": 2, "rrt_runtime_s": 0.0, "rrt_found": True, "smoothed": False,
                "rrt_outcome": "found", "rrt_path_knots": knots.tolist()}
        if minimum_jerk_edges:
            info.update(rrt_interpolation="minimum_jerk_per_edge", rrt_minimum_duration_s=1.0)
        return transitions.RRTResult(q, clear(q), info)

    monkeypatch.setattr(transitions, "rrt_connect", search)
    model = load_model()
    motion, report = plan_sentence(["NURSE", "BLOOD-DRAW"], model=model,
        clearance=lambda q: distance_result(0.01 if len(q) == 1 else -0.01, q))
    segment, = report["transitions"]
    assert segment["status"] == "PASS" and segment["method"] == "rrt_connect"
    path = tmp_path / "nurse_rrt.npz"
    np.savez_compressed(path, **motion)
    report["output_npz"] = str(path)
    monkeypatch.setattr(evaluation_script, "MujocoClearance", lambda *args: clear)
    assert evaluation_script.verify_saved_sentence(report, model)["passed"]
    chosen = segment["attempts"][segment["selected_attempt"]]
    # Reinterpreting either saved curve with the other timing must fail.
    chosen["rrt_interpolation"] = segment["rrt_interpolation"] = (
        "linear" if minimum_jerk_edges else "minimum_jerk_per_edge")
    chosen["rrt_minimum_duration_s"] = segment["rrt_minimum_duration_s"] = 1.0
    with pytest.raises(AssertionError):
        evaluation_script.verify_saved_sentence(report, model)


def test_group2_handoff_keeps_endpoint_and_adds_both_library_slice_defects(words, monkeypatch):
    import sign_robot.transitions as transitions

    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))
    # This handoff regression is independent of the one-shot search outcome.
    monkeypatch.setattr(transitions, "rrt_connect", lambda *args, **kwargs: transitions.RRTResult(
        None, None, {"rrt_found": False, "rrt_outcome": "timeout"}))
    departure = SOURCE_END_FRAME_OVERRIDES.get("MEDICINE", words["MEDICINE"]["sign_frames"][1])
    with np.load(ROOT / words["MEDICINE"]["motion"]) as source:
        retract = source["positions"][departure:].copy()
    with np.load(ROOT / words["MORNING"]["motion"]) as target:
        approach = target["positions"][:words["MORNING"]["sign_frames"][0] + 1].copy()
    # Inject interior slice defects using valid current-library frame indices.
    retract_hit_index = len(retract) // 2
    retract_hit_frame = departure + retract_hit_index
    approach_hit_frame = len(approach) // 2

    def clearance(q):
        if np.array_equal(q, retract):
            result = distance_result(-0.067599238, q, frame=retract_hit_index)
            result.worst_contact["bodies"] = ["fixed_mount", "left_wrist_yaw_link"]
            return result
        if np.array_equal(q, approach):
            result = distance_result(-0.044832, q, frame=approach_hit_frame)
            result.worst_contact["bodies"] = ["R_thumb_proximal", "left_wrist_yaw_link"]
            return result
        return distance_result(-0.0008 if len(q) == 1 else -0.056, q)

    _, report = plan_sentence(["MEDICINE", "MORNING"], clearance=clearance)
    assert report["status"] == "needs_group2_fix"
    assert report["failed_count"] == report["needs_group2_fix_count"] == 1
    assert report["accepted_count"] == report["source_near_count"] == 0
    handoff = {(item["word"], item["frame"]): item for item in report["source_near_handoff"]}
    assert ("MEDICINE", departure) in handoff
    assert handoff["MEDICINE", retract_hit_frame]["clearance_mm"] == pytest.approx(-67.599238)
    assert handoff["MEDICINE", retract_hit_frame]["bodies"] == ["fixed_mount", "left_wrist_yaw_link"]
    assert handoff["MORNING", approach_hit_frame]["clearance_mm"] == pytest.approx(-44.832)
    assert handoff["MORNING", approach_hit_frame]["bodies"] == ["R_thumb_proximal", "left_wrist_yaw_link"]
    assert "except an in-slice collision" in report["failed_trajectory_policy"]


def test_verifier_keeps_rrt_timeout_diagnostic_as_needs_group2_fix(
        monkeypatch, tmp_path, evaluation_script):
    import sign_robot.transitions as transitions

    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))
    monkeypatch.setattr(transitions, "rrt_connect", lambda *args, **kwargs: transitions.RRTResult(
        None, None, {"rrt_found": False, "rrt_outcome": "timeout", "rrt_seed": 5412,
                     "rrt_budget_s": 120.0, "rrt_nodes": 2, "rrt_runtime_s": 96.0, "smoothed": False}))

    def clearance(q):
        return distance_result(-0.0008 if len(q) == 1 else -0.056, q)

    motion, report = plan_sentence(["MEDICINE", "MORNING"], clearance=clearance)
    output = tmp_path / "rrt_timeout_diagnostic.npz"
    np.savez_compressed(output, **motion)
    report["output_npz"] = str(output)
    segment, = report["transitions"]
    assert segment["status"] == report["status"] == "needs_group2_fix"
    assert report["failed_count"] == report["needs_group2_fix_count"] == 1
    assert report["accepted_count"] == 0
    monkeypatch.setattr(evaluation_script, "MujocoClearance", lambda *args: clearance)
    assert evaluation_script.verify_saved_sentence(report, model=None)["passed"]
    segment["status"] = "source_near"
    with pytest.raises(AssertionError):
        evaluation_script.verify_saved_sentence(report, model=None)
