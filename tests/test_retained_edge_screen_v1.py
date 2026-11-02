"""Retained-edge screen (no_new_arm_limit_contact_v1) and clamped-joint stop (clamped_joint_stop_v1)."""
import copy
import json

import numpy as np
import pytest

from sign_robot.motion import ROOT, load_model
from sign_robot.pair_contract import (
    CLAMPED_JOINT_STOP_V1, RETAINED_EDGE_SCREEN_V1, RETAINED_EDGE_SCREEN_V2, clamped_stop_joints, load_policy,
    new_arm_limit_frames, retained_edge_flags,
    read_motion, retained_edge_contacts, validate_policy_v2,
)
from sign_robot.pair_routes import PairWorkBudget, build_pair_context_v2, valid_endpoint_choices_v2
from sign_robot.pair_timing import boundary_state_v2, cut_boundary_state_v2

OLD, NEW = 'transition_policy_hospital_sentences_fast_v1.json', 'transition_policy_hospital_sentences_fast_v2.json'


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


@pytest.fixture(scope='module')
def nurse():
    library = {w['gloss']: w for w in json.loads((ROOT/'motions/hospital_v1_motions.json').read_text())['glosses']}
    clip = read_motion(ROOT/library['NURSE']['motion'])
    model = load_model(ROOT)
    bounds = np.array([model.joint(str(n)).range for n in clip['joint_names']])
    return clip, bounds, [str(n) for n in clip['joint_names']]


def test_new_policy_changes_only_the_two_endpoint_rules():
    old, new = _load(OLD), _load(NEW)
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'endpoints'}
    assert {k for k in new['endpoints'] if new['endpoints'][k] != old['endpoints'].get(k)} == {
        'retained_edge_screen', 'clamped_joint_stop'}
    assert new['endpoints']['retained_edge_screen'] == RETAINED_EDGE_SCREEN_V1
    assert new['endpoints']['clamped_joint_stop'] == CLAMPED_JOINT_STOP_V1
    for key in ('retained_edge_screen', 'clamped_joint_stop'):
        bad = copy.deepcopy(new)
        bad['endpoints'][key] = 'v9'
        with pytest.raises(ValueError):
            validate_policy_v2(bad)


def test_nurse_flip_after_the_core_is_flagged(nurse):
    clip, bounds, names = nurse
    core = (38, 79)  # user protection, config/user_protected_hospital35_v1.json
    flagged = new_arm_limit_frames(clip, core, bounds)
    assert not flagged[core[0]:core[1] + 1].any()
    # wrist roll on its stop at 80-82, mid-swing at 83-84, shoulder yaw on its -2.62 rad stop from 85
    assert np.flatnonzero(flagged[80:99]).tolist() == [0, 1, 2, *range(5, 19)]
    yaw = names.index('left_shoulder_yaw_joint')
    assert clip['positions'][86, yaw] == pytest.approx(bounds[yaw, 0], abs=1e-3)
    # the round-4 NURSE slice [38, 98] kept these frames strictly inside its cut
    assert retained_edge_contacts(clip, core, bounds, (38, 98)) == [80, 81, 82, *range(85, 98)]
    # the cut frame itself is the connector's start and is not counted
    assert retained_edge_contacts(clip, core, bounds, (38, 80)) == []


def test_clamped_stop_joints_take_direction_from_the_role():
    bounds = np.array([[-1.0, 1.0]] * 4)
    position = np.array([1.0 - 1e-6, 1.0 - 1e-6, -1.0 + 1e-6, 0.0])
    velocity = np.array([0.5, -0.5, -0.5, 0.5])
    assert clamped_stop_joints(position, velocity, 'source', bounds).tolist() == [True, False, True, False]
    assert clamped_stop_joints(position, velocity, 'target', bounds).tolist() == [False, True, False, False]


def test_cut_state_rests_only_the_clamped_wrist(nurse):
    clip, bounds, names = nurse
    plain = boundary_state_v2(clip, 80, 'source')
    assert cut_boundary_state_v2(clip, 80, 'source', _load(OLD), bounds) == plain
    rested = cut_boundary_state_v2(clip, 80, 'source', _load(NEW), bounds)
    changed = [names[i] for i, (a, b) in enumerate(zip(plain['velocity'], rested['velocity'])) if a != b]
    assert changed == ['left_wrist_roll_joint'] and rested['velocity'][names.index('left_wrist_roll_joint')] == 0.0
    assert plain['velocity'][names.index('left_wrist_roll_joint')] > 0.4
    assert rested['position'] == plain['position']


def test_nurse_exit_window_keeps_only_the_frame_before_the_flip():
    exits = {}
    for name in (OLD, NEW):
        policy = _load(name)
        context = build_pair_context_v2(ROOT, policy)
        exits[name] = valid_endpoint_choices_v2(context, 'NURSE', 'BLOOD-DRAW', PairWorkBudget(policy))['source']['valid_frames']
    # Round 4 could also cut at 80, but no connector carried the wrist roll's slope into its stop; it kept 98.
    assert {80, 98} <= set(exits[OLD])
    assert exits[NEW] == [80]


V3 = 'transition_policy_hospital_sentences_fast_v3.json'


def test_v2_screen_flags_only_the_proximal_flip(nurse):
    clip, bounds, names = nurse
    flagged, cuts = retained_edge_flags(clip, (38, 79), bounds, RETAINED_EDGE_SCREEN_V2)
    assert cuts is True
    assert np.flatnonzero(flagged).tolist() == list(range(82, 117))  # shoulder yaw leaves the core range, hits -2.62
    # round 4 kept 82-98; the cut frame now counts as kept
    assert retained_edge_contacts(clip, (38, 79), bounds, (38, 98), RETAINED_EDGE_SCREEN_V2) == list(range(82, 99))
    assert retained_edge_contacts(clip, (38, 79), bounds, (38, 81), RETAINED_EDGE_SCREEN_V2) == []


def test_v2_screen_leaves_wrist_only_contacts(nurse):
    _, bounds, _ = nurse
    library = {w['gloss']: w for w in json.loads((ROOT/'motions/hospital_v1_motions.json').read_text())['glosses']}
    for gloss, core, kept in (('MEDICINE', (27, 69), (27, 86)), ('DOCTOR', (34, 57), (23, 57))):
        clip = read_motion(ROOT/library[gloss]['motion'])
        assert retained_edge_contacts(clip, core, bounds, kept, RETAINED_EDGE_SCREEN_V1)  # v1 flagged wrists here
        assert retained_edge_contacts(clip, core, bounds, kept, RETAINED_EDGE_SCREEN_V2) == []


def test_v3_policy_changes_only_the_screen_version():
    old, new = _load(NEW), _load(V3)
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'endpoints'}
    assert new['endpoints'] == {**old['endpoints'], 'retained_edge_screen': RETAINED_EDGE_SCREEN_V2}
