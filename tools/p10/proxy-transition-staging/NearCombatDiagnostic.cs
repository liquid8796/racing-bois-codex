using System.Reflection;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Simulation;

var network=new TestNetwork(0){JitterSeconds=0,BlockClientUntil=0,InputController=null};var a=network.Add("Left");var b=network.Add("Right");a.BlockUplinkUntil=b.BlockUplinkUntil=0;network.PrepareRace(a,b);
b.Steer=-1;network.Run(18);b.Steer=0;network.Run(45);a.Attack=1;b.Attack=-1;a.Throttle=b.Throttle=1;
object F(object obj,string name)=>obj.GetType().GetField(name,BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(obj)!;
object Capture(TestPeer p)
{
    var s=p.Session;long tick=s.LatestAuthoritativeWorld.Tick;var probes=(Array)F(s,"probes");var predicted=(RiderCheckpoint[])F(s,"predictedHistory");
    var neighbors=(PredictionNeighbors)F(s,"predictionNeighbors");
    return new {authorityTick=tick,s.RiderId,s.MaximumNearCombatResidualMeters,s.NearCombatResidualMeters,
        probe=probes.GetValue((int)(tick%probes.Length)),pastPrediction=predicted[(int)(tick%predicted.Length)].Data,
        currentPrediction=((RiderPredictor)F(s,"predictor")).Checkpoint.Data,
        authority=((RiderCheckpoint)F(s,"authoritative")).Data,world=s.LatestAuthoritativeWorld,local=s.LocalRider,
        cached=F(s,"cachedPresentation"),events=F(s,"events"),neighbors=Enumerable.Range(0,neighbors.RiderCount).Select(i=>new{state=RiderCheckpoints.Capture(neighbors.Riders[i],tick).Data,acceleration=neighbors.Acceleration[i],lateral=neighbors.LateralVelocity[i]}).ToArray()};
}
float maximum=0;var peaks=new List<object>();
for(int i=0;i<360;i++)
{var before=Capture(a);network.Run(1);if(a.Session.MaximumNearCombatResidualMeters>maximum){maximum=a.Session.MaximumNearCombatResidualMeters;peaks.Add(new{step=i,before,after=Capture(a),other=Capture(b)});}}
string output=args[0];Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output,JsonSerializer.Serialize(new{maximum,peaks},new JsonSerializerOptions{IncludeFields=true,WriteIndented=true}));Console.WriteLine("NEAR_COMBAT_MAX "+maximum);
