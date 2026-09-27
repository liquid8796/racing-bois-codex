using System.Diagnostics;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;

string endpoint = args.Length > 0 ? args[0] : "ws://127.0.0.1:17950/multiplayer";
string output = args.Length > 1 ? args[1] : "docs/p05/backend/live-ws.json";
bool matrix = args.Length > 2 && args[2] == "matrix";
var scenarios = matrix ? new[]
{
    new Scenario("loopback8",8), new Scenario("rtt80",2,80), new Scenario("rtt150_jitter20_each_direction",2,150,20),
    new Scenario("rtt250_jitter50_each_direction",2,250,50), new Scenario("upstream_stall900",2,80,10,900,true),
    new Scenario("downstream_stall2600",2,80,10,2600,false), new Scenario("connection_break_resume",2,80,10,0,false,true),
    new Scenario("visibility_suspend_resume",2,80,10,0,false,false,true)
} : new[] { new Scenario("eight_clients_default_bots_combat_resume",8,0,0,0,false,true,false,5,true) };
var reports = new List<object>(); int failures = 0;
foreach (var scenario in scenarios)
{
    var sourceUri = new Uri(endpoint);
    await using var proxy = new ImpairedStreamProxy(sourceUri.Port, scenario.Rtt / 2, scenario.Jitter, 4500, scenario.Stall, scenario.Upstream);
    proxy.Clock.Start(); var proxied = new UriBuilder(sourceUri) { Port = proxy.Port }.Uri.AbsoluteUri;
    var clock = new ProbeClock(); var clients = new List<ProbeClient>(); var checks = new List<object>();
    string failure = null; double nextInput = 0;
    bool combatSetup = scenario.CombatProof;
    int observedVictimHealth = 0; long observedHitId = 0;
    try
    {
        for (int i = 0; i < scenario.Peers; i++)
        {
            var transport = new ProbeTransport();
            var session = new MultiplayerSession(transport, new ProbeCodec(), clock, new ProbeResumeStore(), new ProbeCredentialStore());
            clients.Add(new ProbeClient(session, transport));
            session.Connect(proxied, new LocalPlayerProfile(Guid.NewGuid().ToString("N"), "Probe " + (i + 1), i), true);
        }
        await Until(() => clients.All(client => client.Session.Status == SessionStatus.Connected), 8);
        clients[0].Session.CreateLobby("Network fixture", scenario.Bots);
        await Until(() => clients[0].Session.Room != null, 4);
        string code = clients[0].Session.Room.Code;
        foreach (var client in clients.Skip(1)) client.Session.JoinLobby(code);
        await Until(() => clients.All(client => client.Session.Room?.Members.Count == scenario.Peers), 6);
        foreach (var client in clients) client.Session.SetReady(true);
        await Until(() => clients[0].Session.Room.Members.All(member => member.Ready), 5);
        clients[0].Session.StartRace();
        await Until(() => clients.All(client => client.Session.Room?.Phase == LobbyPhase.Racing), 8);
        Check(clients.Select(client => client.Session.RiderId).Distinct().Count() == scenario.Peers, "unique_room_slots");
        if (scenario.CombatProof)
        {
            // The nearest grid partner is chosen by assigned rider ID, not connection completion order.
            clients.Sort((left, right) => left.Session.RiderId.CompareTo(right.Session.RiderId));
            await Until(() => clients[1].Session.LocalRider.Health <= GameplayRules.InitialHealth - 448, 7);
            observedVictimHealth = clients[1].Session.LocalRider.Health;
            var ownEvents = clients[0].Session.SamplePresentation()?.Events;
            observedHitId = ownEvents?.Where(item => item.Kind == RaceEventKind.Hit && item.SourceId == clients[0].Session.RiderId && item.TargetId == clients[1].Session.RiderId)
                .Select(item => item.Id).FirstOrDefault() ?? 0;
            await Until(() => clients[1].Session.SamplePresentation()?.Events.Any(item => item.Kind == RaceEventKind.Hit && item.Id == observedHitId) == true, 3);
            Check(observedHitId > 0 && observedVictimHealth == GameplayRules.InitialHealth - 448, "authoritative_combat_damage_and_reliable_event_reach_both_clients");
            combatSetup = false;
        }
        string resumedIdentity = clients[0].Session.PlayerId;
        int resumedRiderId = clients[0].Session.RiderId;
        double started = clock.NowSeconds; bool interrupted = false, restoredVisibility = false;
        foreach (var client in clients) { client.SentAtStart = client.Transport.SentBytes; client.ReceivedAtStart = client.Transport.ReceivedBytes; }
        while (clock.NowSeconds - started < 12)
        {
            double elapsed = clock.NowSeconds - started;
            if (!interrupted && elapsed >= 3 && (scenario.BreakConnection || scenario.Suspend))
            {
                interrupted = true;
                if (scenario.Suspend) clients[0].Session.NotifyVisibility(false); else clients[0].Transport.BreakConnection();
            }
            if (scenario.Suspend && interrupted && !restoredVisibility && elapsed >= 4.2)
            { restoredVisibility = true; clients[0].Session.NotifyVisibility(true); }
            Pump();
            foreach (var client in clients) client.Record(elapsed > 1);
            await Task.Delay(2);
        }
        await Until(() => clients.All(client => client.Session.Status == SessionStatus.Connected && !client.Session.IsReconnecting), 7);
        Check(clients.All(client => client.Session.InvalidSnapshots == 0), "all_snapshots_validated");
        Check(clients.All(client => client.Session.Room?.Members.Count == scenario.Peers), "membership_not_duplicated");
        Check(clients.All(client => client.Session.LastResolvedTick > 200 && client.Session.LocalRider.LongitudinalMeters > 10), "all_clients_progress");
        Check(clients.All(client => client.MaximumPending <= 120 && client.Transport.LargestReceivedBytes <= 32768 &&
            client.MaximumExtrapolation <= PredictionNeighbors.MaximumAgeTicks * 1000.0 / 60 + .1), "memory_and_extrapolation_bounded");
        if (scenario.BreakConnection || scenario.Suspend || scenario.Stall >= 2000)
            Check(clients[0].Session.PlayerId == resumedIdentity && clients[0].Session.RiderId == resumedRiderId && clients[0].Transport.ConnectAttempts >= 2, "resume_preserves_identity_and_slot");
        if (scenario.Rtt > 0)
            Check(clients.All(client => Percentile(client.Rtt, .5) >= scenario.Rtt * .55), "rtt_measurement_reflects_applied_latency");
        Check(clients.All(client => client.RecordedNearSamples > 0), "near_combat_error_has_real_samples");
        if (scenario.Stall == 0 && !scenario.BreakConnection && !scenario.Suspend)
            Check(clients.All(client => client.Session.LateInputs <= Math.Max(4, client.Transport.InputFramesSent * .05)), "timely_input_budget_below_five_percent_late");
        foreach (var client in clients) client.Session.Disconnect();
        await Until(() => clients.All(client => client.Session.Status == SessionStatus.Offline), 4);
        Check(clients.All(client => !client.Session.IsDisconnecting), "logout_acknowledged_before_close");
    }
    catch (Exception error) { failure = error.Message; failures++; }
    finally { foreach (var client in clients) client.Session.Dispose(); }
    var report = new
    {
        scenario = scenario.Name, status = failure == null ? "PASS" : "FAIL", humanPeers = scenario.Peers,
        configured = new { botCount = scenario.Bots, nominalRoundTripDelayMs = scenario.Rtt, jitterMillisecondsPerDirection = scenario.Jitter,
            orderedByteStreamStallMs = scenario.Stall, stallDirection = scenario.Upstream ? "upstream" : "downstream", packetLossEmulated = false },
        combat = new { observedHitId, observedVictimHealth }, checks, clients = clients.Select(client => client.Report()), error = failure
    };
    reports.Add(report); Console.WriteLine(JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = false }));
    await Task.Delay(250);

    void Check(bool passed, string name) { checks.Add(new { name, passed }); if (!passed) throw new InvalidOperationException(name); }
    void Pump()
    {
        foreach (var client in clients) client.Session.Poll();
        int catchup = 0;
        while (clock.NowSeconds >= nextInput && catchup++ < 4)
        {
            nextInput += 1.0 / 60;
            for (int index = 0; index < clients.Count; index++)
            {
                var client = clients[index];
                var session = client.Session; var rider = session.LocalRider;
                float desiredLane = combatSetup && index == 1 ? 1.25f : session.RiderId == 1 ? 0 : session.RiderId % 2 == 0 ? 1.8f : -1.8f;
                var curve = TrackDefinition.Default.CurvatureAt((long)(rider.LongitudinalMeters * 1000));
                float speed = rider.SpeedMetersPerSecond * 1000;
                float lateralVelocity = Math.Clamp((desiredLane - rider.LateralMeters) * 2000, -6500, 6500);
                float drift = speed * curve / 100000;
                float steer = Math.Clamp((lateralVelocity + drift) / (1200 + speed / 6), -1, 1);
                int attack = 0;
                if (combatSetup && index == 0 && clients.Count > 1)
                {
                    var victim = clients[1].Session.LocalRider; float gap = victim.LateralMeters - rider.LateralMeters;
                    if (gap > 1.05f && gap < 1.55f && Math.Abs(victim.LongitudinalMeters - rider.LongitudinalMeters) < 1) attack = 1;
                }
                session.Step(combatSetup ? 0 : 1, 0, steer, attack); session.SamplePresentation();
            }
        }
        if (clock.NowSeconds - nextInput > .15) nextInput = clock.NowSeconds;
        foreach (var client in clients)
            if (client.Session.Status == SessionStatus.Failed) throw new InvalidOperationException("Client failed: " + client.Session.Error);
    }
    async Task Until(Func<bool> condition, double seconds)
    {
        double deadline = clock.NowSeconds + seconds;
        while (!condition()) { Pump(); if (clock.NowSeconds > deadline) throw new TimeoutException("Lifecycle condition timed out: " + string.Join(" | ", clients.Select(client => client.Session.Status + "/" + client.Session.Room?.Phase + "/" + client.Session.Error))); await Task.Delay(2); }
    }
}
var final = new
{
    generatedUtc = DateTimeOffset.UtcNow, status = failures == 0 ? "PASS" : "FAIL", endpoint, scenarios = reports,
    limitations = "One Windows PC, actual ClientWebSocket plus linked production MultiplayerSession and bounded ordered TCP-delay proxy. No IP packet-loss emulation, second physical LAN client, disconnected WAN or public Internet deployment. These external gates remain unverified."
};
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!); await File.WriteAllTextAsync(output, JsonSerializer.Serialize(final, new JsonSerializerOptions { WriteIndented = true }));
return failures == 0 ? 0 : 1;

static double Percentile(List<double> values, double ratio)
{ if (values.Count == 0) return 0; var sorted = values.Order().ToArray(); return sorted[Math.Min(sorted.Length - 1, (int)(sorted.Length * ratio))]; }
internal sealed record Scenario(string Name, int Peers, int Rtt = 0, int Jitter = 0, int Stall = 0, bool Upstream = false, bool BreakConnection = false, bool Suspend = false, int Bots = 0, bool CombatProof = false);
internal sealed class ProbeClient(MultiplayerSession session, ProbeTransport transport)
{
    public MultiplayerSession Session { get; } = session;
    public ProbeTransport Transport { get; } = transport;
    public readonly List<double> Rtt = new(), Corrections = new();
    public int MaximumPending, MaximumEventCappedRemotes;
    public double MaximumExtrapolation;
    public long SentAtStart, ReceivedAtStart;
    private long lastTick = -1;
    private double maxNearResidual, maxCorrection, maxSteadyResidual, maxContactResidual;
    private int nearSamples, steadySamples, contactSamples, late, future, missing;
    private long finalTick;
    private float finalDistance;
    public int RecordedNearSamples => nearSamples;
    public void Record(bool warmed)
    {
        if (!warmed || Session.LatestWorld == null || Session.LastResolvedTick == lastTick) return;
        lastTick = Session.LastResolvedTick;
        if (Session.RttMs > 0) Rtt.Add(Session.RttMs);
        Corrections.Add(Session.LastCorrectionMeters); MaximumPending = Math.Max(MaximumPending, Session.PendingInputCount);
        MaximumExtrapolation = Math.Max(MaximumExtrapolation, Session.RemoteExtrapolationMs);
        MaximumEventCappedRemotes = Math.Max(MaximumEventCappedRemotes, Session.EventCappedRemoteCount);
        maxNearResidual = Math.Max(maxNearResidual, Session.MaximumNearCombatResidualMeters);
        maxCorrection = Math.Max(maxCorrection, Session.MaximumCorrectionMeters); nearSamples = Math.Max(nearSamples, Session.NearCombatResidualSamples);
        maxSteadyResidual = Math.Max(maxSteadyResidual, Session.MaximumSteadyResidualMeters); steadySamples = Math.Max(steadySamples, Session.SteadyResidualSamples);
        maxContactResidual = Math.Max(maxContactResidual, Session.MaximumContactResidualMeters); contactSamples = Math.Max(contactSamples, Session.ContactResidualSamples);
        late = Math.Max(late, Session.LateInputs); future = Math.Max(future, Session.FutureInputs); missing = Math.Max(missing, Session.MissingInputs);
        finalTick = Session.LastResolvedTick; finalDistance = Session.LocalRider.LongitudinalMeters;
    }
    public object Report() => new { snapshots = Rtt.Count, rttMs = Stats(Rtt), correctionMeters = Stats(Corrections), maximumCorrectionMeters = maxCorrection,
        nearCombatResidualSamples = nearSamples, maximumNearCombatResidualMeters = maxNearResidual,
        steadyResidualSamples = steadySamples, maximumSteadyResidualMeters = steadySamples > 0 ? (double?)maxSteadyResidual : null,
        contactResidualSamples = contactSamples, maximumContactResidualMeters = contactSamples > 0 ? (double?)maxContactResidual : null,
        maximumPendingInputs = MaximumPending, maximumRemoteExtrapolationMs = MaximumExtrapolation,
        maximumEventCappedRemotes = MaximumEventCappedRemotes,
        lateInputs = late, futureInputs = future, missingInputs = missing, connectAttempts = Transport.ConnectAttempts,
        inputFramesSent = Transport.InputFramesSent, lateFraction = Transport.InputFramesSent == 0 ? (double?)null : late / (double)Transport.InputFramesSent,
        receivedPayloadBytes = Transport.ReceivedBytes, sentPayloadBytes = Transport.SentBytes,
        downloadBytesPerSecondDuringRace = (Transport.ReceivedBytes - ReceivedAtStart) / 12.0,
        uploadBytesPerSecondDuringRace = (Transport.SentBytes - SentAtStart) / 12.0,
        maximumMessageBytes = Transport.LargestReceivedBytes, finalTick, finalDistanceMeters = finalDistance };
    private static object Stats(List<double> values)
    {
        var sorted = values.Order().ToArray();
        return new { samples = sorted.Length, p50 = sorted.Length == 0 ? (double?)null : sorted[sorted.Length / 2],
            p95 = sorted.Length == 0 ? (double?)null : sorted[Math.Min(sorted.Length - 1, (int)(sorted.Length * .95))],
            maximum = sorted.Length == 0 ? (double?)null : sorted[^1] };
    }
}
