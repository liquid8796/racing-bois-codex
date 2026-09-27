"""Install only the frozen receipt repair after root's source-bound checkpoint."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--install', action='store_true')
args = parser.parse_args()
manifest = json.loads((HERE / 'handoff.json').read_text())
for row in manifest['files']:
    candidate, target = ROOT / row['candidate'], ROOT / row['source']
    if candidate.parent != HERE or target.parent != ROOT / 'Assets/RacingBois/Editor':
        raise ValueError('Unexpected receipt repair path')
    if sha(candidate) != row['candidateSha256']:
        raise ValueError('Staged candidate changed: ' + str(candidate))
    current = sha(target) if target.exists() else None
    if current not in {row['originalSha256'], row['candidateSha256']}:
        raise ValueError('Live source changed independently: ' + str(target))
    meta = Path(str(target) + '.meta')
    if row['metaSha256'] is not None and (not meta.exists() or sha(meta) != row['metaSha256']):
        raise ValueError('Existing script metadata changed')
if args.install:
    for row in manifest['files']:
        target = ROOT / row['source']
        if not target.exists() or sha(target) != row['candidateSha256']:
            shutil.copyfile(ROOT / row['candidate'], target)
print(json.dumps({'installed': args.install, 'files': len(manifest['files']), 'nativeUnityRun': False}))
