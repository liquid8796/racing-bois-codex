using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Simulation;

var options=new JsonSerializerOptions{WriteIndented=true,IncludeFields=true};options.Converters.Add(new InputConverter());
var tests=new List<object>();var details=new List<object>();int failures=0;
void Check(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
void Test(string name,Action action){try{action();tests.Add(new{name,passed=true});Console.WriteLine("PASS "+name);}catch(Exception error){failures++;tests.Add(new{name,passed=false,error=error.Message});Console.WriteLine("FAIL "+name+": "+error.Message);}}
MpSnapshot Packet(long tick,int speed,int lateral,int protection)
{
    var world=RaceSimulation.CreateDefault(1996,0);var owner=RaceSimulation.AddPlayer(world,1);
    return new MpSnapshot{tick=tick,resolvedThroughTick=tick,riderId=1,own=CheckpointMapper.CaptureDto(owner,tick),lastAppliedInputTick=tick,serverServiceTick=tick+180,
        level=0,courseIndex=0,trackLengthMillimeters=world.Track.LengthMillimeters,
        riders=new[]{new NumericRow{values=new[]{2,0,0,0,0,10000,lateral,speed,0,0,10000,lateral,0,4096,100,7,2,-1,0,0,0,0,100,1,0,0,protection,1000,0,0,0}}}};
}
MultiplayerSnapshotReadModel Project(MpSnapshot packet)=>MultiplayerProjection.World(packet,0,0,Array.Empty<RaceEventReadModel>());
PredictionNeighbors Fill(MultiplayerSnapshotReadModel current,MultiplayerSnapshotReadModel previous)
{var n=new PredictionNeighbors();PredictionNeighborBuilder.Fill(n,current,previous,1);return n;}
Test("new_active_contact_interval_does_not_extrapolate_impulse",()=>
{
    var before=Project(Packet(100,3209,196,0));var now=Project(Packet(103,3119,203,10));var n=Fill(now,before);
    Check(n.Acceleration[0]==0&&n.LateralVelocity[0]==0&&n.VerticalVelocity[0]==0,"Instantaneous contact delta became continuous motion.");
    Check(n.Riders[0].SpeedMillimetersPerSecond==31190&&n.Riders[0].LateralMillimeters==2030,"Current authoritative pose/speed changed.");
});
Test("genuine_braking_without_new_contact_keeps_negative_derivative",()=>
{
    var n=Fill(Project(Packet(103,3119,203,0)),Project(Packet(100,3209,196,0)));
    Check(n.Acceleration[0]==-18000&&n.LateralVelocity[0]==1400,"Legitimate continuous braking/lane motion was suppressed.");
});
Test("unchanged_active_immunity_keeps_motion_estimation",()=>
{
    var n=Fill(Project(Packet(103,3119,203,17)),Project(Packet(100,3209,196,20)));
    Check(n.Acceleration[0]==-18000&&n.LateralVelocity[0]==1400,"Unchanged absolute protection was treated as a new impulse.");
});
Test("expired_until_clamped_to_current_tick_is_not_a_new_grant",()=>
{
    foreach(int beforeRemaining in new[]{0,2,3})
    {var n=Fill(Project(Packet(103,3119,203,0)),Project(Packet(100,3209,196,beforeRemaining)));Check(n.Acceleration[0]==-18000,"Expiry clamp suppressed a valid derivative.");}
});
Test("first_observation_and_missing_history_never_invent_derivatives",()=>
{
    var now=Project(Packet(103,3119,203,10));var n=Fill(now,null);Check(n.Acceleration[0]==0&&n.LateralVelocity[0]==0,"First snapshot invented motion history.");
    var target=new PredictionNeighbors();var before=Project(Packet(100,3209,196,0));
    PredictionNeighborBuilder.Fill(target,now.World,before.World,1,now.CollisionUntilByRider,now.PedestrianContexts,now.RiderCombatContexts);
    Check(target.Acceleration[0]==0,"Visual history without validated private history inferred an impulse.");
});
Test("previous_snapshot_metadata_is_immutable",()=>
{
    var wire=Packet(100,3209,196,20);var before=Project(wire);wire.riders[0].values[26]=0;
    var n=Fill(Project(Packet(103,3119,203,17)),before);
    Check(before.CollisionUntilByRider[2]==120&&n.Acceleration[0]==-18000,"Mutable wire aliased the retained previous context.");
});
TestNetwork Network(int delay=0)=>new TestNetwork(delay){JitterSeconds=0,BlockClientUntil=0,InputController=null};
Test("session_clears_previous_metadata_on_room_epoch_reset",()=>
{
    var net=Network();var peer=net.Add("Metadata lifecycle");peer.BlockUplinkUntil=0;net.PrepareRace(peer);
    var field=typeof(MultiplayerSession).GetField("latestPredictionSnapshot",BindingFlags.Instance|BindingFlags.NonPublic)!;
    Check(field.GetValue(peer.Session)!=null,"Session did not retain validated context.");peer.Session.LeaveLobby();net.Run(30);
    Check(peer.Session.Room==null&&field.GetValue(peer.Session)==null,"Previous race context survived leave/reset.");
});
foreach(int delay in new[]{0,150,250})Test("unchanged_near_combat_gate_"+delay,()=>
{
    var net=Network(delay);var a=net.Add("Left");var b=net.Add("Right");a.BlockUplinkUntil=b.BlockUplinkUntil=0;net.PrepareRace(a,b);
    b.Steer=-1;net.Run(18);b.Steer=0;net.Run(45);a.Attack=1;b.Attack=-1;a.Throttle=b.Throttle=1;net.Run(360);
    Check(a.Session.NearCombatResidualSamples>10&&a.Session.PendingInputCount<=32&&a.Session.FutureInputs==0,"Invalid latency scenario.");
    Check(a.Session.MaximumNearCombatResidualMeters<(delay==0?.15f:delay==150?.6f:1f),"Existing near-combat tolerance exceeded.");
    details.Add(new{kind="latency",delay,maximumRelativeResidualMeters=a.Session.MaximumNearCombatResidualMeters});
});
Test("recorded_impulse_counterfactual_matches_full_later_checkpoint",()=>
{
    using var document=JsonDocument.Parse(File.ReadAllText("docs/p10/proxy-transition-staging/first-production-outlier.json"));
    var e=document.RootElement.GetProperty("correctionTrace").GetProperty("episodes")[0];var before=e.GetProperty("Before");var after=e.GetProperty("After");
    var old=Replay(before,false);var fixedPrediction=Replay(before,true);var expected=Replay(after,false);
    Check(old.Mode==RiderMode.Falling&&expected.Mode==RiderMode.Riding,"Recorded defect no longer reproduced.");
    Check(JsonSerializer.Serialize(fixedPrediction,options)==JsonSerializer.Serialize(expected,options),"Zero contact-impulse derivative did not match every later checkpoint field.");
    details.Add(new{kind="recordedReplay",old,fixedPrediction,expected,scope="Captured current/pending states are exact. Zeroing only riders4/6 acceleration is a counterfactual, justified by separately tested new-interval guard; the trace did not retain the immediately previous private interval snapshot."});
});
RiderCheckpointData Replay(JsonElement frame,bool zeroImpulse)
{
    var n=new PredictionNeighbors();
    foreach(var r in frame.GetProperty("Riders").EnumerateArray())
    {int i=n.RiderCount++;var d=r.GetProperty("State").Deserialize<RiderCheckpointData>(options);RiderCheckpoints.Restore(n.Riders[i],new RiderCheckpoint(d));n.Acceleration[i]=r.GetProperty("Acceleration").GetInt32();n.LateralVelocity[i]=r.GetProperty("LateralVelocity").GetInt32();n.VerticalVelocity[i]=r.GetProperty("VerticalVelocity").GetInt32();if(zeroImpulse&&(d.Id==4||d.Id==6))n.Acceleration[i]=0;}
    foreach(var r in frame.GetProperty("Traffic").EnumerateArray())
    {var t=n.Traffic[n.TrafficCount++];t.Id=I(r,"Id");t.DistanceMillimeters=L(r,"DistanceMillimeters");t.LateralMillimeters=I(r,"LateralMillimeters");t.SpeedMillimetersPerSecond=I(r,"SpeedMillimetersPerSecond");t.WidthMillimeters=I(r,"WidthMillimeters");t.LengthMillimeters=I(r,"LengthMillimeters");t.HeightMillimeters=I(r,"HeightMillimeters");t.Oncoming=r.GetProperty("Oncoming").GetBoolean();t.Active=true;}
    foreach(var r in frame.GetProperty("Pedestrians").EnumerateArray())
    {var p=n.Pedestrians[n.PedestrianCount++];p.Id=I(r,"Id");p.DistanceMillimeters=L(r,"DistanceMillimeters");p.LateralMillimeters=I(r,"LateralMillimeters");p.HeightMillimeters=I(r,"HeightMillimeters");p.Mode=(PedestrianMode)I(r,"Mode");p.ModeAgeTicks=I(r,"ModeAgeTicks");p.FacingSide=I(r,"FacingSide");p.IsCrossing=r.GetProperty("IsCrossing").GetBoolean();p.WalkingSpeedMillimetersPerSecond=I(r,"WalkingSpeedMillimetersPerSecond");var c=r.GetProperty("PredictionContext");PedestrianCheckpoints.RestorePredictionContext(p,new PedestrianPredictionContext(I(c,"WaitTicks"),I(c,"DesiredWalkingSpeed"),I(c,"MotionRemainder")));}
    var authority=frame.GetProperty("Authority").Deserialize<RiderCheckpointData>(options);var predictor=new RiderPredictor(I(frame,"Level"),I(frame,"Course"));predictor.SetNeighbors(n);predictor.Restore(new RiderCheckpoint(authority));
    var pending=frame.GetProperty("Pending").EnumerateArray().ToArray();int index=0;var held=frame.GetProperty("HeldAnalog").Deserialize<RaceInput>(options);long applied=L(frame,"LastAppliedTick");
    for(long tick=authority.Tick+1;tick<=L(frame.GetProperty("Predicted"),"Tick");tick++)
    {RaceInput input;if(index<pending.Length&&L(pending[index],"Tick")==tick){input=pending[index++].GetProperty("Input").Deserialize<RaceInput>(options);held=new RaceInput(input.ThrottlePermille,input.BrakePermille,input.SteerPermille);applied=tick;}else input=applied>=0&&tick-applied<=6?held:default;predictor.Advance(tick,input);}
    return predictor.Checkpoint.Data;
}
string output=args.Length>0?args[0]:"_local/impulse-tests.json";Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
var manifest=JsonDocument.Parse(File.ReadAllText("tools/p10/impulse-derivative-staging/manifest.json"));
bool unchanged=manifest.RootElement.GetProperty("changes").EnumerateArray().All(row=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(row.GetProperty("path").GetString()!))).ToLowerInvariant()==row.GetProperty("before").GetString());
Check(unchanged,"Production source changed during staging.");
File.WriteAllText(output,JsonSerializer.Serialize(new{schema=1,passed=failures==0,failed=failures,tests=tests.Count,results=tests,details,productionUnchanged=unchanged,scope="Staged client-only metadata-history/derivative guard. No production, server, protocol, physics or running-process mutation."},options));return failures==0?0:1;
static int I(JsonElement e,string key)=>e.GetProperty(key).GetInt32();static long L(JsonElement e,string key)=>e.GetProperty(key).GetInt64();
internal sealed class InputConverter:JsonConverter<RaceInput>
{
    public override RaceInput Read(ref Utf8JsonReader r,Type t,JsonSerializerOptions o){using var d=JsonDocument.ParseValue(ref r);var e=d.RootElement;return new RaceInput(e.GetProperty("ThrottlePermille").GetInt32(),e.GetProperty("BrakePermille").GetInt32(),e.GetProperty("SteerPermille").GetInt32(),e.GetProperty("AttackSide").GetInt32(),e.GetProperty("Kick").GetBoolean());}
    public override void Write(Utf8JsonWriter w,RaceInput x,JsonSerializerOptions o){w.WriteStartObject();w.WriteNumber("ThrottlePermille",x.ThrottlePermille);w.WriteNumber("BrakePermille",x.BrakePermille);w.WriteNumber("SteerPermille",x.SteerPermille);w.WriteNumber("AttackSide",x.AttackSide);w.WriteBoolean("Kick",x.Kick);w.WriteEndObject();}
}
