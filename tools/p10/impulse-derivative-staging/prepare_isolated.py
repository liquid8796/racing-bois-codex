"""Build a source-only isolated full-suite copy for the staged client fix."""
from pathlib import Path
import datetime as dt,hashlib,importlib.util,json,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;SUPPORT=HERE/'Support';SUPPORT.mkdir(exist_ok=True)
manifest=json.loads((HERE/'manifest.json').read_text());changes=list(manifest['changes'])
def stage(path,text):
    out=SUPPORT/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text,encoding='utf8');original=ROOT/path
    changes.append({'path':path,'before':hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None,'staged':out.relative_to(ROOT).as_posix(),'after':hashlib.sha256(out.read_bytes()).hexdigest()})
project='src/Tests/RacingBois.PredictionImpulse.Tests/'
fixture=project+'Fixtures/first-contact-impulse.json'
stage(fixture,(ROOT/'docs/p10/proxy-transition-staging/first-production-outlier.json').read_text(encoding='utf-8-sig'))
program=(HERE/'Program.cs').read_text(encoding='utf8').replace('docs/p10/proxy-transition-staging/first-production-outlier.json',fixture)
begin=program.index('var manifest=JsonDocument.Parse');end=program.index('File.WriteAllText(output',begin)
program=program[:begin]+'''var sources=Directory.GetFiles("Assets/RacingBois/Client/Application","*.cs")
    .Concat(Directory.GetFiles("src/Tests/RacingBois.PredictionImpulse.Tests","*.*"))
    .Concat(Directory.GetFiles("src/Tests/RacingBois.PredictionImpulse.Tests/Fixtures","*.json"))
    .Append("src/Tests/RacingBois.P05Client.Tests/NetworkHarness.cs").OrderBy(path=>path,StringComparer.Ordinal)
    .Select(path=>new{path=path.Replace('\\\\','/'),sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()}).ToArray();
'''+program[end:]
program=program.replace('productionUnchanged=unchanged,','sources,').replace('Staged client-only metadata-history/derivative guard. No production, server, protocol, physics or running-process mutation.','Actual linked production Application and server/shared assemblies; isolated metadata, history, replay and latency fixtures. No live deployment or renderer acceptance.')
stage(project+'Program.cs',program)
stage(project+'RacingBois.PredictionImpulse.Tests.csproj','''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><Nullable>disable</Nullable></PropertyGroup>
  <ItemGroup><ProjectReference Include="../../Server/RacingBois.Server.Application/RacingBois.Server.Application.csproj" />
    <Compile Include="../../../Assets/RacingBois/Client/Application/*.cs" Link="Application/%(Filename)%(Extension)" />
    <Compile Include="../RacingBois.P05Client.Tests/NetworkHarness.cs" Link="NetworkHarness.cs" />
  </ItemGroup>
</Project>
''')
runner=(ROOT/'tools/p10/run-regression.py').read_text(encoding='utf8')
anchor='("Prediction", False), ("PredictionProjection", False),';assert anchor in runner
stage('tools/p10/run-regression.py',runner.replace(anchor,anchor+' ("PredictionImpulse", False),'))
spec=importlib.util.spec_from_file_location('regression',ROOT/'tools/p10/run-regression.py');regression=importlib.util.module_from_spec(spec);spec.loader.exec_module(regression)
base=regression.source_inventory()
for folder in ['tools/p10/ProtocolSoak','tools/p10/ProtocolSoakNext','tools/p10/correction-audit']:
    for path in (ROOT/folder).glob('*'):
        if path.is_file() and path.suffix in {'.cs','.csproj'}:base[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
for path in ['tools/p10/run-regression.py','tools/p10/run-network-diagnostic.py','docs/reverse-engineering/logic/economy_tables.json']:
    base[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'_local/p10/impulse-staged-tests'/stamp;out.mkdir(parents=True,exist_ok=False)
for path,sha in base.items():
    source=ROOT/path
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:raise RuntimeError('Source drift: '+path)
    destination=out/path;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
for row in changes:
    source=ROOT/row['path'];actual=hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None
    if actual!=row['before']:raise RuntimeError('Production drift: '+row['path'])
    staged=ROOT/row['staged']
    if hashlib.sha256(staged.read_bytes()).hexdigest()!=row['after']:raise RuntimeError('Staged drift')
    destination=out/row['path'];destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(staged,destination)
manifest={'schema':1,'root':str(out),'changes':changes,'productionBase':base,'scope':'Source-only test copy. No runtime/server/protocol/physics source writes.'}
(HERE/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'candidate-snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n');print(out)
