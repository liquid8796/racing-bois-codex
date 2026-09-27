using System.Diagnostics;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Protocol;
using RacingBois.Simulation;
using RacingBois.Gameplay.Definitions;

internal sealed class CorrectionTrace(ProbeClock clock)
{
    private readonly Dictionary<MultiplayerSession,Peer> peers=new();
    private readonly List<Episode> episodes=new();
    private readonly Dictionary<string,Group> groups=new();
    private readonly double[] thresholds=[.001,.01,.1,.25,.5,1,2,4,8,16,32,double.MaxValue];
    private readonly long[] histogram=new long[12];
    private long accepted, unequalTarget, replayMismatches; private double maximum, observerMilliseconds;
    private static readonly JsonSerializerOptions Json=new(){IncludeFields=true};
    public void Attach(int index,Participant p)
    {
        var peer=new Peer(index,p);peers.Add(p.Session,peer);
        p.Transport.BeforeDispatch=text=>Before(peer,text);
        p.Transport.AfterDispatch=text=>After(peer,text);
    }
    private void Before(Peer p,string text)
    {
        p.Before=null;
        using var d=JsonDocument.Parse(text);
        if(d.RootElement.GetProperty("kind").GetString()!="mpSnapshot")return;
        p.WireTick=d.RootElement.GetProperty("tick").GetInt64();
        p.Terminal=d.RootElement.GetProperty("resultsPending").GetBoolean();
        long began=Stopwatch.GetTimestamp();p.Before=p.Participant.Session.AuditCapture();
        observerMilliseconds+=Stopwatch.GetElapsedTime(began).TotalMilliseconds;
    }
    private void After(Peer p,string text)
    {
        var before=p.Before;if(before==null)return;
        long began=Stopwatch.GetTimestamp();
        var after=p.Participant.Session.AuditCapture();p.Before=null;
        p.LastState=after;
        bool applied=before.HasCheckpoint && after.Authority.Tick==p.WireTick && after.Authority.Tick>before.Authority.Tick && before.RaceEpoch==after.RaceEpoch && before.SessionEpoch==after.SessionEpoch;
        if(!applied)return;
        bool terminal=p.Terminal || GameplayRules.IsTerminal(after.Authority.Mode);
        long comparedOldTick=terminal?before.Authority.Tick:before.Predicted.Tick;
        if(comparedOldTick!=after.Predicted.Tick){unequalTarget++;return;}
        accepted++;double delta=AuditPose.Delta(before.RawPose,after.RawPose);maximum=Math.Max(maximum,delta);
        for(int i=0;i<thresholds.Length;i++)if(delta<=thresholds[i]){histogram[i]++;break;}
        string modes=before.Predicted.Mode+" -> "+after.Predicted.Mode;
        if(!groups.TryGetValue(modes,out var group))groups[modes]=group=new();
        group.Count++;group.Maximum=Math.Max(group.Maximum,delta);if(delta>=1)group.Outliers++;
        foreach(var e in episodes.Where(e=>e.Peer==p.Index && e.AfterWindow.Count<8 && e.At<after.At))e.AfterWindow.Add(after.Compact());
        bool choose=delta>=1 && (delta>p.Maximum || after.At-p.LastEpisodeAt>.5);
        p.Maximum=Math.Max(p.Maximum,delta);
        if(choose)
        {
            var oldReplay=before.Replay(true);var newReplay=after.Replay(true);
            bool oldMatch=JsonSerializer.Serialize(oldReplay,Json)==JsonSerializer.Serialize(before.Predicted,Json);
            bool newMatch=JsonSerializer.Serialize(newReplay,Json)==JsonSerializer.Serialize(after.Predicted,Json);
            if(!oldMatch||!newMatch)replayMismatches++;
            var oldNo=before.Replay(false);var newNo=after.Replay(false);
            var e=new Episode {Peer=p.Index,At=after.At,Delta=delta,ReportedDelta=after.Correction,Before=before,After=after,
                BeforeWindow=p.History.ToArray(),PresentedBefore=p.LastPresented,OldReplayVerified=oldMatch,NewReplayVerified=newMatch,
                PeerAuthorities=peers.Values.Where(other=>other.LastState!=null && other.LastState.RaceEpoch==before.RaceEpoch).Select(other=>new { Peer=other.Index,SampleAt=other.LastState.At,State=other.LastState.Authority }).Cast<object>().ToArray(),
                OldWithoutNeighbors=oldNo,NewWithoutNeighbors=newNo,
                NoNeighborDelta=Math.Sqrt(Math.Pow((oldNo.DistanceMillimeters-newNo.DistanceMillimeters)/1000d,2)+Math.Pow((oldNo.LateralMillimeters-newNo.LateralMillimeters)/1000d,2))};
            if(episodes.Count>=64){var lowest=episodes.MinBy(e=>e.Delta);if(delta>lowest.Delta)episodes.Remove(lowest);else e=null;}
            if(e!=null){episodes.Add(e);p.LastEpisodeAt=after.At;}
        }
        while(p.History.Count>=8)p.History.Dequeue();p.History.Enqueue(after.Compact());
        observerMilliseconds+=Stopwatch.GetElapsedTime(began).TotalMilliseconds;
    }
    public void Presented(MultiplayerSession session)
    {
        if(!peers.TryGetValue(session,out var p))return;
        // Called only after the driver's existing SamplePresentation call; no
        // extra presentation sample changes controller inputs/caches/probes.
        var pose=AuditPose.From(session.LocalRider);
        var sample=new PresentationSample(clock.NowSeconds,session.LastResolvedTick,pose,session.PresentationFrozen);
        foreach(var e in episodes.Where(e=>e.Peer==p.Index && e.PresentedAfter==null && sample.At>=e.At))
        {e.PresentedAfter=sample;if(e.PresentedBefore!=null)e.PresentedDelta=AuditPose.Delta(e.PresentedBefore.Pose,sample.Pose);}
        p.LastPresented=sample;
    }
    public object Report()=>new { acceptedEqualTargetSnapshots=accepted,ignoredUnequalTargets=unequalTarget,maximumCorrection=maximum,replayMismatches,
        observerMilliseconds,histogram=thresholds.Select((upper,i)=>new{upper=upper==double.MaxValue?"overflow":upper.ToString(System.Globalization.CultureInfo.InvariantCulture),count=histogram[i]}),
        modes=groups.Select(g=>new{modePair=g.Key,g.Value.Count,g.Value.Outliers,g.Value.Maximum}),
        episodes=episodes.OrderByDescending(e=>e.Delta).ToArray(),
        scope="Read-only before/after snapshot observation; exact replay verification and without-neighbor counterfactual on isolated new predictors; presented deltas are existing SamplePresentation outputs, not Unity render frames. Top64 bounded outlier windows; no credentials or raw wire frames." };
    private sealed class Group {public long Count,Outliers;public double Maximum;}
    private sealed class Peer(int index,Participant p)
    {public int Index=index;public Participant Participant=p;public CorrectionState Before,LastState;public long WireTick;public bool Terminal;public double Maximum,LastEpisodeAt=-100;public Queue<object> History=new();public PresentationSample LastPresented;}
    private sealed class Episode
    {
        public int Peer;public double At,Delta,ReportedDelta,NoNeighborDelta;public double? PresentedDelta;
        public bool OldReplayVerified,NewReplayVerified;public CorrectionState Before,After;
        public object[] BeforeWindow,PeerAuthorities;public List<object> AfterWindow=new();
        public RiderCheckpointData OldWithoutNeighbors,NewWithoutNeighbors;
        public PresentationSample PresentedBefore,PresentedAfter;
    }
    private sealed record PresentationSample(double At,long AuthorityTick,AuditPose Pose,bool Frozen);
}
