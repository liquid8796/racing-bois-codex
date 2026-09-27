"""Stage tests and read-only diagnostic compatibility; never writes production."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=HERE/'StageSupport';OUT.mkdir(exist_ok=True)
manifest=[]
def save(path,text):
    out=OUT/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text,encoding='utf8')
    actual=ROOT/path
    manifest.append({'path':path,'before':hashlib.sha256(actual.read_bytes()).hexdigest() if actual.exists() else None,'staged':out.relative_to(ROOT).as_posix(),'after':hashlib.sha256(out.read_bytes()).hexdigest()})
def transform(path,pairs):
    text=(ROOT/path).read_text(encoding='utf8')
    for old,new in pairs:
        if old not in text:raise RuntimeError('Missing source anchor '+path+': '+old)
        text=text.replace(old,new)
    save(path,text)
transform('tools/p10/correction-audit/MultiplayerSession.CorrectionAudit.cs',[
 ('p.WalkingSpeedMillimetersPerSecond }; }).Cast<object>().ToArray()', 'p.WalkingSpeedMillimetersPerSecond, PredictionContext=PedestrianCheckpoints.CapturePredictionContext(p) }; }).Cast<object>().ToArray()'),
 ('b.WalkingSpeedMillimetersPerSecond=a.WalkingSpeedMillimetersPerSecond; }','b.WalkingSpeedMillimetersPerSecond=a.WalkingSpeedMillimetersPerSecond; PedestrianCheckpoints.RestorePredictionContext(b,PedestrianCheckpoints.CapturePredictionContext(a)); }')])
transform('tools/p10/correction-audit/CorrectionReplay.cs',[
 ('p.WalkingSpeedMillimetersPerSecond=Int(r,"WalkingSpeedMillimetersPerSecond");', '''p.WalkingSpeedMillimetersPerSecond=Int(r,"WalkingSpeedMillimetersPerSecond");
            if(!r.TryGetProperty("PredictionContext",out var context))throw new InvalidOperationException("Recorded trace predates explicit pedestrian prediction context; use its original source-bound replay, not invented timing.");
            PedestrianCheckpoints.RestorePredictionContext(p,new PedestrianPredictionContext(Int(context,"WaitTicks"),Int(context,"DesiredWalkingSpeed"),Int(context,"MotionRemainder")));''')])
transform('src/Tests/RacingBois.P05Client.Tests/RemoteImmunityRegression.cs',[
 ('new Dictionary<int, long>()), check)', 'new Dictionary<int, long>(), valid.PedestrianContexts, valid.RiderCombatContexts), check)'),
 ('projection.CollisionUntilByRider);','projection.CollisionUntilByRider, projection.PedestrianContexts, projection.RiderCombatContexts);'),
 ('snapshot.CollisionUntilByRider);','snapshot.CollisionUntilByRider, snapshot.PedestrianContexts, snapshot.RiderCombatContexts);'),
 ('row.values.Length == 27','row.values.Length == 31'),
 ('d.CharacterCatalogIndex,(int)Math.Max(0,until-own.Tick) }', 'd.CharacterCatalogIndex,(int)Math.Max(0,until-own.Tick),a.Id!=0?a.Endurance:d.Endurance,a.AttackResolved?1:0,(int)Math.Max(0,a.HitUntilTick-own.Tick),(int)Math.Max(0,a.StealUntilTick-own.Tick) }'),
 ('"Validated server protection did not reach the predictor.");','''"Validated server protection did not reach the predictor.");
                var state = RiderCheckpoints.Capture(proxy,remote.tick).Data;
                check(state.Endurance == own.own.endurance && state.AttackResolved == own.own.attackResolved &&
                    state.HitUntilTick == Math.Max(remote.tick,own.own.hitUntilTick) && state.StealUntilTick == Math.Max(remote.tick,own.own.stealUntilTick),
                    "Real server combat context was not preserved through client projection.");''')])
transform('src/Tests/RacingBois.Multiplayer.Integration.Tests/Program.cs', [('new[] { 3, 4 }','new[] { 3, 4, 5 }')])
transform('src/Tests/RacingBois.P08Content.Tests/Program.cs', [('MultiplayerProtocol.Version==5','MultiplayerProtocol.Version==6'),('Pre-immunity multiplayer compatibility was not fenced','Pre-prediction-context multiplayer compatibility was not fenced')])
transform('tools/p10/run-regression.py', [('("Foundation", False), ("Gameplay", False),','("Foundation", False), ("Gameplay", False), ("Prediction", False), ("PredictionProjection", False),')])
testroot='src/Tests/RacingBois.Prediction.Tests/'
save(testroot+'RacingBois.Prediction.Tests.csproj','''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><Nullable>disable</Nullable><DefineConstants>CANDIDATE</DefineConstants></PropertyGroup>
  <ItemGroup><ProjectReference Include="../../Shared/RacingBois.Gameplay.Definitions/RacingBois.Gameplay.Definitions.csproj" />
    <Compile Include="../../../Packages/com.racingbois.foundation/Runtime/Simulation/**/*.cs" Link="Simulation/%(Filename)%(Extension)" />
  </ItemGroup>
</Project>
''')
program=(HERE/'Program.cs').read_text(encoding='utf8')
start=program.index('var productionBefore=');end=program.index('Directory.CreateDirectory',start)
program=program[:start]+'''var sources=Directory.GetFiles("Packages/com.racingbois.foundation/Runtime/Simulation","*.cs")
    .Concat(Directory.GetFiles("src/Tests/RacingBois.Prediction.Tests","*.*"))
    .Concat(Directory.GetFiles("src/Tests/RacingBois.Prediction.Tests/Fixtures","*.json"))
    .OrderBy(path=>path,StringComparer.Ordinal).Select(path=>new{path=path.Replace('\\\\','/'),sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()}).ToArray();
'''+program[end:]
program=program.replace('productionUnchanged=unchanged,','sources,').replace('"_local/proxy-transition-test.json"','"docs/p10/prediction-regression.json"')
program=program.replace('Offline compiled staging only. Unmodified deployed/soak sources.','Actual production simulation source compiled into an isolated regression executable; no server/Unity mutation.')
behavior=(HERE/'ProxyBehaviorTests.cs').read_text(encoding='utf8')
for name in ['pedestrian-recovery-episode.json','speculative-neighbor-episode.json','maximum-correction-episode.json']:
    old='docs/p09/releases/e/'+name;new=testroot+'Fixtures/'+name
    program=program.replace(old,new);behavior=behavior.replace(old,new)
    save(new,(ROOT/old).read_text(encoding='utf8'))
save(testroot+'Program.cs',program);save(testroot+'ProxyBehaviorTests.cs',behavior)
projectionroot='src/Tests/RacingBois.PredictionProjection.Tests/'
save(projectionroot+'RacingBois.PredictionProjection.Tests.csproj','''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><Nullable>disable</Nullable></PropertyGroup>
  <ItemGroup><ProjectReference Include="../../Shared/RacingBois.Gameplay.Definitions/RacingBois.Gameplay.Definitions.csproj" />
    <Compile Include="../../../Packages/com.racingbois.foundation/Runtime/Simulation/**/*.cs" Link="Simulation/%(Filename)%(Extension)" />
    <Compile Include="../../../Packages/com.racingbois.foundation/Runtime/Protocol/**/*.cs" Link="Protocol/%(Filename)%(Extension)" />
    <Compile Include="../../../Packages/com.racingbois.foundation/Runtime/NetworkMapping/**/*.cs" Link="NetworkMapping/%(Filename)%(Extension)" />
    <Compile Include="../../../Assets/RacingBois/Client/Application/*.cs" Link="Application/%(Filename)%(Extension)" />
  </ItemGroup>
</Project>
''')
projection=(HERE/'IntegrationProgram.cs').read_text(encoding='utf8')
projection=projection.replace('"_local/pedestrian-integration.json"','"docs/p10/prediction-projection-regression.json"')
projection=projection.replace('Isolated staged protocol6/client/foundation sources compiled together; no production write or live network execution. Server encoder is staged for subsequent full integration after authorized supersession.','Actual protocol/client/foundation sources compiled together for value projection, hostile metadata and pose boundary tests; no live network, server or Unity acceptance.')
save(projectionroot+'Program.cs',projection)
(HERE/'support-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print('Staged support files',len(manifest),'without production writes.')
