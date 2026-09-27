// Compiled only by CorrectionAudit.csproj. Reads private state; never changes it.
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
using RacingBois.Protocol;
using System.Text.Json.Serialization;

namespace RacingBois.Client.Application;

public sealed partial class MultiplayerSession
{
    internal CorrectionState AuditCapture()
    {
        var d = predictor?.Checkpoint.Data ?? default;
        var neighborCopy = CopyAuditNeighbors();
        return new CorrectionState
        {
            At = clock.NowSeconds, HasCheckpoint = hasCheckpoint, Authority = authoritative.Data, Predicted = d,
            RawPose = AuditPose.From(predictedRider), LocalPose = AuditPose.From(LocalRider),
            CachedPose = cachedPresentation == null ? null : AuditPose.From(RemoteMotionSampler.Find(cachedPresentation.Riders, RiderId)),
            CachedTick = cachedPresentation?.Tick ?? -1, LastTargetTick = lastTargetTick,
            Course = Room?.CourseIndex ?? 0, Level = Room?.LevelIndex ?? 0,
            RaceEpoch = raceEpoch, SessionEpoch = sessionEpoch, RiderId = RiderId, Phase = Room?.Phase.ToString() ?? "none",
            SnapshotAge = clock.NowSeconds - lastSnapshotAt, RttMs = RttMs, LeadTicks = InputLeadTicks,
            Correction = LastCorrectionMeters, MaximumCorrection = MaximumCorrectionMeters,
            SmoothingS = correctionS, SmoothingD = correctionD, SmoothingRemaining = Math.Max(0, 1 - (clock.NowSeconds-correctionAt)/.12),
            Frozen = PresentationFrozen, PredictionEnabled = PredictionEnabled, HeldAnalog = heldAnalog, LastAppliedTick = lastAppliedInputTick,
            Pending = pending.Select(f => new AuditInput(f.Tick, f.Sequence, f.Input)).ToArray(),
            Events = events.Where(e => e.Tick >= authoritative.Tick - 40).Select(e => new { e.Tick, Kind=e.Kind.ToString(), e.SourceId, e.TargetId, e.Value }).Cast<object>().ToArray(),
            Riders = Enumerable.Range(0, predictionNeighbors.RiderCount).Select(i => new
            {
                State = RiderCheckpoints.Capture(predictionNeighbors.Riders[i], authoritative.Tick).Data,
                Acceleration = predictionNeighbors.Acceleration[i], LateralVelocity = predictionNeighbors.LateralVelocity[i], VerticalVelocity = predictionNeighbors.VerticalVelocity[i]
            }).Cast<object>().ToArray(),
            Traffic = Enumerable.Range(0, predictionNeighbors.TrafficCount).Select(i => { var t=predictionNeighbors.Traffic[i]; return new { t.Id,t.DistanceMillimeters,t.LateralMillimeters,t.SpeedMillimetersPerSecond,t.WidthMillimeters,t.LengthMillimeters,t.HeightMillimeters }; }).Cast<object>().ToArray(),
            Pedestrians = Enumerable.Range(0,predictionNeighbors.PedestrianCount).Select(i=> { var p=predictionNeighbors.Pedestrians[i]; return new { p.Id,p.DistanceMillimeters,p.LateralMillimeters,p.Mode,p.ModeAgeTicks,p.IsCrossing,p.WalkingSpeedMillimetersPerSecond }; }).Cast<object>().ToArray(),
            Neighbors = neighborCopy
        };
    }
    private PredictionNeighbors CopyAuditNeighbors()
    {
        var n=new PredictionNeighbors { RiderCount=predictionNeighbors.RiderCount, TrafficCount=predictionNeighbors.TrafficCount, PedestrianCount=predictionNeighbors.PedestrianCount };
        for(int i=0;i<n.RiderCount;i++)
        { RiderCheckpoints.Restore(n.Riders[i],RiderCheckpoints.Capture(predictionNeighbors.Riders[i],authoritative.Tick)); n.Acceleration[i]=predictionNeighbors.Acceleration[i]; n.LateralVelocity[i]=predictionNeighbors.LateralVelocity[i]; n.VerticalVelocity[i]=predictionNeighbors.VerticalVelocity[i]; }
        for(int i=0;i<n.TrafficCount;i++)
        { var a=predictionNeighbors.Traffic[i];var b=n.Traffic[i];b.Id=a.Id;b.DistanceMillimeters=a.DistanceMillimeters;b.LateralMillimeters=a.LateralMillimeters;b.SpeedMillimetersPerSecond=a.SpeedMillimetersPerSecond;b.WidthMillimeters=a.WidthMillimeters;b.LengthMillimeters=a.LengthMillimeters;b.HeightMillimeters=a.HeightMillimeters;b.Oncoming=a.Oncoming;b.Active=a.Active; }
        for(int i=0;i<n.PedestrianCount;i++)
        { var a=predictionNeighbors.Pedestrians[i];var b=n.Pedestrians[i];b.Id=a.Id;b.DistanceMillimeters=a.DistanceMillimeters;b.LateralMillimeters=a.LateralMillimeters;b.HeightMillimeters=a.HeightMillimeters;b.Mode=a.Mode;b.ModeAgeTicks=a.ModeAgeTicks;b.IsCrossing=a.IsCrossing;b.FacingSide=a.FacingSide;b.WalkingSpeedMillimetersPerSecond=a.WalkingSpeedMillimetersPerSecond; }
        return n;
    }
}

internal sealed class CorrectionState
{
    public double At, SnapshotAge, RttMs, SmoothingRemaining;
    public bool HasCheckpoint,Frozen,PredictionEnabled;
    public int Course,Level,RaceEpoch,SessionEpoch,RiderId,LeadTicks;
    public string Phase;
    public long CachedTick,LastTargetTick,LastAppliedTick;
    public float Correction,MaximumCorrection,SmoothingS,SmoothingD;
    public RiderCheckpointData Authority,Predicted;
    public RaceInput HeldAnalog;
    public AuditPose RawPose,LocalPose,CachedPose;
    public AuditInput[] Pending;
    public object[] Events,Riders,Traffic,Pedestrians;
    [JsonIgnore] public PredictionNeighbors Neighbors;
    public object Compact() => new { At, AuthorityTick=Authority.Tick, PredictedTick=Predicted.Tick, Mode=Predicted.Mode.ToString(),Predicted.ModeAgeTicks,Predicted.RecoveryTicks,Predicted.CollisionUntilTick,RawPose,Correction,RaceEpoch,SessionEpoch,Pending=Pending.Length,SnapshotAge,RttMs,LeadTicks,Frozen };
    public RiderCheckpointData Replay(bool withNeighbors)
    {
        var p=new RiderPredictor(Level,Course); if(withNeighbors)p.SetNeighbors(Neighbors);
        p.Restore(new RiderCheckpoint(Authority)); long target=Pending.Length==0?Authority.Tick:Pending[^1].Tick;
        int index=0;var analog=HeldAnalog;long applied=LastAppliedTick;
        for(long tick=Authority.Tick+1;tick<=target;tick++)
        {
            RaceInput input;
            if(index<Pending.Length && Pending[index].Tick==tick) { input=Pending[index++].Input; analog=new RaceInput(input.ThrottlePermille,input.BrakePermille,input.SteerPermille);applied=tick; }
            else input=applied>=0 && tick-applied<=MultiplayerProtocol.AnalogHoldTicks?analog:default;
            p.Advance(tick,input);
        }
        return p.Checkpoint.Data;
    }
}
internal sealed record AuditInput(long Tick,int Sequence,RaceInput Input);
internal sealed record AuditPose(float S,float D,float H,float Speed,string Mode,int ModeAge,float BikeS,float BikeD)
{
    public static AuditPose From(RaceRiderReadModel r)=>new(r.LongitudinalMeters,r.LateralMeters,r.HeightMeters,r.SpeedMetersPerSecond,r.Mode.ToString(),r.ModeAgeTicks,r.BikeLongitudinalMeters,r.BikeLateralMeters);
    public static double Delta(AuditPose a,AuditPose b)=>Math.Sqrt((a.S-b.S)*(a.S-b.S)+(a.D-b.D)*(a.D-b.D));
}
