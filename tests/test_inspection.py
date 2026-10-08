import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
from sign_robot.motion import ROOT, ACTION_IDS, load_model, load_motion

spec = importlib.util.spec_from_file_location("export_inspection", ROOT / "scripts/export_inspection.py")
inspection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspection)


@pytest.fixture(scope="module")
def model():
    return load_model()


def test_velocity_definition_uses_real_timestamp_intervals():
    times = np.array([0, .1, .3])
    positions = np.array([[0, 0], [.2, -.1], [.8, -.5]])
    assert np.allclose(inspection.backward_velocities(times, positions), [[0, 0], [2, -1], [3, -2]])
    with pytest.raises(ValueError):
        inspection.backward_velocities([0, 0, .3], positions)


@pytest.mark.parametrize("action", ACTION_IDS)
def test_telemetry_matches_source_without_modifying_source(action, model):
    paths = [ROOT / f"motions/{action}.npz", ROOT / f"motions/{action}.json", ROOT / "assets/robot/scene.xml"]
    before = [inspection.digest(p) for p in paths]
    context = inspection.source_context(ROOT, action, 960, 720)
    report = inspection.build_telemetry(ROOT, action, context, model)
    after = [inspection.digest(p) for p in paths]
    assert before == after
    assert report["schema_version"] == 1
    assert report["trajectory_sha256"] == before[0]
    source = load_motion(action)
    assert np.allclose(report["timestamps_s"], source["timestamps_s"], atol=5.1e-8, rtol=0)
    assert np.allclose(report["positions_rad"], source["positions"], atol=5.1e-8, rtol=0)
    velocity = inspection.backward_velocities(source['timestamps_s'], source['positions'])
    assert np.allclose(report['velocities_rad_s'], velocity, atol=5.1e-8, rtol=0)
    assert len(inspection.json_bytes(report)) < 700_000
    assert report["asl_reviewed"] is False
    assert report["execution_mode"] == "kinematic_qpos_replay"
    assert report["validation"]["joint_limits_passed"]
    assert report["validation"]["reference_velocity_limits_passed"]
    assert report["validation"]["max_mimic_error_rad"] < 1e-12
    assert report["validation"]["frames_with_penetration_over_1mm"] == 0
    assert report["phase_intervals"][0]["start_s"] == 0
    assert report["phase_intervals"][-1]["end_s"] == source['timestamps_s'][-1]
    children = {rule['child'] for rule in report['mimic_couplings']}
    plotted = {n for names in report['joint_groups'].values() for n in names}
    assert not children & plotted
    assert len(report['joint_groups']['right_arm']) == 7
    assert len(report['joint_groups']['left_arm']) == 7
    assert len(report['joint_groups']['right_hand']) == 6
    assert len(report['joint_groups']['left_hand']) == 6
    assert plotted <= set(report['joint_names'])
    assert len(report['palm_positions_m']['right']) == len(source['timestamps_s'])


def test_existing_run_cannot_hide_changed_source_or_output(tmp_path):
    content = tmp_path / 'telemetry.json'
    content.write_text('{"test":true}')
    context = {'trajectory_sha256': 'original'}
    record = {'context': context, 'output_sha256': {'telemetry.json': inspection.digest(content)}}
    (tmp_path / 'run.json').write_text(json.dumps(record))
    assert inspection.check_existing(tmp_path, context) == record
    with pytest.raises(ValueError, match='different source'):
        inspection.check_existing(tmp_path, {'trajectory_sha256': 'changed'})
    content.write_text('{"test":false}')
    with pytest.raises(ValueError, match='output changed'):
        inspection.check_existing(tmp_path, context)


def test_manifest_appends_new_runs_and_reuses_same_run(tmp_path):
    path = tmp_path / 'manifest.json'
    first = {'entry': {'action_id': 'HELLO', 'run_id': 'first', 'telemetry': 'results/inspection/HELLO/first/telemetry.json'}}
    second = {'entry': {'action_id': 'HELLO', 'run_id': 'second', 'telemetry': 'results/inspection/HELLO/second/telemetry.json'}}
    inspection.update_manifest(path, [first])
    inspection.update_manifest(path, [first])
    result = inspection.update_manifest(path, [second])
    assert result['schema_version'] == 1
    assert [item['run_id'] for item in result['runs']] == ['first', 'second']
    assert result['actions']['HELLO']['run_id'] == 'second'


def test_no_permission_no_inspection_files(tmp_path):
    with pytest.raises(PermissionError):
        inspection.export_action(ROOT, "HELLO", allow_candidate_preview=False)
