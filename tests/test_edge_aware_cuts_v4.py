"""v4 ranks cuts by retained-edge jerk; v1 ranking stays for older policies."""
from copy import deepcopy

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (EDGE_AWARE_CUT_GENERATOR, FULL_CLIP_METHOD_V2, load_policy,
    validate_policy_v2)
from sign_robot.pair_routes import (PairWorkBudget, build_pair_context_v2, endpoint_pairs_v1,
    retained_edge_jerk_v2, valid_endpoint_choices_v2)


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


def test_v4_changes_only_cut_generator():
    old, new = _load('transition_policy_user_protected_v3.json'), _load('transition_policy_user_protected_v4.json')
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'endpoints'}
    assert {k for k in old['endpoints'] if old['endpoints'][k] != new['endpoints'][k]} == {'generator_version'}
    assert new['endpoints']['generator_version'] == EDGE_AWARE_CUT_GENERATOR
    assert new['formal_acceptance_enabled'] is False


def test_edge_aware_cuts_require_transition_scope():
    policy = deepcopy(_load('transition_policy_user_protected_v4.json'))
    policy['quality']['full_clip_method'] = FULL_CLIP_METHOD_V2
    with pytest.raises(ValueError, match='Edge-aware'):
        validate_policy_v2(policy)


def test_retained_edge_cost_is_zero_at_core_and_grows_outward():
    t = np.arange(20) / 30
    clip = {'timestamps_s': t, 'positions': np.stack([np.sin(7 * t), t**3], axis=1)}
    core = (5, 12)
    assert retained_edge_jerk_v2(clip, core, 12, 'source') == 0.0
    assert retained_edge_jerk_v2(clip, core, 5, 'target') == 0.0
    tail = [retained_edge_jerk_v2(clip, core, f, 'source') for f in range(12, 20)]
    head = [retained_edge_jerk_v2(clip, core, f, 'target') for f in range(5, -1, -1)]
    assert np.all(np.diff(tail) >= 0) and np.all(np.diff(head) >= 0) and tail[-1] > 0


@pytest.fixture(scope='module')
def contexts():
    return {name: build_pair_context_v2(ROOT, _load(f'transition_policy_user_protected_{name}.json')) for name in ('v3', 'v4')}


def test_v4_shortlist_prefers_cuts_at_core_bounds_and_v3_ranking_is_unchanged(contexts):
    v3, v4 = contexts['v3'], contexts['v4']
    old = endpoint_pairs_v1(v3, valid_endpoint_choices_v2(v3, 'COME', 'COME', PairWorkBudget(v3.policy)))
    assert old[0] == (177, 23)
    selection = valid_endpoint_choices_v2(v4, 'COME', 'COME', PairWorkBudget(v4.policy))
    pairs = endpoint_pairs_v1(v4, selection)
    assert len(pairs) == 8 and pairs[0] == (132, 27)
    assert all(a >= 132 and b <= 27 for a, b in pairs)
    clip = v4.clips['COME']
    costs = [retained_edge_jerk_v2(clip, (27, 132), a, 'source') + retained_edge_jerk_v2(clip, (27, 132), b, 'target')
             for a, b in pairs]
    assert costs == sorted(costs)
