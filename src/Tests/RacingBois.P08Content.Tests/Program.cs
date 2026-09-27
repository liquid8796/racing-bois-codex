using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Simulation;
using RacingBois.Server.Application.Career;
using RacingBois.Server.Application.Multiplayer;
using RacingBois.Server.Infrastructure;

Console.WriteLine("Canonical content identity " + ContentFingerprint.Compute());
var tests = new List<object>(); var tracks = new List<object>(); var bikes = new List<object>(); int failures = 0;
void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
void Test(string name, Action run) { try { run(); tests.Add(new { name, passed = true }); Console.WriteLine("PASS " + name); } catch(Exception e) { failures++; tests.Add(new { name, passed = false, error = e.Message }); Console.WriteLine("FAIL " + name + ": " + e.Message); } }
void Reject(Action run) { bool rejected=false; try { run(); } catch(ArgumentException) { rejected=true; } Check(rejected,"Invalid data accepted"); }
Test("all_25_courses_geometry_continuity_grade_bounds_and_no_nonlocal_intersection", () => {
    var signatures = new HashSet<string>();
    for(int course=0;course<5;course++) for(int level=0;level<5;level++) {
        var track=TrackDefinition.ForCourse(course,level); var samples=new List<TrackSample>(); var previous=track.Sample(0);
        var signature=new System.Text.StringBuilder(); double minimumNonlocal=double.MaxValue;
        for(long distance=1000;distance<=track.LengthMillimeters;distance+=1000) {
            var s=track.Sample(distance); double chord=Math.Sqrt(Math.Pow(s.CenterX-previous.CenterX,2)+Math.Pow(s.CenterZ-previous.CenterZ,2));
            Check(chord>.995 && chord<1.005,"Discontinuous ribbon "+course+"/"+level+" at "+distance);
            Check(Math.Abs(s.CenterY*1000-track.HeightMillimetersAt(distance))<2,"Height differs from authority");
            Check(s.ForwardZ > .05f, "Route reverses longitudinal direction");
            Check(Math.Abs(s.GradePermille)<=100 && Math.Abs(s.CurvatureMicroRadiansPerMeter)<=10000,"Authored bounds exceeded");
            if(distance%20000==0) { samples.Add(s); signature.Append(s.CurvatureMicroRadiansPerMeter).Append('/').Append(s.GradePermille).Append(';'); }
            previous=s;
        }
        // Every non-neighbor chord corridor stays wider than road+shoulder on both sides.
        for(int i=0;i<samples.Count;i++) for(int j=i+3;j<samples.Count;j++) {
            double gap=Math.Sqrt(Math.Pow(samples[i].CenterX-samples[j].CenterX,2)+Math.Pow(samples[i].CenterZ-samples[j].CenterZ,2));
            minimumNonlocal=Math.Min(minimumNonlocal,gap); Check(gap>20,"Nonlocal route overlap");
        }
        signature.Append(track.LengthMillimeters); Check(signatures.Add(signature.ToString()),"Duplicate course geometry");
        tracks.Add(new {course,level,lengthMillimeters=track.LengthMillimeters,minimumNonlocalDistanceMeters=minimumNonlocal});
    }
    Reject(()=>TrackDefinition.ForCourse(-1,0)); Reject(()=>TrackDefinition.ForCourse(0,5));
});
Test("fifteen_bikes_have_measurably_distinct_acceleration_braking_and_valid_identity",()=> {
    var signatures=new HashSet<string>(); var speeds=new HashSet<int>();
    for(int i=0;i<BikeCatalog.Count;i++) {
        var b=BikeCatalog.GetAt(i); var h=b.Handling;
        Check(signatures.Add($"{h.MaximumSpeedMillimetersPerSecond}/{h.EnginePermille}/{h.BrakeDeceleration}/{h.SteeringResponse}/{h.CorneringPermille}/{h.OffroadEnginePermille}"),"Duplicate handling");
        var world=RaceSimulation.CreateDefault(8,0); var p=RaceSimulation.AddPlayer(world,1); p.BikeCatalogIndex=i;
        RaceSimulation.FindRider(world,GameplayRules.PoliceId).Mode=RiderMode.Wrecked;
        for(int tick=0;tick<180;tick++) { RaceSimulation.SetInput(world,1,new RaceInput(1000,0,0)); RaceSimulation.Step(world); }
        int accelerated=p.SpeedMillimetersPerSecond; Check(speeds.Add(accelerated),"Indistinguishable measured 3-second acceleration");
        int stoppingTicks=0; while(p.SpeedMillimetersPerSecond>0 && stoppingTicks<240) { RaceSimulation.SetInput(world,1,new RaceInput(0,1000,0)); RaceSimulation.Step(world); stoppingTicks++; }
        Check(p.SpeedMillimetersPerSecond==0,"Brake failed"); bikes.Add(new {index=i,b.Id,maximumSpeed=h.MaximumSpeedMillimetersPerSecond,speedAfter3Seconds=accelerated,stoppingTicks});
    }
});
Test("all_375_route_level_bike_combinations_share_exact_authority_prediction_locomotion",()=> {
    for(int c=0;c<5;c++) for(int l=0;l<5;l++) for(int b=0;b<15;b++) {
        var world=RaceSimulation.CreateDefault(1996,0,l,c); var p=RaceSimulation.AddPlayer(world,1);
        RaceSimulation.FindRider(world,GameplayRules.PoliceId).Mode=RiderMode.Wrecked;
        p.BikeCatalogIndex=b; p.CharacterCatalogIndex=b%8; p.DistanceMillimeters=p.BikeDistanceMillimeters=350000;
        var predictor=new RiderPredictor(l,c); predictor.Restore(RiderCheckpoints.Capture(p,0));
        for(int t=0;t<120;t++) {
            var input=new RaceInput(800,t>90?300:0,t<45?150:-100);
            RaceSimulation.SetInput(world,1,input); RaceSimulation.Step(world); var predicted=predictor.Advance(world.Tick,input).Data;
            Check(predicted.DistanceMillimeters==p.DistanceMillimeters && predicted.LateralMillimeters==p.LateralMillimeters && predicted.SpeedMillimetersPerSecond==p.SpeedMillimetersPerSecond && predicted.HeightMillimeters==p.HeightMillimeters && predicted.LeanMillidegrees==p.LeanMillidegrees && predicted.Mode==p.Mode,"Prediction divergence "+c+"/"+l+"/"+b+" tick "+t);
            Check(predicted.BikeCatalogIndex==b && predicted.CharacterCatalogIndex==b%8,"Checkpoint content identity lost");
        }
        var dto=CheckpointMapper.CaptureDto(p,world.Tick); var copy=CheckpointMapper.ToCheckpoint(dto).Data;
        Check(copy.BikeCatalogIndex==b && copy.CharacterCatalogIndex==b%8,"Wire checkpoint lost equipment");
        var rm=RaceStateProjection.World(world,0,Array.Empty<RaceEventReadModel>());
        Check(rm.CourseIndex==c && ReferenceEquals(rm.Track,world.Track) && rm.Riders[0].BikeCatalogIndex==b,"Readmodel differs from authority");
    }
});
var completions = new List<object>();
Test("all_25_routes_finish_under_controlled_authoritative_inputs",()=> {
    for(int c=0;c<5;c++) for(int l=0;l<5;l++) {
        var world=RaceSimulation.CreateDefault(1996,0,l,c);var rider=RaceSimulation.AddPlayer(world,1);
        RaceSimulation.FindRider(world,GameplayRules.PoliceId).Mode=RiderMode.Wrecked;
        // Geometry/drivability isolation: normal traffic/pedestrians remain, police and competitor pressure are separately tested.
        for(int t=0;t<12000 && !GameplayRules.IsTerminal(rider.Mode);t++) {
            int curve=world.Track.CurvatureAt(rider.DistanceMillimeters+rider.SpeedMillimetersPerSecond/8);
            int drift=(int)((long)rider.SpeedMillimetersPerSecond*curve/100000);
            int steer=Math.Clamp((-rider.LateralMillimeters*2+drift)*1000/(1200+rider.SpeedMillimetersPerSecond/6),-1000,1000);
            RaceSimulation.SetInput(world,1,new RaceInput(1000,0,steer));RaceSimulation.Step(world);
        }
        Check(rider.Mode==RiderMode.Finished && rider.Qualified,"Course cannot complete: "+c+"/"+l+" "+rider.Mode);
        completions.Add(new {course=c,level=l,ticks=rider.FinishTick,seconds=rider.FinishTick/60.0,rider.BikeCondition,rider.Health});
    }
});
Test("unknown_snapshot_equipment_and_route_are_rejected",()=> {
    var world=RaceSimulation.CreateDefault(1,0); var p=RaceSimulation.AddPlayer(world,1); var dto=CheckpointMapper.CaptureDto(p,0);
    dto.rider.bikeCatalogIndex=15; Reject(()=>CheckpointMapper.Validate(dto)); dto.rider.bikeCatalogIndex=0; dto.rider.characterCatalogIndex=-1; Reject(()=>CheckpointMapper.Validate(dto));
    Check(MultiplayerProtocol.Version==6 && RaceProtocol.Version==3 && GameplayRules.Version==3 && GameplayRules.ContentHash.StartsWith("p08-") && ContentFingerprint.Compute() == GameplayRules.ContentHash,"Pre-prediction-context multiplayer compatibility was not fenced");
});
Test("streaming_manifest_rejects_version_url_digest_size_and_identity_corruption",()=> {
    var origin=new Uri("https://racing.example/Content/");
    P08ContentManifest Valid() {
        var entries=new List<P08BundleEntry>{new P08BundleEntry{id="actors",kind="actors",url="actors.bundle",asset="assets/actors.asset",sha256=new string('a',64),bytes=100}};
        for(int c=0;c<5;c++) { entries.Add(new P08BundleEntry{id="route-"+c,kind="route",courseIndex=c,url="route-"+c+".bundle",asset="assets/route"+c+".asset",sha256=new string('b',64),bytes=200});entries.Add(new P08BundleEntry{id="music-"+c,kind="music",url="audio/music-"+c+"."+new string('c',64)+".ogg",asset="",sha256=new string('c',64),bytes=300}); }
        return new P08ContentManifest{schema=1,contentHash=GameplayRules.ContentHash,actorsId="actors",bundles=entries.ToArray()};
    }
    Check(ContentManifestRules.Validate(Valid(),GameplayRules.ContentHash,origin).Count==11,"Valid bundle/music catalog rejected");
    var mutations=new Action<P08ContentManifest>[] {
        m=>m.contentHash="p07",m=>m.bundles[0].sha256="bad",m=>m.bundles[0].bytes=ContentManifestRules.MaximumBundleBytes+1,
        m=>m.bundles[1].id="actors",m=>m.bundles[1].courseIndex=4,m=>m.bundles[0].asset="../escape",m=>m.bundles[2].url="music.ogg"
    };
    foreach(var mutate in mutations){var m=Valid();mutate(m);bool rejected=false;try{ContentManifestRules.Validate(m,GameplayRules.ContentHash,origin);}catch(InvalidDataException){rejected=true;}Check(rejected,"Corrupt manifest accepted");}
    foreach(string url in new[]{"https://other.example/payload.bundle","//other.example/a","../secret","%2e%2e/secret","a\\b.bundle","a.bundle?token=1","/Content/a.bundle"}) {
        bool rejected=false;try{ContentManifestRules.BundleUri(origin,url);}catch(InvalidDataException){rejected=true;}Check(rejected,"Escaping bundle URL accepted");
    }
});
Test("p07_database_additive_cosmetic_migration_preserves_money_receipts_and_grants",()=> {
    string folder=Path.GetFullPath(Path.Combine("_local","p08-content-tests",Guid.NewGuid().ToString("N"))); Directory.CreateDirectory(folder);
    string token,id,transaction=Guid.NewGuid().ToString("N"),grantId; int credits; string ledger;
    using(var store=new RealmStore(new SqliteRealmStateStore(folder))) {
        var issued=store.CreateProfile("Migration fixture"); token=issued.Token;id=issued.Profile.Id; var api=new CareerService(store);
        Check(api.Execute(token,new CareerRequest {operation="trade",bikeId="rb-ember",transactionId=transaction}).ok,"Fixture trade failed");
        grantId=store.BeginMatch(new[]{id});store.Commit(grantId,new[]{new RealmGrant {ProfileId=id,BikeId="rb-ember",BikeCondition=87,LevelIndex=0,CourseIndex=0,Outcome=(int)MultiplayerOutcome.Finished,Rank=1,Reward=1000,Qualified=true}});
        credits=store.Credits(id);ledger=JsonSerializer.Serialize(store.GetProfile(id).Career.Ledger);
    }
    // Recreate an actual P07 serialized row: new cosmetic property absent; existing SQL projections untouched.
    using(var db=new SqliteConnection($"Data Source={Path.Combine(folder,"realm.sqlite3")};Pooling=False")) {db.Open();using var read=db.CreateCommand();read.CommandText="SELECT state_json FROM realm";var node=JsonNode.Parse((string)read.ExecuteScalar());foreach(var profile in node["Profiles"].AsArray())profile["Career"].AsObject().Remove("SelectedCharacterId");using var write=db.CreateCommand();write.CommandText="UPDATE realm SET state_json=$json";write.Parameters.AddWithValue("$json",node.ToJsonString());write.ExecuteNonQuery();}
    using(var store=new RealmStore(new SqliteRealmStateStore(folder))) {
        var api=new CareerService(store);Check(store.GetProfile(id).Career.SelectedCharacterId==CharacterCatalog.DefaultId,"P07 cosmetic migration failed");
        Check(store.Credits(id)==credits && JsonSerializer.Serialize(store.GetProfile(id).Career.Ledger)==ledger,"Migration changed wallet");
        Check(api.Execute(token,new CareerRequest {operation="trade",bikeId="rb-ember",transactionId=transaction}).ok,"Old receipt fingerprint invalidated");
        store.Commit(grantId,Array.Empty<RealmGrant>());Check(store.Credits(id)==credits,"Old match grant applied again");
        string command=Guid.NewGuid().ToString("N");var request=new CareerRequest {operation="character",characterId="rb-kai",transactionId=command};
        Check(api.Execute(token,request).profile.selectedCharacterId=="rb-kai" && api.Execute(token,request).ok,"Cosmetic command not idempotent");
        request.characterId="rb-ash";Check(api.Execute(token,request).code=="transaction_conflict","Cosmetic transaction intent unbound");
        Check(store.Credits(id)==credits && JsonSerializer.Serialize(store.GetProfile(id).Career.Ledger)==ledger,"Cosmetic mutated economy");
    }
    using(var store=new RealmStore(new SqliteRealmStateStore(folder))) Check(store.GetProfile(id).Career.SelectedCharacterId=="rb-kai","Cosmetic did not survive restart");
});
Test("signed_p07_export_import_defaults_cosmetic_without_resetting_wallet",()=> {
    string folder=Path.GetFullPath(Path.Combine("_local","p08-content-tests",Guid.NewGuid().ToString("N"))); Directory.CreateDirectory(folder);
    using var store=new RealmStore(new SqliteRealmStateStore(folder));var issued=store.CreateProfile("Export fixture");var api=new CareerService(store);
    var exported=api.Execute(issued.Token,new CareerRequest{operation="export"});Check(exported.ok,"Export failed");
    var envelope=JsonNode.Parse(exported.exportJson);var payload=JsonNode.Parse(envelope["Payload"].GetValue<string>());
    payload["Version"]=1;payload.AsObject().Remove("SelectedCharacterId");string oldPayload=payload.ToJsonString();
    // Fixture-owned signing key recreates an authentic prior-format signed export, never a production save.
    using var db=new SqliteConnection($"Data Source={Path.Combine(folder,"realm.sqlite3")};Pooling=False");db.Open();using var cmd=db.CreateCommand();cmd.CommandText="SELECT state_json FROM realm";
    var state=JsonNode.Parse((string)cmd.ExecuteScalar());byte[] key=Convert.FromBase64String(state["ExportSigningKey"].GetValue<string>());
    envelope["Payload"]=oldPayload;envelope["Signature"]=Convert.ToHexString(HMACSHA256.HashData(key,System.Text.Encoding.UTF8.GetBytes(oldPayload))).ToLowerInvariant();
    var imported=api.Execute(issued.Token,new CareerRequest{operation="import",transactionId=Guid.NewGuid().ToString("N"),saveJson=envelope.ToJsonString()});
    Check(imported.ok && imported.profile.selectedCharacterId==CharacterCatalog.DefaultId && imported.profile.credits==1000 && imported.profile.bikes.Length==1,"P07 signed export incompatible");
});
bool allRoutesAvailable = Enumerable.Range(0, 5).All(CampaignCatalog.IsPlayableRoute);
if (allRoutesAvailable) Test("all_25_authoritative_qualifications_unlock_once_with_durable_ledger",()=> {
    string folder=Path.GetFullPath(Path.Combine("_local","p08-content-tests",Guid.NewGuid().ToString("N"))); Directory.CreateDirectory(folder);
    using var store=new RealmStore(new SqliteRealmStateStore(folder)); var issued=store.CreateProfile("Campaign fixture"); string id=issued.Profile.Id;
    int credits=1000;
    for(int l=0;l<5;l++) for(int c=0;c<5;c++) {
        Check(CampaignCatalog.IsPlayableRoute(c),"Production content gate remains closed for "+c);
        string match=store.BeginMatch(new[]{id});int reward=1000*(l+1);
        store.Commit(match,new[]{new RealmGrant {ProfileId=id,BikeId=BikeCatalog.StarterBikeId,BikeCondition=100,LevelIndex=l,CourseIndex=c,Outcome=(int)MultiplayerOutcome.Finished,Rank=1,Reward=reward,Qualified=true}});
        credits+=reward;store.Commit(match,Array.Empty<RealmGrant>());Check(store.Credits(id)==credits,"Duplicate qualification reward");
        var career=store.GetProfile(id).Career;Check(c==4?career.LevelIndex==Math.Min(l+1,4):career.LevelIndex==l,"Campaign level drift");
    }
    Check(store.GetProfile(id).Career.CampaignComplete && store.GetProfile(id).Career.QualificationMask==31 && store.GetProfile(id).Career.Ledger.Count==26,"Full campaign did not settle");
});
var sourceFiles=Directory.GetFiles("Packages/com.racingbois.foundation/Runtime","*.cs",SearchOption.AllDirectories).Concat(Directory.GetFiles("Assets/RacingBois/Client/Application","*.cs")).Concat(Directory.GetFiles("src/Server","*.cs",SearchOption.AllDirectories).Where(p=>!p.Split(Path.DirectorySeparatorChar).Any(part=>part=="obj"||part=="bin"))).Append("src/Tests/RacingBois.P08Content.Tests/Program.cs").Append("src/Tests/RacingBois.P08Content.Tests/RacingBois.P08Content.Tests.csproj").OrderBy(x=>x,StringComparer.Ordinal).ToArray();
var report=new {generatedUtc=DateTimeOffset.UtcNow,passed=tests.Count-failures,failed=failures,contentHash=GameplayRules.ContentHash,pendingProductionGate = ProductionContent.AvailableRouteMask != 31, scope="Pure integer simulation, linked client Application, real isolated SQLite; no Unity rendering or live socket/human evidence.",tests,tracks,bikes,completions,sources=sourceFiles.Select(p=>new {path=p.Replace('\\','/'),sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant()})};
string reportPath=args.Length==2&&args[0]=="--report"?args[1]:"docs/p08/gameplay/content-tests.json";Directory.CreateDirectory(Path.GetDirectoryName(reportPath));File.WriteAllText(reportPath,JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));return failures==0?0:1;
