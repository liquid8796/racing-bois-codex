using System.Text.Json;
using RacingBois.Client.Application;

internal sealed class DiagnosticJournal(ProbeClock clock)
{
    internal readonly Queue<object> Events = new();
    private readonly List<PeerTrace> peers = new();
    private double sampled;
    public void Attach(int index, Participant participant)
    {
        var peer = new PeerTrace(index, participant); peers.Add(peer);
        participant.Transport.TraceSent = text => Frame(peer, text, true);
        participant.Transport.Message += text => Frame(peer, text, false);
        participant.Transport.Closed += _ => Add(new { kind = "transport_closed", at = clock.NowSeconds, peer = index, reason = participant.Transport.LastCloseReason, state = State(peer) });
        participant.Session.Changed += () =>
        {
            string signature = participant.Session.Status + "/" + participant.Session.Room?.Phase + "/" + participant.Session.Room?.Revision + "/" + participant.Session.IsHost + "/" + participant.Session.IsReconnecting;
            if (signature == peer.StateSignature) return;
            peer.StateSignature = signature; Add(new { kind = "client_transition", at = clock.NowSeconds, state = State(peer) });
        };
    }
    private void Frame(PeerTrace peer, string text, bool outgoing)
    {
        using var document = JsonDocument.Parse(text); var frame = document.RootElement;
        string kind = frame.GetProperty("kind").GetString();
        var counts = outgoing ? peer.Outgoing : peer.Incoming;
        counts[kind] = counts.GetValueOrDefault(kind) + 1;
        if (kind == "mpSnapshot") { peer.LastSnapshotAt = clock.NowSeconds; peer.LastWireTick = Long(frame, "tick"); peer.LastSnapshotEpoch = (int)Long(frame, "raceEpoch"); }
        if (kind == "mpWelcome") peer.SessionEpoch = (int)Long(frame, "sessionEpoch");
        if (kind == "mpAccepted") peer.LastAcceptedRequest = (int)Long(frame, "requestId");
        if (kind == "mpError")
        {
            string code = frame.GetProperty("code").GetString() ?? "unknown";
            peer.LastError = code.Length <= 64 && code.All(c => char.IsAsciiLetterOrDigit(c) || c == '_') ? code : "unknown";
            peer.ErrorCounts[peer.LastError] = peer.ErrorCounts.GetValueOrDefault(peer.LastError) + 1;
        }
        if (kind is "mpWelcome" or "mpLobby" or "mpAccepted" or "mpCreate" or "mpJoin" or "mpReady" or "mpStart" or "mpBack" or "mpGoodbye" || kind == "mpError" && peer.LastError is not ("input_late" or "input_future"))
            Add(new { kind = outgoing ? "sent_control" : "received_control", message = kind, at = clock.NowSeconds, request = Long(frame, "requestId"), reliable = Long(frame, "reliableSequence"), error = kind == "mpError" ? peer.LastError : null, state = State(peer) });
    }
    public void Sample()
    {
        if (clock.NowSeconds - sampled < 1) return; sampled = clock.NowSeconds;
        foreach (var peer in peers)
        {
            Add(new { kind = "message_window", at = sampled, state = State(peer), outgoing = peer.Outgoing.ToDictionary(), incoming = peer.Incoming.ToDictionary(), errors = peer.ErrorCounts.ToDictionary() });
            peer.Outgoing.Clear(); peer.Incoming.Clear(); peer.ErrorCounts.Clear();
        }
    }
    public void Checkpoint(string reason) => Add(new { kind = reason, at = clock.NowSeconds, states = peers.Select(State).ToArray() });
    public void Health(JsonElement health) => Add(new { kind = "server_health", at = clock.NowSeconds, serviceTick = Long(health, "serviceTick"), rooms = Long(health, "roomCount"), sessions = Long(health, "sessionCount"), rejectedCommands = Long(health, "rejectedCommands"), persistenceFailures = Long(health, "persistenceFailures"), droppedCatchupTicks = Long(health, "droppedCatchupTicks") });
    private object State(PeerTrace peer)
    {
        var session = peer.Participant.Session; var room = session.Room;
        return new { peer = peer.Index, session = session.Status.ToString(), session.IsReconnecting, phase = room?.Phase.ToString(), revision = room?.Revision, raceEpoch = room?.RaceEpoch,
            peer.SessionEpoch, session.IsHost, session.RiderId, members = room?.Members.Count, connected = room?.Members.Count(m => m.Connected), ready = room?.Members.Count(m => m.Ready),
            peer.LastAcceptedRequest, peer.LastError, peer.LastWireTick, peer.LastSnapshotEpoch, snapshotAge = clock.NowSeconds - peer.LastSnapshotAt,
            resolvedTick = session.LastResolvedTick, pending = session.PendingInputCount, session.LateInputs, session.FutureInputs, connectAttempts = peer.Participant.Transport.ConnectAttempts };
    }
    private void Add(object value) { while (Events.Count >= 2048) Events.Dequeue(); Events.Enqueue(value); }
    private static long Long(JsonElement value, string property) => value.TryGetProperty(property, out var field) && field.TryGetInt64(out long number) ? number : -1;
    private sealed class PeerTrace(int index, Participant participant)
    {
        public int Index = index, SessionEpoch, LastSnapshotEpoch, LastAcceptedRequest;
        public long LastWireTick; public double LastSnapshotAt;
        public string LastError = "", StateSignature = "";
        public Participant Participant = participant;
        public readonly Dictionary<string, int> Outgoing = new(), Incoming = new(), ErrorCounts = new();
    }
}
