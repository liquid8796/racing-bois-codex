"""Bind permanent turnover regressions and make a source-only test copy."""
from pathlib import Path
import datetime as dt,hashlib,importlib.util,json,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;SUPPORT=HERE/'Support';SUPPORT.mkdir(exist_ok=True)
changes=json.loads((HERE/'manifest.json').read_text())['changes']
def stage(path,text):
    target=SUPPORT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf8');original=ROOT/path
    changes.append({'path':path,'before':hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None,'staged':target.relative_to(ROOT).as_posix(),'after':hashlib.sha256(target.read_bytes()).hexdigest()})
project='src/Tests/RacingBois.RetiredInput.Tests/'
program=(HERE/'Program.cs').read_text(encoding='utf8')
program=program.replace('"_local/retired-input-tests.json"','"docs/p10/retired-input-regression.json"')
program=program.replace('File.WriteAllText(output,JsonSerializer.Serialize(new{schema=1,', '''var sources=Directory.GetFiles("Assets/RacingBois/Client/Application","*.cs")
    .Concat(Directory.GetFiles("src/Tests/RacingBois.RetiredInput.Tests","*.*"))
    .Append("src/Tests/RacingBois.P05Client.Tests/NetworkHarness.cs")
    .Append("src/Server/RacingBois.Server.Application/Multiplayer/MultiplayerService.cs")
    .OrderBy(path=>path,StringComparer.Ordinal).Select(path=>new{path=path.Replace('\\\\','/'),sha256=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()}).ToArray();
File.WriteAllText(output,JsonSerializer.Serialize(new{schema=1,sources,''')
program=program.replace('Isolated staged client plus actual server application and ordered latency fixture; raw errors remain observed. No live source/wire/server-policy changes.','Actual linked client/server application with isolated ordered latency and scope fixtures; raw rejected inputs and reliable ordering remain observed. No Unity/native/live-deployment acceptance.')
stage(project+'Program.cs',program)
stage(project+'RacingBois.RetiredInput.Tests.csproj','''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><Nullable>disable</Nullable><DefineConstants>CANDIDATE</DefineConstants></PropertyGroup>
  <ItemGroup><ProjectReference Include="../../Server/RacingBois.Server.Application/RacingBois.Server.Application.csproj" />
    <Compile Include="../../../Assets/RacingBois/Client/Application/*.cs" Link="Application/%(Filename)%(Extension)" />
    <Compile Include="../RacingBois.P05Client.Tests/NetworkHarness.cs" Link="NetworkHarness.cs" />
  </ItemGroup>
</Project>
''')
runner=(ROOT/'tools/p10/run-regression.py').read_text(encoding='utf8');anchor='("PredictionImpulse", False),';assert anchor in runner
stage('tools/p10/run-regression.py',runner.replace(anchor,anchor+' ("RetiredInput", False),'))
spec=importlib.util.spec_from_file_location('regression',ROOT/'tools/p10/run-regression.py');regression=importlib.util.module_from_spec(spec);spec.loader.exec_module(regression)
base=regression.source_inventory()
for path in ['tools/p10/run-regression.py','docs/reverse-engineering/logic/economy_tables.json']:base[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'_local/p10/retired-input-staged-tests'/stamp;out.mkdir(parents=True,exist_ok=False)
for path,sha in base.items():
    source=ROOT/path
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:raise RuntimeError('Production source drift')
    target=out/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for row in changes:
    original=ROOT/row['path'];actual=hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None
    if actual!=row['before']:raise RuntimeError('Candidate predecessor drift: '+row['path'])
    source=ROOT/row['staged']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=row['after']:raise RuntimeError('Staged drift')
    target=out/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
manifest={'schema':1,'root':str(out),'changes':changes,'productionBase':base,'scope':'Only client contextual handling/permanent tests staged. No production/server/wire/policy mutation.'}
(HERE/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'candidate-snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n');print(out)
