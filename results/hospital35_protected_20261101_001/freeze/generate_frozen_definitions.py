"""P0-7 frozen definitions: 111-case sequence policy and the 4+33+132+1056 pair batches.

Writes new files only (never overwrites). A copy of this generator is kept with
the freeze evidence.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
RUN = "results/hospital35_protected_20261101_001"
PAIR_POLICY = "config/transition_policy_user_protected_hospital35_v1.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital35_v1.json"


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write_new(relative, value):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    pair_policy = json.loads((ROOT / PAIR_POLICY).read_text(encoding="utf-8"))
    glosses = pair_policy["scope"]["expected_glosses"]
    old = json.loads((ROOT / "config/sequence_policy_user_protected_v1.json").read_text(encoding="utf-8"))
    others = [g for g in glosses if g not in ("COME", "NOW")]
    assert len(others) == 33
    new_cases = [case for w in others for case in (f"COME__{w}__NOW", f"NOW__{w}__COME", f"{w}__{w}__{w}")]
    cases = [*old["cases"], *new_cases]
    assert len(cases) == 111 and len(set(cases)) == 111
    policy = {**old, "policy_id": "group3-hospital35-sequence-development-v1",
              "pair_policy": {"path": PAIR_POLICY, "sha256": sha(PAIR_POLICY)}, "cases": cases,
              "case_note": ("Original 12 COME/NOW engineering cases plus, for each other word w in policy order, "
                            "COME__w__NOW, NOW__w__COME and w__w__w (99). Directed engineering coverage only: not all "
                            "35^3 triples, not all five-word chains, not ASL sentences and not an independent semantic test set.")}
    write_new(SEQUENCE_POLICY, policy)

    universe = [f"{s}__{t}" for s in glosses for t in glosses]
    regression = ["COME__NOW", "NOW__COME", "COME__COME", "NOW__NOW"]
    selfs = [f"{w}__{w}" for w in others]
    hub = [p for w in others for p in (f"COME__{w}", f"{w}__COME", f"NOW__{w}", f"{w}__NOW")]
    taken = set(regression) | set(selfs) | set(hub)
    rest = [p for p in universe if p not in taken]
    assert (len(regression), len(selfs), len(hub), len(rest)) == (4, 33, 132, 1056)
    assert len(taken | set(rest)) == 1225 and len(taken) + len(rest) == 1225
    batches, order = [], []
    for group, pairs in (("regression", regression), ("self", selfs), ("hub", hub), ("rest", rest)):
        for start in range(0, len(pairs), 16):
            batch_id = f"{group}_{start // 16 + 1:03d}"
            relative = f"{RUN}/batches/{batch_id}.json"
            write_new(relative, {"pair_ids": pairs[start:start + 16]})
            batches.append({"batch_id": batch_id, "group": group, "file": relative, "sha256": sha(relative),
                            "pair_count": len(pairs[start:start + 16])})
            order.append(batch_id)
    manifest = {"schema_version": 1, "kind": "hospital35_pair_batches_v1",
                "policy": {"path": PAIR_POLICY, "sha256": sha(PAIR_POLICY)},
                "group_counts": {"regression": 4, "self": 33, "hub": 132, "rest": 1056}, "pair_universe_count": 1225,
                "definition": {"regression": "the four COME/NOW ordered pairs",
                               "self": "every other word with itself, policy order",
                               "hub": "for each other word w: COME->w, w->COME, NOW->w, w->NOW",
                               "rest": "the 33x32 ordered pairs of the other words, universe order"},
                "batches": batches, "order": order,
                "limits": {"max_pairs_per_batch": 16, "soft_wall_time_s": 7200, "min_free_gib": 5}}
    write_new(f"{RUN}/batches/manifest.json", manifest)
    print(json.dumps({"cases": len(cases), "batches": len(batches),
                      "group_batches": {g: sum(b["group"] == g for b in batches) for g in ("regression", "self", "hub", "rest")},
                      "sequence_policy_sha256": sha(SEQUENCE_POLICY), "batch_manifest_sha256": sha(f"{RUN}/batches/manifest.json")}))


if __name__ == "__main__":
    sys.exit(main())
