"""Decode and hash-check four corrected-run comparison videos."""
import hashlib
import json
from pathlib import Path
import imageio.v2 as imageio

out=Path(__file__).resolve().parents[1]
reports={}
observations={
    'COME__NOW':'Failure/algorithm labels visible. Original protected f102/f118/f127; auto protected f129, retained f145 and added transition shown in front/side views.',
    'NOW__COME':'Failure/algorithm labels visible. Original protected f74 and cut f89/f100; auto retained f77, added transition and COME protected f34 shown.',
    'COME__COME':'Failure/algorithm labels visible. Original COME f134/f150/f159 marked retained beyond corrected core end132; auto f161/f177 and added transition shown.',
    'NOW__NOW':'Failure/algorithm labels visible. Original f79/f82 retained and f88 cut; auto f82 retained and added transition shown.'}
for pair, observation in observations.items():
    folder=out/'videos'/pair
    report=json.loads((folder/'report.json').read_text())
    assert all(hashlib.sha256((folder/name).read_bytes()).hexdigest()==value for name,value in report['files'].items())
    reader=imageio.get_reader(folder/'comparison.mp4')
    count=reader.count_frames()
    meta=reader.get_meta_data()
    reader.close()
    assert count==report['video_frames'] and meta['fps']==30
    reports[pair]={'decoded_frames':count,'fps':meta['fps'],'size':meta['size'],
        'video_sha256':hashlib.sha256((folder/'comparison.mp4').read_bytes()).hexdigest(),
        'all_export_hashes_match':True,'contact_sheet_image_tool_inspection':observation}
path=out/'R6/media_checks.json'
assert not path.exists()
path.write_text(json.dumps({'passed':True,'pairs':reports,
    'visual_check_actor':'execution model using view_image; no human/group-2 review',
    'human_approval_supplied':False},indent=2)+'\n')
print(json.dumps({'passed':True,'videos':reports},indent=2))
