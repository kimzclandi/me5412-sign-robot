# TASK-17 — R3

[中文](TASK-17.md)

Status: complete. Source exit is at/after protection end; target entry is at/before protection start. Every point records original time, pose, one-sided linear velocity/zero acceleration, limit/coupling errors, native minimum clearance/worst contact, speed ratio and validity. Algorithm order prefers low boundary speed then proximity to protection; outer cuts use protection bounds without changing protected frames.

Real command: scripts/screen_user_protected_cuts.py --policy config/transition_policy_user_protected_v1.json --output results/user_protected_auto_20261031_001/R3/cut_screen.json with all four --pair arguments. Corrected command exited 0. Valid source/target counts: COME→NOW 60/4; NOW→COME 2/28; COME→COME 60/28; NOW→NOW 2/4. Evidence uses actual motions and robot geometry, with algorithm provenance.

Initial tests: exit 0, 60 passed in 13.12s; final boundary-tolerance regression is recorded in cuts_final_pytest.command.json. First CLI invocation exited 1 due to an unmatched-brace SyntaxError; its command/log are retained as the minimal reproduction. Corrected rerun passed.

Changed pair_routes.py; added scripts/screen_user_protected_cuts.py and tests/test_user_protected_cuts.py. Deviation: a dedicated screening CLI persists all point evidence. No thresholds or human review states changed.

R4 real timing revealed outward-limit tangents and prompted supplemental screening. Final valid source/target counts are 56/3, 1/28, 56/28, 1/3; see TASK-18.en.md and cut_screen_with_tangents.json. Initial screening evidence remains intact.
