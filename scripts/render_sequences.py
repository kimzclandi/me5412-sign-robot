#!/usr/bin/env python3
"""Annotated original-versus-sequence kinematic replays for selected, freshly rechecked chains.

Only selected numerical passes are rendered. A soft wall clock and free-disk
floor are checked before each case; unrendered selections are listed, and the
media denominator (selected cases) is reported apart from the case denominator.
"""
import argparse
from collections import OrderedDict
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import numpy as np
from sign_robot.motion import apply_frame, load_model
from sign_robot.pair_contract import atomic_json, atomic_motion, file_hash, inside, read_json, read_motion
from sign_robot.pair_verification_v2 import _full_replay
from sign_robot.sequence_contract import load_sequence_policy, read_sequence
from sign_robot.sequence_verification import verify_saved_sequence_v1

COLOURS = {'protected': (78, 215, 143), 'retained': (100, 175, 255), 'cut': (255, 110, 100),
           'transition': (255, 199, 65), 'hold': (180, 180, 180)}


def phase(word, frame, count, label):
    if frame >= count:
        return 'hold', 'end hold / 结束保持'
    c0, c1 = word['protected_core_frames']
    if c0 <= frame <= c1:
        return 'protected', f"{label} protected / 用户保护 f{frame}"
    first, last = word['source_frames']
    kind = 'retained' if first <= frame <= last else 'cut'
    return kind, f"{label} {'retained / 保留' if kind == 'retained' else 'cut / 裁剪'} f{frame}"


def render(sequence, evidence, clips, folder, renderer, model, data, cameras, font):
    import imageio.v2 as imageio
    from PIL import Image, ImageDraw
    motion = _full_replay(sequence, clips)
    words = sequence['word_instances']
    counts = [len(clips[w['gloss']]['positions']) for w in words]
    baseline_q = np.vstack([clips[w['gloss']]['positions'] for w in words])
    starts = np.cumsum([0, *counts])
    baseline = {'joint_names': motion['joint_names'], 'positions': baseline_q, 'timestamps_s': np.arange(len(baseline_q)) / 30}
    atomic_motion(folder / 'replay.npz', motion)
    atomic_motion(folder / 'baseline.npz', baseline)
    total = max(len(motion['positions']), len(baseline_q))
    width, height = 320, 384
    numerical = evidence['numerical_checks_passed'] is True
    cache = OrderedDict()

    def views(q):
        key = np.asarray(q, dtype='<f8').tobytes()
        if key not in cache:
            apply_frame(model, data, motion['joint_names'], q)
            cache[key] = []
            for camera in cameras:
                renderer.update_scene(data, camera=camera)
                cache[key].append(Image.fromarray(renderer.render()))
            if len(cache) > 256:
                cache.popitem(last=False)
        return cache[key]

    def label(word):
        return f"#{word['position']} {word['gloss']}"

    def phase_at(index, planned):
        if not planned:
            position = int(np.searchsorted(starts, index, side='right') - 1)
            if position >= len(words):
                return 'hold', 'end hold / 结束保持'
            return phase(words[position], index - starts[position], counts[position], label(words[position]))
        if index >= len(motion['positions']):
            return 'hold', 'end hold / 结束保持'
        moment = index / 30
        segment = next(s for s in sequence['segments'] if s['start_time_s'] - 1e-10 <= moment <= s['end_time_s'] + 1e-10)
        if segment['kind'] == 'polynomial_v2':
            position = sequence['segments'].index(segment)
            tail = sequence.get('rest_tail')
            if tail is not None and tail['segment_indices'][0] <= position <= tail['segment_indices'][1]:
                return 'transition', 'ADDED return to rest / 新增回到初始姿态'
            edge = next(e for e in sequence['edges'] if e['segment_indices'][0] <= position <= e['segment_indices'][1])
            return 'transition', f"ADDED transition {edge['edge_index']} / 新增过渡"
        word = next(w for w in words if w['instance_id'] == segment['word_instance_id'])
        frame = round(segment['source_frames'][0] + (moment - segment['start_time_s']) * 30)
        return phase(word, frame, counts[word['position']], label(word))

    title = sequence['sequence_id'].replace('__', ' → ')
    status = ('NUMERICAL PASS / 数值通过 · FORMAL OFF / 正式关闭' if numerical
              else 'FAILED DIAGNOSTIC / 失败诊断 · NOT SELECTED / 未选用')
    picks = {round(sequence['segments'][e['segment_indices'][0]]['start_time_s'] * 30)
             for e in [*sequence['edges'], *([sequence['rest_tail']] if 'rest_tail' in sequence else [])]}
    stills = []
    with imageio.get_writer(folder / 'comparison.mp4', fps=30, codec='libx264', quality=8, macro_block_size=16,
                            pixelformat='yuv420p', ffmpeg_params=['-threads', '1']) as writer:
        for index in range(total):
            panel = Image.new('RGB', (width * 2, height * 2 + 112), (14, 21, 32))
            draw = ImageDraw.Draw(panel)
            draw.text((8, 5), f'{title}  {index / 30:.2f}s', font=font, fill='white')
            draw.text((8, 29), status, font=font, fill=(130, 235, 170) if numerical else (255, 140, 125))
            draw.text((8, 54), 'SEQUENCE / 多词序列 · ALGORITHM windows / 算法窗口 · KINEMATIC / 运动学回放', font=font, fill='white')
            draw.text((8, 79), 'Green 保护 | Blue 保留 | Red 裁剪 | Yellow 新增 | Gray 保持', font=font, fill='white')
            for row, (planned, m) in enumerate(((False, baseline), (True, motion))):
                q = m['positions'][min(index, len(m['positions']) - 1)]
                kind, text = phase_at(index, planned)
                for column, view in enumerate(views(q)):
                    image = view.copy()
                    d = ImageDraw.Draw(image)
                    d.rectangle((0, 0, width, 60), fill=(14, 21, 32))
                    d.text((6, 3), ('AUTO / 自动' if planned else 'ORIGINAL / 原始') + ' · ' + ('front 正面' if column == 0 else 'side 侧面'), font=font, fill='white')
                    d.text((6, 29), text, font=font, fill=COLOURS[kind])
                    d.rectangle((0, height - 6, width, height), fill=COLOURS[kind])
                    panel.paste(image, (column * width, 112 + row * height))
            writer.append_data(np.asarray(panel))
            if index in picks:
                stills.append(panel.copy())
    sheet = Image.new('RGB', (640 * len(stills), 880))
    for i, still in enumerate(stills):
        sheet.paste(still, (640 * i, 0))
    sheet.save(folder / 'contact_sheet.png')
    # Compare every protected instance in the replay that the video was drawn from.
    checks = []
    for word in words:
        c0, c1 = word['protected_core_frames']
        segment = next(s for s in sequence['segments'] if s.get('word_instance_id') == word['instance_id'])
        frames = np.rint((segment['start_time_s'] + (np.arange(c0, c1 + 1) - segment['source_frames'][0]) / 30) * 30).astype(int)
        checks.append({'instance_id': word['instance_id'], 'replay_frames': [int(frames[0]), int(frames[-1])],
                       'poses_bitwise_equal': bool(np.array_equal(motion['positions'][frames], clips[word['gloss']]['positions'][c0:c1 + 1]))})
    return total, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', dest='cases', help='Default: every case with a selected attempt')
    parser.add_argument('--soft-wall-time-s', type=float, default=7200.0)
    parser.add_argument('--min-free-gib', type=float, default=5.0)
    args = parser.parse_args()
    started = time.monotonic()
    if args.output.exists():
        parser.error('Output exists; choose a new output path')
    run_dir = args.run_dir.resolve()
    manifest = read_json(run_dir / 'manifest.json')
    policy, _ = load_sequence_policy(ROOT, manifest['sequence_policy'])
    summary = read_json(run_dir / 'summary.json')
    cases = [c for c in summary['cases'] if c['selected_attempt'] and (not args.cases or c['sequence_id'] in args.cases)]
    import mujoco
    from PIL import ImageFont
    model = load_model(ROOT)
    data = mujoco.MjData(model)
    cameras = []
    for azimuth in (180, 90):
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [.06, 0, 1.02]
        camera.distance, camera.azimuth, camera.elevation = 1.6, azimuth, -4
        cameras.append(camera)
    font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 14)
    library = read_json(ROOT / 'motions/hospital_v1_motions.json')
    motions = {w['gloss']: w['motion'] for w in library['glosses'] if w.get('motion')}
    args.output.mkdir(parents=True)
    reports = []
    not_rendered = []
    with mujoco.Renderer(model, width=320, height=384) as renderer:
        for case in cases:
            stop = ('SOFT_WALL_TIME_REACHED' if time.monotonic() - started >= args.soft_wall_time_s else
                    'DISK_FREE_BELOW_FLOOR' if shutil.disk_usage(args.output).free < args.min_free_gib * 1024 ** 3 else None)
            if stop or not_rendered:
                not_rendered.append({'sequence_id': case['sequence_id'], 'reason': stop or not_rendered[0]['reason']})
                continue
            source = inside(ROOT, case['selected_output']) if case.get('selected_output') else run_dir
            path = source / 'sequences' / case['sequence_id'] / f"{case['selected_attempt']}.json"
            sequence = read_sequence(path, policy)
            evidence = verify_saved_sequence_v1(ROOT, path, manifest['sequence_policy'])
            if evidence['numerical_checks_passed'] is not True:
                raise ValueError(f"Fresh recheck does not confirm {case['sequence_id']}")
            clips = {w['gloss']: read_motion(inside(ROOT, motions[w['gloss']])) for w in sequence['word_instances']}
            folder = args.output / case['sequence_id']
            folder.mkdir()
            atomic_json(folder / 'independent_verification.json', evidence)
            frames, checks = render(sequence, evidence, clips, folder, renderer, model, data, cameras, font)
            report = {'sequence_id': case['sequence_id'], 'source_sequence': str(path.relative_to(ROOT)),
                      'source_sequence_sha256': file_hash(path), 'numerical_checks_passed': True,
                      'formal_acceptance_enabled': False, 'playback_eligible': False, 'fps': 30, 'video_frames': frames,
                      'video_duration_s': frames / 30, 'replay_duration_s': evidence['replay_duration_s'],
                      'layout': 'original full clips top, sequence bottom; front left, side right; shorter row holds end',
                      'protected_instance_video_checks': checks,
                      'files': {f.name: file_hash(f) for f in folder.iterdir() if f.is_file()}}
            atomic_json(folder / 'report.json', report)
            reports.append(report)
            print(json.dumps({'sequence': case['sequence_id'], 'frames': frames,
                              'protected_equal': all(c['poses_bitwise_equal'] for c in checks)}), flush=True)
    atomic_json(args.output / 'summary.json', {'sequences': reports, 'count': len(reports),
        'case_denominator': summary['denominator'], 'media_denominator': len(cases), 'not_rendered': not_rendered,
        'protected_instances_checked': sum(len(r['protected_instance_video_checks']) for r in reports),
        'protected_instances_equal': sum(c['poses_bitwise_equal'] for r in reports for c in r['protected_instance_video_checks']),
        'formal_pass_count': 0})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
