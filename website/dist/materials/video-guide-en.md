# Official video observations and robot calibration

[中文](video-calibration.md) · **English** · [Documentation index](README.md)

Date: 2026-10-08. The user authorized publicly accessible video reference/calibration. Chrome opened official YouTube players embedded in ASLU pages. Playback, 0.25× speed, and frame controls were used; DOM `currentTime`, `duration`, and `paused` plus paused screenshots recorded observations. No source video download/redistribution, motion-model training/fine-tuning, or ASL-user review occurred in this observation step.

Times below are browser samples to approximately milliseconds for replay, not independently decoded precision frame labels. Monocular video supports qualitative positions/orientations, not true human 3D angles, scale, force, or millimeter error.

## THANK_YOU: played and inspected

[ASLU page](https://www.lifeprint.com/asl101/pages-signs/t/thankyou.htm), [official video](https://www.youtube.com/watch?v=2W0BDFUjsG0). DOM duration: 2.341 s. Played to completion and revisited with frame controls. Integer UI time rounds; table uses DOM values.

| Time (s) | Observed posture/phase |
|---:|---|
| 0.383 | Hand low, preparation. |
| 0.716 | Dominant hand rises to lower face; fingertips near chin. |
| 0.916, 1.016 | Four fingers broadly together; fingertips near lips; hand back toward viewer, palm toward signer. |
| 1.050 | Starts extending from lips; fingers still fairly vertical. |
| 1.116 | Forward/slightly downward movement; palm turns upward. |
| 1.516 | Final forward posture; flat palm upward, fingertips toward recipient. |
| 1.983 | Hand retracted/lowered. |

Confirmed order: near-lip start → inward palm → forward/slightly down toward recipient → upward final palm. Separate low-hand preparation from the core; a complete neutral-to-neutral trajectory need not descend throughout. The page mentions smiling, which the robot cannot reproduce.

## WAIT: played and finger changes inspected

[ASLU page](https://www.lifeprint.com/asl101/pages-signs/w/wait.htm), [official video](https://www.youtube.com/watch?v=YfwgS9ZsBVw). DOM duration: 2.301 s. Played to end and revisited framewise.

| Time (s) | Observed posture/phase |
|---:|---|
| 0.544 | Both hands prepare to rise. |
| 0.944 | Hands ahead of body; signer-left higher/aside, right lower; palms upward/oblique. |
| 1.144, 1.344 | Palms remain broadly positioned; finger flexion changes, rather than repeated whole-hand fists. |
| 1.944 | Hands retracted. |

This is a WAIT lexical example, without complete PLEASE_WAIT pragmatics, polite expression, or connected grammar evidence. The software ID remains for compatibility and candidate status. Exact per-finger phases/human joint angles were not recovered.

## Applying observations to robot deviations

| Comparison | Identified deviation/current correction | Remaining gap |
|---|---|---|
| THANK_YOU start | A2 found fingertips near forehead and palm toward viewer; moved start to lower-face proxy with inward palm. | No true lips; visible hand/face gap; no contact claim. |
| Core path | A2 used 12 intermediate poses with wrist position/orientation to constrain forward/slightly down fingertip proxy; source direction agrees. | Authored engineering targets, not extracted 3D truth; IK error measures target fit only. |
| End | `results/previews/THANK_YOU.png` was inspected; forward palm visible; metadata records palm-up candidate. | Finger spacing differs, no independent adduction or smile. |
| WAIT fingers | Shared the observation of stable palms and differentiated flexion with A2; whole-hand fists are not equivalent. | Coupling, spread, phases require checks; no comprehensibility acceptance here. |
| Timing/control | Human example about 2.3 s; robot THANK_YOU is an 8 s, 30 fps teaching preview. | Natural speed, actual torque, dynamic tracking untested; smooth playback is not control acceptance. |

See `motions/THANK_YOU.json`, trajectory/preview reports, retained `motions/development_failures/`, and final `results/previews/THANK_YOU_calibration.json` with start/middle/end PNGs. Video observations and engineering artifacts are separately attributed; they do not establish human-motion retargeting.

## Follow-up acceptance

A1 should obtain complete-request references and real ASL-user meaning paraphrases; A2 checks handshape/nonmanual gaps. Source videos are neither embedded in the project website nor packaged in public results. `data/source_manifest.json` records source/method/times. The first frozen text run's manifest hash remains historical; later observations do not change its questions, labels, or scores.
