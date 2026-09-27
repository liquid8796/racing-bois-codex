"""Guarded one-file handoff. Only root may opt into --install after review."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import os

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TARGET = ROOT / 'Assets/RacingBois/Client/Adapters/P08MusicDirector.cs'
BEFORE = 'cdd8b9bcbede475f594d672adee7e55130ab71eea2e88744d66d009abf2c2db5'
META = 'bed57dec813e2e651b2e22516ee194be26cbcaa763aa63ef7e7c3278a7341ffe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    validation = json.loads((HERE / 'validation.json').read_text(encoding='utf8'))
    if not validation.get('passed') or validation.get('nativePlaybackVerified') is not False:
        raise ValueError('A successful managed preflight with honest native scope is required.')
    for name, expected in validation['sourceInputs'].items():
        # Project assemblies may refresh after install; require the staged/production source and pinned engine inputs.
        if '/Library/ScriptAssemblies/' in name.replace('\\', '/'):
            continue
        if sha(Path(name)) != expected:
            raise ValueError('Preflight input changed: ' + name)
    expected = validation['sourceInputs'][str(HERE / 'P08MusicDirector.cs')]
    current = sha(TARGET)
    if current not in (BEFORE, expected) or sha(Path(str(TARGET) + '.meta')) != META:
        raise ValueError('Director or its meta differs from the agreed handoff.')
    if args.install and current != expected:
        descriptor, temporary = tempfile.mkstemp(prefix='P08MusicDirector.', suffix='.tmp', dir=TARGET.parent)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write((HERE / 'P08MusicDirector.cs').read_bytes())
            os.replace(temporary, TARGET)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        if sha(TARGET) != expected or sha(Path(str(TARGET) + '.meta')) != META:
            raise ValueError('Installation postcheck failed.')
    print(json.dumps(dict(passed=True, installed=args.install, target=str(TARGET), beforeSha256=current, candidateSha256=expected,
                         nativePlaybackVerified=False)))


if __name__ == '__main__':
    main()
