"""Versioned retry policy: the frozen hospital35 pair policy with only the planner search budget raised.

Gates, validation budgets, endpoints, protection and the candidate cap stay byte-for-byte equal; the old
policy is not touched. Writes a new file only (never overwrites).
"""
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
BASE = "config/transition_policy_user_protected_hospital35_v1.json"
RETRY = "config/transition_policy_user_protected_hospital35_retry_budget_v1.json"
BUDGET = {"wall_time_s": 240.0, "max_collision_samples": 262144, "max_nodes": 16384, "max_time_attempts": 48}
RRT_WALL_TIME_S = 80.0


def main():
    base = json.loads((ROOT / BASE).read_text(encoding="utf-8"))
    policy = json.loads(json.dumps(base))
    policy["policy_id"] = "group3-hospital35-user-protected-development-retry-budget-v1"
    policy["planner"]["budget"].update(BUDGET)
    policy["planner"]["rrt"]["wall_time_s"] = RRT_WALL_TIME_S
    changed = sorted(f"planner.budget.{k}" for k in BUDGET) + ["planner.rrt.wall_time_s", "policy_id"]
    unchanged = {k: v for k, v in policy.items() if k not in ("planner", "policy_id")}
    assert unchanged == {k: v for k, v in base.items() if k not in ("planner", "policy_id")}
    assert {k: v for k, v in policy["planner"].items() if k not in ("budget", "rrt")} == \
        {k: v for k, v in base["planner"].items() if k not in ("budget", "rrt")}
    with open(ROOT / RETRY, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(policy, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"policy": RETRY, "sha256": hashlib.sha256((ROOT / RETRY).read_bytes()).hexdigest(),
                      "base": BASE, "base_sha256": hashlib.sha256((ROOT / BASE).read_bytes()).hexdigest(),
                      "changed": changed, "old_budget": base["planner"]["budget"], "old_rrt_wall_time_s": base["planner"]["rrt"]["wall_time_s"],
                      "new_budget": policy["planner"]["budget"]}))


if __name__ == "__main__":
    main()
