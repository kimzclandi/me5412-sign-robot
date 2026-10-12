# ME5412 collaboration instructions

[中文](AGENTS.md) · **English**

This is a separate project. The user authorized upload to private `kimzclandi/me5412-sign-robot` on 2026-10-09 for collaboration. That original authorization does not include making code public, inviting collaborators, merging unrelated future PRs, or creating Releases. Follow later explicit task authorization where provided.

- Current implementation: three limited expressions, independent text-conditioned learning, and kinematic display. Latest target: ten fixed intents/learned motions, free existing selector, valid-ID motion condition. Use `docs/ten-intent-learning-guide.md`; do not present plans as completed capabilities.
- Meaning, source support, geometry, and actual ASL-user comprehension are separate statuses. Never label candidates validated ASL.
- The user authorized small-scale local learning in independent directories: freeze protocols and preserve failures. Never overwrite weights/old experiments, spend on paid APIs, apply for data, or message others. Prefer free public small samples/local tools.
- Preserve vendor originals, commits/hashes; coupled joints are not independent drives.
- All three pairs agree on public contracts and appoint an integration coordinator per round; language outputs IDs, never joint commands.
- Cross-reviewers who did not tune the corresponding component own final tests, frozen before running; do not tune on results then claim independent validation.
- Motion developers may read sources/development data; never invent human review.
- Deliver startup instructions, actual checks, and unverified limitations.

Current roles: pair 1 covers person 1's keyword baseline and person 2's MiniLM/semantic understanding; pair 2 covers person 3's hand/arm demonstration extraction/cleaning and person 4's robot-joint mapping; pair 3 covers person 5's intent-conditioned training and person 6's inference/execution, transitions/smoothing, and playback comparison. Both in pair 3 help train/debug. Everyone implements and tests; UI, report, slides, integration, and reproduction are shared. Scope is fixed healthcare expressions; no named teammates are assigned. Historical roles remain in `docs/six-person-handoff.md`.

Branch rules: read `docs/github-collaboration.md`. Start from latest master, deliver task branches/PRs, coordinate shared files, and merge after stage checks through the round's coordinator and authorized maintainer. Team development agents do not independently merge others' PRs. Connect selection/generation by valid `action_id`; avoid repeated exact matching of original text.

## Bilingual maintenance

The user requires Chinese and English documentation and website interfaces. Update paired documentation together, including numbers, boundaries, links, usage, and speaker notes. Keep experimental raw artifacts/frozen protocols unchanged; explain them bilingually. Maintain `docs/README.md` as the paired index. Interface additions need both languages, including errors, dynamic results, and accessibility text. Never silently fall back to Chinese in English mode. Public static export/publishing is separate from local/GitHub updates.
