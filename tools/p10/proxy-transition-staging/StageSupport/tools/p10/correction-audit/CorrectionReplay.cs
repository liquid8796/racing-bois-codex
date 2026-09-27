using System.Text.Json;
using System.Text.Json.Serialization;
using System.Security.Cryptography;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;

internal static class CorrectionReplay
{
    private static readonly JsonSerializerOptions Options=MakeOptions();
    private static JsonSerializerOptions MakeOptions(){var o=new JsonSerializerOptions{IncludeFields=true,WriteIndented=true};o.Converters.Add(new InputConverter());return o;}
    public static int Run(string[] args)
    {
        if(args.Length!=3)throw new ArgumentException("--replay <trace.json> <new-report.json>");
        if(File.Exists(args[2]))throw new IOException("Choose a new immutable replay receipt.");
        using var doc=JsonDocument.Parse(File.ReadAllText(args[1]));var rows=new List<object>();bool passed=true;
        foreach(var episode in doc.RootElement.GetProperty("correctionTrace").GetProperty("episodes").EnumerateArray())
        {
            var beforeJson=episode.GetProperty("Before");var afterJson=episode.GetProperty("After");
            var before=Read(beforeJson);var after=Read(afterJson);
            var oldReplay=before.Replay(true);var newReplay=after.Replay(true);
            bool oldMatch=Same(oldReplay,before.Predicted),newMatch=Same(newReplay,after.Predicted);passed &=oldMatch && newMatch;
            var variants=new List<object>();
            foreach(var rider in beforeJson.GetProperty("Riders").EnumerateArray())
            {
                int id=rider.GetProperty("State").GetProperty("Id").GetInt32();
                before.Neighbors=Neighbors(beforeJson,id,null);var excluded=before.Replay(true);
                before.Neighbors=Neighbors(beforeJson,0,new(){{id,before.Predicted.Tick+1}});var immunity=before.Replay(true);
                variants.Add(new { RiderId=id,WithoutThatRider=Compact(excluded),WithSyntheticImmunity=Compact(immunity),
                    ExclusionEqualsAfter=Same(excluded,newReplay),SyntheticImmunityEqualsAfter=Same(immunity,newReplay) });
            }
            var observed=new Dictionary<int,long>();var observedRows=new List<object>();
            if(episode.TryGetProperty("PeerAuthorities",out var peers))
            foreach(var peer in peers.EnumerateArray())
            {
                var authority=peer.GetProperty("State").Deserialize<RiderCheckpointData>(Options);
                observedRows.Add(new { authority.Id,authority.Tick,authority.CollisionUntilTick,Mode=authority.Mode.ToString(),authority.ModeAgeTicks,authority.RecoveryTicks });
                // An authority observation at most one snapshot away may prove
                // an already active immunity interval, but never fabricate it.
                if(Math.Abs(authority.Tick-before.Authority.Tick)<=6 && authority.CollisionUntilTick>before.Authority.Tick)
                    observed[authority.Id]=authority.CollisionUntilTick;
            }
            before.Neighbors=Neighbors(beforeJson,0,observed);var corrected=before.Replay(true);
            rows.Add(new { Peer=episode.GetProperty("Peer").GetInt32(),At=episode.GetProperty("At").GetDouble(),
                Delta=episode.GetProperty("Delta").GetDouble(),BeforeTick=before.Authority.Tick,AfterTick=after.Authority.Tick,TargetTick=before.Predicted.Tick,
                OldReplayVerified=oldMatch,NewReplayVerified=newMatch,Before=Compact(oldReplay),After=Compact(newReplay),variants,
                ObservedPeerAuthorities=observedRows,ObservedImmunityOverrideCount=observed.Count,WithObservedImmunity=Compact(corrected),ObservedImmunityEqualsAfter=Same(corrected,newReplay) });
        }
        var report=new {schema=1,passed,trace=Path.GetFullPath(args[1]),traceSha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[1]))).ToLowerInvariant(),
            scope="Deterministic replay of recorded state with unchanged production RiderPredictor. Exclusion/synthetic-immunity variants are diagnostics only; observed-immunity variant uses other controlled peers' actual server checkpoints within6ticks. No production behavior was changed.",episodes=rows};
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[2]))!);File.WriteAllText(args[2],JsonSerializer.Serialize(report,Options));
        Console.WriteLine($"REPLAY {(passed?"PASS":"FAIL")} {rows.Count} exact before/after outlier checkpoints.");return passed?0:1;
    }
    private static CorrectionState Read(JsonElement value){var state=value.Deserialize<CorrectionState>(Options)!;state.Neighbors=Neighbors(value,0,null);return state;}
    private static bool Same(RiderCheckpointData a,RiderCheckpointData b)=>JsonSerializer.Serialize(a,Options)==JsonSerializer.Serialize(b,Options);
    private static object Compact(RiderCheckpointData d)=>new{d.Tick,Mode=d.Mode.ToString(),d.ModeAgeTicks,d.DistanceMillimeters,d.LateralMillimeters,d.HeightMillimeters,d.SpeedMillimetersPerSecond,d.Health,d.BikeCondition,d.CollisionUntilTick,d.RecoveryTicks};
    private static PredictionNeighbors Neighbors(JsonElement state,int exclude,Dictionary<int,long> immunity)
    {
        var n=new PredictionNeighbors();
        foreach(var row in state.GetProperty("Riders").EnumerateArray())
        {
            var d=row.GetProperty("State").Deserialize<RiderCheckpointData>(Options);if(d.Id==exclude)continue;
            if(immunity?.TryGetValue(d.Id,out long until)==true)d.CollisionUntilTick=until;
            int i=n.RiderCount++;RiderCheckpoints.Restore(n.Riders[i],new RiderCheckpoint(d));
            n.Acceleration[i]=row.GetProperty("Acceleration").GetInt32();n.LateralVelocity[i]=row.GetProperty("LateralVelocity").GetInt32();n.VerticalVelocity[i]=row.GetProperty("VerticalVelocity").GetInt32();
        }
        foreach(var r in state.GetProperty("Traffic").EnumerateArray())
        {
            var t=n.Traffic[n.TrafficCount++];t.Id=Int(r,"Id");t.Active=true;t.DistanceMillimeters=Long(r,"DistanceMillimeters");t.LateralMillimeters=Int(r,"LateralMillimeters");t.SpeedMillimetersPerSecond=Int(r,"SpeedMillimetersPerSecond");t.WidthMillimeters=Int(r,"WidthMillimeters");t.LengthMillimeters=Int(r,"LengthMillimeters");t.HeightMillimeters=Int(r,"HeightMillimeters");t.Oncoming=r.TryGetProperty("Oncoming",out var oncoming)?oncoming.GetBoolean():t.SpeedMillimetersPerSecond<0;
        }
        foreach(var r in state.GetProperty("Pedestrians").EnumerateArray())
        {
            var p=n.Pedestrians[n.PedestrianCount++];p.Id=Int(r,"Id");p.DistanceMillimeters=Long(r,"DistanceMillimeters");p.LateralMillimeters=Int(r,"LateralMillimeters");p.HeightMillimeters=Int(r,"HeightMillimeters");p.Mode=(PedestrianMode)Int(r,"Mode");p.ModeAgeTicks=Int(r,"ModeAgeTicks");p.FacingSide=Int(r,"FacingSide");p.IsCrossing=r.GetProperty("IsCrossing").GetBoolean();p.WalkingSpeedMillimetersPerSecond=Int(r,"WalkingSpeedMillimetersPerSecond");
            if(!r.TryGetProperty("PredictionContext",out var context))throw new InvalidOperationException("Recorded trace predates explicit pedestrian prediction context; use its original source-bound replay, not invented timing.");
            PedestrianCheckpoints.RestorePredictionContext(p,new PedestrianPredictionContext(Int(context,"WaitTicks"),Int(context,"DesiredWalkingSpeed"),Int(context,"MotionRemainder")));
        }
        return n;
    }
    private static int Int(JsonElement e,string p)=>e.TryGetProperty(p,out var v)?v.GetInt32():0;
    private static long Long(JsonElement e,string p)=>e.TryGetProperty(p,out var v)?v.GetInt64():0;
    private sealed class InputConverter:JsonConverter<RaceInput>
    {
        public override RaceInput Read(ref Utf8JsonReader reader,Type type,JsonSerializerOptions options)
        {using var d=JsonDocument.ParseValue(ref reader);var r=d.RootElement;return new RaceInput(Int(r,"ThrottlePermille"),Int(r,"BrakePermille"),Int(r,"SteerPermille"),Int(r,"AttackSide"),r.TryGetProperty("Kick",out var k)&&k.GetBoolean());}
        public override void Write(Utf8JsonWriter w,RaceInput r,JsonSerializerOptions options)
        {w.WriteStartObject();w.WriteNumber("ThrottlePermille",r.ThrottlePermille);w.WriteNumber("BrakePermille",r.BrakePermille);w.WriteNumber("SteerPermille",r.SteerPermille);w.WriteNumber("AttackSide",r.AttackSide);w.WriteBoolean("Kick",r.Kick);w.WriteEndObject();}
    }
}
