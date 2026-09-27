"""Verify/install the reviewed Golden import output and idempotent-dirty fixes; never calls Unity."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
NAMES = ['GoldenSampleBuilder.Outputs.cs', 'GoldenSampleBuilder.Import.cs']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_links(path):
    for value in [path, *path.parents]:
        if value.exists() and (value.is_symlink() or value.is_junction()):
            raise ValueError('Linked handoff path rejected')


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--freeze', action='store_true')
    group.add_argument('--install', action='store_true')
    args = parser.parse_args()
    receipt = HERE / 'handoff.json'
    if args.freeze:
        if receipt.exists():
            raise ValueError('Frozen handoff exists; do not rebind it silently')
        rows = []
        for name in NAMES:
            source, target = HERE / name, ROOT / 'Assets/RacingBois/Editor' / name
            no_links(source); no_links(target)
            meta = Path(str(target) + '.meta')
            rows.append({'candidate': source.relative_to(ROOT).as_posix(), 'candidateSha256': digest(source),
                         'destination': target.relative_to(ROOT).as_posix(), 'originalSha256': digest(target) if target.exists() else None,
                         'originalMetaSha256': digest(meta) if meta.exists() else None})
        tests = json.loads((HERE / 'tests.json').read_text(encoding='utf8'))
        if tests.get('passed') is not True or tests.get('checks') != 20 or tests.get('failures') != 0:
            raise ValueError('Required selected-output fixture controls did not pass')
        value = {'schema': 1, 'files': rows, 'managedOutputControls': tests['checks'],
                 'testSourceSha256': digest(HERE / 'Tests/Program.cs'), 'testReceiptSha256': digest(HERE / 'tests.json'),
                 'nativeVerificationPending': True,
                 'scope': 'Selected import output inventory and unchanged-settings importer dirty-flag restoration. Existing receipts unchanged; no native result or visual acceptance.'}
        with receipt.open('x', encoding='utf8') as stream:
            json.dump(value, stream, indent=2); stream.write('\n')
    frozen = json.loads(receipt.read_text(encoding='utf8'))
    expected = ['Assets/RacingBois/Editor/' + name for name in NAMES]
    if frozen.get('schema') != 1 or [row['destination'] for row in frozen.get('files', [])] != expected:
        raise ValueError('Unexpected handoff target set')
    for name, row in zip(NAMES, frozen['files']):
        source, target = HERE / name, ROOT / row['destination']
        no_links(source); no_links(target)
        if row['candidate'] != source.relative_to(ROOT).as_posix() or digest(source) != row['candidateSha256']:
            raise ValueError('Staged source changed')
        if (digest(target) if target.exists() else None) not in {row['originalSha256'], row['candidateSha256']}:
            raise ValueError('Live importer changed independently; preserve it')
        meta = Path(str(target) + '.meta')
        if row['originalMetaSha256'] is not None and (not meta.exists() or digest(meta) != row['originalMetaSha256']):
            raise ValueError('Original importer script GUID/metadata changed')
    if args.install:
        # The new partial helper lands before the call site, avoiding a missing-method intermediate state.
        for name, row in zip(NAMES, frozen['files']):
            target = ROOT / row['destination']
            if not target.exists() or digest(target) != row['candidateSha256']:
                shutil.copyfile(HERE / name, target)
        if any(digest(ROOT / row['destination']) != row['candidateSha256'] for row in frozen['files']):
            raise ValueError('Installed source differs from reviewed bytes')
    print(json.dumps({'checkedFiles': len(NAMES), 'installed': args.install, 'nativeVerificationPending': True,
                      'managedOutputControls': frozen['managedOutputControls']}))


if __name__ == '__main__':
    main()
