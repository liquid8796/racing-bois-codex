using System.Reflection;
using System.Text.Json;
using RacingBois.Simulation;

if(args.Length!=2||File.Exists(args[1]))throw new ArgumentException("<immutable recorded trace> <new diagnostic report>");
using var document=JsonDocument.Parse(File.ReadAllText(args[0]));var episode=document.RootElement.GetProperty("correctionTrace").GetProperty("episodes")[0];
var before=episode.GetProperty("Before");var after=episode.GetProperty("After");
var replayType=Assembly.Load("CorrectionAudit").GetType("CorrectionReplay")!;
var read=replayType.GetMethod("Read",BindingFlags.Static|BindingFlags.NonPublic)!;
object State(JsonElement value)=>read.Invoke(null,new object[]{value})!;
RiderCheckpointData Run(object state)=>(RiderCheckpointData)state.GetType().GetMethod("Replay")!.Invoke(state,new object[]{true})!;
var expected=Run(State(after));var variants=new List<object>();
foreach(string variant in new[]{"recorded","zero_acceleration_4_6","zero_lateral_4_6","zero_both_4_6","later_observed_kinematics_4_6"})
{
    object state=State(before);var neighbors=(PredictionNeighbors)state.GetType().GetField("Neighbors")!.GetValue(state)!;
    for(int i=0;i<neighbors.RiderCount;i++)
    {
        int id=neighbors.Riders[i].Id;if(id!=4&&id!=6)continue;
        if(variant=="zero_acceleration_4_6"||variant=="zero_both_4_6")neighbors.Acceleration[i]=0;
        if(variant=="zero_lateral_4_6"||variant=="zero_both_4_6")neighbors.LateralVelocity[i]=0;
        if(variant=="later_observed_kinematics_4_6")
        {var later=after.GetProperty("Riders").EnumerateArray().Single(r=>r.GetProperty("State").GetProperty("Id").GetInt32()==id);neighbors.Acceleration[i]=later.GetProperty("Acceleration").GetInt32();neighbors.LateralVelocity[i]=later.GetProperty("LateralVelocity").GetInt32();}
    }
    var actual=Run(state);variants.Add(new{variant,actual,positionError=Math.Sqrt(Math.Pow((actual.DistanceMillimeters-expected.DistanceMillimeters)/1000d,2)+Math.Pow((actual.LateralMillimeters-expected.LateralMillimeters)/1000d,2)),checkpointDifferences=typeof(RiderCheckpointData).GetFields().Where(f=>!Equals(f.GetValue(actual),f.GetValue(expected))).Select(f=>f.Name).ToArray()});
}
var report=new{scope="Read-only isolated replay. Zero-derivative counterfactuals isolate estimator effects; later-observed values are diagnostic hindsight, never a production forecast.",expected,variants};
File.WriteAllText(args[1],JsonSerializer.Serialize(report,new JsonSerializerOptions{IncludeFields=true,WriteIndented=true}));Console.WriteLine("KINEMATICS_AUDIT_WRITTEN "+args[1]);
