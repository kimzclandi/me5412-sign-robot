# Corpus scale and upgrading text-to-robot models

[中文](语料规模与模型升级.md) · **English** · [Documentation index](README.md)

Verified 2026-10-08. The project actually imported **35,263 How2Sign English sentence/ID/timestamp records**, downloading approximately 6.37 MB. These are metadata indexes: new videos, human poses, and robot motion labels are all **zero**. Importing 35k records is not training on 35k signing motions. Original catalog, development/test sets, source manifest, and historical evaluation were unchanged.

This records corpus integration and upgrade boundaries. The separate three-trajectory model's completion/errors/checks are established by its own experiment logs.

## Four corpora, different units

| Corpus | Official scale/unit | Language/modalities | Access and actual status |
|---|---|---|---|
| How2Sign | >80 hours, >35k sentence alignments, about 16k **English vocabulary items** | Continuous ASL, English, multiview RGB/depth; 3h Panoptic subset for 3D pose estimation | CC BY-NC 4.0/research. Small public CSVs need no application. Only realigned text downloaded, no RGB/keypoints. [Project](https://how2sign.github.io/), [paper](https://arxiv.org/pdf/2008.08143v2). |
| WLASL2000 | 2,000 gloss classes, 21,083 videos, 119 signers | Isolated ASL RGB/gloss, frames, bbox, splits, pose baseline resources | README requires reading/agreeing to C-UDA. No metadata exemption assumed; no JSON/video application/download. Counts from [paper Table 2](https://arxiv.org/pdf/1910.11006), not local recount. |
| ASL Citizen 1.0 | 2,731 signs, 83,399 videos, 52 signers | Isolated ASL RGB; lexical/signer-independent metadata | Research agreement accepted through use; redistribution restrictions. Only official description inspected. Use [version-1.0 table](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-description/), not v0.9's 83,912. |
| SignAvatars | About 70k motion sequences, 8.34M SMPL-X labeled frames | ASL and PHOENIX-2014T German subsets, HamNoSys/word subsets; SMPL-X/MANO | [Repository](https://github.com/ZhengdiYu/SignAvatars) requires form/agreement. No application/motion files. RGB from original sources. |

Frames are not words; lexical classes are not sentences; counts cannot simply be added. SignAvatars includes How2Sign/WLASL sources, so 3D conversion does not create independent performances; its total is not ASL-only. [Subset details](https://github.com/ZhengdiYu/SignAvatars#dataset-download).

A paper's modality does not establish local availability. How2Sign downloads list RGB, body/face/hand 2D keypoints, and English CSVs; titles/figures cannot establish acquired gloss or complete 3D motion. [Download page](https://how2sign.github.io/).

## Actual imported data

Directory: `data/corpus_index/how2sign_realigned_v1/`.

| CSV | Rows | Unique SENTENCE_ID | VIDEO_ID count | Bytes |
|---|---:|---:|---:|---:|
| train | 31,165 | 30,932 | 2,192 | 5,607,385 |
| val | 1,741 | 1,529 | 115 | 311,419 |
| test | 2,357 | 1,977 | 149 | 423,682 |
| Total/merged unique | 35,263 | 34,438 | 2,456 | 6,342,486 |

Cross-split SENTENCE_ID intersections are zero. Globally unique SENTENCE_NAME count is 35,263; rows and source sentence IDs differ. There are 33,483 distinct English strings. The documented ASCII-letter/lowercase/internal-apostrophe tokenizer yields 16,026 token types and 622,554 instances. These are local English statistics. **ASL gloss-class count is unavailable from these CSVs**, retained as null.

Raw columns: `VIDEO_ID`, `VIDEO_NAME`, `SENTENCE_ID`, `SENTENCE_NAME`, `START_REALIGNED`, `END_REALIGNED`, `SENTENCE`. Derived `sentence_index.jsonl` preserves source row, official split, English/times, `media_availability: not_checked`, and `motion_target_available_locally: false`. No finger angles, palm orientations, skeleton, SMPL-X, or robot qpos exist there.

Complete raw CSVs are preserved. The derived index is about 15.03 MB. Downloaded 6,367,677 bytes include read-only official download-script text, which was not executed. Video URL availability was not checked; corpus videos were not downloaded/transcoded/viewed; no application or data agreement was submitted/accepted.

## Versions and hashes

Official repository revision: `f85816c184662406bd8e0f338863b7c243763129`. URLs were checked against its [download script](https://github.com/how2sign/how2sign.github.io/blob/f85816c184662406bd8e0f338863b7c243763129/download_how2sign.sh), without executing remote code. Drive bytes lack Git revisions, so actual bytes are separately hashed.

| File | SHA256 |
|---|---|
| train | `67a8f4fb6dc066f38006b89ac84c27a4b05d7fa07d5e6952f997042724d7a847` |
| val | `1bf5d57ce90d61571776d06a179335d99648d8c94fc22b327d2abb328d26137c` |
| test | `d1799dcbf100eda822eeb1a0e6e754d82b12b2a57756bd47073c4e4b8a02ae4d` |
| Derived JSONL | `f45213cd483aef31d08f23ce5c67374ea7a9a348a9062181e6ecf93398595867` |

`download_manifest.json` records URLs/redirects/status/bytes/counts/protection hashes. `data/corpus_index/source_registry.json` records all four sources, revisions, and unavailable reasons.

Offline verification:

```sh
.venv/bin/python scripts/fetch_corpus_index.py --verify
```

For a new fetch, use `--fetch --output-dir data/corpus_index/how2sign_realigned_new`. The script restricts fixed official text URLs/HTTPS redirect hosts, caps reading at 25 MB, rejects HTML/login pages posing as CSV, and refuses existing-directory overwrite. It cannot download videos/sign agreements. Reproduction still follows actual source conditions; public access is not permanent availability.

## Why other three were not downloaded

These are authorization/access boundaries, not judgments of research value.

- [WLASL README](https://github.com/dxli94/WLASL#file-description) requires C-UDA agreement; missing/preprocessed videos have application steps. No agreement was accepted for the user; GitHub JSON was not assumed exempt.
- [ASL Citizen license](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/) is an agreement-based research license restricting data/modified-data distribution. No ZIP download; public code cannot replace data permission.
- [SignAvatars access](https://github.com/ZhengdiYu/SignAvatars#dataset-download) requires application/agreement/link. No author contact/form. SMPL-X/MANO model terms require separate checking.

If the user later obtains permission, record exact license/version/scope before processing a small subset. An application opportunity or paper description is not locally trainable data.

## Three levels of upgrade acceptance

### 1. Learn existing robot primitives

Three authored trajectories can train a small condition/normalized-phase → joint-vector q model. Phase runs 0–1; each column must name a joint. Batch B with J joints yields `[B,J]`; actual dimensions follow implementation.

This is a **learned motion primitive proof**: it tests training, saving/loading, output, and simulation constraints. It does not establish general ASL or learning from public human videos and may inherit handshape/face gaps.

Compare direct lookup/interpolation; report fit, bounds/coupling, smoothness, and playback cost separately. Adjacent correlated frames/random splits mainly test temporal interpolation, not new words/sentences/performances. Speed/noise augmentation does not create independent human demonstrations.

### 2. Retarget actual human demonstrations

Text indexes are only one side of pairing. Text-to-motion requires usable, licensed, quality-checked targets, still absent. Even acquired SMPL-X/MANO cannot directly command G1/Inspire: skeletons, lengths, degrees of freedom, adduction, and face differ.

Retargeting takes human trajectories with coordinate conventions/confidence and emits robot `[T,J]`. Match wrists, fingertips, palm orientations, and face/body-relative locations in a common frame, then enforce bounds/coupling/geometry. Record measured versus estimated targets and features hardware cannot preserve.

Joint MSE alone is insufficient because human/robot truth is not naturally same-dimensional. Check geometry, temporal order, violations, and ASL meaning paraphrases. Independently test dynamic tracking/velocity/torque if control exists. More data cannot supply missing facial hardware.

### 3. Learn sentence expression

Continuous signing requires order, context, nonmanual information, and transitions; isolated glosses concatenated in English order are insufficient. [How2Sign paper](https://arxiv.org/pdf/2008.08143v2) discusses coarticulation/grammar.

Split complete videos/performances and suitable signer/source units; keep same-source variants together to avoid frame/duplicate leakage. Generated outputs still need constraints and candidate protection. Learning and engineering gates serve different purposes. Old 60-question ID-selection scores do not validate a new motion model.

## Claims supported now

Supported: checking four official corpora's scale/modalities/terms; importing/verifying 35,263 public text/time records; preserving versions/raw bytes/index/recomputable counts; establishing pairing entry points.

Unsupported: acquiring 35k human motions, training general English-to-ASL, completing video retargeting, learning 2,000/2,731 signs, treating 8.34M frames as independent samples, or real-user endorsement. Next priority is legally obtaining a small actual motion set and independent acceptance; scale must describe usable supervision.
