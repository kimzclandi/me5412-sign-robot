#!/usr/bin/env python3
"""One pre-registered deterministic fit; refuses a second run in v1."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.learned_motion import encode_text, phase_features, predict_positions, generate
from sign_robot.motion import load_motion, load_model


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    output = ROOT / "results/motion_learning/v1"
    output.mkdir(parents=True, exist_ok=True)
    protocol = json.loads((ROOT / "config/motion_learning_v1.json").read_text(encoding="utf-8"))
    with (output / "attempt.started.json").open("x", encoding="utf-8") as lock:
        json.dump({"started_utc": datetime.now(timezone.utc).isoformat(), "attempt": 1}, lock)
    started = time.perf_counter()
    try:
        for relative, expected in protocol["input_sha256"].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, f"Frozen input changed: {relative}"
        source_files = ["src/sign_robot/learned_motion.py", "scripts/train_motion_model.py", "config/motion_learning_v1.json"]
        dump(output / "execution_manifest.json", {"source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_files},
             "input_sha256": protocol["input_sha256"], "python": sys.version, "numpy": np.__version__,
             "embedding_weights_sha256": hashlib.sha256((ROOT / "models/all-MiniLM-L6-v2/model.safetensors").read_bytes()).hexdigest()})
        np.random.seed(protocol["seed"])
        actions = list(protocol["training_texts"])
        demonstrations = {aid: load_motion(aid) for aid in actions}
        names = demonstrations[actions[0]]["joint_names"]
        neutral = demonstrations[actions[0]]["positions"][0].copy()
        info = json.loads((ROOT / "assets/robot/model_info.json").read_text(encoding="utf-8"))
        index = {str(n): i for i, n in enumerate(names)}
        children = {r["child"] for r in info["couplings"]}
        arm_words = ("shoulder_", "elbow_", "wrist_")
        active = np.asarray([i for i, name in enumerate(names) if name not in children and
                            (str(name).startswith(("L_", "R_")) or any(word in str(name) for word in arm_words))])
        assert len(active) == 26 and len(names) == 53 and len(children) == 12
        model = load_model()
        lower = np.asarray([model.jnt_range[model.joint(str(names[i])).id, 0] for i in active])
        upper = np.asarray([model.jnt_range[model.joint(str(names[i])).id, 1] for i in active])
        for rule in info["couplings"]:
            parent_col = int(np.flatnonzero(active == index[rule["parent"]])[0])
            low, high = model.jnt_range[model.joint(rule["child"]).id]
            lo, hi = sorted(((low-rule["offset"])/rule["multiplier"], (high-rule["offset"])/rule["multiplier"]))
            lower[parent_col], upper[parent_col] = max(lower[parent_col], lo), min(upper[parent_col], hi)
        centers = np.linspace(0, 1, protocol["rbf_count"])
        embeddings = {aid: encode_text(protocol["training_texts"][aid]) for aid in actions}
        e_rows, b_rows, y_rows, splits = [], [], [], {}
        for aid, motion in demonstrations.items():
            assert len(motion["positions"]) == protocol["expected_frames"][aid]
            assert np.array_equal(motion["joint_names"], names) and np.allclose(motion["positions"][0], neutral)
            count = len(motion["positions"])
            mask = np.arange(count) % 2 == 0
            phase = motion["timestamps_s"] / motion["timestamps_s"][-1]
            e_rows.append(np.tile(embeddings[aid], (int(mask.sum()), 1)))
            b_rows.append(phase_features(phase[mask], centers, protocol["rbf_width"]))
            y_rows.append(motion["positions"][mask][:, active] - neutral[active])
            splits[aid] = {"train_indices": np.flatnonzero(mask).tolist(), "validation_indices": np.flatnonzero(~mask).tolist()}
        e, b, target = map(np.concatenate, (e_rows, b_rows, y_rows))
        gram = (e @ e.T) * (b @ b.T)
        dual = np.linalg.solve(gram + len(e) * protocol["ridge_lambda"] * np.eye(len(e)), target)
        weights = np.einsum("ni,nk,nj->ikj", e, b, dual, optimize=True)
        c = {"weights": weights, "centers": centers, "width": np.asarray(protocol["rbf_width"]),
             "neutral": neutral, "active_indices": active, "joint_names": names,
             "effective_lower": lower, "effective_upper": upper,
             "child_indices": np.asarray([index[r["child"]] for r in info["couplings"]]),
             "parent_indices": np.asarray([index[r["parent"]] for r in info["couplings"]]),
             "multipliers": np.asarray([r["multiplier"] for r in info["couplings"]]),
             "offsets": np.asarray([r["offset"] for r in info["couplings"]])}
        np.savez_compressed(output / "model.npz", **c)
        dump(output / "model.json", {"model_type": "learned_text_phase_tensor_ridge", "parameter_shape": list(weights.shape),
             "parameter_count": int(weights.size), "active_joint_names": names[active].tolist(),
             "durations_s": {aid: float(m["timestamps_s"][-1]) for aid, m in demonstrations.items()},
             "independent_demonstrations": 3, "frames": 732, "train_frames": len(e), "validation_frames": 732-len(e),
             "protocol": protocol, "default_enabled": False, "asl_reviewed": False})
        dump(output / "split_indices.json", splits)
        report = {"attempt": 1, "validation_scope": "same-demonstration odd-frame interpolation; no independent action generalization",
                  "fit": {}, "generated": [], "paraphrase_probes": [], "default_enabled": False, "asl_reviewed": False}
        fitting_ok = True
        for aid, motion in demonstrations.items():
            predicted, projection = predict_positions(embeddings[aid], motion["timestamps_s"]/motion["timestamps_s"][-1], c)
            metrics = {"projection": projection}
            for name, indices in splits[aid].items():
                error = predicted[indices][:, active] - motion["positions"][indices][:, active]
                metrics[name] = {"active_rmse_rad": float(np.sqrt(np.mean(error**2))), "active_max_error_rad": float(np.abs(error).max()), "frames": len(indices)}
            held = metrics["validation_indices"]
            metrics["heldout_accepted"] = held["active_rmse_rad"] <= 0.035 and held["active_max_error_rad"] <= 0.12
            fitting_ok &= metrics["heldout_accepted"]
            report["fit"][aid] = metrics
        model_meta = json.loads((output / "model.json").read_text(encoding="utf-8"))
        model_meta["fit_accepted"] = bool(fitting_ok)
        model_meta["heldout_metrics"] = report["fit"]
        dump(output / "model.json", model_meta)
        for aid in actions:
            for scale in protocol["generation"]["duration_scales"]:
                result = generate(protocol["training_texts"][aid], float(demonstrations[aid]["timestamps_s"][-1])*scale)
                assert result["positions"] is not None, result
                stem = aid if scale == 1 else aid + "_slow120"
                np.savez_compressed(output / f"{stem}.npz", positions=result.pop("positions"), timestamps_s=result.pop("timestamps_s"), joint_names=result.pop("joint_names"))
                result["file"] = f"results/motion_learning/v1/{stem}.npz"
                result["duration_scale"] = scale
                dump(output / f"{stem}.json", result)
                report["generated"].append(result)
                print(stem, json.dumps(result["metrics"]), flush=True)
        for aid, text in protocol["paraphrase_probes"].items():
            result = generate(text)
            if result["positions"] is not None:
                np.savez_compressed(output / f"{aid}_paraphrase.npz", positions=result.pop("positions"), timestamps_s=result.pop("timestamps_s"), joint_names=result.pop("joint_names"))
            report["paraphrase_probes"].append(result)
        report["fit_accepted"] = bool(fitting_ok)
        report["engineering_accepted"] = all(row["geometric_accepted"] for row in report["generated"])
        report["accepted"] = report["fit_accepted"] and report["engineering_accepted"]
        report["elapsed_s"] = time.perf_counter()-started
        report["model_sha256"] = hashlib.sha256((output / "model.npz").read_bytes()).hexdigest()
        dump(output / "report.json", report)
        print(json.dumps({key: report[key] for key in ("fit_accepted", "engineering_accepted", "accepted", "elapsed_s")}), flush=True)
    except Exception:
        (output / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
