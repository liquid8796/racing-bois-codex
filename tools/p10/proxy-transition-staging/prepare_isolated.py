"""Make a source-only test snapshot with the staged patch; no live source edits."""
from pathlib import Path
import datetime as dt,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=ROOT/'_local/p10/proxy-transition-staged-tests'/stamp
out.mkdir(parents=True,exist_ok=False)
base=['src','Packages/com.racingbois.foundation/Runtime','Assets/RacingBois/Client/Application','Assets/RacingBois/Client/Adapters','tools/p09/HostPolicyTests','tools/p10/MailboxRaceRepro','tools/p10/ProtocolSoakNext','tools/p10/correction-audit']
sources={}
for folder in base:
    for path in (ROOT/folder).rglob('*'):
        if not path.is_file() or {'bin','obj','__pycache__','staged'}.intersection(path.parts):continue
        if path.suffix not in {'.cs','.csproj','.json','.props','.targets','.config'}:continue
        relative=path.relative_to(ROOT);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        sources[relative.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
for relative in ['global.json','tools/p10/run-regression.py','docs/reverse-engineering/logic/economy_tables.json']:
    path=ROOT/relative;target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    sources[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
manifest=[]
for name in ['integration-manifest.json','support-manifest.json']:manifest+=json.loads((HERE/name).read_text(encoding='utf8'))
for path in (HERE/'StageSimulation').glob('*.cs'):
    relative='Packages/com.racingbois.foundation/Runtime/Simulation/'+path.name;before=ROOT/relative
    manifest.append({'path':relative,'before':hashlib.sha256(before.read_bytes()).hexdigest() if before.exists() else None,'staged':path.relative_to(ROOT).as_posix(),'after':hashlib.sha256(path.read_bytes()).hexdigest()})
for row in manifest:
    original=ROOT/row['path'];current=hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None
    if current!=row['before']:raise RuntimeError('Production drift: '+row['path'])
    staged=ROOT/row['staged']
    if hashlib.sha256(staged.read_bytes()).hexdigest()!=row['after']:raise RuntimeError('Staging drift: '+row['staged'])
    target=out/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(staged,target)
receipt={'schema':1,'scope':'Source-only copy for isolated tests, no live Assets/server/source or running process mutation.','root':str(out),'productionBase':sources,'changes':manifest}
(HERE/'candidate-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
(out/'staged-snapshot.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print(out)
