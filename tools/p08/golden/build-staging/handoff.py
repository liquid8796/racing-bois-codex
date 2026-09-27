"""Check/install only the reviewed scoped Golden build sources; never runs Unity."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
MANIFEST = HERE / 'handoff.json'
NAMES = ['GoldenSampleBuilder.Build.cs', 'GoldenSampleBuilder.Scene.cs',
         'GoldenSampleBuilder.Environment.cs', 'GoldenSampleBuilder.Garage.cs',
         'GoldenSampleBuilder.Lighting.cs', 'NativeBuildProjectSettingsScope.cs',
         'NativeBuildDirtyAssetGuard.cs']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--freeze', action='store_true')
    group.add_argument('--install', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        if MANIFEST.exists():
            raise ValueError('Preserve existing handoff; do not silently rebind review inputs.')
        rows = []
        for name in NAMES:
            candidate = HERE / name
            target = ROOT / 'Assets/RacingBois/Editor' / name
            rows.append({'candidate': candidate.relative_to(ROOT).as_posix(), 'candidateSha256': sha(candidate),
                         'destination': target.relative_to(ROOT).as_posix(), 'originalSha256': sha(target) if target.exists() else None,
                         'originalMetaSha256': sha(Path(str(target) + '.meta')) if Path(str(target) + '.meta').exists() else None})
        value = {'schema': 1, 'liveEdits': False, 'files': rows,
                 'scope': 'Shared scoped settings and dirty-asset guards plus Golden build/owned scene saves. No native result or art acceptance.'}
        MANIFEST.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or len(manifest.get('files', [])) != len(NAMES):
        raise ValueError('Invalid handoff manifest')
    for row in manifest['files']:
        name = Path(row['candidate']).name
        if name not in NAMES or row['candidate'] != (HERE / name).relative_to(ROOT).as_posix() or row['destination'] != 'Assets/RacingBois/Editor/' + name:
            raise ValueError('Unexpected handoff destination')
        candidate, target = ROOT / row['candidate'], ROOT / row['destination']
        if sha(candidate) != row['candidateSha256']:
            raise ValueError('Staged source changed: ' + name)
        actual = sha(target) if target.exists() else None
        if actual not in (row['originalSha256'], row['candidateSha256']):
            raise ValueError('Live source changed independently: ' + name)
        meta = Path(str(target) + '.meta')
        if row['originalMetaSha256'] is not None and (not meta.exists() or sha(meta) != row['originalMetaSha256']):
            raise ValueError('Original script GUID/metadata changed: ' + name)
    if args.install:
        for row in manifest['files']:
            target = ROOT / row['destination']
            if not target.exists() or sha(target) != row['candidateSha256']:
                shutil.copyfile(ROOT / row['candidate'], target)
        for row in manifest['files']:
            if sha(ROOT / row['destination']) != row['candidateSha256']:
                raise ValueError('Installed source differs: ' + row['destination'])
    print(json.dumps({'checked': len(manifest['files']), 'installed': args.install, 'nativeUnityRun': False, 'visualAccepted': False}))


if __name__ == '__main__':
    main()
