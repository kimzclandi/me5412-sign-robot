# Learned trajectory model v1

[中文](学习型轨迹模型.md) · **English** · [Documentation index](README.md)

This small preregistered experiment fitted once. Its only training material was three agent-authored candidate trajectories from the original system, totaling 732 highly correlated frames. These are not 732 independent demonstrations, and no new videos or real ASL motion were used for learning.

Inputs are a registered English meaning and continuous phase `u=t/T`. Frozen MiniLM encodes 384 dimensions. Adding a constant gives a tensor product with 40 Gaussian phase bases. Ridge regression fits weights W on even frames to predict 26 active upper-body coordinates. Fifteen other coordinates retain neutral posture; 12 passive coordinates follow original mimic formulas, yielding 53 coordinates. Predictions are projected into effective hardware bounds including passive constraints; correction magnitudes are explicitly reported.

The model is `q_active(e,u)=neutral+Phi(u)·(e·W)`: text features e, phase bases Phi, and weights W fitted with regularized least squares. Bases are multiplied by `4u(1-u)`, returning both endpoints to neutral. Bounds projection and passive reconstruction follow. Inference loads the learned `model.npz`, without reading original `motions/` trajectories. IDs only check eligibility and select default duration.

Zero-based even frames train; odd frames validate interpolation within the same demonstration. This is not independent motion, vocabulary, or user generalization. Three fixed extra paraphrases are exploratory and do not determine primary acceptance.

The protocol was saved before training in `config/motion_learning_v1.json`. Input/source hashes, weights, splits, metrics, and failures are in `results/motion_learning/v1/`. `scripts/train_motion_model.py` refuses retraining once `attempt.started.json` exists. Failures cannot be overwritten.

Acceptance: odd-frame active-joint RMSE ≤0.035 rad; maximum error ≤0.12 rad; original velocity limits; joint bounds; 12 passive constraints; framewise collision geometry. Projection must be ≤0.02 rad. A +20% duration resamples the continuous model into a slower new trajectory; it does not prove new-motion generalization.

`generate(text, duration_s=None, fps=30)` returns `positions[T,53]`, `timestamps_s[T]`, `joint_names[53]`, metrics, and status. Unknown content returns an empty trajectory. It does not drive a real robot. v1 is disabled by default; passing fit/engineering checks does not validate ASL comprehensibility, clinical applicability, or dynamics.

## Actual result of this experiment

One closed-form solve completed on the original computer. Training and nine candidate generation/checks took approximately 2.84 seconds. Training used 367 even frames; within-trajectory validation used 365 odd frames. Errors below are active-joint errors after explicitly reported bounds projection.

| Candidate | Odd frames | RMSE (rad) | Maximum error (rad) |
|---|---:|---:|---:|
| HELLO | 117 | 0.000430 | 0.004278 |
| THANK_YOU | 120 | 0.002528 | 0.046329 |
| PLEASE_WAIT | 128 | 0.000621 | 0.005549 |

All six primary trajectories (three default and three +20% durations) passed frozen engineering gates: zero final bounds/mimic error, no velocity violation, and no collision-geometry penetration over 1 mm. Maximum projection was about 0.001978 rad, below 0.02 rad. Small raw prediction violations remain recorded as `max_projection_rad` and `raw_out_of_bound_coordinates`.

Three preregistered paraphrases also passed geometry checks, but lack corresponding independent human trajectories. This cannot validate signing semantics or new-motion generalization. A test blocked `np.load` on original motion paths and generation still succeeded. Another verified that +20% duration recomputes additional samples.

This is a learned model that fits three known demonstrations into a text/continuous-phase function. W contains `385×40×26=400,400` scalars, but training text spans only three vector directions. Regularization/phase bases make the fit solvable; parameter count does not establish wider vocabulary or general ASL.

RBF ridge is learned regression, **not a deep generative model**. Only pretrained frozen MiniLM is a neural network; this experiment trains closed-form ridge weights. The protocol's time-rule wording “neural features” is imprecise: interpret it as frozen neural text embeddings plus non-neural RBF phase features. Preserve the original protocol rather than editing retrospectively. Actual embeddings affect numerical joint prediction; output is not an ID trajectory lookup. Three demonstrations and successful geometry checks still cannot establish semantic fidelity of paraphrases.

The first program start encountered a MuJoCo `joint.range` shape compatibility error before fitting and produced no weights. Original error/source hash are in `preflight_failures/001`. After fixing indexing, only one actual fit ran; protocol, thresholds, trajectories, and language module were unchanged. Four specific learning tests passed at that time; the integration owner handles the repository-wide suite.
