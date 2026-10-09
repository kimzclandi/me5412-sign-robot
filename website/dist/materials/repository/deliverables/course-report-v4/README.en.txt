ME5412 course presentation v4

Fourteen English slides. Original Chinese narration is in PPTX notes and speaker-notes.zh-CN.txt; English companion: speaker-notes.en.txt. Suggested total 14m25s; no timed rehearsal.

ME5412_Text_to_Robot_Signing_v4.pptx is editable. PDF is a static image preview; its text cannot be edited.

Slide 11 reports completed RBF ridge and odd-frame errors: three authored demonstrations, 367 fit/365 validation frames, not 732 independent demonstrations. Errors are active-joint errors after bounds projection.
Slide 12 reports 35,263 actual How2Sign text/ID/time rows. New video/pose/robot targets: zero; these texts did not train slide 11.

Default remains limited selection/preview; learning is a separate candidate experiment. No arbitrary-word generation, ASL review, or clinical-effect claim.

Build: scripts/build_course_slides.mjs v4 with bundled Node; PDF fallback: scripts/build_course_slides.py. RUNTIME_ROOT and PRESENTATIONS_SKILL_DIR identify dependencies/skill directory. Use a new version when rebuilding; preserve accepted originals.
QA: qa-v4.json, validation-v4.json, provenance-v4.json, final-previews/, contact-sheet.webp. Original v3 remains under deliverables/course-report-v1/.

Before presentation run run_demo.command and verify http://127.0.0.1:5412. Native PowerPoint has not been checked; inspect font substitution on the classroom computer in advance.
Use docs/ten-intent-learning-guide.en.md for the latest development assignments.
