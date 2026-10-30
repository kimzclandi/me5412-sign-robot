"""Read-only project dashboard backed by frozen local evidence.

Only explicitly listed artifacts are downloadable. Their SHA-256 identities are
fixed in this source; neither query strings nor evidence JSON can choose a path.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import ROOT


class IntegrityError(ValueError):
    """A known artifact no longer has the recorded bytes."""


# Filled from the already delivered phase-2 files, never generated on request.
SOURCES = {'acceptance': {'path': 'results/phase2/acceptance.json',
                'sha256': '79e901692dd6f324f31de3645ea99b755814edc729dadf527b72a73281f86c66'},
 'model': {'path': 'results/motion_learning/v1/model.json',
           'sha256': '260459a3e9709dcd73433f3cf293df385598537dc8bf482ef3e6de5642980f64'},
 'model_report': {'path': 'results/motion_learning/v1/report.json',
                  'sha256': '73578257b4b06ee062131eb17d8b48b3a2de79044fe290838c278a3b69b81c25'},
 'corpus': {'path': 'data/corpus_index/how2sign_realigned_v1/download_manifest.json',
            'sha256': '56cb4e664534e4bc38a42183899f52b8664e2a4a7e487a6b33f1583bec426fc4'},
 'analysis': {'path': 'results/analysis/frozen-test-final/analysis.json',
              'sha256': '9a0a308fe43589797cb0aba616d92bc4ca38c7c598a5dcb47db96fe646f3a5dc'},
 'catalog': {'path': 'data/catalog.json',
             'sha256': '024fda8da4b8409a3bee4100e4f4ff1c6a3eec027100775fceba15cb95a71523'}}
FILES = {'report-pdf': {'path': 'deliverables/course-report-v4/ME5412_Text_to_Robot_Signing_v4.pdf',
                'sha256': 'af12cba2734034bf9e21ab78ecd7697d406c9d90a7f2cf8442cdd51bd760e31e',
                'title': '14 页汇报 PDF',
                'category': '汇报',
                'mime': 'application/pdf',
                'description': '便于查看的图像型 PDF；属于 v4 讨论稿。',
                'disposition': 'inline',
                'title_en': '14-slide PDF',
                'description_en': 'Image-based v4 discussion draft.'},
 'report-pptx': {'path': 'deliverables/course-report-v4/ME5412_Text_to_Robot_Signing_v4.pptx',
                 'sha256': '63066ce828451ad9166472c5a4e621d0f221d61fc90d2f3e5c5ef831c4057f95',
                 'title': '可编辑汇报 PPTX',
                 'category': '汇报',
                 'mime': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                 'description': '14 页可编辑课程汇报；未在原生 PowerPoint 中验收。',
                 'disposition': 'attachment',
                 'title_en': 'Editable 14-slide PPTX',
                 'description_en': 'English slides with original Chinese embedded notes; English TXT '
                                   'notes are provided separately. Native PowerPoint acceptance is '
                                   'pending.'},
 'speaker-notes': {'path': 'deliverables/course-report-v4/speaker-notes.zh-CN.txt',
                   'sha256': '5a0b3fe94d111f2ff2bdd3c52ea1829170f7cf95973bff89b4de545dd65403e5',
                   'title': '中文讲稿',
                   'category': '汇报',
                   'mime': 'text/plain; charset=utf-8',
                   'description': '配套 v4 讲稿；时长为计划值，尚未实际排练。',
                   'disposition': 'attachment',
                   'title_en': 'Chinese speaker notes',
                   'description_en': 'Original v4 narration; planned timing, no timed rehearsal.',
                   'language': 'zh-CN'},
 'model-guide': {'path': 'docs/学习型轨迹模型.md',
                 'sha256': '843b5ca64b7fb109d5ad22e89020b75226c1678f5bc39dbc8cfb807d9e88141e',
                 'title': '学习型轨迹模型说明',
                 'category': '说明',
                 'mime': 'text/markdown; charset=utf-8',
                 'description': '模型输入输出、训练协议、同轨迹插值和明确限制。',
                 'disposition': 'attachment',
                 'title_en': 'Learned trajectory model',
                 'description_en': 'Inputs, protocol, within-trajectory interpolation and limits.',
                 'language': 'zh-CN'},
 'corpus-guide': {'path': 'docs/语料规模与模型升级.md',
                  'sha256': 'ef79c6c7f2cede2fa0434141dd7483b9c60dd77e6a07d8a849ec6c07117d99eb',
                  'title': '语料规模与升级路线',
                  'category': '说明',
                  'mime': 'text/markdown; charset=utf-8',
                  'description': '区分英文语料、人体示范与机器人动作监督。',
                  'disposition': 'attachment',
                  'title_en': 'Corpus scale and upgrade',
                  'description_en': 'English text, human demonstrations and robot motion targets '
                                    'differ.',
                  'language': 'zh-CN'},
 'phase2-acceptance': {'path': 'results/phase2/acceptance.json',
                       'sha256': '79e901692dd6f324f31de3645ea99b755814edc729dadf527b72a73281f86c66',
                       'title': '上一轮验收快照',
                       'category': '证据',
                       'mime': 'application/json; charset=utf-8',
                       'description': '2026-10-08 UTC 的 206 项测试与交付记录；不是本次实时重跑。',
                       'disposition': 'attachment'},
 'model-report': {'path': 'results/motion_learning/v1/report.json',
                  'sha256': '73578257b4b06ee062131eb17d8b48b3a2de79044fe290838c278a3b69b81c25',
                  'title': 'v1 模型实验报告',
                  'category': '证据',
                  'mime': 'application/json; charset=utf-8',
                  'description': '一次冻结训练的拟合、采样几何检查和探索性改写结果。',
                  'disposition': 'attachment'},
 'model-protocol': {'path': 'results/motion_learning/v1/protocol.json',
                    'sha256': 'd27c412494acb54ea375340618d15ef80c681e4398c5bbe65c29aa5872e21ca0',
                    'title': 'v1 训练前冻结协议',
                    'category': '证据',
                    'mime': 'application/json; charset=utf-8',
                    'description': '固定数据、拆分、算法与门槛；原文 neural features 为术语笔误，实际是 RBF 回归。',
                    'disposition': 'attachment'},
 'evaluation-summary': {'path': 'results/evaluation/test-20261008T142047221403Z/summary.json',
                        'sha256': '5e93537376e61bd663d0d6b25b3ff41e792576bcb752b5f8eeb75de5d7813c4a',
                        'title': '60 题文字选择评价汇总',
                        'category': '证据',
                        'mime': 'application/json; charset=utf-8',
                        'description': '保留三种方法的正确、错误和运行边界；不含题目原文。',
                        'disposition': 'attachment'},
 'corpus-manifest': {'path': 'data/corpus_index/how2sign_realigned_v1/download_manifest.json',
                     'sha256': '56cb4e664534e4bc38a42183899f52b8664e2a4a7e487a6b33f1583bec426fc4',
                     'title': 'How2Sign 接入清单',
                     'category': '证据',
                     'mime': 'application/json; charset=utf-8',
                     'description': '文本索引下载记录、统计、许可和 SHA-256；不包含语料原文。',
                     'disposition': 'attachment'},
 'learned-HELLO-front-mp4': {'path': 'results/motion_learning/v1/previews/HELLO_front.mp4',
                             'sha256': 'e81d0c596163d4e29bd5e881d53daf27172f537bfdca6bd0507bce179dfa5636',
                             'title': 'HELLO · 正面 · MP4',
                             'category': '生成样例',
                             'mime': 'video/mp4',
                             'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                             'disposition': 'inline'},
 'learned-HELLO-front-png': {'path': 'results/motion_learning/v1/previews/HELLO_front.png',
                             'sha256': '4bee3f1ae71dab656df9628f832402710fc8f03687a4bac3aa48a545e8270357',
                             'title': 'HELLO · 正面 · PNG',
                             'category': '生成样例',
                             'mime': 'image/png',
                             'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                             'disposition': 'inline'},
 'learned-HELLO-right_side-mp4': {'path': 'results/motion_learning/v1/previews/HELLO_right_side.mp4',
                                  'sha256': 'fbb6c3fd7c5f30028d7d91ee726837e8b4e328a11e6211a2c99f26459a39b083',
                                  'title': 'HELLO · 右侧 · MP4',
                                  'category': '生成样例',
                                  'mime': 'video/mp4',
                                  'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                  'disposition': 'inline'},
 'learned-HELLO-right_side-png': {'path': 'results/motion_learning/v1/previews/HELLO_right_side.png',
                                  'sha256': 'f198450cdddd9f002fd56d09ab1564cea5fb04578d759cdbd10b52b97653fad4',
                                  'title': 'HELLO · 右侧 · PNG',
                                  'category': '生成样例',
                                  'mime': 'image/png',
                                  'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                  'disposition': 'inline'},
 'learned-THANK_YOU-front-mp4': {'path': 'results/motion_learning/v1/previews/THANK_YOU_front.mp4',
                                 'sha256': 'cb965a358a7bdb269236005ae6a795b365a5eb344ab51b427d81dc1cc176f33e',
                                 'title': 'THANK_YOU · 正面 · MP4',
                                 'category': '生成样例',
                                 'mime': 'video/mp4',
                                 'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                 'disposition': 'inline'},
 'learned-THANK_YOU-front-png': {'path': 'results/motion_learning/v1/previews/THANK_YOU_front.png',
                                 'sha256': '0c6310c1419eb2749b3e9a45c669fc1f6bc53adcd4c8a88209aa9476ddd2daf1',
                                 'title': 'THANK_YOU · 正面 · PNG',
                                 'category': '生成样例',
                                 'mime': 'image/png',
                                 'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                 'disposition': 'inline'},
 'learned-THANK_YOU-right_side-mp4': {'path': 'results/motion_learning/v1/previews/THANK_YOU_right_side.mp4',
                                      'sha256': '876bea66114547bb269d4b5f31e23e25bb4aff56ffd9ca8a468452f99af235f0',
                                      'title': 'THANK_YOU · 右侧 · MP4',
                                      'category': '生成样例',
                                      'mime': 'video/mp4',
                                      'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                      'disposition': 'inline'},
 'learned-THANK_YOU-right_side-png': {'path': 'results/motion_learning/v1/previews/THANK_YOU_right_side.png',
                                      'sha256': 'b0c90ca3e073b2900b717d883dce5e09790ebf1e2ac8b8dabd357bb7c023c867',
                                      'title': 'THANK_YOU · 右侧 · PNG',
                                      'category': '生成样例',
                                      'mime': 'image/png',
                                      'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                      'disposition': 'inline'},
 'learned-PLEASE_WAIT-front-mp4': {'path': 'results/motion_learning/v1/previews/PLEASE_WAIT_front.mp4',
                                   'sha256': '59524210cd5e5baf506ffc87871287a4cffa0b0765bc9c0be07dcf9476e034a9',
                                   'title': 'PLEASE_WAIT · 正面 · MP4',
                                   'category': '生成样例',
                                   'mime': 'video/mp4',
                                   'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                   'disposition': 'inline'},
 'learned-PLEASE_WAIT-front-png': {'path': 'results/motion_learning/v1/previews/PLEASE_WAIT_front.png',
                                   'sha256': '6d8927de92d64a379003233e9169955f64098005d2856c3a84ba0c61ebb44072',
                                   'title': 'PLEASE_WAIT · 正面 · PNG',
                                   'category': '生成样例',
                                   'mime': 'image/png',
                                   'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                   'disposition': 'inline'},
 'learned-PLEASE_WAIT-right_side-mp4': {'path': 'results/motion_learning/v1/previews/PLEASE_WAIT_right_side.mp4',
                                        'sha256': '90006942c2e80693400739398d614389d303736a67b3fdce29898be0f606e339',
                                        'title': 'PLEASE_WAIT · 右侧 · MP4',
                                        'category': '生成样例',
                                        'mime': 'video/mp4',
                                        'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                        'disposition': 'inline'},
 'learned-PLEASE_WAIT-right_side-png': {'path': 'results/motion_learning/v1/previews/PLEASE_WAIT_right_side.png',
                                        'sha256': '28a9735f8bb5d839dda2956c9c85abd9d2f5ba31cb69193d43f3cf8e3526a448',
                                        'title': 'PLEASE_WAIT · 右侧 · PNG',
                                        'category': '生成样例',
                                        'mime': 'image/png',
                                        'description': 'v1 生成轨迹的离线 MuJoCo 候选预览；不是实时生成，也未经 ASL 可理解性评审。',
                                        'disposition': 'inline'},
 'team-guide': {'path': 'docs/six-person-handoff.md',
                'sha256': '6fc07f837346264d897be9ce6c2a5473039103d7bee34f9dceb49f45bb1f0bbd',
                'title': '六人接手任务卡',
                'category': '说明',
                'mime': 'text/markdown; charset=utf-8',
                'description': '每位同学和 agent 的输入、范围与验收边界；任务分配仍由小组确认。',
                'disposition': 'attachment',
                'title_en': 'Historical handoff cards',
                'description_en': 'Historical roles, inputs and acceptance. Use the current ten-intent '
                                  'guide first.',
                'language': 'zh-CN'},
 'course-plan': {'path': 'docs/实施路线.md',
                 'sha256': 'b2cb827406f8ea76f6aefd0056961d92e4233f55d93abd5f7cc5597406e170da',
                 'title': '项目实施路线',
                 'category': '说明',
                 'mime': 'text/markdown; charset=utf-8',
                 'description': '从有限候选表达到课程交付的阶段路线与研究边界。',
                 'disposition': 'attachment',
                 'title_en': 'Historical roadmap',
                 'description_en': 'Earlier prototype-to-delivery stages and evidence scope.',
                 'language': 'zh-CN'},
 'team-current': {'path': 'docs/ten-intent-learning-guide.md',
                  'title': '最新六人实施指南',
                  'title_en': 'Ten-intent team guide',
                  'description': '十个固定语意与学习动作的分工、接口和验收。',
                  'description_en': 'Roles, interfaces and acceptance for ten fixed intents and learned '
                                    'motions.',
                  'category': '说明',
                  'mime': 'text/markdown; charset=utf-8',
                  'disposition': 'attachment',
                  'sha256': '1fd91993ffc3ce86a0fce59555f549c8a867481c718b8c12876a3fe94dec5bbf',
                  'language': 'zh-CN'},
 'github-guide': {'path': 'docs/github-collaboration.md',
                  'title': 'GitHub 分支协作',
                  'title_en': 'GitHub collaboration',
                  'description': '任务分支、PR、冲突与合并步骤。',
                  'description_en': 'Task branches, PRs, conflicts and merging.',
                  'category': '说明',
                  'mime': 'text/markdown; charset=utf-8',
                  'disposition': 'attachment',
                  'sha256': '23057827c6ba7e9c83acb85950ae74f83745f75ff6e36ee8b1d49e8c4e81a05f',
                  'language': 'zh-CN'},
 'dependencies': {'path': 'docs/code-dependencies.md',
                  'title': '代码依赖图',
                  'title_en': 'Code dependencies',
                  'description': '本地选择、学习、渲染和展示的文件依赖。',
                  'description_en': 'Dependencies of local selection, learning, rendering and '
                                    'presentation.',
                  'category': '说明',
                  'mime': 'text/markdown; charset=utf-8',
                  'disposition': 'attachment',
                  'sha256': '107f1fc5e6266b0682918ecc2e52f6012eadb6545d11f996e2e70c1a2c666dd2',
                  'language': 'zh-CN'},
 'source-guide': {'path': 'docs/source-review.md',
                  'title': '来源与评价记录',
                  'title_en': 'Sources and evaluation',
                  'description': '来源、冻结文本协议与实际失败。',
                  'description_en': 'Sources, frozen text protocol and observed failures.',
                  'category': '说明',
                  'mime': 'text/markdown; charset=utf-8',
                  'disposition': 'attachment',
                  'sha256': '41ba9e4f662ab18d3883a71456e53c94a08e1714c23a0b877ccb19dd4d33e91e',
                  'language': 'zh-CN'},
 'video-guide': {'path': 'docs/video-calibration.md',
                 'title': '视频校准记录',
                 'title_en': 'Video calibration',
                 'description': '实际观察时刻与机器人偏差。',
                 'description_en': 'Observed video times and robot deviations.',
                 'category': '说明',
                 'mime': 'text/markdown; charset=utf-8',
                 'disposition': 'attachment',
                 'sha256': 'fab4d3814d174e0f7dc01fc8bdb940e93f304c12138f6acaacede43819920c10',
                 'language': 'zh-CN'},
 'defense-guide': {'path': 'docs/实验解读与答辩.md',
                   'title': '实验解读与答辩',
                   'title_en': 'Evaluation and defense',
                   'description': '分母、失败归因和历史答辩提纲。',
                   'description_en': 'Denominators, failure attribution and historical defense outline.',
                   'category': '说明',
                   'mime': 'text/markdown; charset=utf-8',
                   'disposition': 'attachment',
                   'sha256': '21f1fda56a1e08e939f60ddf61872fb651f03910c95e08c135274874330db772',
                   'language': 'zh-CN'},
 'docs-index': {'path': 'docs/README.md',
                'title': '中英说明目录',
                'title_en': 'Bilingual documentation index',
                'description': '全部中英说明的成对入口。',
                'description_en': 'Paired entry points to Chinese and English documentation.',
                'category': '说明',
                'mime': 'text/markdown; charset=utf-8',
                'disposition': 'attachment',
                'sha256': '2357a135b3ecae313702e20c81b418505d62efda66080c879c67a658b2130049',
                'language': 'zh-CN'},
 'speaker-notes-en': {'path': 'deliverables/course-report-v4/speaker-notes.en.txt',
                      'sha256': '05f569b68c7d63bd5a879a7bad21a4341dc2ff5720812207cd68413a0a0ce13a',
                      'title': 'Chinese speaker notes',
                      'category': '汇报',
                      'mime': 'text/plain; charset=utf-8',
                      'description': 'Original v4 narration; planned timing, no timed rehearsal.',
                      'disposition': 'attachment',
                      'title_en': 'Chinese speaker notes',
                      'description_en': 'Original v4 narration; planned timing, no timed rehearsal.',
                      'language': 'en'},
 'model-guide-en': {'path': 'docs/学习型轨迹模型.en.md',
                    'sha256': '0ef0f283e4e0ee32f37d7ce268ded63580ac3e2624a42a398cab9aa6e4dccfa8',
                    'title': 'Learned trajectory model',
                    'category': '说明',
                    'mime': 'text/markdown; charset=utf-8',
                    'description': 'Inputs, protocol, within-trajectory interpolation and limits.',
                    'disposition': 'attachment',
                    'title_en': 'Learned trajectory model',
                    'description_en': 'Inputs, protocol, within-trajectory interpolation and limits.',
                    'language': 'en'},
 'corpus-guide-en': {'path': 'docs/语料规模与模型升级.en.md',
                     'sha256': '40b4ab6c127b44f4b2e12e4b260bed9d95686e053ad87c9dccbfd02550ac477d',
                     'title': 'Corpus scale and upgrade',
                     'category': '说明',
                     'mime': 'text/markdown; charset=utf-8',
                     'description': 'English text, human demonstrations and robot motion targets '
                                    'differ.',
                     'disposition': 'attachment',
                     'title_en': 'Corpus scale and upgrade',
                     'description_en': 'English text, human demonstrations and robot motion targets '
                                       'differ.',
                     'language': 'en'},
 'team-guide-en': {'path': 'docs/six-person-handoff.en.md',
                   'sha256': '7edb3e6094ef3f846a96e024ca92cc9d8848c79a51976e8fde661182828cdbef',
                   'title': 'Historical handoff cards',
                   'category': '说明',
                   'mime': 'text/markdown; charset=utf-8',
                   'description': 'Historical roles, inputs and acceptance. Use the current ten-intent '
                                  'guide first.',
                   'disposition': 'attachment',
                   'title_en': 'Historical handoff cards',
                   'description_en': 'Historical roles, inputs and acceptance. Use the current '
                                     'ten-intent guide first.',
                   'language': 'en'},
 'course-plan-en': {'path': 'docs/实施路线.en.md',
                    'sha256': 'fcbee62ad7f5868206d485a072eda054df584d24ba0448cdf179574b60921a1b',
                    'title': 'Historical roadmap',
                    'category': '说明',
                    'mime': 'text/markdown; charset=utf-8',
                    'description': 'Earlier prototype-to-delivery stages and evidence scope.',
                    'disposition': 'attachment',
                    'title_en': 'Historical roadmap',
                    'description_en': 'Earlier prototype-to-delivery stages and evidence scope.',
                    'language': 'en'},
 'team-current-en': {'path': 'docs/ten-intent-learning-guide.en.md',
                     'title': 'Ten-intent team guide',
                     'title_en': 'Ten-intent team guide',
                     'description': 'Roles, interfaces and acceptance for ten fixed intents and learned '
                                    'motions.',
                     'description_en': 'Roles, interfaces and acceptance for ten fixed intents and '
                                       'learned motions.',
                     'category': '说明',
                     'mime': 'text/markdown; charset=utf-8',
                     'disposition': 'attachment',
                     'sha256': 'f3f1506ccef5b2d36ecc0299a411eac2928b1f48e3a304b09532a59f9160233a',
                     'language': 'en'},
 'github-guide-en': {'path': 'docs/github-collaboration.en.md',
                     'title': 'GitHub collaboration',
                     'title_en': 'GitHub collaboration',
                     'description': 'Task branches, PRs, conflicts and merging.',
                     'description_en': 'Task branches, PRs, conflicts and merging.',
                     'category': '说明',
                     'mime': 'text/markdown; charset=utf-8',
                     'disposition': 'attachment',
                     'sha256': 'f9bb01fcf7ffe960692d2f646e0cf79514268b8bc51e2674de2736fab448bba1',
                     'language': 'en'},
 'dependencies-en': {'path': 'docs/code-dependencies.en.md',
                     'title': 'Code dependencies',
                     'title_en': 'Code dependencies',
                     'description': 'Dependencies of local selection, learning, rendering and '
                                    'presentation.',
                     'description_en': 'Dependencies of local selection, learning, rendering and '
                                       'presentation.',
                     'category': '说明',
                     'mime': 'text/markdown; charset=utf-8',
                     'disposition': 'attachment',
                     'sha256': '7850731e7e92f13d942c23681d35d300a1b0f4b6048369a353379f9b34d98519',
                     'language': 'en'},
 'source-guide-en': {'path': 'docs/source-review.en.md',
                     'title': 'Sources and evaluation',
                     'title_en': 'Sources and evaluation',
                     'description': 'Sources, frozen text protocol and observed failures.',
                     'description_en': 'Sources, frozen text protocol and observed failures.',
                     'category': '说明',
                     'mime': 'text/markdown; charset=utf-8',
                     'disposition': 'attachment',
                     'sha256': '6360c4ed13604d9b895abdefe3a91c1f053a101e1c94f6c954bd290696337815',
                     'language': 'en'},
 'video-guide-en': {'path': 'docs/video-calibration.en.md',
                    'title': 'Video calibration',
                    'title_en': 'Video calibration',
                    'description': 'Observed video times and robot deviations.',
                    'description_en': 'Observed video times and robot deviations.',
                    'category': '说明',
                    'mime': 'text/markdown; charset=utf-8',
                    'disposition': 'attachment',
                    'sha256': 'ebcf9445f7947e6754a6e8eff62504c42aeb30a82b8747a2fd08a720d3256002',
                    'language': 'en'},
 'defense-guide-en': {'path': 'docs/实验解读与答辩.en.md',
                      'title': 'Evaluation and defense',
                      'title_en': 'Evaluation and defense',
                      'description': 'Denominators, failure attribution and historical defense outline.',
                      'description_en': 'Denominators, failure attribution and historical defense '
                                        'outline.',
                      'category': '说明',
                      'mime': 'text/markdown; charset=utf-8',
                      'disposition': 'attachment',
                      'sha256': 'efa6ba8b97dd480abde7dc359f06a1f455aa868b0734cc3ad92db892e39d36b7',
                      'language': 'en'},
 'docs-index-en': {'path': 'docs/README.en.md',
                   'title': 'Bilingual documentation index',
                   'title_en': 'Bilingual documentation index',
                   'description': 'Paired entry points to Chinese and English documentation.',
                   'description_en': 'Paired entry points to Chinese and English documentation.',
                   'category': '说明',
                   'mime': 'text/markdown; charset=utf-8',
                   'disposition': 'attachment',
                   'sha256': '2357a135b3ecae313702e20c81b418505d62efda66080c879c67a658b2130049',
                   'language': 'en'}}


def _safe_path(relative: str, root: Path) -> Path:
    base = root.resolve()
    path = base / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("invalid_artifact_path")
    current = base
    for component in Path(relative).parts:
        current = current / component
        if current.is_symlink():
            raise ValueError("artifact_symlink_not_allowed")
    resolved = path.resolve()
    if not resolved.is_relative_to(base):
        raise ValueError("artifact_outside_project")
    if not resolved.is_file():
        raise FileNotFoundError("artifact_missing")
    return resolved


def _checked_path(spec: dict, root: Path) -> Path:
    path = _safe_path(spec["path"], root)
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise IntegrityError("artifact_integrity_mismatch")
    return path


def artifact(key: str, root: Path = ROOT) -> tuple[Path, dict]:
    """Resolve a public artifact ID. Unknown IDs never reach the filesystem."""
    if key not in FILES:
        raise KeyError("unknown_project_file")
    spec = FILES[key]
    return _checked_path(spec, root), spec


def _source(key: str, root: Path) -> dict:
    return json.loads(_checked_path(SOURCES[key], root).read_text(encoding="utf-8"))


def materials(root: Path = ROOT) -> list[dict]:
    result = []
    for key, spec in FILES.items():
        item = {k: spec[k] for k in ("title", "category", "mime", "description", "sha256")}
        item.update({k: spec[k] for k in ("language", "title_en", "description_en") if k in spec})
        item.update(key=key, url=f"/project-files/{key}", available=False, bytes=None,
                    unavailable_reason=None)
        try:
            path, _ = artifact(key, root)
            item.update(available=True, bytes=path.stat().st_size)
        except FileNotFoundError:
            item["unavailable_reason"] = "missing"
        except IntegrityError:
            item["unavailable_reason"] = "integrity_mismatch"
        except (ValueError, OSError):
            item["unavailable_reason"] = "unavailable"
        result.append(item)
    return result


def overview(root: Path = ROOT) -> dict:
    acceptance = _source("acceptance", root)
    model = _source("model", root)
    report = _source("model_report", root)
    corpus = _source("corpus", root)
    analysis = _source("analysis", root)
    catalog = _source("catalog", root)["actions"]
    public_files = materials(root)
    public_by_key = {item["key"]: item for item in public_files}
    previews = []
    actions = []
    for action in catalog:
        action_id = action["action_id"]
        row = {"action_id": action_id, "label": action["label_zh"],
               "duration_s": model["durations_s"][action_id],
               "frames": model["protocol"]["expected_frames"][action_id],
               "asl_reviewed": action["asl_review_status"] == "reviewed"}
        actions.append(row)
        views = {}
        for view in ("front", "right_side"):
            video = public_by_key[f"learned-{action_id}-{view}-mp4"]
            poster = public_by_key[f"learned-{action_id}-{view}-png"]
            views[view] = {"video_url": video["url"], "poster_url": poster["url"],
                           "available": video["available"] and poster["available"],
                           "video_sha256": video["sha256"]}
        previews.append({**row, "views": views, "kind": "saved_learned_trajectory",
                         "description": "v1 模型生成轨迹的离线 MuJoCo 回放；不是当前输入的实时结果。"})
    counts = corpus["aggregate_counts"]
    labels = {"exact": "固定别名 + 公共规则", "embedding": "MiniLM + 公共规则",
              "llm": "本地 LLM + 公共规则"}
    methods = [{"id": key, "label": labels[key],
                **{name: analysis["methods"][key][name] for name in (
                    "n", "n_supported", "n_unsupported", "accuracy", "supported", "out_of_scope")}}
               for key in analysis["method_order"]]
    return {
        "schema_version": 1,
        "evidence_snapshot": {
            "created_utc": acceptance["created_utc"], "kind": "frozen_phase2", "not_live": True,
            "description": "上次交付的冻结验收快照；这里的测试数不代表本次实时重跑。",
            "tests": {key: int(acceptance["tests"][key]) for key in ("tests", "failures", "errors", "skipped")},
            "source_url": "/project-files/phase2-acceptance"},
        "metrics": {"supported_actions": len(actions),
                    "independent_demonstrations": model["independent_demonstrations"],
                    "metadata_rows": counts["annotation_rows"],
                    "motion_targets": counts["locally_available_motion_targets"],
                    "historical_tests": int(acceptance["tests"]["tests"])},
        "actions": actions,
        "model": {"type": model["model_type"], "description": "冻结文字向量 + 时间相位 RBF 岭回归",
                  "independent_demonstrations": model["independent_demonstrations"],
                  "train_frames": model["train_frames"], "validation_frames": model["validation_frames"],
                  "total_frames": model["frames"], "parameter_count": model["parameter_count"],
                  "learned_joint_count": model["protocol"]["learned_joint_count"],
                  "full_coordinate_count": model["protocol"]["full_coordinate_count"],
                  "fit_accepted": report["fit_accepted"], "engineering_accepted": report["engineering_accepted"],
                  "validation_scope": report["validation_scope"],
                  "scope_zh": "同一示范内偶数帧训练、奇数帧验证，只证明时间插值；未证明新手语泛化。",
                  "model_sha256": report["model_sha256"], "asl_reviewed": report["asl_reviewed"],
                  "default_enabled": report["default_enabled"],
                  "heldout_metrics": [{"action_id": key,
                                       "rmse_rad": item["validation_indices"]["active_rmse_rad"],
                                       "max_error_rad": item["validation_indices"]["active_max_error_rad"],
                                       "frames": item["validation_indices"]["frames"]}
                                      for key, item in report["fit"].items()],
                  "report_url": "/project-files/model-report", "protocol_url": "/project-files/model-protocol"},
        "corpus": {"dataset": corpus["dataset"], "metadata_rows": counts["annotation_rows"],
                   "unique_sentence_ids": counts["unique_sentence_ids"],
                   "unique_english_strings": counts["unique_english_strings"],
                   "english_token_types": counts["english_token_types"],
                   "motion_targets": counts["locally_available_motion_targets"],
                   "splits": [{"name": key, "metadata_rows": item["counts"]["annotation_rows"]}
                              for key, item in corpus["files"].items()],
                   "created_utc": corpus["created_at_utc"], "license": corpus["license"],
                   "source_url": corpus["official_project_url"],
                   "attribution": corpus["attribution"],
                   "scope": "仅英文文本、句子 ID 与时间戳；没有新增视频、人体姿态或机器人动作监督。英文词型不是 ASL 词汇数。"},
        "evaluation": {"case_count": analysis["unique_test_cases"], "raw_rows": analysis["raw_rows"],
                       "supported_cases": methods[0]["n_supported"], "out_of_scope_cases": methods[0]["n_unsupported"],
                       "methods": methods, "source_run": analysis["source_run"],
                       "created_utc": analysis["created_at_utc"], "labels_status": "agent_draft_unreviewed",
                       "scope_zh": "60 条 agent 拟题、未经人工复核；评价文字选择，不评价 ASL 可理解性。",
                       "llm_http_cases": analysis["llm_paths"]["llm_http_response"]["n"],
                       "shared_guard_cases": analysis["llm_paths"]["shared_guard"]["n"],
                       "llm_default_enabled": False,
                       "report_url": "/project-files/evaluation-summary"},
        "course": {"deadline": "2026-11-03", "presentation_minutes": [10, 15], "qa_minutes": 5,
                   "source": "ME5412-2026 Project Assignment Briefing.pptx（课程原件已核对）",
                   "scope": "允许概念、设计与仿真项目；不要求硬件实现。"},
        "roles": [{'id': 'A1',
          'number': '1',
          'role': '语意与文本数据',
          'role_en': 'Intent and text data',
          'focus': '十类完整含义、英文改写与混淆反例',
          'focus_en': 'Ten meanings, English variants and confusing negatives',
          'next_step': '与动作组确定有示范的十类目录，整理开发数据和标签争议。',
          'next_step_en': 'Agree on ten demonstrated meanings with the motion team; organize development data '
                          'and label disputes.'},
         {'id': 'A2',
          'number': '2',
          'role': '免费模型与语意匹配',
          'role_en': 'Free model and intent selection',
          'focus': 'MiniLM 目录匹配、拒绝处理与语言接口',
          'focus_en': 'MiniLM matching, rejection and selection API',
          'next_step': '复用免费本地 MiniLM，在开发集确定阈值，交付合法 ID 与版本。',
          'next_step_en': 'Reuse free local MiniLM, choose development thresholds and deliver valid IDs with '
                          'versions.'},
         {'id': 'B1',
          'number': '3',
          'role': '动作数据与机器人映射',
          'role_en': 'Motion data and robot mapping',
          'focus': '有来源的示范、共用重定向与轨迹检查',
          'focus_en': 'Sourced demonstrations, shared retargeting and checks',
          'next_step': '取得实际可使用的动作监督，统一坐标与时间，输出新版机器人轨迹。',
          'next_step_en': 'Acquire usable motion targets, unify coordinates/timing and deliver versioned robot '
                          'trajectories.'},
         {'id': 'B2',
          'number': '4',
          'role': '条件动作学习',
          'role_en': 'Conditional motion learning',
          'focus': 'ID 与相位条件、权重训练与输出约束',
          'focus_en': 'ID/phase conditioning, learned weights and constraints',
          'next_step': '先冻结新协议，以合法 action_id 驱动模型，保留 v1 权重与失败。',
          'next_step_en': 'Freeze a new protocol, generate by valid action_id, and preserve v1 '
                          'weights/failures.'},
         {'id': 'C1',
          'number': '5',
          'role': '接口、集成与独立评价',
          'role_en': 'Interfaces, integration and independent evaluation',
          'focus': '公共注册、独立测试与完整流程',
          'focus_en': 'Shared registry, independent tests and end-to-end flow',
          'next_step': '协调分支和接口，分别评价语意识别与动作，检查第二台电脑复现。',
          'next_step_en': 'Coordinate branches/interfaces; evaluate language and motion separately; reproduce '
                          'on another computer.'},
         {'id': 'C2',
          'number': '6',
          'role': '展示方案与汇报',
          'role_en': 'Presentation format and report',
          'focus': '前期接入验证，最终选定一种展示方式',
          'focus_en': 'Early integration checks; one final presentation format',
          'next_step': '先接入和检查集成版本，稳定后制作一种主要展示方式与汇报。',
          'next_step_en': 'Integrate and inspect versions early; select one primary presentation format and prepare '
                          'slides/rehearsal.'}],
        "next_steps": [
            {"title": "确认项目范围", "status": "待小组决定", "detail": "选择少量常用表达，明确完整含义与各人负责模块。"},
            {"title": "补齐动作监督", "status": "待开展", "detail": "从有来源和许可的人体示范建立姿态与机器人轨迹配对。"},
            {"title": "冻结独立评价", "status": "待开展", "detail": "按独立示范切分新实验，并为可理解性评价安排独立流程。"},
            {"title": "扩大模型并复现", "status": "依赖新增数据", "detail": "完成前述配对与协议后训练 v2，随后跨电脑复现和排练。"}],
        "generated_previews": previews,
        "materials": public_files,
        "limitations": ["三条自编示范仍是全部独立动作训练数据。", "候选动作均未完成 ASL 使用者评审。",
                        "运动学采样检查不等于动力学控制或真实硬件验证。", "资料链接仅由当前电脑的本地服务提供。"],
    }
