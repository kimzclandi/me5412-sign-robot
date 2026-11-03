"""Core-gap candidate selection and the planned return to the library rest pose (rest_tail_v1)."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from clips_v2 import load_sequence_policy_on_clips_v2
from sign_robot import pair_runner_v2, sequence_verification
from sign_robot.motion import ROOT
from sign_robot.pair_contract import (
    CORE_GAP_SELECTION_V1, SMOOTHNESS_SELECTION_V1, file_hash, freeze_library, json_hash, load_policy, read_motion,
    run_identity, save_pair_trajectory, validate_policy_v2,
)
from sign_robot.pair_routes import build_pair_context_v2, iter_deterministic_attempts_v2
from sign_robot.pair_verification_v2 import _full_replay
from sign_robot.sequence_assembly import SequenceAssemblyError, assemble_sequence
from sign_robot.sequence_contract import (
    library_rest_pose_v1, load_sequence_policy, read_sequence, rest_tail_config, save_sequence, sequence_identity,
    validate_sequence_policy, validate_sequence_v1,
)
from sign_robot.sequence_rest import plan_rest_tail_v1
from sign_robot.sequence_verification import verify_saved_sequence_v1

POLICY = 'config/sequence_policy_hospital_sentences_v3.json'
FAST = 'transition_policy_hospital_sentences_fast_v1.json'


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


def test_fast_policy_changes_only_the_selection_rule():
    old, new = _load('transition_policy_hospital_sentences_braking_v1.json'), _load(FAST)
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'selection_rule'}
    assert old['selection_rule'] == SMOOTHNESS_SELECTION_V1 and new['selection_rule'] == CORE_GAP_SELECTION_V1
    bad = copy.deepcopy(new)
    bad['selection_rule'] = 'numerical_pass_then_whatever_v9'
    with pytest.raises(ValueError, match='candidate-selection'):
        validate_policy_v2(bad)


def _store(rule, candidates, monkeypatch):
    """A run store reduced to what _selection_winner reads: (gap edges, connector frames, peak jerk) per attempt."""
    trajectories, evidence = {}, {}
    for attempt_id, (retained_source, frames, retained_target, jerk) in candidates.items():
        trajectories[attempt_id] = {
            'word_instances': [{'source_frames': [10, 40 + retained_source], 'protected_core_frames': [10, 40]},
                               {'source_frames': [20 - retained_target, 60], 'protected_core_frames': [20, 60]}],
            'segments': [{'end_time_s': 0.0}, {'start_time_s': 1.0, 'end_time_s': 1.0 + frames / 30},
                         {'start_time_s': 1.0 + frames / 30, 'end_time_s': 2.0 + frames / 30}],
            'planner': {'method': 'direct'}, 'id': attempt_id}
        evidence[attempt_id] = {'evidence': {'metrics': {'peak_jerk_rad_s3': jerk, 'peak_acceleration_rad_s2': 10.0,
                                                         'analytic_connector_jerk_integral_rad2_s5': 1.0}}}
    monkeypatch.setattr(pair_runner_v2, 'inside', lambda root, path: path)
    monkeypatch.setattr(pair_runner_v2, 'read_pair_trajectory', lambda path, schema_version: trajectories[path])
    monkeypatch.setattr(pair_runner_v2, 'read_json', lambda path: evidence[path])
    policy = _load(FAST)
    policy['selection_rule'] = rule
    store = SimpleNamespace(policy=policy, run_dir=None)
    reviews = [{'attempt_id': a, 'path': a, 'numerical_checks_passed': True} for a in candidates]
    attempts = [{'attempt_id': a, 'candidate_file': a} for a in candidates]
    return pair_runner_v2.V2RunStore._selection_winner(store, reviews, attempts)


def test_core_gap_rule_prefers_fewest_frames_between_cores(monkeypatch):
    candidates = {'slow_smooth': (0, 90, 0, 5.0), 'fast_long_edge': (40, 9, 0, 400.0), 'fast': (3, 12, 2, 700.0),
                  'fast_tie_smoother': (2, 13, 2, 600.0)}
    assert _store(SMOOTHNESS_SELECTION_V1, candidates, monkeypatch) == 'slow_smooth'
    # gaps: 90, 49, 17, 17 -> the tie goes to the lower peak jerk
    assert _store(CORE_GAP_SELECTION_V1, candidates, monkeypatch) == 'fast_tie_smoother'


def test_rest_pose_is_the_shared_first_frame_of_every_clip():
    _, pair_policy = load_sequence_policy(ROOT, POLICY)
    library, clips = freeze_library(ROOT, pair_policy)
    rest = library_rest_pose_v1(clips)
    assert len(clips) == 35 and all(np.array_equal(c['positions'][0], rest) for c in clips.values())
    names = list(next(iter(clips.values()))['joint_names'])
    assert rest[names.index('left_elbow_joint')] == pytest.approx(0.25)
    broken = {k: {'positions': v['positions'].copy()} for k, v in list(clips.items())[:2]}
    broken[next(iter(broken))]['positions'][0, 0] += 1e-9
    with pytest.raises(ValueError, match='one rest pose'):
        library_rest_pose_v1(broken)


def test_rest_tail_config_is_versioned_and_needs_connector_scope(tmp_path):
    policy, _ = load_sequence_policy(ROOT, POLICY)
    assert rest_tail_config(policy)['max_exit_frames'] == 60
    for change in ({'version': 'rest_tail_v9'}, {'extra': 1}, {'max_exit_frames': 0}):
        bad = copy.deepcopy(policy)
        bad['assembly']['rest_tail'].update(change)
        with pytest.raises(ValueError):
            validate_sequence_policy(bad)
    legacy = json.loads((ROOT/'config/sequence_policy_user_protected_v1.json').read_text())
    legacy['assembly']['rest_tail'] = copy.deepcopy(policy['assembly']['rest_tail'])
    (tmp_path/'p.json').write_text(json.dumps(legacy))
    with pytest.raises(ValueError, match='connector-only'):
        load_sequence_policy(ROOT, tmp_path/'p.json')


@pytest.fixture(scope='module')
def kit(tmp_path_factory):
    folder = tmp_path_factory.mktemp('tail')
    # The verifier reloads the sequence policy; on clips-v2 its pair policy is rebound to bundle v5 as here.
    patch = pytest.MonkeyPatch()
    patch.setattr(sequence_verification, 'load_sequence_policy', load_sequence_policy_on_clips_v2)
    policy, pair_policy = load_sequence_policy_on_clips_v2(ROOT, POLICY)
    context = build_pair_context_v2(ROOT, pair_policy)
    library, clips = freeze_library(ROOT, pair_policy)
    identity = run_identity(library, pair_policy)
    trajectory = next(x for x in iter_deterministic_attempts_v2(context, 'HURT', 'WHERE', seed=5412) if x.trajectory).trajectory
    path = folder/'HURT__WHERE.json'
    save_pair_trajectory(path, trajectory)
    edge = {'run_id': 'fixture', 'attempt_id': 'deterministic', 'candidate_file': path.name,
            'candidate_file_sha256': file_hash(path), 'trajectory': trajectory}
    record = plan_rest_tail_v1(context, 'WHERE', rest_tail_config(policy))
    tail_path = folder/'WHERE.rest_tail.json'
    tail_path.write_text(json.dumps(record))
    tail = {'gloss': 'WHERE', 'file': tail_path.name, 'file_sha256': file_hash(tail_path), 'selected': record['selected']}
    implementation = sequence_identity(ROOT, policy, library, identity)
    sequence = assemble_sequence('HURT__WHERE', [edge], policy=policy, sequence_identity=implementation, rest_tail=tail)
    saved = folder/'sequence.json'
    save_sequence(saved, sequence, policy)
    yield {'folder': folder, 'policy': policy, 'record': record, 'edge': edge, 'tail': tail, 'clips': clips,
           'sequence': sequence, 'saved': saved, 'implementation': implementation}
    patch.undo()


def test_planned_tail_starts_after_the_core_and_ends_at_rest(kit):
    record, selected = kit['record'], kit['record']['selected']
    assert record['status'] == 'TIMED_CANDIDATE' and selected is not None
    core_end = record['protected_core_frames'][1]
    assert selected['exit_frame'] >= core_end
    assert selected['core_gap_frames'] == selected['exit_frame'] - core_end + selected['connector_frames']
    passing = [a for a in record['attempts'] if a['status'] == 'TIMED_CANDIDATE']
    assert selected['core_gap_frames'] == min(a['core_gap_frames'] for a in passing)
    rest = library_rest_pose_v1(kit['clips'])
    assert selected['boundary']['end']['position'] == rest.tolist()
    assert not any(selected['boundary']['end']['velocity']) and not any(selected['boundary']['end']['acceleration'])


def test_sequence_ends_on_the_rest_pose(kit):
    sequence = kit['sequence']
    last = sequence['word_instances'][-1]
    assert last['source_frames'][1] == kit['record']['selected']['exit_frame']
    first, end = sequence['rest_tail']['segment_indices']
    assert end == len(sequence['segments']) - 1
    replay = _full_replay(sequence, {g: kit['clips'][g] for g in ('HURT', 'WHERE')})
    rest = library_rest_pose_v1(kit['clips'])
    assert np.allclose(replay['positions'][-1], rest, atol=1e-9, rtol=0)


def test_verifier_gates_the_tail_as_a_connector(kit):
    evidence = verify_saved_sequence_v1(ROOT, kit['saved'], POLICY, candidate_root=kit['folder'])
    assert evidence['validation_complete'] and evidence['rest_tail_present'] is True
    assert evidence['rest_tail_source_check']['coefficients_identical'] is True
    tail = evidence['rest_tail']
    assert tail['gloss'] == 'WHERE' and tail['boundary']['entry']['position_jump_rad'] <= 1e-6
    assert tail['boundary']['entry']['velocity_jump_arm_rad_s'] <= 1e-5
    assert not [r for r in evidence['reason_codes'] if r.startswith('REST_TAIL_')]
    assert all(c['poses_bitwise_equal'] for c in evidence['protected_instance_checks'])
    tail_segments = range(kit['sequence']['rest_tail']['segment_indices'][0], len(kit['sequence']['segments']))
    assert {m['segment_index'] for m in evidence['dense_recheck_result']} >= set(tail_segments)


def _resave(path, sequence):
    path.write_text(json.dumps({'schema_version': 1, 'sequence': sequence, 'sequence_hash': json_hash(sequence)}))


@pytest.mark.parametrize('mutation', [
    lambda s: s['segments'][-1]['coefficients'][0].__setitem__(5, s['segments'][-1]['coefficients'][0][5] + 1e-3),
    lambda s: s['rest_tail']['source'].update(file_sha256='3' * 64),
])
def test_verifier_rejects_tail_tampering(kit, tmp_path, mutation):
    sequence = copy.deepcopy(kit['sequence'])
    mutation(sequence)
    path = tmp_path/'tampered.json'
    _resave(path, sequence)
    evidence = verify_saved_sequence_v1(ROOT, path, POLICY, candidate_root=kit['folder'])
    assert evidence['numerical_checks_passed'] is not True


@pytest.mark.parametrize('mutation, message', [
    (lambda s: s.pop('rest_tail'), 'rest tail'),
    (lambda s: s['rest_tail'].update(exit_frame=s['rest_tail']['exit_frame'] + 1), 'last occurrence'),
    (lambda s: s['rest_tail']['boundary']['end']['velocity'].__setitem__(0, 1e-3), 'Declared boundary|zero velocity'),
    (lambda s: s['rest_tail']['rest_pose']['position'].__setitem__(0, 0.5), 'rest pose'),
    (lambda s: s['segments'].append(copy.deepcopy(s['segments'][-1])), 'contiguous|trailing'),
])
def test_contract_rejects_malformed_tails(kit, mutation, message):
    sequence = copy.deepcopy(kit['sequence'])
    mutation(sequence)
    with pytest.raises(ValueError, match=message):
        validate_sequence_v1(sequence, kit['policy'])


def test_assembly_requires_a_tail_exactly_when_the_policy_asks(kit):
    with pytest.raises(SequenceAssemblyError) as error:
        assemble_sequence('HURT__WHERE', [kit['edge']], policy=kit['policy'], sequence_identity=kit['implementation'])
    assert error.value.code == 'REST_TAIL_POLICY_MISMATCH'
    with pytest.raises(SequenceAssemblyError) as error:
        assemble_sequence('HURT__WHERE', [kit['edge']], policy=kit['policy'], sequence_identity=kit['implementation'],
                          rest_tail={**kit['tail'], 'gloss': 'HURT'})
    assert error.value.code == 'REST_TAIL_UNAVAILABLE'
    legacy, _ = load_sequence_policy(ROOT, 'config/sequence_policy_hospital_sentences_v2.json')
    with pytest.raises(SequenceAssemblyError):
        assemble_sequence('HURT__WHERE', [kit['edge']], policy=legacy, sequence_identity=kit['implementation'],
                          rest_tail=kit['tail'])
