"""Hash-guarded combined installation. Default validates without writing Assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
    manifest=json.loads((HERE/'handoff.json').read_text(encoding='utf-8'))
    targets=set()
    for row in manifest['files']:
        source=(ROOT/row['candidate']).resolve();target=(ROOT/row['target']).resolve()
        if not source.is_relative_to(ROOT/'tools/p08/media') or not target.is_relative_to(ROOT/'Assets/RacingBois') or target in targets:
            raise ValueError('Invalid or duplicate install path')
        targets.add(target)
        if sha(source)!=row['candidateSha256']:raise ValueError('Reviewed candidate changed: '+row['candidate'])
        if sha(target) not in (row['beforeSha256'],row['candidateSha256']):raise ValueError('Live target changed: '+row['target'])
    if args.install:
        for row in manifest['files']:
            source=ROOT/row['candidate'];target=ROOT/row['target']
            if sha(target)==row['candidateSha256']:continue
            if sha(target)!=row['beforeSha256']:raise ValueError('Concurrent live change: '+row['target'])
            temporary=target.with_name(target.name+'.ui-copy-'+uuid.uuid4().hex+'.tmp')
            try:
                with temporary.open('xb') as stream:
                    stream.write(source.read_bytes());stream.flush();os.fsync(stream.fileno())
                if sha(target)!=row['beforeSha256']:raise ValueError('Concurrent live change before replace: '+row['target'])
                os.replace(temporary,target)
            finally:
                if temporary.exists():temporary.unlink()
    print(json.dumps({'validatedRows':len(targets),'installed':args.install,'nativeAcceptance':False,'fullGameLocalizationAccepted':False}))

if __name__=='__main__':main()
