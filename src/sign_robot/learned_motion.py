"""Experimental text/phase ridge model; inference never reads demonstration NPZs.

Input: frozen normalized MiniLM text embedding [384] and phase [T].
Output: learned active angles [T,26], constrained/reconstructed positions [T,53].
Three authored demonstrations support temporal interpolation only, not new ASL.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

from .contracts import ROOT

EXPERIMENT = ROOT / "results/motion_learning/v1"


def phase_features(phase, centers, width):
    phase = np.asarray(phase, dtype=float)
    if phase.ndim != 1 or not np.isfinite(phase).all() or np.any((phase < 0) | (phase > 1)):
        raise ValueError("Phase must be a finite vector in [0, 1]")
    return np.exp(-0.5 * ((phase[:, None] - centers[None, :]) / width) ** 2) * (4 * phase * (1 - phase))[:, None]


def encode_text(text):
    from .language import _load_encoder
    config = json.loads((ROOT / "config/embedding.json").read_text(encoding="utf-8"))
    vector = _load_encoder(str((ROOT / config["model_path"]).resolve())).encode(
        [text], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
    if vector.shape != (384,) or not np.isfinite(vector).all():
        raise ValueError("Expected a real normalized 384-dimensional text embedding")
    return np.r_[vector.astype(float), 1.0] / np.sqrt(2.0)


@lru_cache(maxsize=2)
def load_checkpoint(directory: str = str(EXPERIMENT)):
    folder = Path(directory)
    with np.load(folder / "model.npz", allow_pickle=False) as data:
        arrays = {name: data[name].copy() for name in data.files}
    metadata = json.loads((folder / "model.json").read_text(encoding="utf-8"))
    return arrays, metadata


def predict_positions(embedding, phase, checkpoint):
    c = checkpoint
    basis = phase_features(phase, c["centers"], float(c["width"]))
    coefficients = np.einsum("i,ikj->kj", embedding, c["weights"], optimize=True)
    raw = c["neutral"][c["active_indices"]][None, :] + basis @ coefficients
    active = np.clip(raw, c["effective_lower"], c["effective_upper"])
    positions = np.tile(c["neutral"], (len(phase), 1))
    positions[:, c["active_indices"]] = active
    for child, parent, multiplier, offset in zip(c["child_indices"], c["parent_indices"], c["multipliers"], c["offsets"]):
        positions[:, child] = offset + multiplier * positions[:, parent]
    return positions, {"max_projection_rad": float(np.abs(raw - active).max()),
                       "raw_out_of_bound_coordinates": int(np.count_nonzero((raw < c["effective_lower"] - 1e-6) | (raw > c["effective_upper"] + 1e-6)))}


def inspect_trajectory(positions, timestamps, names, checkpoint):
    """All generated frames, original collision geoms/URDF velocities; no dynamics."""
    import mujoco
    from .motion import load_model, apply_frame
    model = load_model()
    data = mujoco.MjData(model)
    joint_ids = [model.joint(str(name)).id for name in names]
    violation = np.maximum(model.jnt_range[joint_ids, 0] - positions,
                           positions - model.jnt_range[joint_ids, 1])
    speed = np.abs(np.diff(positions, axis=0) / np.diff(timestamps)[:, None])
    urdf = ET.parse(ROOT / "assets/robot/vendor/g1_29dof_rev_1_0_with_inspire_hand_DFQ.urdf")
    velocity = {joint.get("name"): float(joint.find("limit").get("velocity"))
                for joint in urdf.findall("joint") if joint.find("limit") is not None}
    max_excess = float(np.maximum(speed - np.asarray([velocity[str(n)] for n in names]), 0).max())
    mimic = [np.abs(positions[:, child] - offset - multiplier * positions[:, parent]).max()
             for child, parent, multiplier, offset in zip(checkpoint["child_indices"], checkpoint["parent_indices"], checkpoint["multipliers"], checkpoint["offsets"])]
    events, depth = 0, 0.0
    for frame in positions:
        apply_frame(model, data, names, frame)
        for contact in data.contact:
            if contact.dist < -0.001:
                events += 1
            depth = max(depth, -float(contact.dist))
    return {"joint_limit_violation_rad": float(max(0.0, violation.max())),
            "max_mimic_error_rad": float(max(mimic)), "max_joint_speed_rad_s": float(speed.max()),
            "max_speed_limit_excess_rad_s": max_excess,
            "penetrating_contact_events_below_minus_1mm": events,
            "maximum_reported_penetration_m": depth,
            "collision_frames_checked": len(positions), "collision_scope": "upstream collision geoms at sampled frames only"}


def geometric_acceptance(metrics, protocol):
    gates = protocol["acceptance"]
    return bool(metrics["joint_limit_violation_rad"] <= gates["joint_limit_tolerance_rad"]
                and metrics["max_mimic_error_rad"] <= gates["mimic_tolerance_rad"]
                and metrics["max_speed_limit_excess_rad_s"] <= 1e-8
                and metrics["penetrating_contact_events_below_minus_1mm"] == 0
                and metrics["max_projection_rad"] <= gates["max_projection_rad_max"])


def generate(text, duration_s=None, fps=30, *, checkpoint_dir=None):
    """Compute a research candidate, never actuate a robot or replay training files.

    A legal exact alias is required before encoding. Duration may only be the
    trained duration through 1.2 times that duration. Status does not grant ASL
    approval; default_enabled is always False for this experimental version.
    """
    from .language import select_action
    selected = select_action(text, method="exact")
    if selected["status"] != "execute":
        return {"status": "unsupported", "positions": None, "reason_code": selected["reason_code"], "default_enabled": False}
    if fps != 30:
        return {"status": "unsupported", "positions": None, "reason_code": "v1_requires_30_fps", "default_enabled": False}
    try:
        arrays, meta = load_checkpoint(str(checkpoint_dir or EXPERIMENT))
        aid = selected["action_id"]
        base = float(meta["durations_s"][aid])
        duration = base if duration_s is None else float(duration_s)
        if not np.isfinite(duration) or duration < base - 1e-9 or duration > 1.2 * base + 1e-9:
            return {"status": "unsupported", "positions": None, "reason_code": "duration_out_of_frozen_range", "default_enabled": False}
        times = np.linspace(0, duration, round(duration * fps) + 1)
        positions, metrics = predict_positions(encode_text(text), times / duration, arrays)
        metrics.update(inspect_trajectory(positions, times, arrays["joint_names"], arrays))
        geometric_ok = geometric_acceptance(metrics, meta["protocol"])
        fitting_ok = meta.get("fit_accepted", False)
        summary_path = Path(checkpoint_dir or EXPERIMENT) / "report.json"
        experiment_ok = json.loads(summary_path.read_text(encoding="utf-8")).get("accepted", False) if summary_path.exists() else fitting_ok
        accepted = geometric_ok and fitting_ok and experiment_ok
        reasons = []
        if not fitting_ok: reasons.append("heldout_fit_gate_failed")
        if not geometric_ok: reasons.append("generated_trajectory_engineering_gate_failed")
        if not experiment_ok: reasons.append("experiment_not_accepted")
        return {"status": "candidate" if accepted else "rejected_candidate", "action_id": aid,
                "positions": positions, "timestamps_s": times, "joint_names": arrays["joint_names"],
                "metrics": metrics, "accepted": accepted, "rejection_reasons": reasons,
                "geometric_accepted": geometric_ok, "default_enabled": False,
                "asl_reviewed": False, "execution_mode": "learned_text_phase_regression",
                "duration_s": duration, "conditioning_text": text}
    except (OSError, ValueError, KeyError) as error:
        return {"status": "error", "positions": None, "reason_code": type(error).__name__, "default_enabled": False}
