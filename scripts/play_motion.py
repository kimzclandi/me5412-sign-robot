"""Open a real interactive MuJoCo viewer; macOS: .venv/bin/mjpython this_script."""
import argparse
from pathlib import Path
import sys
import time
import numpy as np
import mujoco
import mujoco.viewer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import ACTION_IDS, apply_frame, load_model, load_motion, require_preview_permission


def main():
    parser = argparse.ArgumentParser(description="Interactive 3D research preview; kinematic replay, not dynamics.")
    parser.add_argument("--action", choices=ACTION_IDS, default="HELLO")
    parser.add_argument("--allow-candidate-preview", action="store_true")
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    motion = load_motion(args.action)
    require_preview_permission(motion, args.allow_candidate_preview)
    model = load_model()
    data = mujoco.MjData(model)
    print(f"UNREVIEWED {args.action}: fixed-base kinematic replay; no ASL or dynamics validation.", flush=True)
    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.lookat[:] = [0.06, 0, 1.09]
        viewer.cam.distance = 1.25
        viewer.cam.azimuth = 180
        viewer.cam.elevation = -4
        start = time.monotonic()
        duration = motion['timestamps_s'][-1]
        while viewer.is_running():
            elapsed = time.monotonic() - start
            if elapsed > duration and not args.loop:
                break
            local_time = elapsed % duration
            frame = min(int(np.searchsorted(motion['timestamps_s'], local_time)), len(motion['timestamps_s']) - 1)
            with viewer.lock():
                apply_frame(model, data, motion['joint_names'], motion['positions'][frame])
                data.time = float(local_time)
            viewer.sync()
            time.sleep(1 / 60)


if __name__ == '__main__':
    main()
