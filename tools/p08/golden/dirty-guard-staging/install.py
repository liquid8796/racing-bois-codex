"""Freeze/install the single native dirty-asset guard correction after root review."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
CANDIDATE = HERE / 'NativeBuildDirtyAssetGuard.cs'
TARGET = ROOT / 'Assets/RacingBois/Editor/NativeBuildDirtyAssetGuard.cs'
META = Path(str(TARGET) + '.meta')
MANIFEST = HERE / 'handoff.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--install', action='store_true')
args = parser.parse_args()
if not MANIFEST.exists():
    MANIFEST.write_text(json.dumps({'schema': 1, 'source': TARGET.relative_to(ROOT).as_posix(),
                                   'originalSha256': sha(TARGET), 'candidateSha256': sha(CANDIDATE),
                                   'metaSha256': sha(META), 'diagnosis': 'docs/p10/native-baseline/diagnosis-baseline01/gather-probe.json'}, indent=2) + '\n', encoding='utf-8')
manifest = json.loads(MANIFEST.read_text())
if sha(CANDIDATE) != manifest['candidateSha256'] or sha(TARGET) not in {manifest['originalSha256'], manifest['candidateSha256']} or sha(META) != manifest['metaSha256']:
    raise ValueError('Guard handoff changed independently; preserve evidence and review it')
if args.install:
    shutil.copyfile(CANDIDATE, TARGET)
    if sha(TARGET) != manifest['candidateSha256'] or sha(META) != manifest['metaSha256']:
        raise ValueError('Guard installation differed')
print(json.dumps({'installed': args.install, 'candidateSha256': manifest['candidateSha256'], 'nativeVerified': False}))
