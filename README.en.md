# ME5412 Robot Signing Research Bench

[中文](README.md) · **English** · [Bilingual documentation index](docs/README.md)

> **Next stage: ten fixed intents → learned conditional motions.** Reuse free local MiniLM for intent selection and train an ID-conditioned trajectory model. Six people work in pairs on text intent understanding, demonstrations-to-robot, and learned motion. Everyone implements and tests; UI, report, slides, and integration are shared. The target is fixed healthcare expressions. Develop in parallel on task branches, merge stable versions, and select one primary presentation format at the end. Online site rebuilding is deferred. Ten classes are a development target; the current implementation still contains the three-class prototype documented below.
>
> Start with the [six-person implementation guide](docs/ten-intent-learning-guide.en.md), [GitHub branches and PRs](docs/github-collaboration.en.md), and [code dependencies](docs/code-dependencies.en.md). Develop on task branches, check PRs before merging into `master`, and freeze the final delivery.

This runnable six-person course prototype maps English text or phrase buttons to a limited motion library. A separate learning experiment generates joint trajectories from text embeddings and continuous phase. One small RBF ridge-regression fit used three authored trajectories, 367 training frames, and 365 validation frames from the same trajectories. Only HELLO, THANK_YOU, and PLEASE_WAIT are currently covered. Real ASL users have not reviewed comprehensibility, and PLEASE_WAIT still has a gap between a WAIT lexical example and a complete polite request.

The code repository is **private on GitHub** for team collaboration; the demonstration website is shared separately. Read the [implementation roadmap](docs/实施路线.en.md), then the [historical handoff cards](docs/six-person-handoff.en.md).

## Entry points for teammates

- [Existing online demonstration](https://me5412-robot-signing-lab.kimzc0103.chatgpt.site): this update covers bilingual repository documentation and web source; the online site has not been republished. Live inference runs locally.
- Code and experiments: once granted access, run `git clone https://github.com/kimzclandi/me5412-sign-robot.git`. Sharing a private repository URL does not grant access; the owner must invite collaborators.
- Full bench: prepare the Python environment below, then start the local service.
- [Website source](website/README.en.md): the static demonstration and standalone preview command. GitHub pushes do not automatically publish the website.

The repository preserves original commits, frozen experiments, failures, and the approximately 3 MB regression checkpoint trained by this project. Third-party MiniLM/LLM pretrained weights, robot vendor meshes, virtual environments, session logs, and private machine configuration are excluded. Fixed-source scripts restore base dependencies. How2Sign text indexes are used for noncommercial course research under the recorded CC BY-NC 4.0 scope; source videos are excluded. See [third-party notices and robot BSD license](THIRD_PARTY_NOTICES.en.txt).

## Open on the current computer

Double-click `run_demo.command`, or run this in the project directory. Repeated starts reuse a healthy process belonging to this project:

```bash
.venv/bin/python -m sign_robot.service start --port 5412
```

Open <http://127.0.0.1:5412>. The launcher waits for a successful health check before reporting readiness. Closing the terminal does not stop the background service. The address works only on the computer running it. Start it again after reboot; no automatic startup or public server is configured.

```bash
.venv/bin/python -m sign_robot.service status
.venv/bin/python -m sign_robot.service stop
```

If the page is unavailable, run `start` first. Logs are in `results/session_logs/service-5412.log`. An occupied port produces an explicit error; the launcher neither takes over the port nor kills other processes. For foreground debugging, run `.venv/bin/python -m sign_robot.server --port 5412` and stop with Ctrl+C.

Suggested demonstration:

1. Enter `Thank you.` Exact matching selects THANK_YOU; unreviewed motion does not play by default.
2. Enable “Allow research preview” and submit again to view a candidate rendered with MuJoCo.
3. Select semantic matching and enter `Many thanks` to inspect paraphrase selection.
4. Enter `I do not want to wait.` or `Please wait and take two pills.` Verify rejection without playback.
5. Open acceptance/boundaries, then team collaboration to assign follow-up work.
6. Open motion inspection and the candidate trajectory. Switch front/right oblique views, scrub frames, and inspect angles, finite-difference velocity, and finger coupling.
7. Open the learning model, enter `Thank you`, extend duration by 20%, and generate/check a research candidate. The actual output is 289 frames × 53 coordinates over 9.6 seconds. Scrub the skeleton computed with MuJoCo forward kinematics and download JSON.

## Website navigation

The default page is the project overview. Eight pages are available through the desktop sidebar or mobile navigation. Fragments such as `#overview` and `#learning` support direct links; back, forward, and refresh preserve page location. Leaving a page pauses its player.

| Page | Use during discussion |
|---|---|
| Project overview | Compare library and learning routes; select five workflow nodes to inspect inputs, outputs, modules, and functional entry points. |
| Interactive demo | Compare exact, semantic, and experimental local LLM selection. Candidate preview requires explicit permission. |
| Learning model | Generate/check an actual output and inspect frames; explain text embeddings, phase bases, and reconstruction from 26 to 53 coordinates. |
| Motion inspection | Compare existing front/side videos, timeline, and joint curves. |
| Data route | Inspect original How2Sign splits; distinguish 35,263 text records from missing motion supervision and three authored demonstrations. |
| Experimental evaluation | Separate supported and out-of-library inputs, each with denominator 30. Show false rejection, wrong motion, and interface errors. |
| Six-person collaboration | The current page still shows earlier roles and has not been synchronized with this documentation change. Use the [current three-pair guide](docs/ten-intent-learning-guide.en.md); no named teammates are assigned. |
| Materials and presentation | Manually play six saved learning-model viewpoint videos and open/download PPTX, PDF, notes, and evidence. |

For a first introduction, use overview → demo → learning → data → evaluation → collaboration → materials. Use motion inspection when explaining a particular handshape or joint issue.

Read-only `GET /api/project` gathers existing evidence. Materials use a fixed whitelist and SHA-256 checks; arbitrary local files are unavailable. **206 passed checks** on the page belong to the frozen learning-upgrade snapshot. The later visualization upgrade separately recorded **222 repository tests**, **12 navigation regression checks**, and desktop/mobile browser checks in `results/visualization-v1/`. It did not replace older acceptance results or add training, motion supervision, or ASL comprehensibility evidence.

Generate inspection materials with `.venv/bin/python scripts/export_inspection.py --allow-candidate-preview`. Independent version directories live under `results/inspection/`. Data/video URLs include fixed run IDs, so re-exporting cannot mix new motion into an old open page. This remains synchronized kinematic prerendering and trajectory data.

The demo and inspection pages play MP4s rendered frame-by-frame with MuJoCo. The learning page runs inference/checks per request and draws the resulting link skeleton. Neither runs actuator dynamics. To rotate a native MuJoCo view of an original trajectory:

```bash
# macOS passive viewer uses mjpython
.venv/bin/mjpython scripts/play_motion.py --action HELLO --allow-candidate-preview
```

## Current capabilities and limits

| Component | Implementation | Evidence limit |
|---|---|---|
| Robot | Fixed-base Unitree G1 + Inspire DFQ; 53 scalar joint positions; 12 mimic relations | No actuator control; not 53 independent drives. |
| Motions | Three agent-authored keyframe/numerical-IK/interpolation candidates. THANK_YOU and WAIT source videos were actually viewed for qualitative calibration. | No extracted human 3D motion or real ASL review; head/face remain static. |
| Exact selection | Shared rejection rules and complete registered phrases | Does not understand arbitrary English. |
| Semantic selection | Shared rules plus local MiniLM with real 384-dimensional embeddings | Initial thresholds are not calibrated probabilities; valid paraphrases can be rejected. |
| Learned trajectories | Frozen MiniLM, 40 Gaussian phase bases, trained ridge weights; 26 active upper-body coordinates reconstructed to 53 | Fits three authored demonstrations; interpolation within those trajectories, not new-sign generalization; separate experimental entry point. |
| Public corpus | 35,263 How2Sign English sentence/ID/timestamp records with original splits and hashes | Zero newly acquired videos, human poses, or robot motion labels; not 35,263 learned expressions. |
| LLM | Strict ID/status validation through local loopback; an existing roughly 0.5B Q8 model was tested | Only 2/3 development positives selected correctly; failed default-enable gate; preserves negative result; no automatic remote API. |
| Evaluation | 18 development examples and 60 frozen exploratory tests; raw records and every failure retained | Agent-drafted labels lack human review; evaluates candidate ID selection only. |
| Clinical/language claims | No validated conclusions | No evidence of treatment benefit, safe deployment, replacing interpreters, or arbitrary sentence translation. |

In the first frozen text test, exact selection scored 38/60 and MiniLM with the same rules 47/60. Supported selections were 8/30 and 17/30; false rejections 22/30 and 13/30; out-of-library wrong executions were 0/30 for both. Small denominators and unreviewed labels cannot establish universal zero risk. The first report is `results/evaluation/test-20261008T135255840626Z/`; later independent runs use new directories.

The actual local LLM research comparison is in `results/evaluation/test-20261008T142047221403Z/`, with 180 raw records across three methods and all failures. Exact/MiniLM scores were unchanged. LLM plus shared rules scored 48/60, but produced one wrong supported ID, two invalid labels, and 2/30 wrong out-of-library actions. Total score alone does not establish superiority. Only 35/60 questions actually called the LLM; shared rules handled 25. Labels lack human review. The earlier sandbox `not_run` record is retained; the subsequent change fixed loopback access permission without changing configuration, questions, or prompt.

Initial software/trajectory checks passed **143 tests**, and **75 resource/data hash checks**. Browser checks covered default blocking, explicit preview, real semantic selection, and mixed-intent rejection. `results/acceptance.json` stores initial scope. Upgrade acceptance lives separately under `results/phase2/`.

## Learning upgrade and course materials

- [Model and actual metrics](docs/学习型轨迹模型.en.md): closed-form regression, unknown-input rejection, actual text vectors at prediction, no reading `motions/*.npz` during inference.
- [Corpus scale and next steps](docs/语料规模与模型升级.en.md): imported index counts, licenses, and missing video/pose supervision.
- `results/motion_learning/v1/`: frozen protocol, weights, one fit log, validation, and nine generated NPZs (six primary checks, three exploratory paraphrases). All six primary checks meet frozen engineering thresholds. Maximum odd-frame RMSE from the same demonstration is 0.002528 rad. Preserve raw limit violations/projection corrections and maximum 0.644 mm micro-penetration; do not claim contact-free output.
- `results/motion_learning/v1/previews/`: six front/side videos rerendered from new model-generated NPZs.
- [14-slide English presentation v4](deliverables/course-report-v4/ME5412_Text_to_Robot_Signing_v4.pptx), [PDF](deliverables/course-report-v4/ME5412_Text_to_Robot_Signing_v4.pdf), [Chinese notes](deliverables/course-report-v4/speaker-notes.zh-CN.txt), [English notes](deliverables/course-report-v4/speaker-notes.en.txt). Suggested narration totals 14m25s; no timed rehearsal. PPTX is editable; PDF is an image preview; native PowerPoint inspection remains undone.
- `results/analysis/frozen-test-final/`: charts/failure interpretation recalculated directly from historical 180 records, without rerunning or tuning frozen text experiments.

Do not overwrite/retrain v1. Freeze a protocol before a new experiment in a new version directory. The service caches v1, so replacing weights in the same directory while running is unsupported; restart after upgrading model versions. Verify the public index offline:

```bash
.venv/bin/python scripts/fetch_corpus_index.py --verify
```

Historical next steps: A1 contextual sources; A2 human-to-robot retargeting; B1 text/motion pairing; B2 independently versioned learning; C1 independent motion/user tests; C2 integration, reproduction, and defense. Expanding an English index cannot establish more motion capability without independent pose supervision. Use the newer ten-intent guide for current assignments.

## Reproduce environment and assets

Python 3.12, Apple silicon, and MuJoCo 3.15 were tested on the original machine. Other operating systems remain untested. `requirements-lock.txt` records dependencies without local absolute paths.

On another Mac with Python 3.12, use the following order. Public dependencies/models require network access, but no paid API:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python scripts/fetch_robot.py
.venv/bin/python scripts/prepare_robot.py
.venv/bin/python scripts/fetch_embedding.py
# Existing candidate trajectories and v1 checkpoint are preserved; do not rebuild/retrain.
.venv/bin/python scripts/render_motions.py --allow-candidate-preview
.venv/bin/python scripts/verify_assets.py
.venv/bin/python -m pytest -q
```

Robot meshes are approximately 27 MB; local MiniLM weights approximately 87 MB. Third-party assets live in ignored directories. Restore fixed revisions and verify hashes. Installation/conversion does not change the separate AI Infra environment.

## Source and interfaces

- `contracts/interfaces.json`: IDs, selection states, trajectory convention.
- `data/catalog.json`: meanings, aliases, exclusions, review status.
- `data/source_manifest.json`: primary sources, actually inspected content, usage, frozen hashes.
- `src/sign_robot/language.py`: shared rejection rules, exact selection, real local embeddings.
- `src/sign_robot/llm.py`: allowlisted local LLM adapter; errors do not fall back to another method.
- `src/sign_robot/motion.py`: named-joint trajectory loading/playback.
- `src/sign_robot/pipeline.py`: separates expression selection from candidate-preview permission.
- `src/sign_robot/server.py`, `web/`: local-only interface.
- `motions/*.npz`: timestamps `[T]`, joint names `[J]`, positions `[T,J]`; rotational coordinates in radians.
- `motions/development_failures/`: retained development failures, including penetration.

Each ID also has JSON recording upstream robot commit, construction, IK error, and limits. Language selects IDs only and never emits joint commands.

## Evaluation and acceptance

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_assets.py
.venv/bin/python scripts/evaluate.py --split test
```

The final command creates a new result directory and must not overwrite earlier runs. Do not tune thresholds on frozen test scores and call the new score independent validation. Use `--include-llm` explicitly for a real local LLM; unavailable methods are `not_run`, and rule rejection is not model inference.

The default LLM remains unconfigured, and this experiment's dedicated port-5413 service was stopped. For research reproduction only, configure the existing local model/MLX environment following `config/local_runtime.example.json`, excluding private paths from Git, start `scripts/start_local_llm.command`, then run:

```bash
SIGN_ROBOT_LLM_CONFIG=config/llm_experimental.json .venv/bin/python scripts/evaluate.py --include-llm --run-reason 'Reproduce local LLM research comparison with the original configuration'
```

The research configuration failed the default-enable gate and must not replace `config/llm.json`. Reused local weights/MLX are separate from MiniLM installation and are not automatically available on a newly prepared machine. Architecture, hashes, and historical uncertainty are in `config/llm_local_provenance.json`. A restricted environment needs access to local port 5413; connection failure is not a model-quality result.

Tests check invalid IDs/JSON, no execution after failure, preview gating, HTTP routes, video Range, trajectory shape, limits, coupling, velocity, and upstream collision geometry. Passing available geometry checks is not a complete self-collision safety proof. Initial acceptance: `results/acceptance.json`; visualization acceptance: `results/visualization-v1/acceptance.json`.

## Sources and use

Robot: [official Unitree model](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/g1_description), with upstream commit/hashes in `assets/robot/upstream_manifest.json`. Import fixes duplicate meshdir/filename paths without altering vendor originals.

Signing references: [ASL University / Lifeprint](https://www.lifeprint.com/), with exact pages/observations in [source review](docs/source-review.en.md) and [video calibration](docs/video-calibration.en.md). THANK_YOU has timed comparisons for start, forward/down movement, and final upward palm. WAIT remains a lexical example. Only links and authored observations are stored, without source images/videos/course materials. Robot candidates are engineering approximations without endorsement from source authors or ASL users.

Semantic model: [Sentence Transformers MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), fixed commit/hashes in `config/embedding_download_manifest.json`.

This is a course research prototype. Further public releases require checking third-party model/code/media licenses and course rules. No data applications or reviewer contacts were made. The existing website retains its access state and has not been republished in this update. The code remains private; publishing it requires separate authorization.
