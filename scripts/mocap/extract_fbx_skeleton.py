"""Extract per-frame world poses of signing-relevant bones from a Studio Galt FBX.

Runs inside Blender (headless), because Blender's FBX importer resolves the rig
hierarchy, pre-rotations and unit scale that a plain binary reader would not:

    blender -b --factory-startup --python scripts/mocap/extract_fbx_skeleton.py -- \
        --fbx "data/mocap/studio_galt_v1/raw/YOU/<file>.fbx" --word YOU \
        --out data/mocap/studio_galt_v1/skeleton/YOU.npz

Output arrays (Blender world frame, Z up, metres, source frame rate):
    frame_times_s [T], bone_names [B], head [T,B,3], tail [T,B,3], rot [T,B,3,3]
Only deform bones are kept; the FK/IK control bones in the "Full" rig are ignored.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

FINGERS = ("thumb", "index", "middle", "ring", "pinky")
# Canonical (UE-style) names; ASK uses an older rig and needs its own alias table.
CANONICAL = (["pelvis", "spine_05", "neck_01", "head"]
             + [f"{part}_{s}" for s in ("l", "r") for part in ("clavicle", "upperarm", "lowerarm", "hand")]
             + [f"{finger}_0{i}_{s}" for s in ("l", "r") for finger in FINGERS for i in (1, 2, 3)])
ALIASES = {"ASK": {}}  # filled in when ASK is processed; see docs once verified


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True)
    parser.add_argument("--word", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main():
    args = parse_args()
    fbx = Path(args.fbx)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), automatic_bone_orientation=False)
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one armature, found {len(armatures)}")
    arm = armatures[0]
    action = arm.animation_data.action if arm.animation_data else None
    if action is None:
        raise RuntimeError("Armature has no action")
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    first, last = (int(round(v)) for v in action.frame_range)
    alias = ALIASES.get(args.word, {})
    names = [alias.get(n, n) for n in CANONICAL]
    missing = [n for n in names if n not in arm.pose.bones]
    if missing:
        raise RuntimeError(f"Missing bones: {missing}")

    frames = list(range(first, last + 1))
    head = np.zeros((len(frames), len(names), 3))
    tail = np.zeros_like(head)
    rot = np.zeros((len(frames), len(names), 3, 3))
    world = np.array(arm.matrix_world)
    for t, frame in enumerate(frames):
        scene.frame_set(frame)
        for b, name in enumerate(names):
            pose = arm.pose.bones[name]
            m = world @ np.array(pose.matrix)
            head[t, b] = m[:3, 3]
            tail[t, b] = (world @ np.r_[np.array(pose.tail), 1.0])[:3]
            rot[t, b] = m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, frame_times_s=(np.array(frames) - first) / fps,
                        bone_names=np.array(CANONICAL), head=head, tail=tail, rot=rot)
    meta = {"word": args.word, "source_fbx": fbx.name,
            "source_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(),
            "blender_version": bpy.app.version_string, "source_fps": fps,
            "frames": len(frames), "frame_range": [first, last],
            "frame": "Blender world, Z up, metres", "bone_aliases": alias}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
