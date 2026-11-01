import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

SOURCE = Path('/home/kingderman/Documents/ME5412-github-latest')
EVIDENCE = Path('/home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001')
WORK = Path('/tmp/me5412_auto_cuts_20261031_001')

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def inventory(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(directory) / name
            rel = str(p.relative_to(root))
            if p.is_symlink():
                result[rel] = {'kind': 'symlink', 'target': os.readlink(p)}
            elif p.is_dir():
                result[rel] = {'kind': 'directory'}
            else:
                result[rel] = {'kind': 'file', 'bytes': p.stat().st_size, 'sha256': digest(p)}
    return result

EVIDENCE.mkdir(parents=True, exist_ok=False)
(EVIDENCE / 'R1').mkdir()
before = inventory(SOURCE)
(EVIDENCE / 'R1/baseline_inventory.json').write_text(json.dumps(before, indent=2) + '\n')
for name, args in [('git_status', ['git', '--no-optional-locks', 'status', '--short', '--branch', '--untracked-files=all']),
                   ('git_diff', ['git', 'diff', '--binary']), ('git_head', ['git', 'rev-parse', 'HEAD'])]:
    r = subprocess.run(args, cwd=SOURCE, capture_output=True)
    (EVIDENCE / f'R1/{name}.txt').write_bytes(r.stdout + r.stderr)
    assert r.returncode == 0
archive = EVIDENCE / 'baseline.tar'
with tarfile.open(archive, 'w') as tar:
    tar.add(SOURCE, arcname='repository', recursive=True)
WORK.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    tar.extractall(WORK, filter='fully_trusted')
restored = inventory(WORK / 'repository')
after = inventory(SOURCE)
assert before == after, 'Source changed during preservation'
assert before == restored, 'Restore mismatch'
report = {'source': str(SOURCE), 'work': str(WORK / 'repository'), 'archive': str(archive),
          'archive_bytes': archive.stat().st_size, 'archive_sha256': digest(archive),
          'entries': len(before), 'source_unchanged': True, 'restore_matches': True,
          'symlinks_preserved_not_dereferenced': True}
(EVIDENCE / 'R1/preservation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
