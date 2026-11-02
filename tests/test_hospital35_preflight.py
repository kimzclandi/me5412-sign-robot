"""Per-word preflight: injected core defects are attributed to the protected source, never passed."""
import copy
import json
import dataclasses
import importlib.util

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import load_policy
from sign_robot.pair_routes import build_pair_context_v2

SPEC = importlib.util.spec_from_file_location("preflight_hospital35", ROOT / "scripts/preflight_hospital35.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)

POLICY = ROOT / "config/transition_policy_user_protected_hospital35_v1.json"


@pytest.fixture(scope="module")
def context():
    result = build_pair_context_v2(ROOT, load_policy(POLICY, supported_versions=(2,)))
    assert not result.input_blockers and len(result.approvals) == 35
    return result


def _clip_with(context, gloss, change):
    clip = {key: np.array(value, copy=True) for key, value in context.clips[gloss].items()}
    change(clip, context)
    return clip


def _column(clip, fragment):
    return next(i for i, n in enumerate(clip["joint_names"]) if fragment in str(n))


def _margin_frame(context, clip, column, core, amount):
    joint = context.model.joint(str(clip["joint_names"][column]))
    low, high = joint.range
    frames = [f for f in range(core[0] + 3, core[1] - 3) if low + abs(amount) < clip["positions"][f, column] < high - abs(amount)]
    assert frames, "need a frame with room for the injected change"
    return frames[0]


def test_clear_word_has_complete_core_and_both_endpoint_roles(context):
    core = preflight.audit_core(context, "COME")
    assert core["complete"] and core["status"] == "CORE_CLEAR" and not core["defects"]
    assert core["geometry"]["passed"] and core["geometry"]["samples"] > 0
    endpoints = preflight.endpoint_roles(context, "NOW")
    assert endpoints["complete"]
    assert endpoints["roles"]["source"]["window_frames"] == [51, 103]
    assert endpoints["roles"]["target"]["window_frames"] == [0, 27]
    assert all(endpoints["roles"][r]["valid_count"] > 0 for r in ("source", "target"))
    assert preflight.classify(core, endpoints) == ["PREFLIGHT_CLEAR"]


def test_injected_limit_coupling_and_speed_defects_gate_the_core(context):
    core = context.approvals["COME"].protected_core_frames

    def over_limit(clip, ctx):
        column = _column(clip, "right_elbow")
        clip["positions"][core[0] + 10, column] = ctx.model.joint(str(clip["joint_names"][column])).range[1] + 0.05

    def coupled(clip, ctx):
        child = ctx.library["couplings"][0]["child"]
        clip["positions"][core[0] + 10, list(map(str, clip["joint_names"])).index(child)] += 0.01

    def fast(clip, ctx):
        column = _column(clip, "right_shoulder_pitch")
        frame = _margin_frame(ctx, clip, column, core, 0.6)
        clip["positions"][frame, column] += 0.6

    for change, metric in ((over_limit, "joint_limit_error"), (coupled, "coupling_error"), (fast, "speed_ratio")):
        row = preflight.audit_core(context, "COME", _clip_with(context, "COME", change))
        assert row["complete"] and row["status"] == "CORE_SOURCE_DEFECT", metric
        assert metric in {d["metric"] for d in row["defects"]}


def test_acceleration_and_jerk_inside_core_stay_informational(context):
    core = context.approvals["COME"].protected_core_frames

    def kink(clip, ctx):
        # 0.35 rad on one quiet frame: about 10.5 rad/s, 157 rad/s^2 and 3.5e3 rad/s^3.
        column = _column(clip, "right_shoulder_pitch")
        q = clip["positions"][:, column]
        low, high = ctx.model.joint(str(clip["joint_names"][column])).range
        frames = [f for f in range(core[0] + 4, core[1] - 4) if low + 0.4 < q[f] < high - 0.4]
        frame = min(frames, key=lambda f: abs(q[f + 1] - q[f]) + abs(q[f] - q[f - 1]))
        clip["positions"][frame, column] += 0.35

    row = preflight.audit_core(context, "COME", _clip_with(context, "COME", kink))
    assert {d["metric"] for d in row["informational_defects"]} >= {"peak_acceleration_rad_s2", "peak_jerk_rad_s3"}
    assert not any(d["metric"] in ("peak_acceleration_rad_s2", "peak_jerk_rad_s3") for d in row["defects"])
    assert "speed_ratio" not in {d["metric"] for d in row["defects"]}


def test_sampled_core_collision_is_attributed_with_its_source_frame(context):
    real = context.clearance

    class Measured:
        def __init__(self, batch):
            self.sampled_frames = len(batch)
            self.frame_clearances_m = np.full(len(batch), 0.05)
            self.frame_clearances_m[len(batch) // 2] = -0.004
            self.min_distance_m = float(self.frame_clearances_m.min())
            self.worst_contact = {"bodies": ["left_wrist_pitch_link", "torso_link"], "frame": len(batch) // 2}

    stubbed = dataclasses.replace(context, clearance=lambda batch: Measured(batch))
    row = preflight.audit_core(stubbed, "COME")
    assert row["status"] == "CORE_SOURCE_DEFECT" and row["geometry"]["passed"] is False
    defect = next(d for d in row["defects"] if d["metric"] == "sampled_core_clearance_mm")
    core = context.approvals["COME"].protected_core_frames
    assert core[0] <= defect["source_frame"] <= core[1] and defect["origin"] == "protected_source_clip"
    assert context.clearance is real


def test_exhausted_budget_is_incomplete_not_clear(context):
    policy = copy.deepcopy(context.policy)
    policy["validation"]["max_sampled_poses"] = 8
    row = preflight.audit_core(dataclasses.replace(context, policy=policy), "COME")
    assert row["complete"] is False and row["status"] == "INCOMPLETE"
    endpoints = preflight.endpoint_roles(context, "COME")
    assert preflight.classify(row, endpoints) == ["INCOMPLETE"]


def test_predicted_pair_impacts_keep_the_full_denominator():
    glosses = ["A", "B", "C", "D"]
    rows = {"A": {"labels": ["CORE_SOURCE_DEFECT"]}, "B": {"labels": ["NO_EXIT_ENDPOINT"]},
            "C": {"labels": ["NO_ENTRY_ENDPOINT"]}, "D": {"labels": ["PREFLIGHT_CLEAR"]}}
    impacts = preflight.affected_pairs(glosses, rows)
    assert impacts["core_source_defect"]["count"] == 2 * 4 - 1
    assert impacts["no_exit_endpoint"]["count"] == 4 and impacts["no_entry_endpoint"]["count"] == 4
    assert impacts["denominator"] == 16
    assert impacts["any"]["count"] + impacts["unaffected_count"] == 16
    assert set(impacts["any"]["pair_ids"]) == (set(impacts["core_source_defect"]["pair_ids"])
                                               | set(impacts["no_exit_endpoint"]["pair_ids"])
                                               | set(impacts["no_entry_endpoint"]["pair_ids"]))
    assert "D__D" not in impacts["any"]["pair_ids"]


def test_global_input_blocker_is_reported_without_shrinking_scope(tmp_path):
    policy = load_policy(POLICY, supported_versions=(2,))
    policy["endpoints"]["protection_bundle_sha256"] = "0" * 64
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy))
    result = preflight.preflight(ROOT, path)
    assert result["status"] == "GLOBAL_INPUT_BLOCKED" and result["words"] == {}
    assert result["global_input_blockers"]
