# TASK-19 — R5

[中文](TASK-19.md)

Status: verifier adaptation complete. Fresh saved-file reads reconstruct motions, user protection, robot geometry and all curve segments. Checks cover mode/policy binding, protection references, two occurrences, outer-cut rules, exact protected poses, relative timing, p/v/a, complete-clip quality, analytic connector limits/coupling/speed and 1×/2×/4× geometry. Source knot times snap only floating roundoff within 1e-12 seconds; tests verify bitwise-equal poses for both 115-frame COME instances. Automatic mode explicitly has approval_checks_passed=false and separate input_checks_passed=true.

Added intrinsic protected-source defect and full-curve extrema localization with source frame/time, replay/video time and joint. Worst source geometry records whether it is protected. No-candidate diagnosis cannot certify complete-curve numerical validation.

Command: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_user_protected_verification.py tests/test_pair_verification_v2.py tests/test_pair_runner_v2.py tests/test_user_protected_windows.py. Initial exit 1: 73 passed/2 failed because a new geometry annotation used np.bool and was not JSON serializable. Converting it to standard bool produced exit 0: 75 passed in 16.14s. Both logs are retained. Minimal reproduction: tests/test_pair_runner_v2.py::test_real_independent_verifier_reconstructs_saved_runner_outputs.

Covers lost repeats, deleted protection, altered protection references, forged approval, changed time_scale and smoothness-before-duration selection. Changed pair_verification_v2.py and new tests; see changes.json.

Deviation: corrected the new evidence JSON type. No thresholds, failed evidence or original motions were altered. Four-pair independent outcomes remain R6 work.
