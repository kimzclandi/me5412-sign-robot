import json
import numpy as np
import pytest
from sign_robot.motion import ROOT, load_model, validate_motion
from sign_robot.retarget import Skeleton, finger_flexion, hand_frame, FINGERS

SKELETON = ROOT / "data/mocap/studio_galt_v1/skeleton/YOU.npz"
CLIP = ROOT / "motions/studio_galt_v1/YOU"


@pytest.fixture(scope="module")
def model():
    return load_model()


def test_hand_frame_is_right_handed_orthonormal():
    rng = np.random.default_rng(0)
    frame = hand_frame(*rng.normal(size=(4, 5, 3)))
    assert np.allclose(np.einsum("tji,tjk->tik", frame, frame), np.eye(3), atol=1e-9)
    assert np.allclose(np.linalg.det(frame), 1.0)


def test_finger_flexion_is_zero_at_bind_and_reads_the_you_handshape():
    data = np.load(SKELETON)
    sk = Skeleton(data, data["rot"][0])
    flex = {f: np.degrees(finger_flexion(sk, f, "r")) for f in FINGERS + ("thumb",)}
    assert all(abs(v[0]) < 1e-6 for v in flex.values())
    pointing = int(np.argmax(flex["middle"]))  # YOU: index extended, other fingers closed
    assert flex["index"][pointing] < 30
    assert min(flex[f][pointing] for f in ("middle", "ring", "pinky")) > 180


def test_retargeted_clip_matches_motion_contract(model):
    with np.load(CLIP.with_suffix(".npz")) as data:
        motion = {k: data[k] for k in ("timestamps_s", "joint_names", "positions")}
    meta = json.loads(CLIP.with_suffix(".json").read_text())
    validate_motion(motion)
    q, names, t = motion["positions"], motion["joint_names"], motion["timestamps_s"]
    assert [str(n) for n in names] == [model.joint(i).name for i in range(model.njnt)]
    assert np.allclose(np.diff(t), 1 / 30)
    ids = [model.joint(str(n)).id for n in names]
    assert np.all(q >= model.jnt_range[ids, 0] - 1e-9) and np.all(q <= model.jnt_range[ids, 1] + 1e-9)
    assert np.allclose(q[0], q[-1])  # starts and ends at the shared neutral pose
    c0, c1 = meta["core_frames"]
    assert 0 < c0 < c1 < len(t) - 1
    info = json.loads((ROOT / "assets/robot/model_info.json").read_text())
    index = {str(n): i for i, n in enumerate(names)}
    for rule in info["couplings"]:
        assert np.allclose(q[:, index[rule["child"]]], rule["offset"] + rule["multiplier"] * q[:, index[rule["parent"]]])
    for side in ("left", "right"):
        assert meta["ik_error"][side]["wrist_position_m"]["max"] < 0.01
    assert meta["asl_reviewed"] is False
