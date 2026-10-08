"""Named-joint, fixed-base kinematic candidate trajectories (not a controller)."""
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ACTION_IDS = ("HELLO", "THANK_YOU", "PLEASE_WAIT")


def load_motion(action_id, root=None):
    if action_id not in ACTION_IDS:
        raise ValueError("Unknown action ID")
    folder = Path(root or ROOT) / "motions"
    with np.load(folder / f"{action_id}.npz", allow_pickle=False) as data:
        motion = {key: data[key].copy() for key in ("timestamps_s", "joint_names", "positions")}
    motion["metadata"] = json.loads((folder / f"{action_id}.json").read_text())
    validate_motion(motion)
    return motion


def validate_motion(motion):
    t, names, q = (motion[key] for key in ("timestamps_s", "joint_names", "positions"))
    if t.ndim != 1 or len(t) < 2 or not np.isfinite(t).all() or not np.all(np.diff(t) > 0):
        raise ValueError("Motion timestamps must be finite and strictly increasing")
    if names.ndim != 1 or len(set(names.tolist())) != len(names):
        raise ValueError("Motion joint names must be unique")
    if q.shape != (len(t), len(names)) or not np.isfinite(q).all():
        raise ValueError("Motion positions must have finite shape [T, J]")
    return True


def apply_frame(model, data, joint_names, positions):
    """Set one *kinematic* frame, map by name, and recompute forward kinematics."""
    import mujoco
    if len(joint_names) != len(positions):
        raise ValueError("Joint names and positions length mismatch")
    for name, value in zip(joint_names, positions):
        joint = model.joint(str(name))
        if int(joint.type[0]) not in (int(mujoco.mjtJoint.mjJNT_HINGE), int(mujoco.mjtJoint.mjJNT_SLIDE)):
            raise ValueError("Only scalar joints are supported by the trajectory contract")
        data.qpos[joint.qposadr[0]] = value
    data.qvel[:] = 0
    mujoco.mj_forward(model, data)


def require_preview_permission(motion, allow_candidate_preview=False):
    if not motion["metadata"].get("asl_reviewed", False) and not allow_candidate_preview:
        raise PermissionError("Unreviewed candidate; explicit research preview permission required")


def load_model(root=None):
    import mujoco
    return mujoco.MjModel.from_xml_path(str(Path(root or ROOT) / "assets/robot/scene.xml"))
