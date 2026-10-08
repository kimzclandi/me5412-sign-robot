"""Read-only experimental model adapter and actual forward-kinematic preview."""
from __future__ import annotations

import hashlib
import json
from threading import Lock
from .contracts import ROOT

INFERENCE_LOCK = Lock()


def status(root=ROOT):
    folder = root / "results/motion_learning/v1"
    report = json.loads((folder / "report.json").read_text())
    meta = json.loads((folder / "model.json").read_text())
    corpus = json.loads((root / "data/corpus_index/how2sign_realigned_v1/download_manifest.json").read_text())
    return {"version": "v1", "model_type": meta["model_type"],
            "model_sha256": report["model_sha256"],
            "checkpoint_hash_verified": hashlib.sha256((folder / "model.npz").read_bytes()).hexdigest() == report["model_sha256"],
            "accepted": report["accepted"], "default_enabled": False, "asl_reviewed": False,
            "independent_demonstrations": meta["independent_demonstrations"],
            "train_frames": meta["train_frames"], "validation_frames": meta["validation_frames"],
            "validation_scope": report["validation_scope"], "fit": report["fit"],
            "durations_s": meta["durations_s"], "corpus": corpus["aggregate_counts"],
            "corpus_modality": corpus["modality"]}


def kinematic_preview(result):
    """Return actual body-frame origins [T,B,3] in metres, not video lookup.

    Edges follow the MuJoCo body tree; points are link-frame origins, not
    anatomical landmarks or mesh surfaces. Legs are omitted for readability.
    """
    import mujoco
    import numpy as np
    from .motion import load_model, apply_frame
    model = load_model()
    data = mujoco.MjData(model)
    ids = [i for i in range(1, model.nbody)
           if not any(word in model.body(i).name for word in ("hip_", "knee_", "ankle_"))]
    lookup = {body: i for i, body in enumerate(ids)}
    edges = [[lookup[int(model.body_parentid[b])], lookup[b]] for b in ids
             if int(model.body_parentid[b]) in lookup]
    frames = []
    for frame in result["positions"]:
        apply_frame(model, data, result["joint_names"], frame)
        frames.append(data.xpos[ids].copy())
    return {"body_names": [model.body(i).name for i in ids], "edges": edges,
            "positions_m": np.asarray(frames).round(7).tolist(),
            "scope": "MuJoCo body-frame origins; kinematic links only, no mesh or dynamics"}


def generate_request(request, root=ROOT):
    text = request.get("text")
    scale = request.get("duration_scale", 1.0)
    if not isinstance(text, str) or len(text) > 1000:
        raise ValueError("text must be a string of at most 1000 characters")
    if type(scale) not in (int, float) or scale not in (1.0, 1.2):
        raise ValueError("duration_scale must be 1.0 or 1.2")
    from .language import select_action
    selected = select_action(text, method="exact")
    if selected["status"] != "execute":
        return {"status": "unsupported", "accepted": False, "positions_rad": None,
                "reason_code": selected["reason_code"], "default_enabled": False, "asl_reviewed": False}
    with INFERENCE_LOCK:
        summary = status(root)
        if not summary["checkpoint_hash_verified"]:
            raise ValueError("checkpoint hash does not match the frozen experiment")
        from .learned_motion import generate
        result = generate(text, duration_s=summary["durations_s"][selected["action_id"]] * scale,
                          checkpoint_dir=root / "results/motion_learning/v1")
        result["model_sha256"] = summary["model_sha256"]
        if result.get("positions") is not None:
            # Rejected candidates retain diagnostics, but have no playable pose.
            if result.get("accepted"):
                result["kinematics"] = kinematic_preview(result)
            result["positions_rad"] = result.pop("positions").tolist()
            result["timestamps_s"] = result["timestamps_s"].tolist()
            result["joint_names"] = result["joint_names"].tolist()
        else:
            result["positions_rad"] = result.pop("positions", None)
        return result
