"""Validate or atomically install only the reviewed Multiplayer generated module."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser()
parser.add_argument('--install', action='store_true')
args=parser.parse_args()
plan=json.loads((HERE/'handoff.json').read_text(encoding='utf-8'))
if len(plan['files'])!=1: raise ValueError('One reviewed target required')
row=plan['files'][0]
if row['target']!='Assets/RacingBois/Client/Application/UiText.Multiplayer.Generated.cs': raise ValueError('Unexpected target')
candidate=ROOT/row['candidate'];target=ROOT/row['target'];meta=target.with_suffix('.cs.meta')
for parent in [target,*target.parents,candidate,*candidate.parents]:
    if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)(): raise ValueError('Linked path rejected')
for field in ('activePointer','amendment','union'):
    if sha(ROOT/plan[field]['path'])!=plan[field]['sha256']: raise ValueError('Reviewed chain changed: '+field)
for preserved in plan['preservedFiles']:
    if sha(ROOT/preserved['path'])!=preserved['sha256']: raise ValueError('Untouched provider changed: '+preserved['path'])
subprocess.run([sys.executable,str(HERE.parent/'global-copy-effective/generate.py'),'--check'],cwd=ROOT,check=True)
if sha(candidate)!=row['candidateSha256'] or sha(meta)!=row['metaSha256'] or sha(target) not in (row['beforeSha256'],row['candidateSha256']):
    raise ValueError('Reviewed source/target/meta identity changed')
if args.install and sha(target)!=row['candidateSha256']:
    temporary=target.with_name(target.name+'.copy-fit-'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(candidate.read_bytes());stream.flush();os.fsync(stream.fileno())
        if sha(target)!=row['beforeSha256'] or sha(meta)!=row['metaSha256']: raise ValueError('Concurrent target/meta change')
        os.replace(temporary,target)
    finally:
        if temporary.exists(): temporary.unlink()
if args.install and sha(target)!=row['candidateSha256']: raise ValueError('Installed bytes differ')
if sha(meta)!=row['metaSha256']: raise ValueError('Metadata changed')
for preserved in plan['preservedFiles']:
    if sha(ROOT/preserved['path'])!=preserved['sha256']: raise ValueError('Untouched provider changed: '+preserved['path'])
print(json.dumps(dict(validatedFiles=1,installed=args.install,metadataUnchanged=True,nativeValidation=False)))
