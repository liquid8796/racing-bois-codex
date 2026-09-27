using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;

bool candidate = false;
#if CANDIDATE
candidate = true;
#endif
string fixture = "src/Tests/RacingBois.Prediction.Tests/Fixtures/pedestrian-recovery-episode.json";
string reportPath = args.Length > 0 ? args[0] : "docs/p10/prediction-regression.json";
var options = new JsonSerializerOptions { IncludeFields = true, WriteIndented = true }; options.Converters.Add(new InputConverter());
using var document = JsonDocument.Parse(File.ReadAllText(fixture)); var episode = document.RootElement.GetProperty("episode");
var before = episode.GetProperty("Before"); var after = episode.GetProperty("After");
var rows = new List<object>(); var details = new List<object>(); int failed = 0;
void Check(bool value,string message){if(!value)throw new InvalidOperationException(message);}
void Test(string name,Action action){try{action();rows.Add(new{name,passed=true});Console.WriteLine("PASS "+name);}catch(Exception e){failed++;rows.Add(new{name,passed=false,error=e.Message});Console.WriteLine("FAIL "+name+": "+e.Message);}}
RiderCheckpointData ReadCheckpoint(JsonElement value)=>value.Deserialize<RiderCheckpointData>(options);
PredictionNeighbors Neighbors(JsonElement value)
{
    var n=new PredictionNeighbors();
    foreach(var r in value.GetProperty("Riders").EnumerateArray())
    {int i=n.RiderCount++;RiderCheckpoints.Restore(n.Riders[i],new RiderCheckpoint(ReadCheckpoint(r.GetProperty("State"))));n.Acceleration[i]=r.GetProperty("Acceleration").GetInt32();n.LateralVelocity[i]=r.GetProperty("LateralVelocity").GetInt32();n.VerticalVelocity[i]=r.GetProperty("VerticalVelocity").GetInt32();}
    foreach(var r in value.GetProperty("Traffic").EnumerateArray())
    {var t=n.Traffic[n.TrafficCount++];t.Id=I(r,"Id");t.Active=true;t.DistanceMillimeters=L(r,"DistanceMillimeters");t.LateralMillimeters=I(r,"LateralMillimeters");t.SpeedMillimetersPerSecond=I(r,"SpeedMillimetersPerSecond");t.WidthMillimeters=I(r,"WidthMillimeters");t.LengthMillimeters=I(r,"LengthMillimeters");t.HeightMillimeters=I(r,"HeightMillimeters");t.Oncoming=r.GetProperty("Oncoming").GetBoolean();}
    foreach(var r in value.GetProperty("Pedestrians").EnumerateArray())
    {var p=n.Pedestrians[n.PedestrianCount++];p.Id=I(r,"Id");p.DistanceMillimeters=L(r,"DistanceMillimeters");p.LateralMillimeters=I(r,"LateralMillimeters");p.HeightMillimeters=I(r,"HeightMillimeters");p.FacingSide=I(r,"FacingSide");p.Mode=(PedestrianMode)I(r,"Mode");p.ModeAgeTicks=I(r,"ModeAgeTicks");p.IsCrossing=r.GetProperty("IsCrossing").GetBoolean();p.WalkingSpeedMillimetersPerSecond=I(r,"WalkingSpeedMillimetersPerSecond");
        // Legacy protocol5 fixture has no private timing. The unrelated waiting
        // actors are >100m away and cannot reach this owner in30ticks. Holding
        // them is explicit; the tested recovery actor's new wait120 is known.
        p.WaitTicks=p.Mode==PedestrianMode.Waiting?359:120;p.DesiredWalkingSpeed=Math.Abs(p.WalkingSpeedMillimetersPerSecond)>=1200?Math.Abs(p.WalkingSpeedMillimetersPerSecond):1400;
    }
    return n;
}
RiderCheckpointData Replay(JsonElement value)
{
    var p=new RiderPredictor(I(value,"Level"),I(value,"Course"));p.SetNeighbors(Neighbors(value));var a=ReadCheckpoint(value.GetProperty("Authority"));p.Restore(new RiderCheckpoint(a));
    var frames=value.GetProperty("Pending").EnumerateArray().ToArray();var held=value.GetProperty("HeldAnalog").Deserialize<RaceInput>(options);long applied=L(value,"LastAppliedTick"),target=L(value.GetProperty("Predicted"),"Tick");int index=0;
    for(long tick=a.Tick+1;tick<=target;tick++)
    {RaceInput input;if(index<frames.Length && L(frames[index],"Tick")==tick){input=frames[index++].GetProperty("Input").Deserialize<RaceInput>(options);held=new RaceInput(input.ThrottlePermille,input.BrakePermille,input.SteerPermille);applied=tick;}else input=applied>=0 && tick-applied<=6?held:default;p.Advance(tick,input);}
    return p.Checkpoint.Data;
}
var replayBefore=Replay(before);var replayAfter=Replay(after);var expectedAfter=ReadCheckpoint(after.GetProperty("Predicted"));
double residual=Math.Sqrt(Math.Pow((replayBefore.DistanceMillimeters-expectedAfter.DistanceMillimeters)/1000d,2)+Math.Pow((replayBefore.LateralMillimeters-expectedAfter.LateralMillimeters)/1000d,2));
details.Add(new { fixtureBefore=ReadCheckpoint(before.GetProperty("Predicted")),replayBefore,replayAfter,expectedAfter,residualMeters=residual });
Test("captured_post_authority_replay_remains_exact",()=>Check(JsonSerializer.Serialize(replayAfter,options)==JsonSerializer.Serialize(expectedAfter,options),"Fresh-authority replay changed."));
Test("captured_recovery_prediction_matches_later_authority",()=>
{
    Check(replayBefore.Mode==expectedAfter.Mode,"Missed deterministic collider recovery still leaves rider driving.");
    Check(replayBefore.ModeAgeTicks==expectedAfter.ModeAgeTicks,"Recovery/contact tick changed.");
    Check(replayBefore.Health==expectedAfter.Health && replayBefore.BikeCondition==expectedAfter.BikeCondition,"Contact outcome differs from authority.");
    Check(residual<=.011,"Remaining motion error exceeds centimeter snapshot quantization: "+residual);
});
Test("stumbled_179_not_collidable_180_recovers_before_contact",()=>
{
    var w=RaceSimulation.CreateDefault(1996,0);var owner=RaceSimulation.AddPlayer(w,1);owner.DistanceMillimeters=owner.BikeDistanceMillimeters=0;owner.LateralMillimeters=owner.BikeLateralMillimeters=0;owner.SpeedMillimetersPerSecond=50000;
    var n=new PredictionNeighbors{PedestrianCount=1};var p=n.Pedestrians[0];p.Id=4008;p.DistanceMillimeters=1000;p.Mode=PedestrianMode.Stumbled;p.ModeAgeTicks=178;p.IsCrossing=true;
    var predictor=new RiderPredictor(0);predictor.SetNeighbors(n);predictor.Restore(RiderCheckpoints.Capture(owner,100));
    Check(predictor.Advance(101,default).Data.Mode==RiderMode.Riding,"Stumbled179 became collidable early.");
    Check(predictor.Advance(102,default).Data.Mode==RiderMode.Falling,"Recovery180 was not applied before swept contact.");
    Check(n.Pedestrians[0].Mode==PedestrianMode.Stumbled && n.Pedestrians[0].ModeAgeTicks==178,"Prediction mutated its caller's snapshot.");
});
GameplayWorld Sandbox(RiderPredictor p)=>(GameplayWorld)typeof(RiderPredictor).GetField("sandbox",BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(p)!;
void KnownEnd(bool crossing)
{
    var w=RaceSimulation.CreateDefault(1996,0);var owner=RaceSimulation.AddPlayer(w,1);RaceSimulation.FindRider(w,2001).Mode=RiderMode.Wrecked;
    w.NextTrafficTick=w.NextPedestrianTick=long.MaxValue;w.PedestrianCount=1;var a=w.Pedestrians[0];a.Id=4008;a.DistanceMillimeters=100000;a.Mode=PedestrianMode.Walking;a.ModeAgeTicks=crossing?10:299;a.IsCrossing=crossing;a.FacingSide=1;a.DesiredWalkingSpeed=a.WalkingSpeedMillimetersPerSecond=1500;a.LateralMillimeters=crossing?7690:7700;
    var n=new PredictionNeighbors{PedestrianCount=1};var q=n.Pedestrians[0];q.Id=a.Id;q.DistanceMillimeters=a.DistanceMillimeters;q.Mode=a.Mode;q.ModeAgeTicks=a.ModeAgeTicks;q.IsCrossing=a.IsCrossing;q.FacingSide=a.FacingSide;q.WalkingSpeedMillimetersPerSecond=a.WalkingSpeedMillimetersPerSecond;q.LateralMillimeters=a.LateralMillimeters;
    q.WaitTicks=a.WaitTicks;q.DesiredWalkingSpeed=a.DesiredWalkingSpeed;q.MotionRemainder=a.MotionRemainder;
    var predictor=new RiderPredictor(0);predictor.SetNeighbors(n);predictor.Restore(RiderCheckpoints.Capture(owner,0));
    uint rng=Sandbox(predictor).PedestrianRandomState;
    for(int tick=1;tick<=20;tick++){RaceSimulation.SetInput(w,1,default);RaceSimulation.Step(w);predictor.Advance(tick,default);}
    var actual=Sandbox(predictor).Pedestrians[0];
    Check(actual.Mode==a.Mode && actual.ModeAgeTicks==a.ModeAgeTicks && actual.DistanceMillimeters==a.DistanceMillimeters && actual.LateralMillimeters==a.LateralMillimeters && actual.FacingSide==a.FacingSide && actual.WalkingSpeedMillimetersPerSecond==a.WalkingSpeedMillimetersPerSecond,"Known walking end did not match authoritative state.");
    Check(Sandbox(predictor).PedestrianRandomState==rng && Sandbox(predictor).EventCount==0,"Prediction consumed authority RNG or exposed events.");
    details.Add(new{crossing,authorityMode=a.Mode,authorityAge=a.ModeAgeTicks,a.DistanceMillimeters,a.LateralMillimeters,a.FacingSide,a.WaitTicks,authorityRng=w.PedestrianRandomState});
}
Test("known_along_road_300_tick_stop_matches_authority",()=>KnownEnd(false));
Test("known_crossing_shoulder_stop_reverse_matches_authority",()=>KnownEnd(true));
Test("waiting_uses_explicit_duration_speed_and_submillimeter_remainder",()=>
{
    foreach(int wait in new[]{60,120,359})foreach(int side in new[]{-1,1})
    {
        var w=RaceSimulation.CreateDefault(1996,0);var own=RaceSimulation.AddPlayer(w,1);RaceSimulation.FindRider(w,2001).Mode=RiderMode.Wrecked;w.NextPedestrianTick=w.NextTrafficTick=long.MaxValue;
        w.PedestrianCount=1;var a=w.Pedestrians[0];a.Id=4008;a.DistanceMillimeters=100000;a.Mode=PedestrianMode.Waiting;a.ModeAgeTicks=wait-2;a.WaitTicks=wait;a.DesiredWalkingSpeed=1600;a.MotionRemainder=side*47;a.FacingSide=side;a.IsCrossing=true;
        var n=new PredictionNeighbors{PedestrianCount=1};var p=n.Pedestrians[0];p.Id=a.Id;p.DistanceMillimeters=a.DistanceMillimeters;p.Mode=a.Mode;p.ModeAgeTicks=a.ModeAgeTicks;p.WaitTicks=a.WaitTicks;p.DesiredWalkingSpeed=a.DesiredWalkingSpeed;p.MotionRemainder=a.MotionRemainder;p.FacingSide=a.FacingSide;p.IsCrossing=true;
        var predictor=new RiderPredictor(0);predictor.SetNeighbors(n);predictor.Restore(RiderCheckpoints.Capture(own,0));
        for(int tick=1;tick<=20;tick++)
        {
            RaceSimulation.SetInput(w,1,default);RaceSimulation.Step(w);predictor.Advance(tick,default);var actual=Sandbox(predictor).Pedestrians[0];
            Check(actual.Mode==a.Mode && actual.ModeAgeTicks==a.ModeAgeTicks && actual.LateralMillimeters==a.LateralMillimeters && actual.WalkingSpeedMillimetersPerSecond==a.WalkingSpeedMillimetersPerSecond && actual.MotionRemainder==a.MotionRemainder,"Explicit waiting boundary/movement differs at tick"+tick);
        }
    }
});
#if CANDIDATE
Test("pedestrian_context_bounds_and_state_consistency_fail_closed",()=>
{
    void Reject(Action a){bool rejected=false;try{a();}catch(ArgumentException){rejected=true;}Check(rejected,"Invalid metadata accepted.");}
    foreach(int wait in new[]{-1,0,59,360,int.MaxValue})Reject(()=>new PedestrianPredictionContext(wait,1400,0));
    foreach(int speed in new[]{0,1199,1601,int.MaxValue})Reject(()=>new PedestrianPredictionContext(120,speed,0));
    foreach(int remainder in new[]{-60,60})Reject(()=>new PedestrianPredictionContext(120,1400,remainder));
    foreach(int wait in new[]{60,359})foreach(int speed in new[]{1200,1600})foreach(int remainder in new[]{-59,59})Check(new PedestrianPredictionContext(wait,speed,remainder).IsValid,"Metadata boundary rejected.");
    var context=new PedestrianPredictionContext(120,1400,0);
    Check(context.Matches(PedestrianMode.Waiting,119,0,1,true)&&!context.Matches(PedestrianMode.Waiting,120,0,1,true),"Waiting coherence not validated.");
    Check(context.Matches(PedestrianMode.Stumbled,179,0,-1,true)&&!context.Matches(PedestrianMode.Stumbled,180,0,1,true),"Recovery coherence not validated.");
    Check(context.Matches(PedestrianMode.Walking,299,-1400,-1,false)&&!context.Matches(PedestrianMode.Walking,300,-1400,-1,false)&&!context.Matches(PedestrianMode.Walking,1,1400,-1,true),"Walking coherence not validated.");
    Reject(()=>PedestrianCheckpoints.RestorePredictionContext(new RacePedestrian(),default));
});
#endif
#if CANDIDATE
ProxyBehaviorTests.Run(Test,Check,details,options);
#endif
var golden=GameplayVerification.Run();
Test("authoritative_3000_tick_golden_and_rng_unchanged",()=>Check(golden.Passed,"Authority golden changed: "+golden.Hash));
var sources=Directory.GetFiles("Packages/com.racingbois.foundation/Runtime/Simulation","*.cs")
    .Concat(Directory.GetFiles("src/Tests/RacingBois.Prediction.Tests","*.*"))
    .Concat(Directory.GetFiles("src/Tests/RacingBois.Prediction.Tests/Fixtures","*.json"))
    .OrderBy(path=>path,StringComparer.Ordinal).Select(path=>new{path=path.Replace('\\','/'),sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()}).ToArray();
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(reportPath))!);
File.WriteAllText(reportPath,JsonSerializer.Serialize(new{schema=1,candidate,passed=failed==0,failed,tests=rows.Count,results=rows,details,goldenHash=golden.Hash,sources,fixture,fixtureSha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(fixture))).ToLowerInvariant(),scope="Actual production simulation source compiled into an isolated regression executable; no server/Unity mutation. Captured protocol5 recovery fixture has no private waiting metadata; unrelated far waiting actors explicitly held. Dedicated authoritative waiting fixtures supply exact timing/speed/remainder."},options));
return failed==0?0:1;
static int I(JsonElement e,string p)=>e.GetProperty(p).GetInt32();
static long L(JsonElement e,string p)=>e.GetProperty(p).GetInt64();
internal sealed class InputConverter:JsonConverter<RaceInput>
{
    public override RaceInput Read(ref Utf8JsonReader r,Type t,JsonSerializerOptions o){using var d=JsonDocument.ParseValue(ref r);var e=d.RootElement;return new RaceInput(e.GetProperty("ThrottlePermille").GetInt32(),e.GetProperty("BrakePermille").GetInt32(),e.GetProperty("SteerPermille").GetInt32(),e.GetProperty("AttackSide").GetInt32(),e.GetProperty("Kick").GetBoolean());}
    public override void Write(Utf8JsonWriter w,RaceInput x,JsonSerializerOptions o){w.WriteStartObject();w.WriteNumber("ThrottlePermille",x.ThrottlePermille);w.WriteNumber("BrakePermille",x.BrakePermille);w.WriteNumber("SteerPermille",x.SteerPermille);w.WriteNumber("AttackSide",x.AttackSide);w.WriteBoolean("Kick",x.Kick);w.WriteEndObject();}
}
