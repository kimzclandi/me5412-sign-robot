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
                'disposition': 'inline'},
 'report-pptx': {'path': 'deliverables/course-report-v4/ME5412_Text_to_Robot_Signing_v4.pptx',
                 'sha256': '63066ce828451ad9166472c5a4e621d0f221d61fc90d2f3e5c5ef831c4057f95',
                 'title': '可编辑汇报 PPTX',
                 'category': '汇报',
                 'mime': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                 'description': '14 页可编辑课程汇报；未在原生 PowerPoint 中验收。',
                 'disposition': 'attachment'},
 'speaker-notes': {'path': 'deliverables/course-report-v4/speaker-notes.zh-CN.txt',
                   'sha256': 'db05de550b76e4d7038747b3f1d1606244eaa16f4ac4ec3fdf5a4d70330e6cb2',
                   'title': '中文讲稿',
                   'category': '汇报',
                   'mime': 'text/plain; charset=utf-8',
                   'description': '配套 v4 讲稿；时长为计划值，尚未实际排练。',
                   'disposition': 'attachment'},
 'model-guide': {'path': 'docs/学习型轨迹模型.md',
                 'sha256': '4ac92d1d81d1b68169cf9d89ec06fd807b0de1bd5b5651c241b2a058d2ed0eaf',
                 'title': '学习型轨迹模型说明',
                 'category': '说明',
                 'mime': 'text/markdown; charset=utf-8',
                 'description': '模型输入输出、训练协议、同轨迹插值和明确限制。',
                 'disposition': 'attachment'},
 'corpus-guide': {'path': 'docs/语料规模与模型升级.md',
                  'sha256': '8d54dbbaea784adde623ce5462552b09353f0f4f5b43cf04d3992d1d0b36b83d',
                  'title': '语料规模与升级路线',
                  'category': '说明',
                  'mime': 'text/markdown; charset=utf-8',
                  'description': '区分英文语料、人体示范与机器人动作监督。',
                  'disposition': 'attachment'},
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
                'sha256': '184c019142d6ffc60817d4696c14276c27b8622553341316488ea5dc14ecadb0',
                'title': '六人接手任务卡',
                'category': '说明',
                'mime': 'text/markdown; charset=utf-8',
                'description': '每位同学和 agent 的输入、范围与验收边界；任务分配仍由小组确认。',
                'disposition': 'attachment'},
 'course-plan': {'path': 'docs/实施路线.md',
                 'sha256': 'e659b691d4e1223680668452cfab0a2bef3a02449f91c72e0ca69bf2a813e679',
                 'title': '项目实施路线',
                 'category': '说明',
                 'mime': 'text/markdown; charset=utf-8',
                 'description': '从有限候选表达到课程交付的阶段路线与研究边界。',
                 'disposition': 'attachment'}}


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
        "roles": [
            {"id": "A1", "role": "来源与 ASL 复核", "focus": "完整含义、手型、非手部信息与许可",
             "next_step": "找到可使用的独立人体示范，逐条记录已确认与未确认内容。"},
            {"id": "A2", "role": "机器人与轨迹", "focus": "人体到机器人的映射、耦合、接触",
             "next_step": "对新增示范生成新版本轨迹，并保留正面、侧面和逐帧验收。"},
            {"id": "B1", "role": "文本与动作配对", "focus": "英文含义、动作标签和缺失数据",
             "next_step": "补齐文字—人体动作—机器人轨迹的配对关系，独立制定新数据划分。"},
            {"id": "B2", "role": "文字条件模型", "focus": "学习轨迹、输入边界与实验协议",
             "next_step": "收到新独立示范后先冻结 v2 协议，再训练；保留 v1 与 LLM 负结果。"},
            {"id": "C1", "role": "独立评价", "focus": "数据独立性、选择错误与可理解性",
             "next_step": "按独立动作、视频或使用者切分；把人体评审与几何检查分开。"},
            {"id": "C2", "role": "集成与汇报", "focus": "接口、可视化、复现与交付",
             "next_step": "在另一台电脑复现，并让每位组员核对自己的结果与限制。"}],
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
