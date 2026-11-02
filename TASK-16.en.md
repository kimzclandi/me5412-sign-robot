# TASK-16 — R2

[中文](TASK-16.md)

Status: complete. Added distinct user-protection records/types and algorithm provenance. Automatic windows have no human approval fields; legacy review mode remains compatible. User time text, conservative frames, motion path/hash/count/timing and prior-video binding limitation are traceable. New policy freezes the existing numerical constraints, quality, validation and planner values with formal acceptance disabled; see R2/engineering_freeze.json.

Changed files and absolute paths/hashes are in changes.json. Approval time now has an injectable _utc_now clock; tests use a fixed time while production retains UTC expiry validation and date-negative tests.

Command: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_contract_v2.py tests/test_pair_windows_v2.py tests/test_user_protected_windows.py tests/test_pair_routes_v2.py tests/test_pair_verification_v2.py tests/test_pair_runner_v2.py. Exit 0: 129 passed in 19.48s. Log R2/contract_windows_pytest.log. Covers wrong motion/version/conservative ranges, forged approval fields, lost occurrences, deleted protection and legacy compatibility.

Decision: explicit endpoint_mode within v2, mutually exclusive protection versus legacy approval fields, algorithm-only generated provenance and pending formal review.

Deviation: added tests/conftest.py to remove wall-clock date dependence. R3–R5 generation and independent verification adaptations remain pending; no pilot success is claimed.
