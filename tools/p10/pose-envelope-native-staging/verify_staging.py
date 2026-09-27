"""Read-only frozen-source checks plus isolated compiler/contract validation."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'docs/p10/pose-envelope-native-staging'
OUT.mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def staged():return {p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and not any(part in {'bin','obj','__pycache__'} for part in p.relative_to(HERE).parts) and p.suffix in {'.cs','.py','.csproj','.asmdef','.json'}}
before=staged();frozen=json.loads((ROOT/'tools/p10/pose-envelope-staging/production-before.json').read_text());prepared=json.loads((HERE/'prepared-inputs.json').read_text())
checks=[]
for row in prepared['namespaceCopies']:
    original=(ROOT/row['source']).read_bytes();changed=(ROOT/row['path']).read_bytes()
    ok=sha(ROOT/row['source'])==row['sourceSha256'] and original.count(row['from'].encode())==1 and changed==original.replace(row['from'].encode(),row['to'].encode()) and sha(ROOT/row['path'])==row['sha256']
    checks.append({'source':row['source'],'path':row['path'],'namespaceOnly':ok})
assert all(r['namespaceOnly'] for r in checks)
assert sha(ROOT/prepared['frozenCandidateManifest']['path'])==prepared['frozenCandidateManifest']['sha256']
commands=[('unity-api-compile',['dotnet','build',str(HERE/'EditorCompile.csproj'),'-v','minimal','--nologo']),
          ('contracts',['dotnet','run','--project',str(HERE/'Tests/Tests.csproj'),'-c','Release','--',str(OUT/'config-scope-tests.json')]),
          ('independent-png-verifier',[sys.executable,'-m','unittest','discover','-s',str(HERE),'-p','test_verifier.py','-v']),
          ('install-dry-run',[sys.executable,str(HERE/'install.py')])]
results=[]
for name,command in commands:
    result=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90)
    log=OUT/(name+'.log');log.write_text(result.stdout,encoding='utf-8');results.append({'name':name,'exitCode':result.returncode,'log':log.relative_to(ROOT).as_posix(),'sha256':sha(log)})
changed=[p for p,digest in frozen['sources'].items() if sha(ROOT/p)!=digest]
report={'schema':1,'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'passed':all(r['exitCode']==0 for r in results) and not changed and before==staged(),
        'namespaceOnlyCopies':checks,'stagedInputs':before,'stagedStable':before==staged(),'frozenSourceCount':len(frozen['sources']),'frozenSourceChanges':changed,'results':results,
        'requiredSelectedPrefabs':{p:(ROOT/p).is_file() for p in ['Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Apex_r4.prefab','Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Ash_V6.prefab']},
        'installedByThisTask':False,'nativeBuilt':False,'nativeRendered':False,'visualAccepted':False,
        'scope':'Staging compile/configuration/journal/numerical/PNG-codec controls only. Root still owns installation, actual Editor state restoration, build, native run and image review.'}
(OUT/'staging-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in {'stagedInputs','results'}},indent=2))
raise SystemExit(0 if report['passed'] else 1)
