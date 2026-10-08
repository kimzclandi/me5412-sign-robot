import json
import hashlib
import xml.etree.ElementTree as ET
import numpy as np
import pytest
import mujoco
from sign_robot.motion import ROOT, ACTION_IDS, load_model, load_motion, validate_motion, apply_frame, require_preview_permission


@pytest.fixture(scope="module")
def model():
    return load_model()


def test_real_model_retains_coupling_and_has_no_actuators(model):
    assert model.nq == 53
    assert model.neq == 12
    assert model.nu == 0
    assert all(int(x) == int(mujoco.mjtJoint.mjJNT_HINGE) for x in model.jnt_type)


def test_original_vendor_hashes_and_motion_sources():
    manifest = json.loads((ROOT / "assets/robot/upstream_manifest.json").read_text())
    for entry in manifest['files']:
        file = ROOT / "assets/robot/vendor" / entry['file']
        assert hashlib.sha256(file.read_bytes()).hexdigest() == entry['sha256']
    sources = {s['source_id'] for s in json.loads((ROOT / "data/source_manifest.json").read_text())['sources']}
    for action in ACTION_IDS:
        assert set(load_motion(action)['metadata']['source_ids']) <= sources


@pytest.mark.parametrize("action", ACTION_IDS)
def test_motion_bounds_mimic_speed_and_replay(action, model):
    motion = load_motion(action)
    q, names, t = (motion[k] for k in ("positions", "joint_names", "timestamps_s"))
    assert set(names) == {model.joint(i).name for i in range(model.njnt)}
    ids = [model.joint(str(n)).id for n in names]
    assert np.all(q >= model.jnt_range[ids, 0] - 1e-8)
    assert np.all(q <= model.jnt_range[ids, 1] + 1e-8)
    assert np.allclose(q[0], q[-1])
    index = {str(n): i for i, n in enumerate(names)}
    info = json.loads((ROOT / "assets/robot/model_info.json").read_text())
    for r in info["couplings"]:
        assert np.allclose(q[:, index[r['child']]], r['offset'] + r['multiplier'] * q[:, index[r['parent']]], atol=1e-12)
    robot = ET.parse(ROOT / "assets/robot/vendor/g1_29dof_rev_1_0_with_inspire_hand_DFQ.urdf")
    velocities = {j.get("name"): float(j.find("limit").get("velocity")) for j in robot.findall("joint") if j.find("limit") is not None}
    speed = np.abs(np.diff(q, axis=0) / np.diff(t)[:, None])
    assert np.all(speed <= np.asarray([velocities[str(n)] for n in names])[None, :] + 1e-8)
    # Replay all frames against actual upstream collision geometry.
    data = mujoco.MjData(model)
    for frame in q:
        apply_frame(model, data, names, frame)
        assert np.isfinite(data.xpos).all()
        assert all(c.dist >= -0.001 for c in data.contact)
    assert motion['metadata']['asl_reviewed'] is False


def test_named_mapping_not_array_order(model):
    motion = load_motion("HELLO")
    first, second = mujoco.MjData(model), mujoco.MjData(model)
    apply_frame(model, first, motion['joint_names'], motion['positions'][90])
    apply_frame(model, second, motion['joint_names'][::-1], motion['positions'][90, ::-1])
    assert np.allclose(first.qpos, second.qpos)


def test_candidate_preview_requires_explicit_permission():
    motion = load_motion("HELLO")
    with pytest.raises(PermissionError):
        require_preview_permission(motion)
    require_preview_permission(motion, allow_candidate_preview=True)


def test_bad_time_and_nonfinite_frames_rejected():
    motion = load_motion("HELLO")
    motion['timestamps_s'][2] = motion['timestamps_s'][1]
    with pytest.raises(ValueError):
        validate_motion(motion)
    motion = load_motion("HELLO")
    motion['positions'][3, 5] = np.nan
    with pytest.raises(ValueError):
        validate_motion(motion)


def test_hello_lateral_motion_and_wait_nonuniform_finger_motion(model):
    motion = load_motion("HELLO")
    data = mujoco.MjData(model)
    positions = []
    for time in (2.8, 3.8, 4.8):
        frame = np.argmin(np.abs(motion['timestamps_s'] - time))
        apply_frame(model, data, motion['joint_names'], motion['positions'][frame])
        positions.append(data.site('right_palm').xpos.copy())
    assert np.ptp(np.asarray(positions)[:, 1]) > 0.09
    wait = load_motion("PLEASE_WAIT")
    n = wait['joint_names'].tolist()
    a = wait['positions'][90:180, n.index('R_index_proximal_joint')]
    b = wait['positions'][90:180, n.index('R_middle_proximal_joint')]
    assert np.ptp(a) > 0.09
    assert not np.allclose(a, b)


def test_thanks_fingertip_proxy_moves_forward_without_upward_detour(model):
    motion = load_motion("THANK_YOU")
    data = mujoco.MjData(model)
    points = []
    for q in motion['positions'][90:145]:
        apply_frame(model, data, motion['joint_names'], q)
        palm = data.site('right_palm')
        points.append(palm.xpos + 0.17 * palm.xmat.reshape(3, 3)[:, 0])
    points = np.asarray(points)
    assert np.all(np.diff(points[:, 0]) > -0.001)
    assert points[:, 2].max() <= points[0, 2] + 0.005
    assert points[-1, 2] < points[0, 2] - 0.04
