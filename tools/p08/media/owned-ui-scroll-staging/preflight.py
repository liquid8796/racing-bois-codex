"""Compile the isolated scroll driver against root's settled native assemblies."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
MANAGED=Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed/UnityEngine')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser()
parser.add_argument('--proof',required=True)
parser.add_argument('--union',required=True)
args=parser.parse_args()
files=[HERE/name for name in ['OwnedUiScrollDriver.cs','Driver.csproj','prepare_driver.py','preflight.py']]
files += [ROOT/args.proof,ROOT/args.union,ROOT/'docs/p08/ui-owned-render/20260928-ui-render-06-driver.json',
          HERE.parent/'owned-ui-driver-r5-staging/AttachedUiDriver.cs',HERE.parent/'owned-ui-driver-r5-staging/handoff.json',
          HERE.parent/'native-ui-contract-staging/Fixtures.cs',
          HERE.parent/'owned-ui-render-r2-staging/bin/Debug/netstandard2.1/RacingBois.Tools.OwnedUiRenderR2.dll',
          ROOT/'Library/PackageCache/com.unity.nuget.newtonsoft-json@4dfd81071c64/Runtime/Newtonsoft.Json.dll']
files += [ROOT/'Library/ScriptAssemblies'/name for name in ['RacingBois.Client.Application.dll','RacingBois.Client.Adapters.dll',
          'RacingBois.Client.Presentation.dll','RacingBois.Client.Bootstrap.dll','RacingBois.Protocol.dll','RacingBois.Gameplay.Definitions.dll']]
files += sorted(MANAGED.glob('*.dll'))
previous=json.loads((ROOT/'docs/p08/ui-owned-render/20260928-ui-render-06-driver.json').read_text(encoding='utf-8-sig'))
if not previous['passed']: raise ValueError('Preserved successful run06 prerequisite differs')
before={str(path.resolve()):sha(path) for path in files}
result=subprocess.run(['dotnet','build',str(HERE/'Driver.csproj'),'--nologo','-v:minimal'],cwd=ROOT,capture_output=True,text=True)
after={str(path.resolve()):sha(path) for path in files}
changed=[path for path in before if before[path]!=after[path]]
dll=HERE/'bin/Debug/netstandard2.1/RacingBois.Tools.OwnedUiScrollDriver.dll'
report=dict(schema=1,passed=result.returncode==0 and not changed,compilation=result.stdout+result.stderr,
            inputHashesBefore=before,inputHashesAfter=after,changedInputs=changed,driverSha256=sha(dll) if dll.exists() else None,
            nativeExecuted=False,scope='Managed compilation and stable inputs only. Actual viewport-contained focus, scroll offsets and 48-image evidence require root native execution.')
(HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=report['passed'],changedInputs=changed,nativeExecuted=False)))
raise SystemExit(0 if report['passed'] else 1)
