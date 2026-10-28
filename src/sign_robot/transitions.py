"""Rate-limited kinematic sentence transitions; source word clips stay intact.

The first word keeps frame 0 (rise from neutral), the last keeps its return to
neutral, just as stitch_baseline.py does. Interior words use inclusive sign_frames.
This is a geometric preview, not a dynamics controller or an ASL validation.

Signed clearance is positive for separation and negative for penetration.
Normal paths require at least 2 mm; paths with either endpoint strictly below
2 mm must never worsen the smaller endpoint clearance. Both use the same
direct, via1, via2, neutral-hub, then source retract/approach escalation.
A passing near-source path is labelled ``source_near`` and handed to the
source-motion group. These gates use only pairs whose relative pose can change
under library/planner joints. Static pairs remain measured separately as vendor
structural gaps; no body is removed. Separations at or above 9.5 mm are reported
as ``>=9.5`` (``clearance_capped``) so the adjacent-link mesh floor is never
mistaken for a precise query certification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
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
# Signed distance: positive separation, negative penetration. Normal paths
# require distance >= this unchanged physical 2 mm threshold.
PENETRATION_TOLERANCE_M = 0.002
# Either endpoint strictly below 2 mm uses the relative endpoint floor and
# remains on the Group 2 source_near handoff, including positive gaps < 2 mm.
ENDPOINT_NEAR_M = 0.002
CLEARANCE_DETECTION_MARGIN_M = 0.25
HEIGHT_TOLERANCE_M = 1e-7
MOVING_JOINT_TOL_RAD = 1e-9
MOTION_LIBRARY_PATH = ROOT / "motions/hospital_v1_motions.json"
# Adjacent arm-link meshes (e.g. elbow↔wrist_pitch) sit ~9.500 mm apart. That
# value is a true mj_geomDistance result (distmax=1.0 still returns ~9.50015 mm),
# not a MuJoCo distmax clip. Report separations at/above this floor as >=9.5.
CLEARANCE_DISPLAY_CAP_M = 0.0095
CLEARANCE_CAP_TOL_M = 1e-9
POSE_MATCH_TOL_RAD = 1e-9


@lru_cache(maxsize=8)
def _library_joint_ranges(library_path):
    """Full-frame joint extrema, shared across clearance objects in one run."""
    path = Path(library_path)
    root = path.parent.parent
    lower, upper, frames, paths = {}, {}, 0, []
    for word in json.loads(path.read_text())["glosses"]:
        if not word["motion_ready"]:
            continue
        with np.load(root / word["motion"], allow_pickle=False) as source:
            motion = {key: source[key] for key in ("timestamps_s", "joint_names", "positions")}
            validate_motion(motion)
            for name, lo, hi in zip(motion["joint_names"], motion["positions"].min(axis=0),
                                    motion["positions"].max(axis=0)):
                name = str(name)
                lower[name] = min(lower.get(name, float(lo)), float(lo))
                upper[name] = max(upper.get(name, float(hi)), float(hi))
            frames += len(motion["positions"])
        paths.append(word["motion"])
    if not paths:
        raise ValueError("Moving-joint derivation requires a nonempty motion library")
    return lower, upper, frames, tuple(paths)


def moving_ancestor_joint_ids(model, moving_joint_ids):
    """Moving joints on each body's path to world, including its own joints."""
    ancestors = []
    for body in range(model.nbody):
        joints, current = set(), body
        while current:
            start = int(model.body_jntadr[current])
            joints.update(joint for joint in range(start, start + int(model.body_jntnum[current]))
                          if joint in moving_joint_ids)
            current = int(model.body_parentid[current])
        ancestors.append(frozenset(joints))
    return tuple(ancestors)


def derive_static_body_pairs(model, moving_joint_ids):
    """Equal moving-ancestor sets mean no moving joint on the body-to-body path.

    This is a topology computation, independent of anatomical/body/geom names.
    Native MuJoCo eligibility and same-hand exclusions are applied when measuring.
    """
    ancestors = moving_ancestor_joint_ids(model, moving_joint_ids)
    return frozenset((a, b) for a in range(model.nbody) for b in range(a + 1, model.nbody)
                     if ancestors[a] == ancestors[b])


def joint_rate_limits(joint_names):
    """Video-library rates, including coupled finger joints; other joints are fixed."""
    return np.array([
        FINGER_RATE_RAD_S if str(n).startswith(("L_", "R_")) else
        ARM_RATE_RAD_S if any(p in str(n) for p in ("shoulder", "elbow", "wrist")) else np.inf
        for n in joint_names
    ])



def clearance_is_capped(distance_m):
    """True when a moving-pair separation is at/above the 9.5 mm display floor."""
    return float(distance_m) >= CLEARANCE_DISPLAY_CAP_M - CLEARANCE_CAP_TOL_M


def format_clearance_mm(distance_m):
    """Human clearance: exact mm, or >=9.5 when at/above the display floor."""
    distance_m = float(distance_m)
    if clearance_is_capped(distance_m):
        return ">=9.5"
    return f"{distance_m * 1000:.6f}"


def annotate_clearance_dict(result_dict):
    """Attach clearance_capped / clearance_mm_display without dropping numerics."""
    distance = float(result_dict["min_distance_m"])
    capped = clearance_is_capped(distance)
    result_dict = dict(result_dict)
    result_dict["clearance_capped"] = capped
    result_dict["clearance_mm_display"] = format_clearance_mm(distance)
    return result_dict


def timescale_to_rate_limits(positions, joint_names):
    """Linearly stretch a path for rate limits and the 0.3 s minimum duration."""
    q = np.asarray(positions, dtype=float)
    if len(q) < 2:
        return q.copy()
    limits = joint_rate_limits(joint_names)
    delta = np.abs(np.diff(q, axis=0))
    with np.errstate(divide="ignore", invalid="ignore"):
        need = delta * FPS / limits
    need = np.where(np.isfinite(need), need, 0.0)
    scale = float(need.max(initial=0.0))
    min_intervals = int(np.ceil(FPS * MIN_LEG_DURATION_S))
    target = max(len(q) - 1, min_intervals)
    if scale > 1.0 + 1e-12:
        target = max(target, int(np.ceil((len(q) - 1) * scale)))
    if target == len(q) - 1:
        out = q.copy()
        out[0], out[-1] = q[0], q[-1]
        return out
    u_old = np.linspace(0.0, 1.0, len(q))
    u_new = np.linspace(0.0, 1.0, target + 1)
    out = np.empty((target + 1, q.shape[1]), dtype=float)
    for col in range(q.shape[1]):
        out[:, col] = np.interp(u_new, u_old, q[:, col])
    out[0], out[-1] = q[0], q[-1]
    return out


def build_retract_approach_route(retract, approach, joint_names):
    """Concat source retract + optional min-jerk bridge + target approach."""
    retract = np.asarray(retract, dtype=float)
    approach = np.asarray(approach, dtype=float)
    if len(retract) < 1 or len(approach) < 1:
        raise ValueError("retract and approach slices must be nonempty")
    bridge = None
    if np.max(np.abs(retract[-1] - approach[0])) > POSE_MATCH_TOL_RAD:
        bridge = minimum_jerk_blend(retract[-1], approach[0], joint_names)
        pieces = [retract, bridge[1:-1], approach]
    else:
        pieces = [retract, approach[1:]]
    raw = np.vstack([p for p in pieces if len(p)])
    timed = timescale_to_rate_limits(raw, joint_names)
    timed[0], timed[-1] = retract[0], approach[-1]
    info = {
        "bridge_intervals": 0 if bridge is None else len(bridge) - 1,
        "raw_frames": int(len(raw)),
        "timed_frames": int(len(timed)),
    }
    return timed, info


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
    min_distance_m: float
    collisions: list = field(default_factory=list)
    sampled_frames: int = 0
    near_contacts: list = field(default_factory=list)
    worst_contact: dict | None = None
    vendor_structural_gaps: list = field(default_factory=list)


class MujocoClearance:
    """Inspect upstream collision geoms at every transition sample, endpoints too.

    Temporarily expand geom/explicit-pair detection margins for mj_collision,
    starting at 2 mm and growing through 25 cm if needed, then restore them in
    a finally block. Once an eligible moving pair is detected, any omitted pair is
    farther than the detection margin and cannot lower the minimum. Native pair
    filtering and the existing same-hand rule stay intact. contact.dist is a
    signed surface distance, not the margin-adjusted constraint distance. Thus
    even separated poses have a numeric minimum and closest body/geom pair.
    Static pairs are derived from full-library joint spans plus planner IK and
    measured once across the scene, since their relative poses are invariant. Their
    vendor gap records never enter the 2 mm/endpoint-relative gates. Models with
    no eligible moving pair, or empty trajectories, raise ValueError.
    """

    def __init__(self, model, joint_names, *, library_path=MOTION_LIBRARY_PATH):
        import mujoco
        from sign_robot.retarget import ARM_SUFFIXES

        self.model, self.data = model, mujoco.MjData(model)
        self.joint_names = joint_names
        library_path = Path(library_path).resolve()
        lower, upper, frames, paths = _library_joint_ranges(library_path)
        # Include the exact arm-joint contract used by G1Retargeter, even if a
        # future small library happens not to exercise one of its IK joints.
        ik_names = {f"{side}_{suffix}" for side in ("left", "right") for suffix in ARM_SUFFIXES}
        # Unknown joints stay conservatively moving rather than being silently
        # exempted by a library that contains no evidence about them.
        self.moving_joint_ids = frozenset(
            joint for joint in range(model.njnt)
            if (name := model.joint(joint).name) not in lower or name in ik_names
            or upper[name] - lower[name] > MOVING_JOINT_TOL_RAD)
        self.moving_ancestor_joint_ids = moving_ancestor_joint_ids(model, self.moving_joint_ids)
        self.static_body_pairs = derive_static_body_pairs(model, self.moving_joint_ids)
        self.derivation = {
            "library_path": str(library_path.relative_to(ROOT) if library_path.is_relative_to(ROOT) else library_path),
            "library_motion_paths": list(paths), "library_words": len(paths), "library_frames": frames,
            "joint_span_tolerance_rad": MOVING_JOINT_TOL_RAD,
            "moving_joint_names": [model.joint(j).name for j in sorted(self.moving_joint_ids)],
            "static_body_pair_count": len(self.static_body_pairs),
            "static_rule": "equal moving ancestor joint ID sets; no moving joint on the body-to-body path",
            "vendor_measurement": "scene-spanning native mj_collision eligibility, then mj_geomDistance per static geom pair",
        }
        # Library-constant joints are evaluated at their constant values. The
        # current robot's legs/waist equal qpos0, also used by the neutral hub.
        self._constant_columns = []
        self._constant_values = []
        for column, name in enumerate(joint_names):
            name = str(name)
            joint = model.joint(name)
            if joint.id not in self.moving_joint_ids:
                self.data.qpos[int(joint.qposadr[0])] = lower[name]
                self._constant_columns.append(column)
                self._constant_values.append(lower[name])
        mujoco.mj_forward(model, self.data)
        self.derivation["vendor_detection_margin_m"] = max(
            CLEARANCE_DETECTION_MARGIN_M, float(np.linalg.norm(np.ptp(self.data.geom_xpos, axis=0))) + 1.0)
        vendor_pairs = {}
        for contact in self._contacts(vendor_only=True):
            key = tuple(contact["geom_ids"])
            if key not in vendor_pairs:
                # Expanded mesh contacts can use a coarse separating axis at
                # large margins. Re-measure the actual surface distance with a
                # scene-spanning bound, independent of that detection margin.
                distance = float(mujoco.mj_geomDistance(
                    model, self.data, *key, self.derivation["vendor_detection_margin_m"], None))
                vendor_pairs[key] = {**contact, "distance_m": distance, "distance_mm": distance * 1000}
        self.vendor_structural_gaps = sorted(vendor_pairs.values(), key=lambda c: c["distance_m"])

    def _contacts(self, *, vendor_only=False):
        """Measure free space with native pair filtering; never edit the MJCF."""
        import mujoco
        model = self.model
        margins, pair_margins = model.geom_margin.copy(), model.pair_margin.copy()
        try:
            # Expand only while no eligible MOVING pair is measured. Static
            # contacts must not stop expansion and hide the gated minimum.
            # Large margins
            # on every sample make mesh narrow-phase checks needlessly costly.
            # The last pass spans the scene so distant eligible pairs are also
            # measured rather than returning a clipped-distance sentinel.
            span = float(np.linalg.norm(np.ptp(self.data.geom_xpos, axis=0)))
            full_margin = max(CLEARANCE_DETECTION_MARGIN_M, span + 1.0)
            detection_margins = ((full_margin,) if vendor_only else
                                 (PENETRATION_TOLERANCE_M, 0.01, 0.05,
                                  CLEARANCE_DETECTION_MARGIN_M, full_margin))
            for margin in detection_margins:
                model.geom_margin[:] = np.maximum(margins, margin)
                model.pair_margin[:] = np.maximum(pair_margins, margin)
                mujoco.mj_collision(model, self.data)
                contacts = []
                for contact in self.data.contact[:self.data.ncon]:
                    geoms = sorted(map(int, contact.geom),
                                   key=lambda g: (model.body(model.geom_bodyid[g]).name, g))
                    bodies = [model.body(model.geom_bodyid[g]).name for g in geoms]
                    if same_hand(bodies):
                        continue
                    body_ids = tuple(sorted(int(model.geom_bodyid[g]) for g in geoms))
                    static = body_ids[0] == body_ids[1] or body_ids in self.static_body_pairs
                    if static != vendor_only:
                        continue
                    contacts.append({"bodies": bodies,
                                     "geoms": [model.geom(g).name or f"geom_{g}" for g in geoms],
                                     "geom_ids": geoms, "distance_m": float(contact.dist)})
                if contacts or vendor_only:
                    return contacts
        finally:
            model.geom_margin[:] = margins
            model.pair_margin[:] = pair_margins
        raise ValueError("Clearance requires at least one eligible moving non-same-hand geom pair")

    def __call__(self, positions):
        if not len(positions):
            raise ValueError("Clearance requires at least one pose")
        if self._constant_columns and np.any(
                np.abs(np.asarray(positions)[:, self._constant_columns] - self._constant_values)
                > MOVING_JOINT_TOL_RAD):
            raise ValueError("Planner pose varies a library-constant joint; static classification is invalid")
        pairs, near_pairs = {}, {}
        worst = None
        for frame, row in enumerate(positions):
            apply_frame(self.model, self.data, self.joint_names, row)
            for contact in self._contacts():
                distance = contact["distance_m"]
                location = ("start_endpoint" if frame == 0 else
                            "end_endpoint" if frame == len(positions) - 1 else "interior")
                item = {**contact, "frame": frame, "location": location}
                if worst is None or distance < worst["distance_m"]:
                    worst = item
                key = tuple(contact["bodies"])
                if distance < ENDPOINT_NEAR_M:
                    if key not in near_pairs or distance < near_pairs[key]["distance_m"]:
                        near_pairs[key] = item
                if distance < PENETRATION_TOLERANCE_M:
                    if key not in pairs or distance < pairs[key]["distance_m"]:
                        pairs[key] = item
        return ClearanceResult(not pairs, worst["distance_m"],
                               list(pairs.values()), len(positions),
                               list(near_pairs.values()), worst, self.vendor_structural_gaps)


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


def _clearance_reasons(result, required_clearance):
    if result.min_distance_m >= required_clearance:
        return []
    worst = result.worst_contact or min(result.collisions, key=lambda c: c["distance_m"], default=None)
    reasons = [f"minimum signed clearance {result.min_distance_m} m is below "
               f"required floor {required_clearance} m"]
    if worst:
        reasons.append(f"{' | '.join(worst['bodies'])}, distance_m={worst['distance_m']}, "
                       f"sample {worst['frame']} ({worst.get('location', 'unspecified')})")
    return reasons


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
    source_near: bool = False


def plan_transition(a, b, joint_names, *, clearance: Callable,
                    via_factory=None, via2_factory=None, hub_factory=None,
                    height_check=None, model=None,
                    source_retract=None, target_approach=None,
                    source_retract_frames=None, target_approach_frames=None):
    """Direct, via1/via2, hub, then source retract / target approach fallback.

    If either endpoint is strictly below 2 mm, every complete candidate must
    meet the smaller endpoint clearance; accepted paths retain source_near.
    Normal paths require signed clearance >= PENETRATION_TOLERANCE_M (2 mm).
    All passing one-/two-via candidates compete on minimum signed clearance.
    Hub clearance is checked on both legs as well as the complete path. After
    hub failure, the general retract/approach route uses the source word's
    post-sign frames and the target word's pre-sign frames. An in-slice
    collision below the floor stops the segment without RRT. A failed
    candidate is retained for diagnosis with its worst pair, never for execution.
    """
    direct = minimum_jerk_blend(a, b, joint_names)
    endpoints = [annotate_clearance_dict(asdict(clearance(direct[[i]]))) for i in (0, -1)]
    endpoint_min = min(r["min_distance_m"] for r in endpoints)
    endpoint_near = endpoint_min < ENDPOINT_NEAR_M
    endpoint_floor = endpoint_min if endpoint_near else None
    required_clearance = endpoint_min if endpoint_near else PENETRATION_TOLERANCE_M
    attempts = []

    def assess(q, kind, leg_intervals, directions=(), legs=()):
        result = clearance(q)
        leg_clearance = [asdict(clearance(leg)) for leg in legs]
        height = height_check(q) if height_check else {"passed": True}
        passed = (result.min_distance_m >= required_clearance and
                  all(r["min_distance_m"] >= required_clearance for r in leg_clearance))
        relative_ok = passed if endpoint_near else None
        status = ("source_near" if endpoint_near else "PASS") if passed else "FAILED"
        reasons = _clearance_reasons(result, required_clearance) if not passed else []
        for number, leg in enumerate(leg_clearance):
            reasons.extend(f"hub leg {number + 1}: {reason}" for reason in
                           _clearance_reasons(ClearanceResult(**leg), required_clearance))
        worst = result.worst_contact or min(result.collisions, key=lambda c: c["distance_m"], default=None)
        directions = list(directions)
        attempts.append({"kind": kind, "method": kind,
                         "via_direction": directions[0] if kind == "via1" else None,
                         "via_directions": directions, "intervals": len(q) - 1,
                         "leg_intervals": leg_intervals,
                         "leg_clearance": leg_clearance,
                         "source_near": bool(endpoint_near),
                         "required_clearance_m": required_clearance,
                         "relative_floor_passed": relative_ok,
                         "clearance": annotate_clearance_dict(asdict(result)), "height": height,
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
            used_via=attempt["kind"] in ("via1", "via2", "hub", "retract_approach"),
            attempts=attempts, reasons=attempt["reasons"], warnings=warnings,
            via_direction=attempt["via_direction"], selected_attempt=index,
            endpoint_clearance=endpoints, endpoint_floor_m=endpoint_floor,
            method=attempt["kind"], via_directions=attempt["via_directions"],
            source_near=bool(endpoint_near))

    def score(choice):
        return attempts[choice[0]]["clearance"]["min_distance_m"]

    direct_choice = assess(direct, "direct", [len(direct) - 1])
    direct_ok = attempts[0]["status"] != "FAILED"
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
    passing = [c for c in candidates if attempts[c[0]]["status"] != "FAILED"]
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
    if attempts[hub_choice[0]]["status"] != "FAILED":
        return finish(hub_choice)

    retract_choice = None
    if source_retract is not None and target_approach is not None:
        retract = np.asarray(source_retract, dtype=float)
        approach = np.asarray(target_approach, dtype=float)
        if len(retract) < 1 or len(approach) < 1:
            raise ValueError("source_retract and target_approach must be nonempty")
        if not np.allclose(retract[0], a, atol=POSE_MATCH_TOL_RAD, rtol=0.0):
            raise ValueError("source_retract must start at the source sign endpoint")
        if not np.allclose(approach[-1], b, atol=POSE_MATCH_TOL_RAD, rtol=0.0):
            raise ValueError("target_approach must end at the target sign endpoint")

        def slice_collision(label, slice_q, library_frames):
            result = clearance(slice_q)
            if result.min_distance_m >= required_clearance:
                return None
            worst = result.worst_contact or min(
                result.collisions, key=lambda c: c["distance_m"], default=None)
            lib_frame = None
            if worst is not None and library_frames is not None:
                start, end = library_frames
                lib_frame = int(start + worst["frame"])
                if lib_frame > end:
                    lib_frame = int(end)
            return {
                "slice": label,
                "library_frame": lib_frame,
                "route_frame": None if worst is None else int(worst["frame"]),
                "bodies": None if worst is None else list(worst["bodies"]),
                "geoms": None if worst is None else list(worst.get("geoms", [])),
                "distance_m": result.min_distance_m,
                "required_clearance_m": required_clearance,
            }

        retract_hit = slice_collision(
            "retract", retract, source_retract_frames)
        approach_hit = slice_collision(
            "approach", approach, target_approach_frames)
        route, route_info = build_retract_approach_route(retract, approach, joint_names)
        legs = []
        if route_info["bridge_intervals"]:
            # Diagnostic legs: retract, bridge, approach (bridge reconstructed).
            bridge = minimum_jerk_blend(retract[-1], approach[0], joint_names)
            legs = [retract, bridge, approach]
        index, q = assess(route, "retract_approach",
                          [len(route) - 1],
                          legs=())
        attempt = attempts[index]
        attempt["source_retract_frames"] = (
            list(source_retract_frames) if source_retract_frames is not None else None)
        attempt["target_approach_frames"] = (
            list(target_approach_frames) if target_approach_frames is not None else None)
        attempt["retract_approach_info"] = route_info
        attempt["in_slice_collision"] = bool(retract_hit or approach_hit)
        attempt["slice_collisions"] = [hit for hit in (retract_hit, approach_hit) if hit]
        if retract_hit or approach_hit:
            attempt["status"] = "FAILED"
            attempt["relative_floor_passed"] = False if endpoint_near else None
            reasons = list(attempt.get("reasons") or [])
            for hit in (retract_hit, approach_hit):
                if not hit:
                    continue
                reasons.append(
                    f"{hit['slice']} slice collision: library_frame={hit['library_frame']}, "
                    f"bodies={' | '.join(hit['bodies'] or [])}, distance_m={hit['distance_m']}")
            attempt["reasons"] = reasons
            # In-slice collision: do not continue to RRT.
            retract_choice = (index, q)
            return finish(retract_choice)
        retract_choice = (index, q)
        if attempt["status"] != "FAILED":
            return finish(retract_choice)

    pool = [direct_choice, *candidates, hub_choice]
    if retract_choice is not None:
        pool.append(retract_choice)
    return finish(max(pool, key=score))


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
        clearance = MujocoClearance(model, names, library_path=root / "motions/hospital_v1_motions.json")
    height_check = (lambda q: wrist_height_check(model, names, q)) if model is not None else None
    pieces, transitions, segments, handoff, count = [], [], [], [], 0
    for k, (gloss, q) in enumerate(zip(glosses, clips)):
        s0, s1 = words[gloss]["sign_frames"]
        # Deliberately keep baseline first-word rise and last-word return.
        start = 0 if k == 0 else s0
        end = len(q) - 1 if k == len(glosses) - 1 else s1
        if k:
            prev = glosses[k - 1]
            prev_s0, prev_s1 = words[prev]["sign_frames"]
            source_full = clips[k - 1]
            retract = source_full[prev_s1:]
            approach = q[: s0 + 1]
            plan = plan_transition(
                pieces[-1][-1], q[start], names, clearance=clearance,
                height_check=height_check, model=model,
                source_retract=retract, target_approach=approach,
                source_retract_frames=(prev_s1, len(source_full) - 1),
                target_approach_frames=(0, s0))
            chosen = plan.attempts[plan.selected_attempt]
            source_frames = (prev_s1, s0)
            for word, source_frame, result in zip((glosses[k - 1], gloss), source_frames,
                                                   plan.endpoint_clearance):
                contacts = result["near_contacts"] or result["collisions"]
                if not contacts and result["min_distance_m"] < ENDPOINT_NEAR_M:
                    contacts = [result["worst_contact"]] if result["worst_contact"] else []
                for collision in contacts:
                    if collision["distance_m"] >= ENDPOINT_NEAR_M:
                        continue
                    item = {"word": word, "frame": source_frame, "bodies": collision["bodies"],
                            "distance_m": collision["distance_m"],
                            "clearance_mm": collision["distance_m"] * 1000}
                    if "geoms" in collision:
                        item["geoms"] = collision["geoms"]
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
                                "source_near": plan.source_near,
                                "method": plan.method,
                                "via_direction": plan.via_direction,
                                "via_directions": plan.via_directions,
                                "selected_attempt": plan.selected_attempt,
                                "clearance": chosen["clearance"],
                                "min_clearance_mm": float(chosen["clearance"]["min_distance_m"] * 1000),
                                "min_clearance_mm_display": format_clearance_mm(
                                    chosen["clearance"]["min_distance_m"]),
                                "clearance_capped": bool(chosen["clearance"].get("clearance_capped")),
                                "closest_pair": chosen["worst_collision"],
                                "worst_collision": chosen["worst_collision"],
                                "endpoint_clearance": plan.endpoint_clearance,
                                "endpoint_clearances_mm": [float(r["min_distance_m"] * 1000)
                                                           for r in plan.endpoint_clearance],
                                "endpoint_clearances_mm_display": [
                                    format_clearance_mm(r["min_distance_m"])
                                    for r in plan.endpoint_clearance],
                                "endpoint_clearance_capped": [
                                    bool(r.get("clearance_capped")) for r in plan.endpoint_clearance],
                                "endpoint_floor_m": plan.endpoint_floor_m,
                                "relative_floor_passed": chosen["relative_floor_passed"],
                                "vendor_structural_gaps": chosen["clearance"]["vendor_structural_gaps"],
                                "hub_attempted": any(a["kind"] == "hub" for a in plan.attempts),
                                "retract_approach_attempted": any(
                                    a["kind"] == "retract_approach" for a in plan.attempts),
                                "in_slice_collision": bool(chosen.get("in_slice_collision")),
                                "slice_collisions": list(chosen.get("slice_collisions") or []),
                                "source_retract_frames": chosen.get("source_retract_frames"),
                                "target_approach_frames": chosen.get("target_approach_frames"),
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
    source_near = sum(t["status"] == "source_near" for t in transitions)
    passed = sum(t["status"] == "PASS" for t in transitions)
    report = {"glosses": glosses, "fps": FPS, "frames": len(q),
              "duration_s": len(q) / FPS, "last_timestamp_s": (len(q) - 1) / FPS,
              "transition_count": len(transitions), "pass_count": passed,
              "source_near_count": source_near, "accepted_count": passed + source_near,
              "failed_count": failed,
              "status": "FAILED" if failed else "source_near" if source_near else "PASS",
              "rate_limits_rad_s": {"arm": ARM_RATE_RAD_S, "finger": FINGER_RATE_RAD_S},
              "minimum_leg_duration_s": MIN_LEG_DURATION_S,
              "normal_clearance_minimum_m": PENETRATION_TOLERANCE_M,
              "endpoint_near_below_m": ENDPOINT_NEAR_M,
              "collision_threshold_note": "moving pairs only; signed distance: positive separation, negative penetration; normal whole-path minimum >= 0.002 m",
              "source_near_rule": "either moving-pair endpoint minimum strictly < 0.002 m; same full search, label source_near only if the relative floor passes",
              "relative_floor_rule": "near-source whole-path minimum >= min(endpoint clearances); otherwise continue search through hub and retract/approach, then FAILED",
              "escalation_order": ["direct", "best_via1_or_via2", "hub", "source_retract_approach", "FAILED"],
              "clearance_display_cap_m": CLEARANCE_DISPLAY_CAP_M,
              "clearance_cap_note": "separations >= 9.5 mm display as >=9.5; verified true elbow/wrist_pitch mesh gap (~9.50015 mm via mj_geomDistance distmax=1.0), not a distmax clip",
              "neutral_hub_source": "fixed-base model qpos0 for named trajectory joints; never assumed clear",
              "clearance_scope": "moving pairs at all samples including endpoints; static pairs with equal moving-ancestor joint sets measured separately as vendor structural gaps; native MuJoCo pairs and same-hand exclusion unchanged; temporarily expanded detection margins, restored after each query; finite signed moving minimum and closest body/geom pair",
              "clearance_derivation": getattr(clearance, "derivation", None),
              "vendor_structural_gaps": getattr(clearance, "vendor_structural_gaps", []),
              "sentence_peak_rates": peak_rates(q, names),
              "failed_trajectory_policy": "FAILED emits the checked candidate with greatest minimum clearance for diagnostic replay only; source_near retains inherited endpoint proximity and is not an absolute 2 mm clearance certification",
              "source_near_handoff": handoff,
              "word_segments": segments, "transitions": transitions}
    return motion, report
