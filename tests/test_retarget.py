import json
import numpy as np
import pytest
from sign_robot.motion import ROOT, load_model, validate_motion
from sign_robot.retarget import Skeleton, finger_flexion, hand_frame, FINGERS

SKELETON = ROOT / "data/mocap/studio_galt_v1/skeleton/YOU.npz"
LIBRARY = ROOT / "motions/studio_galt_v1"
INDEX = json.loads((LIBRARY / "index.json").read_text())


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


def test_index_covers_group1_vocabulary_in_order():
    words = [e["gloss"] for e in INDEX["words"]]
    assert len(words) == 27 and len(set(words)) == 27
    assert [e["id"] for e in INDEX["words"]] == list(range(1, 28))
    assert {e["robot_status"] for e in INDEX["words"]} <= set(INDEX["status_scale"])
    assert all(e["robot_note"] for e in INDEX["words"] if e["robot_status"] != "usable")


@pytest.mark.parametrize("entry", INDEX["words"], ids=lambda e: e["gloss"])
def test_retargeted_clip_matches_motion_contract(entry, model):
    clip = ROOT / entry["motion"]
    with np.load(clip) as data:
        motion = {k: data[k] for k in ("timestamps_s", "joint_names", "positions")}
    meta = json.loads(clip.with_suffix(".json").read_text())
    validate_motion(motion)
    q, names, t = motion["positions"], motion["joint_names"], motion["timestamps_s"]
    assert [str(n) for n in names] == [model.joint(i).name for i in range(model.njnt)]
    assert np.allclose(np.diff(t), 1 / 30)
    ids = [model.joint(str(n)).id for n in names]
    assert np.all(q >= model.jnt_range[ids, 0] - 1e-9) and np.all(q <= model.jnt_range[ids, 1] + 1e-9)
    assert np.allclose(q[0], q[-1])  # starts and ends at the shared neutral pose
    c0, c1 = meta["core_frames"]
    assert 0 < c0 < c1 < len(t) - 1 and meta["core_frames"] == entry["core_frames"]
    info = json.loads((ROOT / "assets/robot/model_info.json").read_text())
    index = {str(n): i for i, n in enumerate(names)}
    for rule in info["couplings"]:
        assert np.allclose(q[:, index[rule["child"]]], rule["offset"] + rule["multiplier"] * q[:, index[rule["parent"]]])
    if entry["robot_status"] == "usable":  # sign-phase wrist error, rest frames excluded
        for err in meta["ik_error_sign_phase"].values():
            assert err["frames"] == 0 or err["wrist_position_m"]["max"] < 0.02
    assert meta["asl_reviewed"] is False


def test_sign_frames_sit_inside_core_and_baseline_stitches():
    import sys
    sys.path.insert(0, str(ROOT / "scripts/mocap"))
    from stitch_baseline import stitch
    for e in INDEX["words"]:
        c0, c1 = e["core_frames"]
        s0, s1 = e["sign_frames"]
        assert c0 <= s0 < s1 <= c1
    motion = stitch(["YOU", "BUY", "BOOK"])
    validate_motion(motion)
    q = motion["positions"]
    assert np.allclose(q[0], q[-1])  # sentence starts and ends at neutral
    assert np.abs(np.diff(q, axis=0)).max() * 30 < 30  # no jump at the seams
