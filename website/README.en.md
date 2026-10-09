# Shareable static website

[中文](README.md) · **English**

[Existing online version](https://me5412-robot-signing-lab.kimzc0103.chatgpt.site).

This directory contains bilingual static presentation source. The online site has not been republished in this update; site rebuilding is deferred. Select the final presentation format once integration is stable. The legacy website remains unchanged; its independent deployment source commit was `2687479cd60b3f37747f7d4ec33dffbb225716c9`. Sites account configuration, write credentials, and deployment state are excluded.

From the repository root:

```bash
python3 -m http.server 5414 --bind 127.0.0.1 --directory website/dist
```

Open <http://127.0.0.1:5414>. Eight sections show workflows, exact phrase matching, saved robot videos, trajectory inspection, team roles, evaluation, and presentation downloads. MiniLM, LLM, and new trajectory generation run in the main Python bench; this static site performs no new model inference.

Use the Chinese/English switch for both static and dynamically rendered interface text. Documentation downloads provide paired language versions; original experimental artifacts retain their recorded values.

`dist` is suitable for static hosting and has local-reference/JavaScript checks. The website is published independently; pushing this GitHub repository does not automatically update it. Exclude personal deployment configuration under `.openai` and `.sites-runtime`.

Sources and use: [English attribution](dist/materials/attribution.en.txt), [Chinese attribution](dist/materials/attribution.txt).
