import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path('/tmp/me5412_auto_cuts_20261031_001/repository')
SOURCE = Path('/home/kingderman/Documents/ME5412-github-latest')
OUT = ROOT / 'results/user_protected_auto_20261031_001'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def begin(task, files, baseline=False):
    directory = OUT/task
    directory.mkdir(parents=True, exist_ok=True)
    records = {}
    for relative in files:
        p = (SOURCE if baseline else ROOT)/relative
        records[relative] = digest(p)
        if p.is_file():
            copy = directory/'before'/relative
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, copy)
    (directory/'before_hashes.json').write_text(json.dumps(records,indent=2)+'\n')

def finish(task, number, cn, en, files):
    for lang, body, label in [('',cn,'English'),('.en',en,'中文')]:
        link = f'TASK-{number:02d}.en.md' if not lang else f'TASK-{number:02d}.md'
        text = f'# TASK-{number:02d} — {task}\n\n[{label}]({link})\n\n'+body+'\n'
        (ROOT/f'TASK-{number:02d}{lang}.md').write_text(text)
    before_path = OUT/task/'before_hashes.json'
    before = json.loads(before_path.read_text()) if before_path.exists() else {}
    changes = [{'file':str(SOURCE/f),'relative':f,'before_sha256':before.get(f),
                'after_sha256':digest(ROOT/f)} for f in files]
    (OUT/task/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')

if __name__ == '__main__':
    action, task, *files = sys.argv[1:]
    if action == 'begin':
        begin(task,files)
