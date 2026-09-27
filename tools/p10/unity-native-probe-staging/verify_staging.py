"""Compile only against installed Unity reference assemblies; no live Unity or Assets writes."""
from pathlib import Path
import datetime as dt,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
output=ROOT/'docs/p10/unity-native-probe-staging'/stamp;output.mkdir(parents=True,exist_ok=False)
def inventory():
    paths=[]
    for folder in [HERE,ROOT/'Assets/RacingBois/Client/Application',ROOT/'Packages/com.racingbois.foundation/Runtime']:
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in {'.cs','.csproj','.asmdef','.py'} and not {'obj','bin','__pycache__'}.intersection(path.parts):paths.append(path)
    for name in ['BrowserSocketTransport.cs','UnityWireCodec.cs','UnityMultiplayerStorage.cs']:paths.append(ROOT/'Assets/RacingBois/Client/Adapters'/name)
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
before=inventory();results=[]
for label,command in [('managed-unity-compile',['dotnet','build',str(HERE/'EditorCompile.csproj'),'-v:q']),
                      ('configuration',['dotnet','run','--project',str(HERE/'ConfigTests/ConfigTests.csproj'),'--',str(output/'config-tests.json')]),
                      ('build-lifecycle',['dotnet','run','--project',str(HERE/'LifecycleTests/LifecycleTests.csproj'),'--',str(output/'lifecycle-tests.json')]),
                      ('launcher-postchecks',[sys.executable,str(HERE/'test_runner.py'),str(output/'launcher-tests.json')])]:
    run=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,check=False)
    (output/(label+'.log')).write_bytes(run.stdout);results.append({'name':label,'exitCode':run.returncode})
after=inventory();changed=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))
test_reports={name:json.loads((output/name).read_text(encoding='utf-8')) for name in ['config-tests.json','lifecycle-tests.json','launcher-tests.json']}
passed=all(r['exitCode']==0 for r in results) and not changed and all(value.get('passed') is True for value in test_reports.values())
receipt={'schema':1,'status':'PASS' if passed else 'FAIL','sourceStable':not changed,'changedSources':changed,'sources':before,'results':results,
         'testReceipts':{name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in test_reports},
         'scope':'Managed compile against installed Unity assemblies plus pure option validation. No live Editor invocation, Assets installation, Unity build, Mono native execution, WSS/TLS evidence or game acceptance.'}
(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':receipt['status'],'receipt':str(output/'receipt.json')}));sys.exit(0 if passed else 1)
