using System.Security.Cryptography;
using RacingBois.Protocol;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;

namespace RacingBois.Server.Application.Multiplayer;

public interface IMultiplayerSink
{
    bool Send(string connectionId, byte[] message, bool reliable);
    void Close(string connectionId, string reason);
}

/// <summary>Single-owner room/session application. Transport callbacks enqueue typed messages into its owner.</summary>
public sealed class MultiplayerService : IDisposable
{
    private readonly RealmStore realm;
    private readonly IMultiplayerSink sink;
    private readonly Func<object, byte[]> encode;
    private readonly IRealmPersistence persistence;
    private interface ICompletion { bool Ready { get; } void Apply(); }
    private sealed class Completion<T>(Task<T> task, Action<T> success, Action<Exception> failed) : ICompletion
    {
        public bool Ready => task.IsCompleted;
        public void Apply() { if (task.IsCompletedSuccessfully) success(task.Result); else failed(task.Exception?.GetBaseException() ?? new TaskCanceledException()); }
    }
    private sealed class PendingProfile(string connectionId, MpHello hello, string intent)
    { public string ConnectionId = connectionId; public MpHello Hello = hello; public string Intent = intent; public bool Closed; }
    private readonly List<ICompletion> completions = new();
    private readonly Dictionary<string, PendingProfile> pendingProfiles = new(StringComparer.Ordinal);
    private readonly Dictionary<string, (RealmProfile Profile, string Token)> preparedProfiles = new(StringComparer.Ordinal);
    private readonly Dictionary<string, SessionLease> sessions = new(StringComparer.Ordinal);
    private readonly Dictionary<string, SessionLease> connections = new(StringComparer.Ordinal);
    private readonly Dictionary<string, SessionLease> resume = new(StringComparer.Ordinal);
    private readonly Dictionary<string, (string Intent, SessionLease Lease, long Expires)> hellos = new(StringComparer.Ordinal);
    private readonly Dictionary<string, GameRoom> rooms = new(StringComparer.Ordinal);
    private readonly Dictionary<string, Queue<long>> controlWindows = new(StringComparer.Ordinal);
    public long ServiceTick { get; private set; }
    public int RoomCount => rooms.Count;
    public int SessionCount => sessions.Count;
    public int HelloCacheCount => hellos.Count;
    public int PendingStorageCount => completions.Count;
    public long RejectedInputs { get; private set; }
    public long SnapshotBytes { get; private set; }
    public long PersistenceFailures { get; private set; }
    public string RealmId => realm.RealmId;

    public MultiplayerService(RealmStore realm, IMultiplayerSink sink, Func<object, byte[]> encode, IRealmPersistence? persistence = null)
    { this.realm = realm; this.sink = sink; this.encode = encode; this.persistence = persistence ?? new RealmPersistence(realm); }
    public void PollPersistence()
    {
        for (int i = completions.Count - 1; i >= 0; i--)
        {
            var completion = completions[i]; if (!completion.Ready) continue;
            completions.RemoveAt(i); completion.Apply();
        }
    }
    private void Schedule<T>(Func<Task<T>> request, Action<T> success, Action<Exception> failed)
    {
        if (completions.Count >= 128) { failed(new InvalidOperationException("persistence_queue_full")); return; }
        completions.Add(new Completion<T>(request(), success, failed));
    }
    public void Dispose() => persistence.Dispose();

    public void Handle(string connectionId, object message)
    {
        if (message is MpHello hello) { Attach(connectionId, hello); return; }
        if (!connections.TryGetValue(connectionId, out var session)) { RawError(connectionId, "session_required"); return; }
        if (!CredentialActive(session)) { Revoke(session); return; }
        int epoch = message switch { MpCommand command => command.sessionEpoch, MpInput input => input.sessionEpoch, MpPing ping => ping.sessionEpoch, MpAck ack => ack.sessionEpoch, _ => -1 };
        int version = message switch { MpCommand command => command.protocolVersion, MpInput input => input.protocolVersion, MpPing ping => ping.protocolVersion, MpAck ack => ack.protocolVersion, _ => -1 };
        if (epoch != session.Epoch || version != MultiplayerProtocol.Version) { Error(session, "session_epoch", 0, true); return; }
        session.LastActivityTick = ServiceTick;
        switch (message)
        {
            case MpInput input: Input(session, input); break;
            case MpAck ack: Acknowledge(session, ack.reliableSequence); break;
            case MpPing ping:
                if (!Acknowledge(session, ping.reliableAck) || ping.nonce == null || ping.nonce.Length > 64) break;
                rooms.TryGetValue(session.RoomId, out var current);
                SendRaw(session.ConnectionId, new MpPong { sessionEpoch = session.Epoch, nonce = ping.nonce,
                    clientMicroseconds = ping.clientMicroseconds, serverServiceTick = ServiceTick,
                    roomTick = current?.World?.Tick ?? 0, raceEpoch = current?.RaceEpoch ?? 0 }, true); break;
            case MpCommand command: Command(session, command); break;
            default: Error(session, "unknown_message", 0, true); break;
        }
    }
    private void Attach(string connectionId, MpHello hello)
    {
        if (connections.ContainsKey(connectionId)) { RawError(connectionId, "already_attached"); return; }
        if (hello.protocolVersion != MultiplayerProtocol.Version || hello.simulationRulesVersion != MultiplayerProtocol.RulesVersion || hello.contentHash != MultiplayerProtocol.ContentHash)
        { RawError(connectionId, "version_mismatch"); return; }
        if (hello.requestNonce == null || hello.requestNonce.Length != 32 || hello.requestNonce.Any(character => !Uri.IsHexDigit(character)) ||
            hello.resumeToken == null || hello.profileToken == null || hello.resumeToken.Length > 64 || hello.profileToken.Length > 64 || hello.lastReliableSequence < 0)
        { RawError(connectionId, "invalid_hello"); return; }
        string name;
        try { name = DisplayName(hello.displayName); } catch (ArgumentException) { RawError(connectionId, "invalid_name"); return; }
        string nonce = RealmStore.Hash(hello.requestNonce);
        string intent = RealmStore.Hash(name + "\0" + hello.freshGuest + "\0" + hello.profileToken + "\0" + hello.resumeToken);
        var pendingConnection = pendingProfiles.FirstOrDefault(pair => pair.Value.ConnectionId == connectionId);
        if (pendingConnection.Value != null && pendingConnection.Key != nonce)
        { pendingConnection.Value.Closed = true; RawError(connectionId, "handshake_pending_conflict"); return; }
        if (pendingProfiles.TryGetValue(nonce, out var pendingProfile))
        {
            if (pendingProfile.Intent != intent || hello.lastReliableSequence != 0) { RawError(connectionId, "hello_nonce_conflict"); return; }
            string previous = pendingProfile.ConnectionId; pendingProfile.ConnectionId = connectionId; pendingProfile.Hello = hello; pendingProfile.Closed = false;
            if (previous != connectionId) sink.Close(previous, "handshake_replaced");
            return;
        }
        SessionLease session; bool resumed = false; string profileToken = "";
        if (hello.resumeToken.Length > 0)
        {
            if (!resume.TryGetValue(RealmStore.Hash(hello.resumeToken), out session!) ||
                (!session.Connected && ServiceTick - session.DisconnectedAt >= MultiplayerProtocol.ResumeGraceTicks))
            { RawError(connectionId, "resume_expired"); return; }
            if (!CredentialActive(session)) { Revoke(session); RawError(connectionId, "profile_unavailable"); return; }
            if (hello.profileToken.Length > 0 && realm.Authenticate(hello.profileToken)?.Id != session.ProfileId)
            { RawError(connectionId, "resume_owner"); return; }
            resumed = true;
        }
        else if (hellos.TryGetValue(nonce, out var attempt) && attempt.Expires > ServiceTick)
        {
            if (attempt.Intent != intent) { RawError(connectionId, "hello_nonce_conflict"); return; }
            if (!sessions.ContainsKey(attempt.Lease.Id)) { RawError(connectionId, "hello_nonce_revoked"); return; }
            session = attempt.Lease; resumed = true; profileToken = session.IssuedProfileToken;
        }
        else
        {
            if (hello.lastReliableSequence != 0) { RawError(connectionId, "future_ack"); return; }
            if (hellos.Count + pendingProfiles.Count >= 256) { RawError(connectionId, "hello_capacity"); return; }
            if (sessions.Count + pendingProfiles.Count >= MultiplayerProtocol.MaxPeers) { RawError(connectionId, "server_full"); return; }
            session = new SessionLease { Name = name, Guest = hello.freshGuest, LastActivityTick = ServiceTick };
            if (hello.freshGuest)
            {
                if (hello.profileToken.Length > 0) { RawError(connectionId, "guest_profile_conflict"); return; }
                session.ProfileId = "guest-" + session.Id;
            }
            else
            {
                RealmProfile profile;
                if (hello.profileToken.Length > 0)
                {
                    var existing = realm.Authenticate(hello.profileToken);
                    if (existing == null) { RawError(connectionId, "profile_unavailable"); return; }
                    profile = existing;
                }
                else
                {
                    if (preparedProfiles.TryGetValue(nonce, out var prepared)) { profile = prepared.Profile; profileToken = prepared.Token; }
                    else
                    {
                        var pending = new PendingProfile(connectionId, hello, intent); pendingProfiles.Add(nonce, pending);
                        Schedule(() => persistence.CreateProfile(name), created =>
                        {
                            pendingProfiles.Remove(nonce); preparedProfiles.Add(nonce, created);
                            try { Attach(pending.ConnectionId, pending.Hello); if (pending.Closed) Disconnect(pending.ConnectionId); }
                            finally { preparedProfiles.Remove(nonce); }
                        }, error =>
                        {
                            pendingProfiles.Remove(nonce); PersistenceFailures++;
                            if (!pending.Closed) RawError(pending.ConnectionId, error.Message == "profile_capacity" ? "profile_capacity" : "profile_storage_unavailable");
                        });
                        return;
                    }
                }
                session.ProfileId = profile.Id; session.Name = profile.Name; session.Credits = profile.Credits;
                session.ProfileCredential = profileToken.Length > 0 ? profileToken : hello.profileToken;
            }
            session.IssuedProfileToken = profileToken;
            sessions.Add(session.Id, session); resume.Add(RealmStore.Hash(session.ResumeToken), session);
            hellos[nonce] = (intent, session, ServiceTick + MultiplayerProtocol.ResumeGraceTicks);
        }
        if (!CredentialActive(session)) { Revoke(session); RawError(connectionId, "profile_unavailable"); return; }
        if (hello.lastReliableSequence > session.ReliableSequence) { RawError(connectionId, "future_ack"); return; }
        if (resumed)
        {
            if (session.ConnectionId.Length > 0)
            { string old = session.ConnectionId; connections.Remove(old); sink.Close(old, "session_replaced"); }
            session.Epoch++; session.LastRequestId = 0; session.AcceptedRequests.Clear(); session.PendingRequests.Clear();
        }
        session.ConnectionId = connectionId; session.Connected = true; session.LastActivityTick = ServiceTick;
        if (!session.Guest) session.Credits = realm.Credits(session.ProfileId);
        connections.Add(connectionId, session);
        bool reset = !resumed || session.ReplayReset || (session.History.Count > 0 && hello.lastReliableSequence < session.History.Peek().Sequence - 1);
        SendRaw(connectionId, new MpWelcome
        {
            requestNonce = hello.requestNonce, sessionId = session.Id, sessionEpoch = session.Epoch, resumeToken = session.ResumeToken,
            profileToken = profileToken, profileId = session.ProfileId, displayName = session.Name, realmId = realm.RealmId,
            credits = session.Credits, guest = session.Guest, resumed = resumed, reliableReset = reset,
            reliableSequence = reset ? session.ReliableSequence : hello.lastReliableSequence, serverServiceTick = ServiceTick
        }, true);
        if (reset) { session.History.Clear(); session.HistoryBytes = 0; session.ReliableAck = session.ReliableSequence; session.ReplayReset = false; }
        else
        {
            Acknowledge(session, hello.lastReliableSequence);
            foreach (var frame in session.History) if (frame.Sequence > hello.lastReliableSequence) sink.Send(connectionId, frame.Bytes, true);
        }
        if (rooms.TryGetValue(session.RoomId, out var room))
        {
            var member = room.Members.Single(item => item.Session == session); member.Timeline.ResetEpoch();
            TransferHost(room); room.Revision++; BroadcastLobby(room); SendSnapshot(room, member);
            if (room.Result != null) Reliable(session, sequence => MultiplayerProjection.Result(room, sequence));
        }
        else SendRooms(session, 0);
    }
    public void Disconnect(string connectionId)
    {
        foreach (var pending in pendingProfiles.Values) if (pending.ConnectionId == connectionId) pending.Closed = true;
        if (!connections.Remove(connectionId, out var session) || session.ConnectionId != connectionId) return;
        session.Connected = false; session.ConnectionId = ""; session.DisconnectedAt = ServiceTick;
        if (rooms.TryGetValue(session.RoomId, out var room))
        {
            var member = room.Members.Single(item => item.Session == session); member.Ready = false; member.Timeline.Suspend();
            CancelCountdown(room); TransferHost(room); room.Revision++; BroadcastLobby(room);
        }
    }
    public void Step()
    {
        PollPersistence(); ServiceTick++;
        foreach (var key in hellos.Where(pair => pair.Value.Expires <= ServiceTick).Select(pair => pair.Key).ToArray()) hellos.Remove(key);
        foreach (var session in sessions.Values.ToArray())
        {
            if (ServiceTick % 60 == 0 && !CredentialActive(session)) { Revoke(session); continue; }
            if (session.Connected && ServiceTick - session.LastActivityTick > 1200)
            { string connection = session.ConnectionId; Disconnect(connection); sink.Close(connection, "heartbeat_timeout"); }
            if (!session.Connected && ServiceTick - session.DisconnectedAt >= MultiplayerProtocol.ResumeGraceTicks)
            {
                Leave(session); sessions.Remove(session.Id); resume.Remove(RealmStore.Hash(session.ResumeToken)); controlWindows.Remove(session.Id);
            }
        }
        foreach (var room in rooms.Values.ToArray())
        {
            if (room.PendingAbort.Length > 0) PersistAbort(room);
            if (room.State == MultiplayerRoomState.Countdown && ServiceTick >= room.StartServiceTick)
            { room.State = MultiplayerRoomState.Racing; room.Revision++; BroadcastLobby(room); }
            if (room.State == MultiplayerRoomState.Racing)
            {
                bool stepped = !room.Complete;
                if (stepped) room.Step(); var world = room.World!;
                if (stepped && world.EventCount > 0)
                {
                    var events = new RaceEventSnapshot[world.EventCount];
                    for (int i = 0; i < events.Length; i++) { var item = world.Events[i]; events[i] = new RaceEventSnapshot { id = item.Id, tick = item.Tick, kind = (int)item.Kind, sourceId = item.ActorId, targetId = item.TargetId, value = item.Value }; }
                    foreach (var member in room.Members) Reliable(member.Session, sequence => new MpEventBatch { roomId = room.Id, matchId = room.MatchId, raceEpoch = room.RaceEpoch, reliableSequence = sequence, events = events });
                }
                if (room.Complete) Complete(room);
            }
            if (ServiceTick % 3 == 0 && room.World != null)
                foreach (var member in room.Members) if (member.Session.Connected) SendSnapshot(room, member);
            if (room.Members.Count == 0)
            {
                if (room.MatchId.Length > 0 && room.Result == null) Complete(room);
                if (!room.StartPending && !room.ResultWritePending && room.PendingAbort.Length == 0 && (room.MatchId.Length == 0 || room.Result != null)) rooms.Remove(room.Id);
            }
        }
    }
    private void Command(SessionLease session, MpCommand command)
    {
        if (command.requestId <= 0 || command.requestId - (long)session.LastRequestId > 10000) { Error(session, "request_sequence", command.requestId); return; }
        if (session.PendingRequests.Contains(command.requestId)) return;
        if (session.AcceptedRequests.Contains(command.requestId)) { Accepted(session, command.requestId); return; }
        if (command.requestId <= session.LastRequestId) { Error(session, "request_stale", command.requestId); return; }
        if (!controlWindows.TryGetValue(session.Id, out var window)) { window = new Queue<long>(); controlWindows.Add(session.Id, window); }
        while (window.Count > 0 && window.Peek() <= ServiceTick - 60) window.Dequeue();
        if (window.Count >= 10) { Error(session, "command_rate", command.requestId); return; }
        window.Enqueue(ServiceTick); session.LastRequestId = command.requestId;
        string? error = command switch
        {
            MpCreateRoom create => Create(session, create), MpJoinRoom join => Join(session, join.code),
            MpSetReady ready => WithRoom(session, ready.roomId, room =>
            { if (room.State != MultiplayerRoomState.Lobby) return "room_started"; room.Members.Single(member => member.Session == session).Ready = ready.ready; room.Revision++; BroadcastLobby(room); return null; }),
            MpStartRace start => WithRoom(session, start.roomId, room => QueueStart(session, command.requestId, room)),
            MpLeaveRoom leave => WithRoom(session, leave.roomId, room => { Leave(session); return null; }),
            MpReturnToLobby back => WithRoom(session, back.roomId, room =>
            {
                if (room.HostSessionId != session.Id) return "host_only";
                if (room.State != MultiplayerRoomState.Results) return "result_required";
                room.State = MultiplayerRoomState.Lobby; room.World = null; room.Participants.Clear(); room.Result = null; room.MatchId = "";
                foreach (var member in room.Members) member.Ready = false;
                room.Revision++; BroadcastLobby(room); return null;
            }),
            MpListRooms => List(session, command.requestId),
            MpGoodbye => Goodbye(session), _ => "unknown_command"
        };
        if (error == "__pending") return;
        if (error != null) { Error(session, error, command.requestId); return; }
        session.AcceptedRequests.Enqueue(command.requestId); while (session.AcceptedRequests.Count > 64) session.AcceptedRequests.Dequeue(); Accepted(session, command.requestId);
        if (command is MpGoodbye)
        {
            string connection = session.ConnectionId;
            connections.Remove(connection); sessions.Remove(session.Id); resume.Remove(RealmStore.Hash(session.ResumeToken)); controlWindows.Remove(session.Id);
            session.Connected = false; session.ConnectionId = "";
            // The host drains its reliable FIFO before sending CloseOutput; the accepted command is first.
            sink.Close(connection, "logout");
        }
    }
    private string? QueueStart(SessionLease session, int requestId, GameRoom room)
    {
        if (room.HostSessionId != session.Id) return "host_only";
        if (room.State != MultiplayerRoomState.Lobby || room.Members.Count == 0 || room.Members.Any(member => !member.Ready || !member.Session.Connected)) return "not_ready";
        if (room.PendingAbort.Length > 0) return "persistence_pending";
        if (room.StartPending) return "start_pending";
        foreach (var member in room.Members)
        {
            string? eligibility = RaceEligibility(member.Session, room.LevelIndex);
            if (eligibility != null) return eligibility;
        }
        room.StartPending = true; session.PendingRequests.Add(requestId); int revision = room.Revision, epoch = session.Epoch;
        Schedule(() => persistence.BeginMatch(room.Members.Where(member => !member.Session.Guest).Select(member => member.Session.ProfileId).ToArray()), matchId =>
        {
            room.StartPending = false;
            if (session.Epoch == epoch) session.PendingRequests.Remove(requestId);
            if (!sessions.ContainsKey(session.Id) || !session.Connected || session.Epoch != epoch || room.Revision != revision ||
                room.State != MultiplayerRoomState.Lobby || room.HostSessionId != session.Id || room.Members.Any(member => !member.Ready || !member.Session.Connected))
            {
                room.PendingAbort = matchId; room.PersistenceRetryAt = 0; PersistAbort(room);
                if (session.Connected && session.Epoch == epoch) Error(session, "start_cancelled", requestId);
                return;
            }
            foreach (var member in room.Members)
            {
                string? eligibility = RaceEligibility(member.Session, room.LevelIndex);
                if (!CredentialActive(member.Session)) eligibility = "profile_revoked";
                if (eligibility != null)
                {
                    room.PendingAbort = matchId; room.PersistenceRetryAt = 0; PersistAbort(room);
                    if (session.Connected && session.Epoch == epoch) Error(session, eligibility, requestId);
                    return;
                }
                if (member.Session.Guest) continue;
                var career = realm.GetRaceConfiguration(member.Session.ProfileId);
                member.BikeId = career.selectedBikeId;
                member.CharacterCatalogIndex = CharacterCatalog.TryGet(career.selectedCharacterId, out var character) ? character.CatalogIndex : 0;
                member.BikeCondition = career.bikes.FirstOrDefault(bike => bike.bikeId == career.selectedBikeId)?.condition ?? 100;
            }
            room.Prepare(matchId, ServiceTick); BroadcastLobby(room); foreach (var member in room.Members) SendSnapshot(room, member);
            session.AcceptedRequests.Enqueue(requestId); while (session.AcceptedRequests.Count > 64) session.AcceptedRequests.Dequeue(); Accepted(session, requestId);
        }, error =>
        {
            room.StartPending = false; if (session.Epoch == epoch) session.PendingRequests.Remove(requestId); PersistenceFailures++;
            if (session.Connected && session.Epoch == epoch) Error(session, error.Message == "profile_busy" ? "profile_busy" : "persistence_unavailable", requestId);
        });
        return "__pending";
    }
    private string? Create(SessionLease session, MpCreateRoom create)
    {
        if (session.RoomId.Length > 0) return "already_in_room";
        if (rooms.Count >= MultiplayerProtocol.MaxRooms) return "room_capacity";
        if (create.botCount is < 0 or > 6 || create.name == null || create.name.Trim().Length is < 1 or > 40 || create.name.Any(character => char.IsControl(character) || character is '<' or '>')) return "room_settings";
        if (create.courseIndex is < 0 or >= CampaignCatalog.RouteCount || !CampaignCatalog.IsPlayableRoute(create.courseIndex)) return "course_unavailable";
        if (create.levelIndex is < 0 or >= CampaignCatalog.LevelCount) return "room_settings";
        string? eligibility = RaceEligibility(session, create.levelIndex);
        if (eligibility != null) return eligibility;
        string code; do { code = Code(); } while (rooms.Values.Any(room => room.Code == code));
        var room = new GameRoom { Code = code, Name = create.name.Trim(), BotCount = create.botCount, HostSessionId = session.Id,
            PublicRoom = create.publicRoom, CourseIndex = create.courseIndex, LevelIndex = create.levelIndex };
        rooms.Add(room.Id, room); AddMember(room, session); return null;
    }
    private string? Join(SessionLease session, string code)
    {
        if (session.RoomId.Length > 0) return "already_in_room";
        if (code == null || code.Trim().Length != 6) return "room_not_found";
        var room = rooms.Values.FirstOrDefault(room => room.Code == code.Trim().ToUpperInvariant());
        if (room == null) return "room_not_found";
        if (room.State != MultiplayerRoomState.Lobby) return "late_join_closed";
        if (room.Members.Count >= 8) return "room_full";
        if (room.Members.Any(member => member.Session.ProfileId == session.ProfileId)) return "profile_in_room";
        string? eligibility = RaceEligibility(session, room.LevelIndex);
        if (eligibility != null) return eligibility;
        AddMember(room, session); return null;
    }
    private void AddMember(GameRoom room, SessionLease session)
    {
        int id = 1; while (room.Members.Any(member => member.RiderId == id)) id++;
        room.Members.Add(new RoomMember(session, id, ++room.NextJoinOrder)); session.RoomId = room.Id; room.Revision++; BroadcastLobby(room);
    }
    private void Leave(SessionLease session)
    {
        if (!rooms.TryGetValue(session.RoomId, out var room)) { session.RoomId = ""; return; }
        var member = room.Members.Single(item => item.Session == session); member.Timeline.Suspend();
        if (room.State == MultiplayerRoomState.Racing) room.MarkDnf(member);
        room.Members.Remove(member); session.RoomId = "";
        CancelCountdown(room); TransferHost(room); room.Revision++; BroadcastLobby(room);
        if (session.Connected) Reliable(session, sequence => new MpLobby { reliableSequence = sequence, serverServiceTick = ServiceTick, state = (int)MultiplayerRoomState.Closing });
    }
    private void CancelCountdown(GameRoom room)
    {
        if (room.State != MultiplayerRoomState.Countdown) return;
        room.PendingAbort = room.MatchId; room.PersistenceRetryAt = 0;
        room.MatchId = ""; room.World = null; room.Participants.Clear(); room.State = MultiplayerRoomState.Lobby;
        foreach (var member in room.Members) member.Ready = false;
        PersistAbort(room);
    }
    private void PersistAbort(GameRoom room)
    {
        if (room.PendingAbort.Length == 0 || room.AbortWritePending || ServiceTick < room.PersistenceRetryAt) return;
        room.PersistenceRetryAt = ServiceTick + 60; room.AbortWritePending = true; string match = room.PendingAbort;
        Schedule(() => persistence.Commit(match, []), result =>
        { room.AbortWritePending = false; room.PendingAbort = ""; room.PersistenceErrorReported = false; },
            error => { room.AbortWritePending = false; PersistenceFault(room); });
    }
    private void PersistenceFault(GameRoom room)
    {
        PersistenceFailures++;
        if (room.PersistenceErrorReported) return;
        room.PersistenceErrorReported = true;
        foreach (var member in room.Members.Where(member => member.Session.Connected)) Error(member.Session, "result_save_retry");
    }
    private static void TransferHost(GameRoom room)
    {
        if (room.Members.Any(member => member.Session.Id == room.HostSessionId && member.Session.Connected)) return;
        room.HostSessionId = room.Members.Where(member => member.Session.Connected).OrderBy(member => member.JoinOrder).FirstOrDefault()?.Session.Id ?? "";
    }
    private void Complete(GameRoom room)
    {
        if (room.Result != null || room.ResultWritePending || room.MatchId.Length == 0 || ServiceTick < room.PersistenceRetryAt) return;
        room.PersistenceRetryAt = ServiceTick + 60; room.ResultWritePending = true;
        foreach (var participant in room.Participants) if (participant.Outcome == MultiplayerOutcome.Racing) participant.Outcome = MultiplayerOutcome.Dnf;
        var grants = room.Participants.Select(participant => new RealmGrant
        {
            SessionId = participant.Member.Session.Id, ProfileId = participant.Member.Session.ProfileId, Name = participant.Member.Session.Name,
            RiderId = participant.Member.RiderId, Guest = participant.Member.Session.Guest, Credits = participant.Member.Session.Credits,
            Outcome = (int)participant.Outcome, Rank = participant.Rank, Reward = participant.Reward, FinishTick = participant.FinishTick,
            BikeId = participant.Member.BikeId, BikeCondition = participant.BikeCondition,
            LevelIndex = room.LevelIndex, CourseIndex = room.CourseIndex, Qualified = participant.Qualified
        }).ToArray();
        Schedule(() => persistence.Commit(room.MatchId, grants), result =>
        {
            room.ResultWritePending = false; room.Result = result; room.PersistenceErrorReported = false;
            foreach (var grant in result.Grants) if (sessions.TryGetValue(grant.SessionId, out var session)) session.Credits = grant.Credits;
            room.State = MultiplayerRoomState.Results; room.Revision++; BroadcastLobby(room);
            foreach (var member in room.Members) Reliable(member.Session, sequence => MultiplayerProjection.Result(room, sequence));
        }, error => { room.ResultWritePending = false; PersistenceFault(room); });
    }
    private void Input(SessionLease session, MpInput input)
    {
        if (!Acknowledge(session, input.reliableAck)) return;
        if (!rooms.TryGetValue(session.RoomId, out var room) || room.Id != input.roomId || room.RaceEpoch != input.raceEpoch ||
            room.World == null || room.State is not (MultiplayerRoomState.Countdown or MultiplayerRoomState.Racing))
        { RejectedInputs++; Error(session, "race_epoch", 0, false, input.sequence); return; }
        var member = room.Members.Single(item => item.Session == session);
        string? error = member.Timeline.Add(input, room.World.Tick);
        if (error != null) { RejectedInputs++; Error(session, error, 0, false, input.sequence); }
    }
    private string? WithRoom(SessionLease session, string roomId, Func<GameRoom, string?> command)
        => rooms.TryGetValue(session.RoomId, out var room) && room.Id == roomId ? command(room) : "not_room_member";
    private string? List(SessionLease session, int requestId) { SendRooms(session, requestId); return null; }
    private string? Goodbye(SessionLease session) { Leave(session); return null; }
    private void SendRooms(SessionLease session, int requestId) => Reliable(session, sequence => new MpRoomList
    {
        requestId = requestId, reliableSequence = sequence,
        rooms = rooms.Values.Where(room => room.PublicRoom && room.State == MultiplayerRoomState.Lobby).Select(room => new MpRoomSummary
        { code = room.Code, name = room.Name, players = room.Members.Count, state = (int)room.State,
            publicRoom = room.PublicRoom, courseIndex = room.CourseIndex, levelIndex = room.LevelIndex }).ToArray()
    });
    private string? RaceEligibility(SessionLease session, int level)
    {
        if (session.Guest) return level == 0 ? null : "campaign_locked";
        var career = realm.GetRaceConfiguration(session.ProfileId);
        if (level != career.levelIndex) return "campaign_locked";
        var bike = career.bikes.FirstOrDefault(item => item.bikeId == career.selectedBikeId);
        return bike != null && bike.condition <= 0 ? "repair_required" : null;
    }
    private bool CredentialActive(SessionLease session) => session.Guest || realm.IsTokenActive(session.ProfileCredential);
    private void Revoke(SessionLease session)
    {
        string connection = session.ConnectionId;
        Leave(session); connections.Remove(connection); sessions.Remove(session.Id);
        resume.Remove(RealmStore.Hash(session.ResumeToken)); controlWindows.Remove(session.Id);
        session.Connected = false; session.ConnectionId = "";
        if (connection.Length > 0) sink.Close(connection, "profile_revoked");
    }
    private void BroadcastLobby(GameRoom room)
    { foreach (var member in room.Members) Reliable(member.Session, sequence => MultiplayerProjection.Lobby(room, ServiceTick, sequence)); }
    private void SendSnapshot(GameRoom room, RoomMember member)
    {
        if (!member.Session.Connected) return;
        var snapshot = MultiplayerProjection.Snapshot(room, member, ServiceTick); if (snapshot == null) return;
        var bytes = encode(snapshot); if (bytes.Length > MultiplayerProtocol.MaxSnapshotBytes) throw new InvalidOperationException("Snapshot budget exceeded.");
        SnapshotBytes += bytes.Length; sink.Send(member.Session.ConnectionId, bytes, false);
    }
    private void Accepted(SessionLease session, int requestId) => Reliable(session, sequence => new MpCommandAccepted { requestId = requestId, sessionEpoch = session.Epoch, roomId = session.RoomId, reliableSequence = sequence });
    private void Error(SessionLease session, string code, int requestId = 0, bool terminal = false, int inputSequence = 0)
    {
        Reliable(session, sequence => new MpError { code = code, message = code, requestId = requestId, sequence = inputSequence,
            sessionEpoch = session.Epoch, serverServiceTick = ServiceTick, reliableSequence = sequence, terminal = terminal });
        if (terminal) sink.Close(session.ConnectionId, code);
    }
    private bool Acknowledge(SessionLease session, long ack)
    {
        if (ack < 0 || ack > session.ReliableSequence) { Error(session, "invalid_ack", 0, true); return false; }
        if (ack <= session.ReliableAck) return true;
        session.ReliableAck = ack;
        while (session.History.Count > 0 && session.History.Peek().Sequence <= ack) session.HistoryBytes -= session.History.Dequeue().Bytes.Length;
        return true;
    }
    private void Reliable(SessionLease session, Func<long, object> create)
    {
        long sequence = ++session.ReliableSequence; byte[] bytes = encode(create(sequence));
        if (session.History.Count >= 64 || session.HistoryBytes + bytes.Length > 65536)
        {
            session.History.Clear(); session.HistoryBytes = 0; session.ReplayReset = true;
            if (session.Connected) { string id = session.ConnectionId; sink.Close(id, "reliable_overflow"); Disconnect(id); }
            return;
        }
        session.History.Enqueue((sequence, bytes)); session.HistoryBytes += bytes.Length;
        if (session.Connected && !sink.Send(session.ConnectionId, bytes, true))
        { string id = session.ConnectionId; sink.Close(id, "slow_reader"); Disconnect(id); }
    }
    private void RawError(string connectionId, string code)
    { SendRaw(connectionId, new MpError { code = code, message = code, terminal = true, serverServiceTick = ServiceTick }, true); sink.Close(connectionId, code); }
    private void SendRaw(string connectionId, object message, bool reliable) => sink.Send(connectionId, encode(message), reliable);
    private static string DisplayName(string? value)
    {
        value = (value ?? "").Trim().Normalize(); if (value.Length == 0) value = "Rider";
        if (value.Length > 24 || value.Any(character => char.IsControl(character) || character is '<' or '>')) throw new ArgumentException("displayName");
        return value;
    }
    private static string Code()
    { const string alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; return new string(RandomNumberGenerator.GetBytes(6).Select(value => alphabet[value % alphabet.Length]).ToArray()); }
}
