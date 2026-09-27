"""Hash-guarded installation of the observed empty imported-TTF texture contract."""
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
PROOF = ROOT / 'docs/p10/native-baseline/diagnosis-baseline03/imported-font-textures-full.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    if not MANIFEST.exists():
        value = {'schema': 1, 'source': TARGET.relative_to(ROOT).as_posix(), 'originalSha256': sha(TARGET),
                 'candidateSha256': sha(CANDIDATE), 'metaSha256': sha(META),
                 'diagnosis': PROOF.relative_to(ROOT).as_posix(), 'diagnosisSha256': sha(PROOF),
                 'nativeVerified': False, 'scope': 'Only observed empty readonly TTF importer texture caches; source/owner/material/importer/dependency/texture identity stays bound.'}
        with MANIFEST.open('x', encoding='utf8') as stream:
            json.dump(value, stream, indent=2); stream.write('\n')
    manifest = json.loads(MANIFEST.read_text(encoding='utf8'))
    if manifest['source'] != TARGET.relative_to(ROOT).as_posix() or sha(CANDIDATE) != manifest['candidateSha256'] or sha(TARGET) not in {manifest['originalSha256'], manifest['candidateSha256']} or sha(META) != manifest['metaSha256'] or sha(PROOF) != manifest['diagnosisSha256']:
        raise ValueError('Imported-font guard handoff changed; preserve and review the different bytes')
    if args.install:
        shutil.copyfile(CANDIDATE, TARGET)
        if sha(TARGET) != manifest['candidateSha256'] or sha(META) != manifest['metaSha256']:
            raise ValueError('Guard installation differs from reviewed bytes')
    print(json.dumps({'installed': args.install, 'candidateSha256': manifest['candidateSha256'], 'nativeVerified': False}))


if __name__ == '__main__':
    main()
