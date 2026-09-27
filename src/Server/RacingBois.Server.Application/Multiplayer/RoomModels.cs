using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Server.Application.Multiplayer;

internal sealed class SessionLease
{
    public string Id = Guid.NewGuid().ToString("N"), ResumeToken = RealmStore.Capability(), ConnectionId = "", ProfileId = "", Name = "", RoomId = "";
    public string IssuedProfileToken = "";
    // Private capability for revocation checks; never mapped into lobby or telemetry.
    public string ProfileCredential = "";
    public bool Guest, Connected, ReplayReset;
    public int Epoch = 1, Credits, LastRequestId;
    public long DisconnectedAt, LastActivityTick, ReliableSequence, ReliableAck;
    public readonly Queue<(long Sequence, byte[] Bytes)> History = new();
    public int HistoryBytes;
    public readonly Queue<int> AcceptedRequests = new();
    public readonly HashSet<int> PendingRequests = new();
}
internal sealed class RoomMember(SessionLease session, int riderId, int order)
{
    public SessionLease Session { get; } = session;
    public int RiderId { get; } = riderId;
    public int JoinOrder { get; } = order;
    public bool Ready;
    public InputTimeline Timeline = new();
    public string BikeId = "";
    public int CharacterCatalogIndex;
    public int BikeCondition = 100;
}
internal sealed class Participant(RoomMember member)
{
    public RoomMember Member { get; } = member;
    public MultiplayerOutcome Outcome;
    public int Rank, Reward;
    public int BikeCondition = member.BikeCondition;
    public bool Qualified;
    public long FinishTick = -1;
}
internal sealed class GameRoom
{
    public string Id = Guid.NewGuid().ToString("N"), Code = "", Name = "", HostSessionId = "", MatchId = "";
    public int BotCount, Revision = 1, RaceEpoch, NextJoinOrder;
    public int CourseIndex, LevelIndex;
    public bool PublicRoom = true;
    public long StartServiceTick;
    public MultiplayerRoomState State;
    public readonly List<RoomMember> Members = new();
    public readonly List<Participant> Participants = new();
    public GameplayWorld? World;
    public RealmResult? Result;
    public string PendingAbort = "";
    public long PersistenceRetryAt;
    public bool PersistenceErrorReported;
    public bool StartPending, AbortWritePending, ResultWritePending;
    public void Prepare(string matchId, long serviceTick)
    {
        PersistenceRetryAt = 0; PersistenceErrorReported = false;
        MatchId = matchId; RaceEpoch++; StartServiceTick = serviceTick + MultiplayerProtocol.CountdownTicks;
        World = RaceSimulation.CreateDefault(1996 + RaceEpoch, BotCount, LevelIndex, CourseIndex); Participants.Clear(); Result = null;
        foreach (var member in Members.OrderBy(member => member.RiderId))
        {
            member.Timeline = new InputTimeline();
            var rider = RaceSimulation.AddPlayer(World, member.RiderId, member.RiderId - 1);
            if (rider != null)
            {
                rider.BikeCondition = member.BikeCondition;
                rider.BikeCatalogIndex = BikeCatalog.TryGet(member.BikeId, out var bike) ? bike.CatalogIndex : 0;
                rider.CharacterCatalogIndex = member.CharacterCatalogIndex;
            }
            Participants.Add(new Participant(member));
        }
        State = MultiplayerRoomState.Countdown; Revision++;
    }
    public void Step()
    {
        if (World == null) return;
        foreach (var participant in Participants)
        {
            if (participant.Outcome != MultiplayerOutcome.Racing) continue;
            var member = participant.Member;
            RaceSimulation.SetInput(World, member.RiderId, member.Session.Connected ? member.Timeline.Sample(World.Tick + 1) : default);
        }
        RaceSimulation.Step(World);
        foreach (var participant in Participants)
        {
            if (participant.Outcome != MultiplayerOutcome.Racing) continue;
            var rider = RaceSimulation.FindRider(World, participant.Member.RiderId);
            if (rider == null) { participant.Outcome = MultiplayerOutcome.Dnf; continue; }
            if (rider.Mode == RiderMode.Finished) participant.Outcome = MultiplayerOutcome.Finished;
            else if (rider.Mode == RiderMode.Busted) participant.Outcome = MultiplayerOutcome.Busted;
            else if (rider.Mode == RiderMode.Wrecked) participant.Outcome = MultiplayerOutcome.Wrecked;
            else if (World.Tick >= 36000) participant.Outcome = MultiplayerOutcome.Dnf;
            if (participant.Outcome != MultiplayerOutcome.Racing)
            {
                participant.Rank = rider.Rank;
                participant.Reward = participant.Outcome is MultiplayerOutcome.Finished or MultiplayerOutcome.Busted ? rider.Reward : 0;
                participant.FinishTick = rider.FinishTick;
                participant.BikeCondition = rider.BikeCondition;
                participant.Qualified = participant.Outcome == MultiplayerOutcome.Finished && rider.Rank is >= 1 and <= 3;
            }
        }
    }
    public bool Complete => Participants.Count > 0 && Participants.All(participant => participant.Outcome != MultiplayerOutcome.Racing);
    public void MarkDnf(RoomMember member)
    {
        var participant = Participants.FirstOrDefault(item => item.Member == member);
        if (participant != null && participant.Outcome == MultiplayerOutcome.Racing)
        {
            participant.Outcome = MultiplayerOutcome.Dnf; participant.Reward = 0;
            if (World != null) participant.BikeCondition = RaceSimulation.FindRider(World, member.RiderId)?.BikeCondition ?? member.BikeCondition;
        }
        if (World != null) RaceSimulation.RemovePlayer(World, member.RiderId);
    }
}
