using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
var options=new JsonSerializerOptions{IncludeFields=true,WriteIndented=true};options.Converters.Add(new InputConverter());
using var doc=JsonDocument.Parse(File.ReadAllText("docs/p09/releases/e/speculative-neighbor-episode.json"));var e=doc.RootElement.GetProperty("episode");var before=e.GetProperty("Before");
RiderCheckpointData Read(JsonElement x)=>x.Deserialize<RiderCheckpointData>(options);
var authority=Read(before.GetProperty("Authority"));var expected=Read(e.GetProperty("After").GetProperty("Predicted"));
PredictionNeighbors Make(int excludeTraffic=0)
{
    var n=new PredictionNeighbors();
    foreach(var r in before.GetProperty("Riders").EnumerateArray()){int i=n.RiderCount++;RiderCheckpoints.Restore(n.Riders[i],new RiderCheckpoint(Read(r.GetProperty("State"))));n.Acceleration[i]=I(r,"Acceleration");n.LateralVelocity[i]=I(r,"LateralVelocity");n.VerticalVelocity[i]=I(r,"VerticalVelocity");}
    foreach(var r in before.GetProperty("Traffic").EnumerateArray()){if(I(r,"Id")==excludeTraffic)continue;var t=n.Traffic[n.TrafficCount++];t.Id=I(r,"Id");t.Active=true;t.DistanceMillimeters=L(r,"DistanceMillimeters");t.LateralMillimeters=I(r,"LateralMillimeters");t.SpeedMillimetersPerSecond=I(r,"SpeedMillimetersPerSecond");t.WidthMillimeters=I(r,"WidthMillimeters");t.LengthMillimeters=I(r,"LengthMillimeters");t.HeightMillimeters=I(r,"HeightMillimeters");t.Oncoming=r.GetProperty("Oncoming").GetBoolean();}
    foreach(var r in before.GetProperty("Pedestrians").EnumerateArray()){var p=n.Pedestrians[n.PedestrianCount++];p.Id=I(r,"Id");p.DistanceMillimeters=L(r,"DistanceMillimeters");p.LateralMillimeters=I(r,"LateralMillimeters");p.HeightMillimeters=I(r,"HeightMillimeters");p.Mode=(PedestrianMode)I(r,"Mode");p.ModeAgeTicks=I(r,"ModeAgeTicks");p.FacingSide=I(r,"FacingSide");p.IsCrossing=r.GetProperty("IsCrossing").GetBoolean();p.WalkingSpeedMillimetersPerSecond=I(r,"WalkingSpeedMillimetersPerSecond");}
    return n;
}
object Compact(RiderCheckpointData d)=>new{d.Tick,Mode=d.Mode.ToString(),d.ModeAgeTicks,d.DistanceMillimeters,d.LateralMillimeters,d.SpeedMillimetersPerSecond,d.Health,d.BikeCondition,d.CollisionUntilTick};
object Run(bool sortedAll,int excludeTraffic=0)
{
    var p=new RiderPredictor(I(before,"Level"),I(before,"Course"));p.SetNeighbors(Make(excludeTraffic));p.Restore(new RiderCheckpoint(authority));
    var w=(GameplayWorld)typeof(RiderPredictor).GetField("sandbox",BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(p)!;
    var advance=typeof(RiderPredictor).GetMethod("AdvanceNeighbors",BindingFlags.Instance|BindingFlags.NonPublic)!;
    var owner=w.Riders[0];var originalOrder=w.Riders.Take(w.RiderCount).ToArray();
    var frames=before.GetProperty("Pending").EnumerateArray().ToArray();int index=0;var held=before.GetProperty("HeldAnalog").Deserialize<RaceInput>(options);long applied=L(before,"LastAppliedTick"),target=L(before.GetProperty("Predicted"),"Tick");
    var timeline=new List<object>();
    for(long tick=authority.Tick+1;tick<=target;tick++)
    {
        RaceInput input;if(index<frames.Length&&L(frames[index],"Tick")==tick){input=frames[index++].GetProperty("Input").Deserialize<RaceInput>(options);held=new RaceInput(input.ThrottlePermille,input.BrakePermille,input.SteerPermille);applied=tick;}else input=applied>=0&&tick-applied<=6?held:default;
        if(!sortedAll)p.Advance(tick,input);
        else
        {
            RiderCheckpoints.SetPrevious(owner);owner.Input=input;owner.LastInputTick=w.Tick;w.Tick=tick;w.EventCount=0;DrivingDynamics.Step(w,owner);advance.Invoke(p,null);
            Array.Sort(w.Riders,0,w.RiderCount,Comparer<RaceRider>.Create((a,b)=>a.Id.CompareTo(b.Id)));
            DrivingDynamics.ResolveContacts(w);
            CombatResolver.BeginAttack(w,owner);if(owner.Mode==RiderMode.Attacking&&owner.AttackAgeTicks==GameplayRules.AttackImpactTick)owner.AttackResolved=true;
            Array.Copy(originalOrder,w.Riders,originalOrder.Length);w.EventCount=0;
        }
        if(tick<=authority.Tick+3)timeline.Add(Compact(p.Checkpoint.Data));
    }
    var end=p.Checkpoint.Data;var differences=typeof(RiderCheckpointData).GetFields().Where(f=>!Equals(f.GetValue(end),f.GetValue(expected))).Select(f=>new { field=f.Name, actual=f.GetValue(end), expected=f.GetValue(expected) }).ToArray();
    return new{sortedAll,excludeTraffic,timeline,final=Compact(end),positionResidualMeters=Math.Sqrt(Math.Pow((end.DistanceMillimeters-expected.DistanceMillimeters)/1000d,2)+Math.Pow((end.LateralMillimeters-expected.LateralMillimeters)/1000d,2)),fullCheckpointMatches=JsonSerializer.Serialize(end,options)==JsonSerializer.Serialize(expected,options),differences};
}
var output=args.Length>0?args[0]:"_local/contact-order.json";Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output,JsonSerializer.Serialize(new{scope="Isolated diagnostic contact-order counterfactual, not a production patch: same captured inputs, checkpoints and proxy motion; all contacts resolved in sorted actor ID order only in experimental variant. Actual physics source untouched.",authority=Compact(authority),expected=Compact(expected),legacy=Run(false),withoutTraffic3001=Run(false,3001),authorityOrder=Run(true)},options));
Console.WriteLine("CONTACT_ORDER_DIAGNOSTIC_WRITTEN "+output);
static int I(JsonElement e,string p)=>e.GetProperty(p).GetInt32();static long L(JsonElement e,string p)=>e.GetProperty(p).GetInt64();
internal sealed class InputConverter:JsonConverter<RaceInput>
{
    public override RaceInput Read(ref Utf8JsonReader r,Type t,JsonSerializerOptions o){using var d=JsonDocument.ParseValue(ref r);var e=d.RootElement;return new RaceInput(e.GetProperty("ThrottlePermille").GetInt32(),e.GetProperty("BrakePermille").GetInt32(),e.GetProperty("SteerPermille").GetInt32(),e.GetProperty("AttackSide").GetInt32(),e.GetProperty("Kick").GetBoolean());}
    public override void Write(Utf8JsonWriter w,RaceInput x,JsonSerializerOptions o){w.WriteStartObject();w.WriteNumber("ThrottlePermille",x.ThrottlePermille);w.WriteNumber("BrakePermille",x.BrakePermille);w.WriteNumber("SteerPermille",x.SteerPermille);w.WriteNumber("AttackSide",x.AttackSide);w.WriteBoolean("Kick",x.Kick);w.WriteEndObject();}
}
