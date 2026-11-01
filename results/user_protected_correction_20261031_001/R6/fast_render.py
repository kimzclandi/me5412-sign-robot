"""Raster-only MuJoCo settings for faster export; no trajectory/geometry edits."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
import mujoco

OriginalRenderer=mujoco.Renderer


class FastRenderer(OriginalRenderer):
    def __init__(self,model,*args,**kwargs):
        model.vis.quality.offsamples=0
        model.vis.quality.shadowsize=512
        super().__init__(model,*args,**kwargs)

    def update_scene(self,*args,**kwargs):
        super().update_scene(*args,**kwargs)
        self.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
        self.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION]=False


def main():
    mujoco.Renderer=FastRenderer
    output=Path(sys.argv[sys.argv.index('--output')+1])
    try:
        runpy.run_path(ROOT/'scripts/render_user_protected_pairs.py',run_name='__main__')
    except SystemExit as exc:
        if exc.code not in (None,0):
            raise
    config={'kind':'raster_render_settings_only','shadows':False,'reflections':False,
            'offscreen_multisamples':0,'shadow_map_size':512,'native_robot_geometry_unchanged':True,
            'trajectory_code_and_validation_policy_unchanged':True,
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'frozen_entrypoint':'scripts/render_user_protected_pairs.py',
            'frozen_entrypoint_sha256':hashlib.sha256((ROOT/'scripts/render_user_protected_pairs.py').read_bytes()).hexdigest()}
    (output/'render_configuration.json').write_text(json.dumps(config,indent=2)+'\n')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
