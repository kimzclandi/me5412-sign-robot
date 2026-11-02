import importlib.util

from sign_robot.motion import ROOT

spec=importlib.util.spec_from_file_location('auto_render',ROOT/'scripts/render_user_protected_pairs.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_cut_and_protected_phase_labels_do_not_hide_removed_frames():
    word={'gloss':'COME','protected_core_frames':[27,141],'source_frames':[27,160]}
    assert module.cut_ranges(27,160,201)==[[0,26],[161,200]]
    assert module.original_phase(26,word,201)[0]=='cut'
    assert module.original_phase(27,word,201)[0]=='protected'
    assert module.original_phase(141,word,201)[0]=='protected'
    assert module.original_phase(142,word,201)[0]=='retained'
    assert module.original_phase(161,word,201)[0]=='cut'


def test_failed_preview_is_persistently_labelled_failed_and_unselected():
    assert 'FAILED' in module.result_label(False) and 'NOT SELECTED' in module.result_label(False)
    assert 'FORMAL OFF' in module.result_label(True)
