"""User protection v2 (MORNING ends at 37, NURSE at 75) and per-word staged exits (staged_exit_v1)."""
import copy
import json

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import STAGED_EXIT_METHOD, load_policy, staged_group_mask, validate_policy_v2
from sign_robot.pair_routes import PairWorkBudget, build_pair_context_v2, staged_exit_knots, valid_endpoint_choices_v2
from sign_robot.pair_search import iter_rrt_attempts_v2
from sign_robot.sequence_contract import library_rest_pose_v1

OLD, NEW = 'transition_policy_hospital_sentences_fast_v3.json', 'transition_policy_hospital_sentences_fast_v4.json'


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


@pytest.fixture(scope='module')
def context():
    return build_pair_context_v2(ROOT, _load(NEW))


def test_protection_v2_changes_only_morning_and_nurse_ends():
    old = json.loads((ROOT/'config/user_protected_hospital35_v1.json').read_text())['records']
    new = json.loads((ROOT/'config/user_protected_hospital35_v2.json').read_text())['records']
    changed = {b['gloss']: (a['protected_core_frames'], b['protected_core_frames']) for a, b in zip(old, new) if a != b}
    assert changed == {'MORNING': ([26, 69], [26, 37]), 'NURSE': ([38, 79], [38, 75])}


def test_new_policy_changes_only_protection_and_staged_exits():
    old, new = _load(OLD), _load(NEW)
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'endpoints', 'planner'}
    assert {k for k in new['endpoints'] if new['endpoints'][k] != old['endpoints'][k]} == {
        'window_version', 'protection_file', 'protection_bundle_sha256'}
    assert {k for k in new['planner'] if new['planner'].get(k) != old['planner'].get(k)} == {'staged_exits'}
    assert sorted(new['planner']['staged_exits']['words']) == ['MORNING', 'NURSE']


@pytest.mark.parametrize('change', [
    lambda s: s['words']['NURSE']['stages'][0].update(group='left_foot'),
    lambda s: s['words']['NURSE']['stages'][0].update(to=['somewhere']),
    lambda s: s['words']['NURSE']['stages'][2].update(to=['ik:up:2']),  # wrist groups have no IK target
    lambda s: s['words']['NURSE']['stages'][1].update(to=['ik:up:9']),
    lambda s: s['words'].update(GOODBYE=s['words']['NURSE']),
    lambda s: s.update(version='staged_exit_v9'),
])
def test_staged_exit_config_is_validated(change):
    policy = _load(NEW)
    change(policy['planner']['staged_exits'])
    with pytest.raises(ValueError):
        validate_policy_v2(policy)


def test_staged_words_exit_exactly_at_the_new_core_end(context):
    for source, target, end in (('NURSE', 'BLOOD-DRAW', 75), ('MORNING', 'NIGHT', 37)):
        selection = valid_endpoint_choices_v2(context, source, target, PairWorkBudget(context.policy))
        assert selection['source']['protected_core_frames'][1] == end
        assert selection['source']['valid_frames'] == [end] and selection['source']['staged_exit'] is True


def test_nurse_stages_move_one_group_at_a_time(context):
    clip, target = context.clips['NURSE'], context.clips['BLOOD-DRAW']
    names = clip['joint_names']
    a, b = clip['positions'][75], target['positions'][34]
    staged = {'stages': [{'group': 'right_arm', 'to': ['ik:out+up:2']},
                         {'group': 'left_upper_arm', 'to': ['ik:out+forward:3']},
                         {'group': 'left_wrist', 'to': ['zero']}]}
    [(name, knots)] = list(staged_exit_knots(a, b, library_rest_pose_v1(context.clips), names, staged, context.model))
    assert name == 'right_arm:ik:out+up:2+left_upper_arm:ik:out+forward:3+left_wrist:zero'
    assert len(knots) == 5 and np.array_equal(knots[0], a) and np.array_equal(knots[-1], b)
    for step, group in enumerate(('right_arm', 'left_upper_arm', 'left_wrist')):
        moved = knots[step + 1] != knots[step]
        assert moved.any() and not (moved & ~staged_group_mask(names, group)).any()
    assert np.all(knots[3][staged_group_mask(names, 'left_wrist')] == 0.0)
    fingers = np.array([str(n).startswith('R_') for n in names])
    assert np.array_equal(knots[1][fingers], a[fingers])  # arm IK leaves the fingers alone


def test_staged_words_skip_rrt_and_generic_routes(context):
    assert list(iter_rrt_attempts_v2(context, 'NURSE', 'BLOOD-DRAW', seed=5412)) == []
    policy = copy.deepcopy(context.policy)
    assert STAGED_EXIT_METHOD not in policy['planner']['methods']
