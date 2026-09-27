"""Create immutable protocol6 backend/ARM tests and hashed QA fixtures. No SSH or activation."""
from pathlib import Path,PurePosixPath
import datetime as dt,hashlib,importlib.util,json,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
RELEASE='p09-20260927-f';PREVIOUS='p09-20260927-e'
OUT=ROOT/'Build/OciStaging'/RELEASE;REPORT=ROOT/'docs/p09/releases/f'
spec=importlib.util.spec_from_file_location('base_package',ROOT/'tools/p09/package.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def test_sources():
    indexed={row['path']:row['sha256'] for row in base.sources(include_tests=True)['files']}
    for p in (ROOT/'Assets/RacingBois/Client/Application').glob('*.cs'):indexed[p.relative_to(ROOT).as_posix()]=digest(p)
    rows=[{'path':path,'sha256':sha} for path,sha in sorted(indexed.items())]
    return {'sha256':hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),'files':rows}
def differences(old,new):
    a={r['path']:r['sha256'] for r in old};b={r['path']:r['sha256'] for r in new}
    return [{'path':p,'before':a.get(p),'after':b.get(p)} for p in sorted(a.keys()|b.keys()) if a.get(p)!=b.get(p)]
def archive(folder,path):
    seen={}
    with tarfile.open(path,'w:gz') as tar:
        for item in sorted(folder.rglob('*')):
            relative=item.relative_to(folder).as_posix()
            if item.is_dir():tar.add(item,arcname=relative,recursive=False);continue
            sha=digest(item)
            if sha in seen:
                member=tar.gettarinfo(item,arcname=relative);member.type=tarfile.LNKTYPE;member.linkname=seen[sha];member.size=0;tar.addfile(member)
            else:seen[sha]=relative;tar.add(item,arcname=relative,recursive=False)
    with tarfile.open(path) as tar:
        for member in tar.getmembers():
            for name in [member.name]+([member.linkname] if member.islnk() else []):
                p=PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:raise RuntimeError('Unsafe archive path')
            if member.issym():raise RuntimeError('Unexpected symbolic link')
OUT.mkdir(parents=True,exist_ok=False);REPORT.mkdir(parents=True,exist_ok=True)
before=base.sources();tests_before=test_sources()
previous=json.loads((ROOT/'Build/OciStaging'/PREVIOUS/'release.json').read_text(encoding='utf8'))
projects={'server':'src/Server/RacingBois.Server.Host','tests/persistence':'src/Tests/RacingBois.Persistence.Tests',
          'tests/multiplayer':'src/Tests/RacingBois.Multiplayer.Integration.Tests','tests/gameplay':'src/Tests/RacingBois.Gameplay.Tests',
          'tests/prediction':'src/Tests/RacingBois.Prediction.Tests','tests/prediction-projection':'src/Tests/RacingBois.PredictionProjection.Tests',
          'tests/p05-client':'src/Tests/RacingBois.P05Client.Tests'}
for target,project in projects.items():
    print('PUBLISH '+target,flush=True)
    with (REPORT/('publish-'+target.replace('/','-')+'.log')).open('wb') as log:
        result=subprocess.run(['dotnet','publish',str(ROOT/project),'-c','Release','-r','linux-arm64','--self-contained','true','-o',str(OUT/target),'--nologo','-v','quiet'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    if result.returncode:raise RuntimeError('Publish failed: '+target)
if before!=base.sources() or tests_before!=test_sources():raise RuntimeError('Source changed during publish; do not deploy.')
manifest={'schemaVersion':1,'releaseId':RELEASE,'generatedUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'Protocol6 backend-only candidate; no activation, ARM execution or P08/desktop visual acceptance.',
          'runtime':'linux-arm64','protocolVersion':6,'source':before,'testSource':tests_before,
          'files':[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(OUT.rglob('*')) if p.is_file()]}
write(OUT/'release.json',manifest)
tarpath=OUT.with_suffix('.tar.gz');archive(OUT,tarpath)
fixtures=OUT.parent/(RELEASE+'-arm-fixtures.tar.gz')
with tarfile.open(fixtures,'w:gz') as tar:
    for row in tests_before['files']:
        p=ROOT/row['path']
        if digest(p)!=row['sha256']:raise RuntimeError('Source fixture drift: '+row['path'])
        tar.add(p,arcname=row['path'],recursive=False)
fixture_receipt={'releaseId':RELEASE,'archive':str(fixtures),'sha256':digest(fixtures),'bytes':fixtures.stat().st_size,'testSourceSha256':tests_before['sha256'],'files':tests_before['files']}
write(REPORT/'arm-fixtures-package.json',fixture_receipt)
delta={'previousRelease':PREVIOUS,'releaseId':RELEASE,'sourceSha256':before['sha256'],'sourceChanged':differences(previous['source']['files'],manifest['source']['files']),
       'testSourceChanged':differences(previous['testSource']['files'],manifest['testSource']['files']),
       'packagedFilesChanged':differences(previous['files'],manifest['files']),
       'previousClientSourceInventoryMissing':True,
       'testSourceNote':'e did not inventory Client.Application in its package. Newly listed App paths are added coverage, not necessarily edits from e; the separately reviewed30-file patch records actual changed sources.'}
write(REPORT/'source-delta.json',delta)
receipt={'releaseId':RELEASE,'sourceSha256':before['sha256'],'testSourceSha256':tests_before['sha256'],'archive':str(tarpath),'archiveSha256':digest(tarpath),'archiveBytes':tarpath.stat().st_size,
         'manifestSha256':digest(OUT/'release.json'),'packagedFiles':len(manifest['files']),'sourceChangedFiles':len(delta['sourceChanged']),
         'armFixturesArchive':str(fixtures),'armFixturesSha256':digest(fixtures),'scope':'Immutable local package only; not uploaded, activated or executed on ARM.'}
write(REPORT/'package.json',receipt);write(ROOT/'docs/p09'/f'{RELEASE}-package.json',receipt);print(json.dumps(receipt,indent=2),flush=True)
