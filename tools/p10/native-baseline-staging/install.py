"""Read-only default; root explicitly applies reviewed stage and the bounded workload bridge."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    prepared = json.loads((HERE / 'prepared-inputs.json').read_text())
    bridge = prepared['copied'][0]
    for row in prepared['copied']:
        if digest(HERE / row['candidate']) != row['candidateSha256']:
            raise ValueError('Staged copied source changed: ' + row['candidate'])
        current = digest(ROOT / row['source'])
        allowed = {row['sourceSha256']} | ({row['candidateSha256']} if row == bridge else set())
        if current not in allowed:
            raise ValueError('Original source changed: ' + row['source'])
    rows = []
    for folder in ['Runtime', 'Editor']:
        for path in sorted((HERE / folder).iterdir()):
            if path.suffix not in {'.cs', '.asmdef'}:
                continue
            destination = ROOT / 'Assets/RacingBois/Diagnostics/NativeBaseline' / folder / path.name
            if destination.exists() and digest(destination) != digest(path):
                raise ValueError('Different existing diagnostic source: ' + str(destination))
            rows.append((path, destination))
    rows.append((HERE / bridge['candidate'], ROOT / bridge['source']))
    # The shared native helpers are owned/reviewed by the p08 build repair.
    for name, reviewed_stage in [('NativeBuildProjectSettingsScope.cs', 'build-staging'),
                                 ('NativeBuildDirtyAssetGuard.cs', 'imported-font-guard-staging'),
                                 ('NativeBuildFontPreservationScope.cs', 'font-scope-staging')]:
        source = ROOT / 'tools/p08/golden' / reviewed_stage / name
        destination = ROOT / 'Assets/RacingBois/Editor' / name
        if not destination.exists() or digest(source) != digest(destination):
            raise ValueError('Install reviewed shared native-build helper first: ' + name)
    manifest = [{'candidate': path.relative_to(ROOT).as_posix(), 'target': destination.relative_to(ROOT).as_posix(), 'sha256': digest(path)} for path, destination in rows]
    if args.apply:
        for source, destination in rows:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    print(json.dumps({'applied': args.apply, 'files': manifest, 'scope': 'Explicit diagnostic installation only; no native build/run or acceptance.'}, indent=2))


if __name__ == '__main__':
    main()
