"""Install exactly the frozen reviewed sources; default is a no-write validation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    plan = json.loads((HERE / 'handoff.json').read_text(encoding='utf-8'))
    for item in plan['files']:
        target, candidate = ROOT / item['target'], HERE / item['candidate']
        if not target.resolve().is_relative_to((ROOT / 'Assets/RacingBois/Client').resolve()) or target.is_symlink():
            raise ValueError('Invalid target')
        if sha(candidate) != item['candidateSha256']:
            raise ValueError('Candidate changed: ' + str(candidate))
        if sha(target) not in (item['beforeSha256'], item['candidateSha256']):
            raise ValueError('Live target changed: ' + str(target))
    if args.install:
        for item in plan['files']:
            target, candidate = ROOT / item['target'], HERE / item['candidate']
            if sha(target) == item['candidateSha256']:
                continue
            # Recheck immediately before each scoped write, preserving all unrelated files.
            if sha(target) != item['beforeSha256']:
                raise ValueError('Concurrent target change: ' + str(target))
            temporary = target.with_name(target.name + '.locale-install.tmp')
            with temporary.open('xb') as stream:
                stream.write(candidate.read_bytes()); stream.flush(); os.fsync(stream.fileno())
            try:
                os.replace(temporary, target)
            finally:
                if temporary.exists(): temporary.unlink()
    print(json.dumps({'validatedFiles': len(plan['files']), 'installed': args.install,
                      'nativeValidation': False, 'fullCampaignPlaybackAccepted': False}))

if __name__ == '__main__':
    main()
