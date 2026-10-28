"""Rate-limited kinematic sentence transitions; source word clips stay intact.

The first word keeps frame 0 (rise from neutral), the last keeps its return to
neutral, just as stitch_baseline.py does. Interior words use inclusive sign_frames.
This is a geometric preview, not a dynamics controller or an ASL validation.

Clearance escalation is deliberately ordered.  A single-frame endpoint check
comes first; an endpoint whose minimum measured contact distance is strictly
below :data:`ENDPOINT_NEAR_M` is reported as ``source_collision`` and is handed
to the source-motion group without searching for a detour.  ``0.0`` means that
any contacting/penetrating endpoint is near the hard ``-2 mm`` line.  Only when
both endpoints are clear do we try one-via and two-via candidates, followed by
the model's neutral (hub) pose.  ``fixed_mount`` and every other active MuJoCo
geometry remain in these checks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Callable

import numpy as np

from sign_robot.motion import ROOT, apply_frame, load_model, validate_motion

FPS = 30
ARM_RATE_RAD_S = 15.0
FINGER_RATE_RAD_S = 10.0
MIN_LEG_DURATION_S = 0.3
VIA_DISPLACEMENT_M = 0.065
# Robot frame: +X forward (toe geoms), +Y left (shoulder offsets), +Z up.
# Normalize combinations so every wrist target moves 6.5 cm in total.
VIA_DIRECTIONS = (
    ("out", (0, 1, 0)),
    ("up", (0, 0, 1)),
    ("forward", (1, 0, 0)),
    ("out+up", (0, 1, 1)),
    ("out+forward", (1, 1, 0)),
    ("up+forward", (1, 0, 1)),
    ("out+up+forward", (1, 1, 1)),
)
# Follow the task's explicit failure rule, contact.dist < -0.002 m. This is
# a penetration tolerance, NOT a claim of positive 2 mm free-space clearance.
PENETRATION_TOLERANCE_M = 0.002
# Hard fail line remains contact.dist < -PENETRATION_TOLERANCE_M (-2 mm).
# ENDPOINT_NEAR_M: an endpoint min contact.dist strictly below this value is
# source_collision.  With 0.0, this includes both hard-failing endpoints and
# negative contacts inside the permitted 2 mm band; neither triggers a search.
ENDPOINT_NEAR_M = 0.0
HEIGHT_TOLERANCE_M = 1e-7


def joint_rate_limits(joint_names):
    """Video-library rates, including coupled finger joints; other joints are fixed."""
    return np.array([
        FINGER_RATE_RAD_S if str(n).startswith(("L_", "R_")) else
        ARM_RATE_RAD_S if any(p in str(n) for p in ("shoulder", "elbow", "wrist")) else np.inf
        for n in joint_names
    ])


def minimum_jerk_blend(a, b, joint_names):
    """Include both endpoints with at least 0.3 s per min-jerk leg at 30 fps.

    s'(u) peaks at 15/8. Thus ceil(fps * 15/8 * max(|b-a|/rate))
    is the shortest rate-safe integer duration, subject to the 0.3 s floor.
    Never change the rate limits.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape or a.shape != (len(joint_names),):
        raise ValueError("Transition endpoints must match joint_names")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Transition endpoints must be finite")
    intervals = max(int(np.ceil(FPS * MIN_LEG_DURATION_S)),
                    int(np.ceil(FPS * 1.875 * np.max(np.abs(b - a) / joint_rate_limits(joint_names), initial=0))))
    u = np.linspace(0, 1, intervals + 1)[:, None]
    s = 10 * u**3 - 15 * u**4 + 6 * u**5
    q = a + s * (b - a)
    q[0], q[-1] = a, b  # Preserve exact source values, including floating-point bits.
    return q


def same_hand(bodies):
    """Same exclusion as mocap/summarize_library.py: own finger/wrist meshes."""
    sides = {b[0] if b[:2] in ("L_", "R_") else
             "L" if b.startswith("left_wrist") else
             "R" if b.startswith("right_wrist") else None for b in bodies}
    return len(sides) == 1 and None not in sides


@dataclass
class ClearanceResult:
    passed: bool
    min_distance_m: float | None = None
    collisions: list = field(default_factory=list)
    sampled_frames: int = 0
    near_contacts: list = field(default_factory=list)
    worst_contact: dict | None = None


class MujocoClearance:
    """Inspect upstream collision geoms at every transition sample, endpoints too.

    No collision masks/geoms/model limits are changed. Contact distances only
    bound detected contacts; no contacts is reported as None, not a measured gap.
    """

    def __init__(self, model, joint_names):
        import mujoco
        self.model, self.data = model, mujoco.MjData(model)
        self.joint_names = joint_names

    def __call__(self, positions):
        distances, pairs, near_pairs = [], {}, {}
        worst = None
        for frame, row in enumerate(positions):
            apply_frame(self.model, self.data, self.joint_names, row)
            for contact in self.data.contact[:self.data.ncon]:
                bodies = sorted(self.model.body(self.model.geom_bodyid[int(g)]).name for g in contact.geom)
                if same_hand(bodies):
                    continue
                distance = float(contact.dist)
                distances.append(distance)
                location = ("start_endpoint" if frame == 0 else
                            "end_endpoint" if frame == len(positions) - 1 else "interior")
                item = {"bodies": bodies, "distance_m": distance,
                        "frame": frame, "location": location}
                if worst is None or distance < worst["distance_m"]:
                    worst = item
                key = tuple(bodies)
                if distance < ENDPOINT_NEAR_M:
                    if key not in near_pairs or distance < near_pairs[key]["distance_m"]:
                        near_pairs[key] = item
                if distance < -PENETRATION_TOLERANCE_M:
                    if key not in pairs or distance < pairs[key]["distance_m"]:
                        pairs[key] = item
        return ClearanceResult(not pairs, min(distances) if distances else None,
                               list(pairs.values()), len(positions),
                               list(near_pairs.values()), worst)


def neutral_pose(joint_names, model=None):
    """Exact fixed-base model qpos0 for the named scalar trajectory joints.

    This is a routing reference, never an assumption that the hub or its legs
    are collision-free.  All of them must pass the same clearance check.
    """
    model = model if model is not None else load_model()
    addresses = [int(model.joint(str(n)).qposadr[0]) for n in joint_names]
    return model.qpos0[addresses].copy()


def _ik_wrist_offset(solver, reference, joint_names, vector, *, offset_sides=("left", "right")):
    """Solve both arms from a reference, keeping all non-arm joints exact."""
    model = solver.m
    solver.d.qpos[:] = model.qpos0
    apply_frame(model, solver.d, joint_names, reference)
    q = solver.d.qpos.copy()
    addresses = [int(model.joint(str(n)).qposadr[0]) for n in joint_names]
    robot_to_world = solver.d.xmat[model.body("fixed_mount").id].reshape(3, 3).copy()
    sides = ("left", "right")
    vector = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(vector)
    offset = VIA_DISPLACEMENT_M * vector / norm if norm else np.zeros(3)
    goals = {}
    for side in sides:
        delta = (robot_to_world @ (offset * (1, 1 if side == "left" else -1, 1))
                 if side in offset_sides else np.zeros(3))
        wrist = solver.d.xpos[model.body(f"{side}_wrist_yaw_link").id].copy()
        elbow = solver.d.xpos[model.body(f"{side}_elbow_link").id].copy()
        rotation = solver.d.site_xmat[model.site(f"{side}_palm").id].reshape(3, 3).copy()
        goals[side] = (wrist + delta, elbow + delta / 2, rotation)
    previous = {side: q[solver.robot[side]["ids"]].copy() for side in sides}
    solved, _ = solver.solve_arms(q, sides, goals, previous, [])
    via_q = q.copy()
    for side in sides:
        via_q[solver.robot[side]["ids"]] = solved[side]
    return via_q[addresses]


def ik_via_candidates(a, b, joint_names, model=None):
    """Fixed Cartesian wrist directions, each solved from the same midpoint.

    Reuse the bounded arm IK without modifying retarget.py. Palm orientation
    stays near the midpoint; elbows softly follow half the wrist displacement.
    Only arm joints are solved: fingers (including coupled joints) and all other
    coordinates retain the exact convex midpoint of the endpoints.
    """
    from sign_robot.retarget import G1Retargeter

    model = model if model is not None else load_model()
    solver = G1Retargeter(model, [])  # No finger solving/recoupling is needed.
    midpoint = (np.asarray(a) + np.asarray(b)) / 2
    for direction, vector in VIA_DIRECTIONS:
        # Clearance is assessed on the entire emitted path, rather than trusting
        # a penalty on this one IK pose. Every solve uses the same seed.
        yield direction, _ik_wrist_offset(solver, midpoint, joint_names, vector)


def ik_dual_via_candidates(a, b, joint_names, model=None):
    """Two IK knots: endpoint offsets, then neutral-arm retreat + outward.

    The first family offsets source and target wrists in the same seven robot
    directions as via1, retaining their respective fingers/non-arm coordinates.
    The retreat family uses qpos0 arms and one-third interpolated fingers/other
    joints for via1, solved by IK at that reference's wrist/elbow/palm targets.
    Via2 offsets those retreated wrists out, out+up, or out+forward; its non-arm
    coordinates are two-thirds from source to target.  A serialized family
    parks either arm at neutral+out (or +out+up/+out+forward) at both knots;
    the other arm stays at source for via1 and reaches target for via2.  Fingers
    and other non-arm joints still use the one-/two-thirds interpolation.
    No source-word identity affects this set. Every complete path is checked.
    """
    from sign_robot.retarget import G1Retargeter

    model = model if model is not None else load_model()
    solver = G1Retargeter(model, [])
    a, b = np.asarray(a), np.asarray(b)
    for direction, vector in VIA_DIRECTIONS:
        yield [direction, direction], [
            _ik_wrist_offset(solver, a, joint_names, vector),
            _ik_wrist_offset(solver, b, joint_names, vector),
        ]
    arm = np.array([any(p in str(n) for p in ("shoulder", "elbow", "wrist"))
                    for n in joint_names])
    neutral = neutral_pose(joint_names, model)
    retreat = a + (b - a) / 3
    retreat[arm] = neutral[arm]
    first = _ik_wrist_offset(solver, retreat, joint_names, (0, 0, 0))
    outward = first.copy()
    outward[~arm] = (a + 2 * (b - a) / 3)[~arm]
    for direction, vector in VIA_DIRECTIONS:
        if direction in ("out", "out+up", "out+forward"):
            yield ["neutral_retreat", direction], [
                first.copy(), _ik_wrist_offset(solver, outward, joint_names, vector),
            ]
    # A single neutral hub can still leave the other hand sweeping through a
    # stationary wrist.  These fixed, symmetric families park one arm at a
    # time with an outward wrist offset while the other arm changes pose.
    # They are general geometry candidates, not word-specific exceptions.
    for parked_side in ("left", "right"):
        parked = arm & np.array([str(n).startswith(parked_side + "_") for n in joint_names])
        first_reference, second_reference = a.copy(), b.copy()
        first_reference[~arm] = (a + (b - a) / 3)[~arm]
        second_reference[~arm] = (a + 2 * (b - a) / 3)[~arm]
        first_reference[parked] = neutral[parked]
        second_reference[parked] = neutral[parked]
        for direction, vector in VIA_DIRECTIONS:
            if direction not in ("out", "out+up", "out+forward"):
                continue
            first = _ik_wrist_offset(solver, first_reference, joint_names, vector,
                                     offset_sides=(parked_side,))
            second = _ik_wrist_offset(solver, second_reference, joint_names, vector,
                                      offset_sides=(parked_side,))
            yield [f"neutral_retreat_{parked_side}+{direction}",
                   f"hold_{parked_side}+{direction}"], [first, second]


def body_heights(model, joint_names, positions, bodies):
    """World z in metres; kinematic replay, never stepping dynamics."""
    import mujoco
    data = mujoco.MjData(model)
    ids = [model.body(n).id for n in bodies]
    out = []
    for row in positions:
        apply_frame(model, data, joint_names, row)
        out.append(data.xpos[ids, 2].copy())
    return np.asarray(out)


def wrist_height_check(model, joint_names, positions):
    """Detect new wrist undershoot below the lower endpoint, independent of gloss.

    This cannot repair the descent already present inside a source word while
    retaining its sign_frames endpoint. Report that source descent separately.
    """
    z = body_heights(model, joint_names, positions,
                     ("left_wrist_yaw_link", "right_wrist_yaw_link"))
    dips = np.maximum(0, np.minimum(z[0], z[-1]) - z.min(axis=0))
    return {"passed": bool(np.all(dips <= HEIGHT_TOLERANCE_M)),
            "left_wrist_undershoot_m": float(dips[0]),
            "right_wrist_undershoot_m": float(dips[1])}


def _clearance_reasons(result, endpoint_floor=None):
    if endpoint_floor is not None:
        return [f"minimum contact distance {result.min_distance_m} m worsens "
                f"source endpoint minimum {endpoint_floor} m"] + [
            f"{' | '.join(c['bodies'])}, distance_m={c['distance_m']}, "
            f"sample {c['frame']} ({c.get('location', 'unspecified')})"
            for c in result.collisions if c["distance_m"] < endpoint_floor]
    if result.passed:
        return []
    if result.collisions:
        return [f"penetration {-c['distance_m'] * 1000:.3f} mm > 2 mm: "
                f"{' | '.join(c['bodies'])}, sample {c['frame']} "
                f"({c.get('location', 'unspecified')})" for c in result.collisions]
    return [f"clearance failed (minimum contact distance {result.min_distance_m} m)"]


@dataclass
class TransitionPlan:
    positions: np.ndarray
    status: str
    used_via: bool
    attempts: list
    reasons: list
    warnings: list = field(default_factory=list)
    via_direction: str | None = None
    selected_attempt: int = 0
    endpoint_clearance: list = field(default_factory=list)
    endpoint_floor_m: float | None = None
    method: str = "direct"
    via_directions: list = field(default_factory=list)


def plan_transition(a, b, joint_names, *, clearance: Callable,
                    via_factory=None, via2_factory=None, hub_factory=None,
                    height_check=None, model=None):
    """Endpoint gate, direct quintic, best via1/via2, then qpos0 hub fallback.

    Endpoint-near paths stop as source_collision, without a detour search. Their
    direct samples are diagnostic only, even if they worsen an inherited hard
    penetration; the old relative floor is retained as an explicit diagnostic.
    Clear endpoints use the absolute 2 mm rule on every complete candidate.
    All passing one-/two-via candidates compete on minimum contact distance.
    Hub clearance is checked on both legs as well as the complete path. A failed
    candidate is retained for diagnosis with its worst pair, never for execution.
    """
    direct = minimum_jerk_blend(a, b, joint_names)
    endpoints = [asdict(clearance(direct[[i]])) for i in (0, -1)]
    endpoint_min = min((r["min_distance_m"] for r in endpoints
                        if r["min_distance_m"] is not None), default=None)
    endpoint_floor = (endpoint_min if endpoint_min is not None and
                      endpoint_min < -PENETRATION_TOLERANCE_M else None)
    endpoint_near = endpoint_min is not None and endpoint_min < ENDPOINT_NEAR_M
    attempts = []

    def assess(q, kind, leg_intervals, directions=(), legs=()):
        result = clearance(q)
        leg_clearance = [asdict(clearance(leg)) for leg in legs]
        height = height_check(q) if height_check else {"passed": True}
        relative_ok = (None if endpoint_floor is None else
                       result.min_distance_m is not None and result.min_distance_m >= endpoint_floor)
        if endpoint_near:
            status = "source_collision"
        else:
            status = "PASS" if result.passed and all(r["passed"] for r in leg_clearance) else "FAILED"
        reasons = _clearance_reasons(result) if status == "FAILED" else []
        worst = result.worst_contact or min(result.collisions, key=lambda c: c["distance_m"], default=None)
        directions = list(directions)
        attempts.append({"kind": kind, "method": kind,
                         "via_direction": directions[0] if kind == "via1" else None,
                         "via_directions": directions, "intervals": len(q) - 1,
                         "leg_intervals": leg_intervals,
                         "leg_clearance": leg_clearance,
                         "relative_floor_passed": relative_ok,
                         "clearance": asdict(result), "height": height,
                         "worst_collision": worst, "status": status, "reasons": reasons})
        return len(attempts) - 1, q

    def through(knots, kind, directions=(), check_legs=False):
        legs = [minimum_jerk_blend(left, right, joint_names)
                for left, right in zip(knots, knots[1:])]
        q = np.vstack([legs[0]] + [leg[1:] for leg in legs[1:]])
        return assess(q, kind, [len(leg) - 1 for leg in legs], directions,
                      legs if check_legs else ())

    def finish(choice, warnings=None):
        index, q = choice
        attempt = attempts[index]
        if warnings is None:
            warnings = ([] if attempt["height"]["passed"] else
                        ["wrist undershoot remains; collision status reported separately"])
        return TransitionPlan(
            positions=q, status=attempt["status"],
            used_via=attempt["kind"] in ("via1", "via2", "hub"),
            attempts=attempts, reasons=attempt["reasons"], warnings=warnings,
            via_direction=attempt["via_direction"], selected_attempt=index,
            endpoint_clearance=endpoints, endpoint_floor_m=endpoint_floor,
            method="FAILED" if attempt["status"] == "FAILED" else attempt["kind"],
            via_directions=attempt["via_directions"])

    def score(choice):
        distance = attempts[choice[0]]["clearance"]["min_distance_m"]
        # No detected contacts outranks detected contacts; None stays None in
        # reports, since this is not a measured positive free-space distance.
        return np.inf if distance is None else distance

    if endpoint_near:
        choice = assess(direct, "source_collision", [len(direct) - 1])
        warnings = [f"source endpoint minimum {endpoint_min} m is below ENDPOINT_NEAR_M "
                    f"({ENDPOINT_NEAR_M} m); no detour searched; direct samples are diagnostic only"]
        if attempts[0]["relative_floor_passed"] is False:
            warnings.extend(_clearance_reasons(
                ClearanceResult(**attempts[0]["clearance"]), endpoint_floor))
        return finish(choice, warnings)

    direct_choice = assess(direct, "direct", [len(direct) - 1])
    direct_ok = attempts[0]["status"] == "PASS"
    if direct_ok and attempts[0]["height"]["passed"]:
        return finish(direct_choice)
    candidates = []
    singles = (via_factory(a, b, joint_names) if via_factory is not None else
               ik_via_candidates(a, b, joint_names, model))
    for direction, via in singles:
        candidates.append(through([a, via, b], "via1", [direction]))
    duals = (via2_factory(a, b, joint_names) if via2_factory is not None else
             ik_dual_via_candidates(a, b, joint_names, model))
    for directions, vias in duals:
        if len(vias) != 2 or len(directions) != 2:
            raise ValueError("A via2 candidate must have exactly two knots and direction names")
        candidates.append(through([a, *vias, b], "via2", directions))
    passing = [c for c in candidates if attempts[c[0]]["status"] == "PASS"]
    if direct_ok:
        # A sag-only search may replace an accepted direct path only when it
        # also removes the undershoot. Never exchange clearance for appearance.
        passing = [c for c in passing if attempts[c[0]]["height"]["passed"]]
        if not passing:
            return finish(direct_choice, ["wrist undershoot retained: no via passed both height and collision checks"])
    if passing:
        return finish(max(passing, key=score))
    hub = hub_factory(joint_names) if hub_factory is not None else neutral_pose(joint_names, model)
    hub_choice = through([a, hub, b], "hub", check_legs=True)
    if attempts[hub_choice[0]]["status"] == "PASS":
        return finish(hub_choice)
    return finish(max([direct_choice, *candidates, hub_choice], key=score))


def lookup_words(root=ROOT):
    """Same precedence/readiness rules as mocap/stitch_baseline.py."""
    root, words = Path(root), {}
    hospital = root / "motions/hospital_v1_motions.json"
    if hospital.exists():
        words.update({w["gloss"]: w for w in json.loads(hospital.read_text())["glosses"] if w["motion_ready"]})
    for library in ("studio_galt_v1", "wlasl_video_v1"):
        path = root / "motions" / library / "index.json"
        if path.exists():
            for w in json.loads(path.read_text())["words"]:
                if w["robot_status"] != "poor":
                    words.setdefault(w["gloss"], w)
    return words


def peak_rates(positions, joint_names):
    rates = np.abs(np.diff(positions, axis=0)) * FPS
    names = [str(n) for n in joint_names]
    arm = [i for i, n in enumerate(names) if any(p in n for p in ("shoulder", "elbow", "wrist"))]
    finger = [i for i, n in enumerate(names) if n.startswith(("L_", "R_"))]
    return {"arm_rad_s": float(rates[:, arm].max(initial=0)),
            "finger_rad_s": float(rates[:, finger].max(initial=0))}


def plan_sentence(glosses, *, root=ROOT, model=None, clearance=None):
    """Return the baseline-compatible motion and a separate, explicit status report.

    Source words are not retimed or edited. Rate/collision promises apply only to
    the inserted transitions, including their boundary samples, not to word cores.
    """
    glosses = [g.upper() for g in glosses]
    if not glosses:
        raise ValueError("At least one gloss is required")
    root, words = Path(root), lookup_words(root)
    unknown = [g for g in glosses if g not in words]
    if unknown:
        raise ValueError(f"Not in the library: {unknown}")
    clips, names = [], None
    for gloss in glosses:
        with np.load(root / words[gloss]["motion"], allow_pickle=False) as data:
            clip = {k: data[k].copy() for k in ("timestamps_s", "joint_names", "positions")}
        validate_motion(clip)
        if not np.allclose(np.diff(clip["timestamps_s"]), 1 / FPS):
            raise ValueError(f"{gloss}: expected 30 fps")
        if names is None:
            names = clip["joint_names"]
        elif not np.array_equal(names, clip["joint_names"]):
            raise ValueError(f"{gloss}: inconsistent joint_names")
        s0, s1 = words[gloss]["sign_frames"]
        if not 0 <= s0 <= s1 < len(clip["positions"]):
            raise ValueError(f"{gloss}: invalid sign_frames")
        clips.append(clip["positions"])
    if clearance is None:
        model = model if model is not None else load_model(root)
        clearance = MujocoClearance(model, names)
    height_check = (lambda q: wrist_height_check(model, names, q)) if model is not None else None
    pieces, transitions, segments, handoff, count = [], [], [], [], 0
    for k, (gloss, q) in enumerate(zip(glosses, clips)):
        s0, s1 = words[gloss]["sign_frames"]
        # Deliberately keep baseline first-word rise and last-word return.
        start = 0 if k == 0 else s0
        end = len(q) - 1 if k == len(glosses) - 1 else s1
        if k:
            plan = plan_transition(pieces[-1][-1], q[start], names, clearance=clearance,
                                   height_check=height_check, model=model)
            chosen = plan.attempts[plan.selected_attempt]
            source_frames = (words[glosses[k - 1]]["sign_frames"][1], s0)
            for word, source_frame, result in zip((glosses[k - 1], gloss), source_frames,
                                                   plan.endpoint_clearance):
                # Near contacts can pass the absolute -2 mm check, so the old
                # hard-collision list alone cannot supply the Group 2 handoff.
                contacts = result["near_contacts"] or result["collisions"]
                for collision in contacts:
                    if collision["distance_m"] >= ENDPOINT_NEAR_M:
                        continue
                    item = {"word": word, "frame": source_frame, "bodies": collision["bodies"],
                            "distance_m": collision["distance_m"],
                            "clearance_mm": collision["distance_m"] * 1000}
                    if item not in handoff:
                        handoff.append(item)
            transitions.append({"from_gloss": glosses[k - 1], "to_gloss": gloss,
                                "start_frame": count - 1,
                                "end_frame": count + len(plan.positions) - 2,
                                "source_start_frame": words[glosses[k - 1]]["sign_frames"][1],
                                "target_start_frame": s0,
                                "intervals": len(plan.positions) - 1,
                                "duration_s": (len(plan.positions) - 1) / FPS,
                                "status": plan.status, "used_via": plan.used_via,
                                "method": plan.method,
                                "via_direction": plan.via_direction,
                                "via_directions": plan.via_directions,
                                "selected_attempt": plan.selected_attempt,
                                "clearance": chosen["clearance"],
                                "min_clearance_mm": (None if chosen["clearance"]["min_distance_m"] is None else
                                                     chosen["clearance"]["min_distance_m"] * 1000),
                                "worst_collision": chosen["worst_collision"],
                                "endpoint_clearance": plan.endpoint_clearance,
                                "endpoint_floor_m": plan.endpoint_floor_m,
                                "relative_floor_passed": chosen["relative_floor_passed"],
                                "reasons": plan.reasons, "warnings": plan.warnings,
                                "attempts": plan.attempts,
                                "peak_rates": peak_rates(plan.positions, names)})
            pieces.append(plan.positions[1:-1])
            count += len(plan.positions) - 2
        segment = q[start:end + 1]
        segments.append({"gloss": gloss, "motion": words[gloss]["motion"],
                         "source_start_frame": start, "source_end_frame": end,
                         "start_frame": count, "end_frame": count + len(segment) - 1})
        pieces.append(segment)
        count += len(segment)
    q = np.vstack(pieces)
    motion = {"timestamps_s": np.arange(len(q)) / FPS, "joint_names": names, "positions": q}
    validate_motion(motion)
    failed = sum(t["status"] == "FAILED" for t in transitions)
    source_collisions = sum(t["status"] == "source_collision" for t in transitions)
    passed = sum(t["status"] == "PASS" for t in transitions)
    report = {"glosses": glosses, "fps": FPS, "frames": len(q),
              "duration_s": len(q) / FPS, "last_timestamp_s": (len(q) - 1) / FPS,
              "transition_count": len(transitions), "pass_count": passed,
              "source_collision_count": source_collisions, "accepted_count": passed + source_collisions,
              "failed_count": failed,
              "status": "FAILED" if failed else "source_collision" if source_collisions else "PASS",
              "rate_limits_rad_s": {"arm": ARM_RATE_RAD_S, "finger": FINGER_RATE_RAD_S},
              "minimum_leg_duration_s": MIN_LEG_DURATION_S,
              "collision_failure_below_m": -PENETRATION_TOLERANCE_M,
              "endpoint_near_below_m": ENDPOINT_NEAR_M,
              "collision_threshold_note": "explicit task rule: fail below -2 mm, not a positive 2 mm separation guarantee",
              "source_collision_rule": "first gate: either single-frame endpoint minimum below ENDPOINT_NEAR_M; no via/hub search; emitted direct samples are diagnostic only, not a clearance pass",
              "relative_floor_rule": "for endpoints below -2 mm, retain endpoint_floor_m and relative_floor_passed as diagnostics; the first gate still stops search",
              "escalation_order": ["endpoint_near", "direct", "best_via1_or_via2", "hub", "FAILED"],
              "neutral_hub_source": "fixed-base model qpos0 for named trajectory joints; never assumed clear",
              "clearance_scope": "all transition samples including endpoints; upstream geoms; same-hand adjacency excluded",
              "sentence_peak_rates": peak_rates(q, names),
              "failed_trajectory_policy": "emit least-penetrating checked candidate for diagnostic replay; source_collision and FAILED are not certified for execution",
              "source_collision_handoff": handoff,
              "word_segments": segments, "transitions": transitions}
    return motion, report
