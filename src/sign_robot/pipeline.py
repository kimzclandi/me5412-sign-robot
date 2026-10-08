"""Separate language selection from permission to show unreviewed motions."""
from __future__ import annotations

from pathlib import Path
from .contracts import ROOT, load_catalog, validate_selection


def resolve_execution(selection: dict, *, allow_candidate_preview: bool = False,
                      catalog: list[dict] | None = None,
                      preview_dir: Path | None = None) -> dict:
    catalog = load_catalog() if catalog is None else catalog
    validate_selection(selection, catalog)
    if selection["status"] != "execute":
        return {"state": "rejected", "preview_url": None}
    action = next(a for a in catalog if a["action_id"] == selection["action_id"])
    reviewed = action.get("asl_review_status") == "reviewed"
    if not reviewed and allow_candidate_preview is not True:
        return {"state": "review_required", "preview_url": None,
                "message": "已选中候选表达。该动作尚未经 ASL 使用者验证；勾选研究预览后可查看。"}
    media = (preview_dir or ROOT / "results/previews") / f'{action["action_id"]}.mp4'
    if not media.is_file():
        return {"state": "unavailable", "preview_url": None,
                "message": "动作预览尚未生成。请先执行动作制作与渲染脚本。"}
    return {"state": "ready", "preview_url": f'/media/{action["action_id"]}.mp4',
            "mode": "kinematic_prerender", "asl_reviewed": reviewed,
            "message": "MuJoCo 运动学预渲染；候选动作的 ASL 可理解性尚未验证。" if not reviewed
            else "播放已登记评审的运动学轨迹。"}


def run_selection(text: str, method: str, allow_candidate_preview: bool = False) -> dict:
    from .language import select_action
    catalog = load_catalog()
    selection = select_action(text, method=method, catalog=catalog)
    return {"selection": validate_selection(selection, catalog),
            "execution": resolve_execution(selection, catalog=catalog,
                allow_candidate_preview=allow_candidate_preview)}
