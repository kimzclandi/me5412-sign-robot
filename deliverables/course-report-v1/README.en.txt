ME5412 initial course presentation

Editable: ME5412_Text_to_Robot_Signing_v3.pptx.
Static: ME5412_Text_to_Robot_Signing_v3.pdf, image-only; text not selectable/editable.
Original Chinese narration: speaker-notes.zh-CN.txt and PPTX notes.
English narration companion: speaker-notes.en.txt.
Twelve slides; suggested total 12m50s, without timed rehearsal.

Before speaking run project-root run_demo.command and verify http://127.0.0.1:5412.
Selection results come from 60 frozen exploratory cases with unreviewed labels. Robot images are real MuJoCo renders; all remain kinematic candidates pending comprehension validation.

Build source: scripts/build_course_slides.mjs / .py, using bundled Node/Python. mjs accepts RUNTIME_ROOT and PRESENTATIONS_SKILL_DIR. Use new version arguments such as v4 rather than overwrite final files:
<bundled-node> scripts/build_course_slides.mjs v4
PDF fallback places rendered PNGs via reportlab; edit PPTX for editable charts/text.

Native PowerPoint inspection remains undone; check classroom fonts beforehand. Member names/contributions were not invented.
Historical version: for current learning and roles, see learning-v1 and ten-intent guides in docs/.
