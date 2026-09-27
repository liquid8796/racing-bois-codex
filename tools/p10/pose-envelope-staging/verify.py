"""Bind isolated validation/Unity API compilation to exact staged and frozen inputs."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'docs/p10/pose-envelope-staging';OUT.mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def stage_files():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and
            not any(part in {'bin','obj','__pycache__'} for part in p.relative_to(HERE).parts) and p.suffix in {'.cs','.py','.csproj','.json','.diff'}}
baseline=json.loads((HERE/'production-before.json').read_text());manifest=json.loads((HERE/'candidate-manifest.json').read_text())
for row in manifest['files']:
    assert sha(ROOT/row['candidate'])==row['candidateSha256']
    assert (sha(ROOT/row['target']) if (ROOT/row['target']).exists() else None)==row['beforeSha256']
before=stage_files();records=[]
commands=[('replay-and-envelope',['dotnet','run','--project',str(HERE/'EnvelopeTests.csproj'),'-c','Release','--',str(OUT/'verified-validation.json')]),
          ('unity-client-compile',['dotnet','build',str(HERE/'UnityCompile.csproj'),'-c','Release','-v','minimal','--nologo'])]
for name,command in commands:
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=90)
    log=OUT/(name+'.log');log.write_text(result.stdout+result.stderr,encoding='utf-8')
    records.append({'name':name,'exitCode':result.returncode,'log':log.relative_to(ROOT).as_posix(),'logSha256':sha(log)})
data=json.loads((OUT/'verified-validation.json').read_text());details=data['details']
frozen_changes=[p for p,digest in baseline['sources'].items() if sha(ROOT/p)!=digest]
report={'schema':1,'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'passed':all(row['exitCode']==0 for row in records) and data['passed'] and not frozen_changes and before==stage_files(),
        'tests':data['tests'],'realEpisodes':data['episodes'],'controlledScenarios':len(details),
        'maximumRawCorrectionMeters':max(d['rawCorrectionMeters'] for d in details),
        'maximumTemporaryVisualOffsetMeters':max(d['maxOffset'] for d in details),
        'maximumFirstRiderStepMeters':max(d['firstRiderStep'] for d in details),
        'maximumFirstBikeStepMeters':max(d['firstBikeStep'] for d in details),
        'maximumAdditionalCorrectionSpeedMps':max(d['maxCorrectionSpeed'] for d in details),
        'maximumControlledSettlingSeconds':max(d['settledSeconds'] for d in details),
        'minimumControlledCameraRiderDepthMeters':min(d['minCameraDepth'] for d in details),
        'frozenSourceCount':len(baseline['sources']),'frozenSourceChanges':frozen_changes,'stagedSourcesStable':before==stage_files(),
        'stagedFiles':before,'commands':records,'validationSha256':sha(OUT/'verified-validation.json'),
        'productionApplied':False,'nativeUnityRendered':False,'visualAccepted':False,
        'scope':'Actual39 source-bound retained episode pairs,78 exact before/after prediction replays, controlled continuations and pure policy controls. Unity API compilation is not native visual/runtime acceptance.'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key not in {'stagedFiles','commands'}},indent=2))
raise SystemExit(0 if report['passed'] else 1)
