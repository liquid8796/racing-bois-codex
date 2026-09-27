"""Root-only guarded installation of the reviewed desktop build candidate; default is read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
NAMES = {'P08DesktopBuilder.cs', 'P08DesktopBuilder.Owned.cs', 'P08DesktopCompiledSources.cs', 'P08OwnedUiAssets.cs', 'P08ProtectedUiFonts.cs'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def checked(relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative or any(part in {'', '.', '..'} for part in relative.split('/')):
        raise ValueError('Noncanonical path')
    path = ROOT / relative
    path.resolve().relative_to(ROOT.resolve())
    for item in [path, *path.parents]:
        if item == ROOT:
            break
        if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
            raise ValueError('Linked source/target rejected')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    plan = json.loads((HERE / 'handoff.json').read_text(encoding='utf-8'))
    if plan.get('state') != 'reviewed-staged-candidate' or plan.get('releaseAccepted') is not False:
        raise ValueError('Reviewed candidate handoff required')
    expected = {'Assets/RacingBois/Editor/' + name for name in NAMES}
    expected |= {'Assets/RacingBois/Editor/' + name + '.meta' for name in NAMES - {'P08DesktopBuilder.cs'}}
    expected.add('tools/p08/desktop/audit_desktop.py')
    if len(plan['files']) != len(expected) or {row['target'] for row in plan['files']} != expected:
        raise ValueError('Incomplete reviewed installation closure')
    targets = []
    for row in plan['files']:
        candidate, target = checked(row['candidate']), checked(row['target'])
        allowed = row['target'] == 'tools/p08/desktop/audit_desktop.py' or (target.parent == ROOT / 'Assets/RacingBois/Editor' and target.name.removesuffix('.meta') in NAMES)
        if not allowed or candidate.parent != HERE or target in targets:
            raise ValueError('Unreviewed or duplicate target')
        targets.append(target)
        if sha(candidate) != row['candidateSha256'] or sha(target) not in (row['beforeSha256'], row['candidateSha256']):
            raise ValueError('Candidate/target changed: ' + row['target'])
        if 'unchangedMetaSha256' in row and sha(target.with_suffix('.cs.meta')) != row['unchangedMetaSha256']:
            raise ValueError('Original script metadata changed')
    if args.install:
        for row in sorted(plan['files'], key=lambda value: (not value['target'].endswith('.meta'), value['target'])):
            candidate, target = checked(row['candidate']), checked(row['target'])
            if sha(target) == row['candidateSha256']:
                continue
            temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                with temporary.open('xb') as stream:
                    stream.write(candidate.read_bytes()); stream.flush(); os.fsync(stream.fileno())
                if sha(target) != row['beforeSha256']:
                    raise ValueError('Concurrent target edit')
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
        if any(sha(checked(row['target'])) != row['candidateSha256'] for row in plan['files']):
            raise ValueError('Post-install mismatch')
    print(json.dumps({'validatedFiles': len(targets), 'installed': args.install, 'nativeBuildVerified': False, 'releaseAccepted': False}))


if __name__ == '__main__':
    main()
