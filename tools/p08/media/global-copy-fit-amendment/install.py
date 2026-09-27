"""Install only the reviewed one-cell generated-module amendment; preserve script metadata."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
plan=json.loads((HERE/'handoff.json').read_text(encoding='utf-8'));row=plan['files'][0]
target=ROOT/row['target'];candidate=ROOT/row['candidate'];meta=target.with_suffix('.cs.meta')
if row['target']!='Assets/RacingBois/Client/Application/UiText.Career.Generated.cs' or len(plan['files'])!=1:raise ValueError('Unexpected target')
if sha(candidate)!=row['candidateSha256'] or sha(meta)!=row['metaSha256'] or sha(target) not in (row['beforeSha256'],row['candidateSha256']):raise ValueError('Reviewed source/target/meta identity changed')
if args.install and sha(target)!=row['candidateSha256']:
    temporary=target.with_name(target.name+'.pristine-'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:stream.write(candidate.read_bytes());stream.flush();os.fsync(stream.fileno())
        if sha(target)!=row['beforeSha256']:raise ValueError('Concurrent target change')
        os.replace(temporary,target)
    finally:
        if temporary.exists():temporary.unlink()
print(json.dumps({'validatedFiles':1,'installed':args.install,'metadataUnchanged':True,'nativeValidation':False}))
