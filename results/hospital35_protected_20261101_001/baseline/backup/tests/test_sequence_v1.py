"""Multi-word sequence contract, one-slice assembly and independent chain verification."""
import copy
import itertools
import json

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (file_hash, freeze_library, json_hash, polynomial_boundary_v2, read_json, read_motion,
    run_identity, save_pair_trajectory, validate_trajectory_v2)
from sign_robot.pair_routes import build_pair_context_v2, iter_deterministic_attempts_v2
from sign_robot.pair_verification_v2 import _full_replay
from sign_robot.sequence_assembly import SequenceAssemblyError, assemble_sequence, combinations
from sign_robot.sequence_contract import (SEQUENCE_ENTRYPOINTS, load_sequence_policy, read_sequence, save_sequence,
    sequence_code_files, sequence_glosses, sequence_identity, validate_sequence_v1)
from sign_robot.sequence_verification import verify_saved_sequence_v1

POLICY = 'config/sequence_policy_user_protected_v1.json'


@pytest.fixture(scope='module')
def kit(tmp_path_factory):
    folder = tmp_path_factory.mktemp('pairs')
    policy, pair_policy = load_sequence_policy(ROOT, POLICY)
    context = build_pair_context_v2(ROOT, pair_policy)
    library, _ = freeze_library(ROOT, pair_policy)
    identity = run_identity(library, pair_policy)
    candidates = {}
    for a, b in itertools.product(('COME', 'NOW'), repeat=2):
        trajectory = next(x for x in iter_deterministic_attempts_v2(context, a, b, seed=5412) if x.trajectory).trajectory
        path = folder / f'{a}__{b}.json'
        save_pair_trajectory(path, trajectory)
        candidates[f'{a}__{b}'] = {'run_id': 'fixture', 'attempt_id': 'deterministic', 'candidate_file': path.name,
                                   'candidate_file_sha256': file_hash(path), 'trajectory': trajectory}
    return {'folder': folder, 'policy': policy, 'library': library, 'identity': identity, 'candidates': candidates,
            'sequence_identity': sequence_identity(ROOT, policy, library, identity)}


def build(kit, sequence_id, **kwargs):
    glosses = sequence_id.split('__')
    edges = [kit['candidates'][f'{a}__{b}'] for a, b in zip(glosses, glosses[1:])]
    return assemble_sequence(sequence_id, edges, policy=kwargs.get('policy', kit['policy']),
                             sequence_identity=kwargs.get('sequence_identity', kit['sequence_identity']))


def clips(kit):
    return {w['gloss']: read_motion(ROOT/w['motion']) for w in kit['library']['words'] if w['gloss'] in ('COME', 'NOW')}


def rehash(identity, **changes):
    identity.update(changes)
    identity['identity_hash'] = json_hash({k: v for k, v in identity.items() if k != 'identity_hash'})


def resave(path, sequence):
    path.write_text(json.dumps({'schema_version': 1, 'sequence': sequence, 'sequence_hash': json_hash(sequence)}))


def test_policy_freezes_twelve_cases_and_binds_pair_policy(tmp_path):
    policy, pair_policy = load_sequence_policy(ROOT, POLICY)
    three = [c for c in policy['cases'] if c.count('__') == 2]
    assert three == ['__'.join(p) for p in itertools.product(('COME', 'NOW'), repeat=3)]
    assert len(policy['cases']) == 12 and sum(len(c.split('__')) for c in policy['cases']) == 44
    assert sum(len(c.split('__')) - 1 for c in policy['cases']) == 32
    assert policy['formal_acceptance_enabled'] is False and pair_policy['formal_acceptance_enabled'] is False
    broken = copy.deepcopy(policy)
    broken['pair_policy']['sha256'] = '0' * 64
    (tmp_path/'p.json').write_text(json.dumps(broken))
    with pytest.raises(ValueError, match='frozen hash'):
        load_sequence_policy(ROOT, tmp_path/'p.json')
    for bad in ('', 'COME', 'COME__NOW__COME__NOW__COME__NOW', 'COME__now'):
        with pytest.raises(ValueError):
            sequence_glosses(bad, policy)


def test_pair_v2_still_rejects_three_words(kit):
    trajectory = copy.deepcopy(kit['candidates']['COME__NOW']['trajectory'])
    trajectory['word_instances'].append({**trajectory['word_instances'][0], 'instance_id': 'extra'})
    with pytest.raises(ValueError, match='two explicit word instances'):
        validate_trajectory_v2(trajectory)


def test_middle_word_played_once_and_connectors_copied(kit):
    sequence = build(kit, 'COME__NOW__COME')
    words = sequence['word_instances']
    incoming = kit['candidates']['COME__NOW']['trajectory']
    outgoing = kit['candidates']['NOW__COME']['trajectory']
    assert words[1]['source_frames'] == [incoming['word_instances'][1]['source_frames'][0],
                                         outgoing['word_instances'][0]['source_frames'][1]]
    slices = [s for s in sequence['segments'] if s['kind'] == 'source_slice_v2']
    assert [s['word_instance_id'] for s in slices] == [w['instance_id'] for w in words]
    for edge, pair in zip(sequence['edges'], (incoming, outgoing)):
        first, last = edge['segment_indices']
        copied, original = sequence['segments'][first:last + 1], pair['segments'][1:-1]
        assert [c['coefficients'] for c in copied] == [o['coefficients'] for o in original]
        for c, o in zip(copied, original):
            assert c['end_time_s'] - c['start_time_s'] == pytest.approx(o['end_time_s'] - o['start_time_s'], abs=1e-12)
    words_clips = clips(kit)
    replay = _full_replay(sequence, words_clips)
    c0, c1 = words[1]['protected_core_frames']
    hits = [i for i in range(len(replay['positions']) - (c1 - c0))
            if np.array_equal(replay['positions'][i:i + c1 - c0 + 1], words_clips['NOW']['positions'][c0:c1 + 1])]
    assert len(hits) == 1


def test_two_word_degenerate_equals_pair_replay(kit):
    pair = kit['candidates']['NOW__COME']['trajectory']
    sequence = build(kit, 'NOW__COME')
    a, b = _full_replay(sequence, clips(kit)), _full_replay(pair, clips(kit))
    assert a['positions'].shape == b['positions'].shape
    assert np.allclose(a['positions'], b['positions'], atol=1e-12, rtol=0)


def test_repeated_words_get_distinct_occurrences_and_time_offsets(kit):
    sequence = build(kit, 'NOW__NOW__NOW__NOW__NOW')
    ids = [w['instance_id'] for w in sequence['word_instances']]
    assert len(set(ids)) == 5 and [w['position'] for w in sequence['word_instances']] == list(range(5))
    starts = [s['start_time_s'] for s in sequence['segments'] if s['kind'] == 'source_slice_v2']
    assert all(np.isclose(t * 30, round(t * 30), atol=1e-9) for t in starts) and starts == sorted(starts)
    validate_sequence_v1(sequence, kit['policy'])


def test_assembly_rejects_mismatched_references(kit):
    edge = copy.deepcopy(kit['candidates']['NOW__COME'])
    edge['trajectory']['word_instances'][0]['protection_sha256'] = '1' * 64
    with pytest.raises(SequenceAssemblyError) as error:
        assemble_sequence('COME__NOW__COME', [kit['candidates']['COME__NOW'], edge], policy=kit['policy'],
                          sequence_identity=kit['sequence_identity'])
    assert error.value.code == 'OCCURRENCE_REFERENCE_MISMATCH'
    with pytest.raises(SequenceAssemblyError):
        assemble_sequence('COME__NOW__COME', [kit['candidates']['COME__NOW']], policy=kit['policy'],
                          sequence_identity=kit['sequence_identity'])
    pools = {'A': [0, 1, 2], 'B': [0, 1]}
    assert combinations(pools, ['A', 'B'], 4) == [(0, 0), (0, 1), (1, 0), (1, 1)]


@pytest.mark.parametrize('mutation, message', [
    (lambda s: s['word_instances'][1].update(instance_id=s['word_instances'][0]['instance_id']), 'unique IDs'),
    (lambda s: s['word_instances'][1].update(source_frames=[10, 20]), 'protected core'),
    (lambda s: s['word_instances'][0].update(source_frames=[20, 132]), 'no implicit neutral'),
    (lambda s: s['segments'][3].update(start_time_s=s['segments'][3]['start_time_s'] + 1 / 30), 'contiguous'),
    (lambda s: s['segments'][1].update(kind='spline_v9'), 'representation'),
    (lambda s: s['pair_identity'].update(code_hash='2' * 64), 'pair identity hash'),
    (lambda s: s['edges'].reverse(), 'Edge endpoints'),
    (lambda s: s['edges'].pop(), 'connector group'),
])
def test_contract_rejects_malformed_sequences(kit, mutation, message):
    sequence = copy.deepcopy(build(kit, 'COME__NOW__COME'))
    mutation(sequence)
    with pytest.raises(ValueError, match=message):
        validate_sequence_v1(sequence, kit['policy'])


def test_identity_covers_sequence_entrypoints(tmp_path, kit):
    files = sequence_code_files(ROOT, kit['library']['code_files'])
    assert set(SEQUENCE_ENTRYPOINTS) <= set(files)
    assert {'src/sign_robot/sequence_contract.py', 'src/sign_robot/sequence_assembly.py',
            'src/sign_robot/sequence_verification.py', 'tests/test_sequence_v1.py'} <= set(files)
    for name in SEQUENCE_ENTRYPOINTS:
        (tmp_path/name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path/name).write_text('x')
    before = sequence_code_files(tmp_path, {})
    (tmp_path/SEQUENCE_ENTRYPOINTS[0]).write_text('y')
    assert sequence_code_files(tmp_path, {}) != before
    (tmp_path/SEQUENCE_ENTRYPOINTS[1]).unlink()
    with pytest.raises(ValueError, match='Missing sequence entry point'):
        sequence_code_files(tmp_path, {})


@pytest.fixture(scope='module')
def saved(kit, tmp_path_factory):
    path = tmp_path_factory.mktemp('sequence')/'sequence.json'
    save_sequence(path, build(kit, 'COME__NOW__COME'), kit['policy'])
    return path


def test_verifier_checks_every_occurrence_and_region(kit, saved):
    evidence = verify_saved_sequence_v1(ROOT, saved, POLICY, candidate_root=kit['folder'])
    assert evidence['validation_complete'] and evidence['input_checks_passed']
    assert evidence['formal_status'] == 'NOT_ENABLED' and evidence['pair_labels_inherited'] is False
    assert evidence['word_occurrences'] == 3 and evidence['connector_groups'] == 2
    assert len(evidence['protected_instance_checks']) == 3
    assert all(c['poses_bitwise_equal'] and c['replay_grid_poses_bitwise_equal'] for c in evidence['protected_instance_checks'])
    assert all(c['max_relative_timing_error_s'] <= 1e-12 for c in evidence['protected_instance_checks'])
    assert [t['edge_index'] for t in evidence['transitions']] == [0, 1]
    assert {s['instance_id'] for s in evidence['dense_recheck_result'] if s['kind'] == 'source_slice_v2'} == {
        'o0_COME', 'o1_NOW', 'o2_COME'}
    assert 'ALGORITHM_WINDOWS_NOT_HUMAN_REVIEWED' not in evidence['formal_pending_reasons']


def _tamper(kit, saved, tmp_path, mutation):
    sequence = read_sequence(saved, kit['policy'])
    mutation(sequence)
    path = tmp_path/'tampered.json'
    resave(path, sequence)
    return verify_saved_sequence_v1(ROOT, path, POLICY, candidate_root=kit['folder'])


@pytest.mark.parametrize('mutation', [
    lambda s: s['segments'][1]['coefficients'][0].__setitem__(5, s['segments'][1]['coefficients'][0][5] + 1e-3),
    lambda s: s['edges'][0]['source'].update(candidate_file_sha256='3' * 64),
    lambda s: s['edges'][1]['source'].update(candidate_file='COME__COME.json'),
    lambda s: rehash(s['sequence_identity'], sequence_code_hash='4' * 64),
    lambda s: s['word_instances'][1].update(protection_sha256='5' * 64),
])
def test_verifier_rejects_tampering(kit, saved, tmp_path, mutation):
    evidence = _tamper(kit, saved, tmp_path, mutation)
    assert evidence['numerical_checks_passed'] is not True and not evidence['validation_complete']


def test_verifier_rejects_contract_valid_connector_edit(kit, saved, tmp_path):
    def edit(sequence):
        edge = sequence['edges'][1]
        segment = sequence['segments'][edge['segment_indices'][1]]
        segment['coefficients'][0][3] += 1e-3
        edge['boundary']['end'] = polynomial_boundary_v2(segment, 'end')
    evidence = _tamper(kit, saved, tmp_path, edit)
    assert evidence['status'] == 'ERROR' and 'pair candidate' in evidence['diagnostic_details']['message']


def test_verifier_rejects_corrupt_envelope_and_middle_retime(kit, saved, tmp_path):
    envelope = read_json(saved)
    envelope['sequence']['segments'][3]['source_frames'] = [4, 76]
    (tmp_path/'bad.json').write_text(json.dumps(envelope))
    assert verify_saved_sequence_v1(ROOT, tmp_path/'bad.json', POLICY, candidate_root=kit['folder'])['status'] == 'ERROR'

    def retime(sequence):
        sequence['segments'][3]['time_scale'] = 1.1
    assert _tamper(kit, saved, tmp_path, retime)['status'] == 'ERROR'


def test_budget_exhaustion_is_incomplete_not_pass(kit, tmp_path):
    policy = copy.deepcopy(kit['policy'])
    policy['validation']['max_sampled_poses'] = 64
    path = tmp_path/'policy.json'
    path.write_text(json.dumps(policy))
    identity = sequence_identity(ROOT, policy, kit['library'], kit['identity'])
    sequence = build(kit, 'COME__NOW__COME', policy=policy, sequence_identity=identity)
    save_sequence(tmp_path/'s.json', sequence, policy)
    evidence = verify_saved_sequence_v1(ROOT, tmp_path/'s.json', path, candidate_root=kit['folder'])
    assert evidence['status'] == 'TIMEOUT' and evidence['numerical_checks_passed'] is None
    assert evidence['validation_complete'] is False
