#!/usr/bin/env python3
"""Real-geometry, annotated original-versus-automatic kinematic comparisons."""
import argparse
from collections import OrderedDict
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from sign_robot.motion import apply_frame,load_model
from sign_robot.pair_contract import (atomic_json,atomic_motion,file_hash,json_hash,read_json,
    read_motion,read_pair_trajectory,run_identity,freeze_library)
from sign_robot.pair_runner_v2 import V2RunStore
from sign_robot.pair_verification_v2 import _full_replay,verify_saved_pair_v2


def cut_ranges(first,last,count):
    return [[a,b] for a,b in ((0,first-1),(last+1,count-1)) if a<=b]


def original_phase(frame,word,count):
    if frame>=count:
        return 'hold','end hold / 结束保持'
    core=word['protected_core_frames']
    if core[0]<=frame<=core[1]:
        return 'protected',f"{word['gloss']} protected / 用户保护 f{frame}"
    first,last=word['source_frames']
    return ('retained',f"{word['gloss']} retained / 保留 f{frame}") if first<=frame<=last else ('cut',f"{word['gloss']} cut / 裁剪 f{frame}")


def result_label(numerical_pass):
    return 'NUMERICAL PASS / 数值通过 · FORMAL OFF / 正式关闭' if numerical_pass else 'FAILED DIAGNOSTIC / 失败诊断 · NOT SELECTED / 未选用'


def choose_preview(store,record):
    selected=record.get('selected_candidate_id')
    if selected:
        entry=next(a for a in record['attempts'] if a['attempt_id']==selected)
        return entry['candidate_file'],True,'independently_selected_numerical_candidate'
    candidates=[]
    for entry in record['attempts']:
        saved=store._read_attempt(entry,record['pair_id'])
        for artifact in saved['artifacts']:
            curve=read_pair_trajectory(store.run_dir/artifact['path'],schema_version=2)
            duration=curve['segments'][-2]['end_time_s']-curve['segments'][1]['start_time_s']
            timing=saved['diagnostic'].get('timing',{}).get('attempts',[])
            count=len(timing[-1].get('reason_codes',[])) if timing else 100
            candidates.append((not artifact['eligible_for_selection'],count,duration,artifact['path']))
    if not candidates:
        raise ValueError(f"No saved curve for diagnostic preview: {record['pair_id']}")
    return min(candidates)[-1],False,'saved_failed_curve_for_diagnosis_only'


def render_pair(store,record,out,renderer,model,data,cameras,cache,font):
    import imageio.v2 as imageio
    from PIL import Image,ImageDraw
    pair=record['pair_id']
    folder=out/pair
    folder.mkdir(exist_ok=False)
    relative,numerical,selection=choose_preview(store,record)
    path=store.run_dir/relative
    curve=read_pair_trajectory(path,schema_version=2)
    evidence=verify_saved_pair_v2(ROOT,path,store.policy)
    if numerical and evidence.get('numerical_checks_passed') is not True:
        raise ValueError('Fresh independent recheck does not confirm selected candidate')
    numerical=numerical and evidence.get('numerical_checks_passed') is True
    atomic_json(folder/'independent_verification.json',evidence)
    library=read_json(store.run_dir/'library_manifest.json')
    words={w['gloss']:w for w in library['words']}
    clips={w['gloss']:read_motion(ROOT/words[w['gloss']]['motion']) for w in curve['word_instances']}
    motion=_full_replay(curve,clips)
    baseline_q=np.vstack([clips[w['gloss']]['positions'] for w in curve['word_instances']])
    baseline={'joint_names':motion['joint_names'],'positions':baseline_q,'timestamps_s':np.arange(len(baseline_q))/30}
    atomic_motion(folder/'replay.npz',motion)
    atomic_motion(folder/'baseline.npz',baseline)
    atomic_json(folder/'trajectory.json',{'schema_version':2,'trajectory':curve,'trajectory_hash':json_hash(curve)})
    first_count=len(clips[curve['word_instances'][0]['gloss']]['positions'])
    total=max(len(motion['positions']),len(baseline_q))
    width,height=320,384
    colours={'protected':(78,215,143),'retained':(100,175,255),'cut':(255,110,100),'transition':(255,199,65),'hold':(180,180,180)}
    def frame_views(q):
        key=np.asarray(q,dtype='<f8').tobytes()
        if key in cache:
            value=cache.pop(key)
            cache[key]=value
            return value
        apply_frame(model,data,motion['joint_names'],q)
        values=[]
        for camera in cameras:
            renderer.update_scene(data,camera=camera)
            values.append(Image.fromarray(renderer.render()))
        cache[key]=values
        if len(cache)>256:
            cache.popitem(last=False)
        return values
    def phase_at(index,planned):
        if not planned:
            instance=0 if index<first_count else 1
            local=index if instance==0 else index-first_count
            word=curve['word_instances'][instance]
            return original_phase(local,word,len(clips[word['gloss']]['positions']))
        if index>=len(motion['positions']):
            return 'hold','end hold / 结束保持'
        moment=index/30
        segment=next(s for s in curve['segments'] if s['start_time_s']-1e-10<=moment<=s['end_time_s']+1e-10)
        if segment['kind']=='polynomial_v2':
            return 'transition','ADDED transition / 新增过渡'
        word=next(w for w in curve['word_instances'] if w['instance_id']==segment['word_instance_id'])
        frame=round(segment['source_frames'][0]+(moment-segment['start_time_s'])*30)
        return original_phase(frame,word,len(clips[word['gloss']]['positions']))
    picks={round(curve['segments'][1]['start_time_s']*30),round(curve['segments'][-2]['end_time_s']*30),round(len(motion['positions'])/2)}
    stills=[]
    with imageio.get_writer(folder/'comparison.mp4',fps=30,codec='libx264',quality=8,
            macro_block_size=16,pixelformat='yuv420p',ffmpeg_params=['-threads','1']) as writer:
        for index in range(total):
            panel=Image.new('RGB',(width*2,height*2+112),(14,21,32))
            draw=ImageDraw.Draw(panel)
            draw.text((8,5),pair.replace('__',' → ')+f'  {index/30:.2f}s',font=font,fill='white')
            draw.text((8,29),result_label(numerical),font=font,fill=(130,235,170) if numerical else (255,140,125))
            draw.text((8,54),'ALGORITHM windows / 算法窗口 · KINEMATIC / 运动学回放',font=font,fill='white')
            draw.text((8,79),'Green 保护 | Blue 保留 | Red 裁剪 | Yellow 新增 | Gray 保持',font=font,fill='white')
            for row,(planned,m) in enumerate(((False,baseline),(True,motion))):
                q=m['positions'][min(index,len(m['positions'])-1)]
                kind,phase=phase_at(index,planned)
                for column,view in enumerate(frame_views(q)):
                    image=view.copy()
                    d=ImageDraw.Draw(image)
                    d.rectangle((0,0,width,60),fill=(14,21,32))
                    d.text((6,3),('AUTO / 自动' if planned else 'ORIGINAL / 原始')+' · '+('front 正面' if column==0 else 'side 侧面'),font=font,fill='white')
                    d.text((6,29),phase,font=font,fill=colours[kind])
                    d.rectangle((0,height-6,width,height),fill=colours[kind])
                    panel.paste(image,(column*width,112+row*height))
            writer.append_data(np.asarray(panel))
            if index in picks:
                stills.append(panel.copy())
            if index%90==0:
                print(json.dumps({'pair':pair,'render_frame':index,'total':total}),flush=True)
    sheet=Image.new('RGB',(640*len(stills),880))
    for i,still in enumerate(stills):
        sheet.paste(still,(640*i,0))
    sheet.save(folder/'contact_sheet.png')
    q,t=motion['positions'],motion['timestamps_s']
    v=np.gradient(q,t,axis=0,edge_order=2)
    a=np.gradient(v,t,axis=0,edge_order=2)
    j=np.gradient(a,t,axis=0,edge_order=2)
    with (folder/'trajectory_evidence.csv').open('w') as stream:
        writer=csv.writer(stream)
        writer.writerow(['time_s','phase','max_abs_velocity_rad_s','max_abs_acceleration_rad_s2','max_abs_jerk_rad_s3'])
        writer.writerows([[float(t[i]),phase_at(i,True)[0],float(abs(v[i]).max()),float(abs(a[i]).max()),float(abs(j[i]).max())] for i in range(len(t))])
    report={'pair_id':pair,'source_run':str(store.run_dir.relative_to(ROOT)),'source_curve':relative,
        'source_curve_sha256':file_hash(path),'selection':selection,'diagnostic_only':not numerical,
        'numerical_checks_passed':numerical,'formal_acceptance_enabled':False,'playback_eligible':False,
        'window_provenance':'algorithm','fps':30,'video_frames':total,'video_duration_s':total/30,
        'replay_duration_s':float(t[-1]),'baseline_duration_s':float(baseline['timestamps_s'][-1]),
        'layout':'original top, algorithm bottom; front left, side right; shorter row holds end, no time warping',
        'word_instances':[{**w,'cut_frames':cut_ranges(*w['source_frames'],len(clips[w['gloss']]['positions']))} for w in curve['word_instances']],
        'transition_time_s':[curve['segments'][1]['start_time_s'],curve['segments'][-2]['end_time_s']],
        'reason_codes':evidence['reason_codes'],'metrics':evidence.get('metrics'),
        'protected_source_audit':evidence.get('protected_source_audit'),
        'files':{f.name:file_hash(f) for f in folder.iterdir() if f.is_file()}}
    atomic_json(folder/'report.json',report)
    print(json.dumps({'pair':pair,'numerical_pass':numerical,'video':str(folder/'comparison.mp4')}),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pair',action='append',required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; choose a new output path')
    store=V2RunStore.load(ROOT,args.run_dir)
    library,_=freeze_library(ROOT,store.policy)
    if run_identity(library,store.policy)!=store.manifest['identity']:
        raise ValueError('Code or inputs changed; choose a new run_id')
    import mujoco
    from PIL import ImageFont
    model=load_model(ROOT)
    data=mujoco.MjData(model)
    cameras=[]
    for azimuth in (180,90):
        cam=mujoco.MjvCamera()
        cam.lookat[:]=[.06,0,1.02]
        cam.distance=1.6
        cam.azimuth=azimuth
        cam.elevation=-4
        cameras.append(cam)
    font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',14)
    args.output.mkdir(parents=True,exist_ok=False)
    reports=[]
    with mujoco.Renderer(model,width=320,height=384) as renderer:
        cache=OrderedDict()
        for pair in args.pair:
            record=store._head_record(pair)
            if record is None or record['verification_state']=='NOT_RUN':
                raise ValueError('Pair must have independent review before video export')
            reports.append(render_pair(store,record,args.output,renderer,model,data,cameras,cache,font))
    atomic_json(args.output/'summary.json',{'pairs':reports,'denominator':len(reports),
        'numerical_pass_count':sum(r['numerical_checks_passed'] for r in reports),'formal_pass_sim_count':0})
    return 0


if __name__=='__main__':
    raise SystemExit(main())
