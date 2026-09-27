using System.Diagnostics;
using System.Net.WebSockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

if (args.Length > 0 && args[0] == "--replay") return CorrectionReplay.Run(args);

// Credentials only exist in the production session's in-memory stores. Reports contain
// aggregate measurements and case identifiers, never welcomes, bearer values or raw frames.
if (args.Length < 3 || !Uri.TryCreate(args[0], UriKind.Absolute, out var endpoint) ||
    endpoint.Scheme is not ("ws" or "wss") || endpoint.UserInfo.Length != 0 ||
    endpoint.Query.Length != 0 || endpoint.Fragment.Length != 0 || endpoint.AbsolutePath != "/multiplayer")
{ Console.Error.WriteLine("Usage: ProtocolSoak <ws[s]://host/multiplayer> <report.json> <seconds:30..86400> [peers:1..8] [--fuzz]"); return 2; }
int duration = int.Parse(args[2]), count = args.Length > 3 ? int.Parse(args[3]) : 8;
if (duration is < 30 or > 86400 || count is < 1 or > 8 || !endpoint.IsLoopback)
    throw new ArgumentException("Use WSS outside loopback, a bounded duration, and at most eight clients.");
string reportPath = Path.GetFullPath(args[1]);
if (File.Exists(reportPath)) throw new IOException("A soak receipt is immutable; choose a new path.");
Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);
string runId = Guid.NewGuid().ToString("N"); var startedUtc = DateTimeOffset.UtcNow;
var clock = new ProbeClock(); var clients = new List<Participant>(); var cases = new List<object>();
var stopwatch = Stopwatch.StartNew(); var correctionAudit = new CorrectionTrace(clock); var driver = new RaceDriver(clients, clock, correctionAudit);
var journal = new DiagnosticJournal(clock);
string errorCode = null; int cycles = 0, reconnects = 0, storms = 0;
double lastProgress = 0, lastTransition = -100, nextBreak = duration < 180 ? 15 : 120, nextStorm = 600;
long lastServiceTick = -1; double lastServiceProgress = clock.NowSeconds;
using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(6) };
int healthArgument = Array.IndexOf(args, "--health-url");
var healthUri = healthArgument >= 0 && healthArgument + 1 < args.Length ? new Uri(args[healthArgument + 1]) :
    new UriBuilder(endpoint) { Scheme = endpoint.Scheme == "wss" ? "https" : "http", Path = "/multiplayer/health" }.Uri;
if (healthUri.Host != endpoint.Host || healthUri.Port != endpoint.Port || healthUri.UserInfo.Length != 0 || healthUri.Query.Length != 0 || healthUri.Fragment.Length != 0 ||
    healthUri.Scheme != (endpoint.Scheme == "wss" ? "https" : "http") || healthUri.AbsolutePath is not ("/ready" or "/multiplayer/health"))
    throw new ArgumentException("Health URL must be /ready or /multiplayer/health on the same trusted origin.");
bool detailedHealth = healthUri.AbsolutePath == "/multiplayer/health";
var sourcePaths = Directory.GetFiles("Packages/com.racingbois.foundation/Runtime", "*.cs", SearchOption.AllDirectories)
    .Concat(Directory.GetFiles("Assets/RacingBois/Client/Application", "*.cs"))
    .Concat(Directory.GetFiles("tools/p10/ProtocolSoak", "*.cs", SearchOption.TopDirectoryOnly))
    .Concat(Directory.GetFiles("tools/p10/ProtocolSoakNext", "*.cs", SearchOption.TopDirectoryOnly)).Concat(Directory.GetFiles("tools/p10/correction-audit", "*.cs", SearchOption.TopDirectoryOnly)).Append("tools/p10/correction-audit/CorrectionAudit.csproj").Append("tools/p10/ProtocolSoakNext/ProtocolSoakNext.csproj").OrderBy(path => path, StringComparer.Ordinal).Distinct().ToArray();
var sources = sourcePaths.ToDictionary(path => path.Replace('\\', '/'), HashFile);
double maxHealthStepMs = 0; long baselinePersistence = -1, latestPersistence = 0, baselineDroppedTicks = -1, latestDroppedTicks = 0;
bool completed = false;
try
{
    await Health();
    if (args.Contains("--fuzz")) await Fuzz();
    for (int index = 0; index < count; index++)
    {
        var transport = new ProbeTransport();
        var session = new MultiplayerSession(transport, new ProbeCodec(), clock, new ProbeResumeStore(), new ProbeCredentialStore());
        var participant = new Participant(session, transport); clients.Add(participant);
        journal.Attach(index, participant); correctionAudit.Attach(index, participant);
        session.Connect(endpoint.AbsoluteUri, new LocalPlayerProfile(Guid.NewGuid().ToString("N"), "P10 probe " + index, index), true);
    }
    await Until(() => clients.All(p => p.Session.Status == SessionStatus.Connected), 20, "initial_connect");
    clients[0].Session.CreateLobby(new LobbyOptions("P10 isolated soak " + runId[..6], 5, publicRoom: false));
    await Until(() => clients[0].Session.Room != null, 10, "create_lobby");
    string roomCode = clients[0].Session.Room.Code;
    foreach (var p in clients.Skip(1)) p.Session.JoinLobby(roomCode);
    await Until(() => clients.All(p => p.Session.Room?.Members.Count == count), 15, "join_lobby");
    await StartRace();
    foreach (var p in clients) { p.Identity = p.Session.PlayerId; p.Slot = p.Session.RiderId; }
    while (stopwatch.Elapsed.TotalSeconds < duration)
    {
        driver.Pump();
        foreach (var p in clients) p.Observe(clock.NowSeconds);
        journal.Sample();
        if (clients.Any(p => p.Session.InvalidSnapshots != 0 || p.MaximumPending > 120 || p.Transport.LargestReceivedBytes > MultiplayerProtocol.MaxSnapshotBytes))
            throw new ProbeFailure("snapshot_or_queue_budget");
        var owner = clients.FirstOrDefault(p => p.Session.IsHost) ?? clients[0];
        if (clock.NowSeconds - lastTransition > 10 && owner.Session.Room?.Phase == LobbyPhase.Results && clients.All(p => p.Session.Result != null))
        {
            owner.Session.ReturnToLobby();
            await Until(() => clients.All(p => p.Session.Room?.Phase == LobbyPhase.Lobby), 12, "result_return");
            await StartRace(); cycles++; lastTransition = clock.NowSeconds;
        }
        // Reconnect only during a race. A unique identity/slot assertion is verified after
        // the production resume state machine reconnects and receives a current checkpoint.
        if (clock.NowSeconds >= nextBreak && clients.All(p => p.Session.Status == SessionStatus.Connected && !p.Session.IsReconnecting) && owner.Session.Room?.Phase == LobbyPhase.Racing)
        {
            var p = clients[reconnects % count]; p.Transport.BreakConnection();
            await Until(() => p.Transport.ConnectAttempts > p.AttemptsAtResume && p.Session.Status == SessionStatus.Connected && !p.Session.IsReconnecting, 20, "resume_timeout");
            if (p.Session.PlayerId != p.Identity || p.Session.RiderId != p.Slot) throw new ProbeFailure("resume_identity_changed");
            p.AttemptsAtResume = p.Transport.ConnectAttempts; reconnects++; nextBreak = clock.NowSeconds + 120;
        }
        if (clock.NowSeconds >= nextStorm && owner.Session.Room?.Phase == LobbyPhase.Racing)
        {
            int[] attempts = clients.Select(p => p.Transport.ConnectAttempts).ToArray();
            foreach (var p in clients) p.Transport.BreakConnection();
            await Until(() => clients.Select((p, i) => p.Transport.ConnectAttempts > attempts[i] && p.Session.Status == SessionStatus.Connected && !p.Session.IsReconnecting).All(v => v), 25, "storm_resume_timeout");
            foreach (var p in clients) { if (p.Session.PlayerId != p.Identity || p.Session.RiderId != p.Slot) throw new ProbeFailure("storm_identity_changed"); p.AttemptsAtResume = p.Transport.ConnectAttempts; }
            storms++; nextStorm = clock.NowSeconds + 600;
        }
        if (clock.NowSeconds - lastProgress >= 10)
        {
            await Health(); lastProgress = clock.NowSeconds; Write("RUNNING");
            Console.WriteLine($"SOAK elapsed={stopwatch.Elapsed.TotalSeconds:F0}s cycles={cycles} resumes={reconnects} storms={storms}");
        }
        await Task.Delay(2);
    }
    if (clients.Any(p => p.ProgressSamples == 0 || p.MaximumDistance < 10) || reconnects == 0)
        throw new ProbeFailure("missing_real_race_or_resume_samples");
    foreach (var p in clients) p.Session.Disconnect();
    await Until(() => clients.All(p => p.Session.Status == SessionStatus.Offline), 10, "logout_ack_timeout");
    completed = true;
}
catch (ProbeFailure error) { errorCode = error.Code; }
catch (Exception error) { errorCode = error.GetType().Name; }
finally { foreach (var p in clients) p.Session.Dispose(); }
Write(completed ? "PASS" : "FAIL");
Console.WriteLine($"{(completed ? "PASS" : "FAIL")} native socket soak {stopwatch.Elapsed.TotalSeconds:F1}s; error={errorCode ?? "none"}");
return completed ? 0 : 1;

async Task Until(Func<bool> condition, double timeout, string failure)
{
    double deadline = clock.NowSeconds + timeout;
    while (!condition()) { driver.Pump(); journal.Sample(); if (clock.NowSeconds > deadline) { journal.Checkpoint("timeout_" + failure); throw new ProbeFailure(failure); } await Task.Delay(2); }
}
async Task StartRace()
{
    foreach (var p in clients) p.Session.SetReady(true);
    await Until(() => clients.All(p => p.Session.Room?.Members.All(m => m.Ready) == true), 10, "ready_timeout");
    (clients.FirstOrDefault(p => p.Session.IsHost) ?? clients[0]).Session.StartRace();
    await Until(() => clients.All(p => p.Session.Room?.Phase == LobbyPhase.Racing), 12, "start_timeout");
}
async Task Health()
{
    var pending = http.GetStringAsync(healthUri);
    while (!pending.IsCompleted) { driver.Pump(); await Task.Delay(2); }
    using var doc = JsonDocument.Parse(await pending); var h = doc.RootElement;
    if (!detailedHealth)
    {
        if (h.GetProperty("status").GetString() != "ready" || h.GetProperty("contentHash").GetString() != GameplayRules.ContentHash ||
            h.GetProperty("protocolVersion").GetInt32() != MultiplayerProtocol.Version) throw new ProbeFailure("readiness_or_version_mismatch");
        // Public readiness intentionally omits infrastructure counters. The authoritative
        // checkpoint tick must still advance while the room is racing.
        if (clients.Any(p => p.Session.Room?.Phase == LobbyPhase.Racing && clock.NowSeconds - p.LastProgressAt > 20))
            throw new ProbeFailure("authoritative_checkpoint_stalled");
        return;
    }
    long tick = h.GetProperty("serviceTick").GetInt64();
    if (tick > lastServiceTick) { lastServiceTick = tick; lastServiceProgress = clock.NowSeconds; }
    else if (clock.NowSeconds - lastServiceProgress > 20) throw new ProbeFailure("server_tick_stalled");
    latestPersistence = h.GetProperty("persistenceFailures").GetInt64();
    latestDroppedTicks = h.GetProperty("droppedCatchupTicks").GetInt64();
    if (baselinePersistence < 0) baselinePersistence = latestPersistence;
    if (baselineDroppedTicks < 0) baselineDroppedTicks = latestDroppedTicks;
    if (latestPersistence > baselinePersistence) throw new ProbeFailure("server_persistence_failure");
    maxHealthStepMs = Math.Max(maxHealthStepMs, h.GetProperty("maximumStepMilliseconds").GetDouble());
    journal.Health(h);
}
async Task Fuzz()
{
    // An explicit fixed corpus, not a claim of exhaustive protocol fuzz coverage.
    var casesToRun = new[] {
        ("empty_object", "{}", false), ("truncated_json", "{\"kind\":", false),
        ("unknown_kind", "{\"kind\":\"clientReward\",\"credits\":2147483647}", false),
        ("duplicate_kind", "{\"kind\":\"mpHello\",\"kind\":\"mpHello\"}", false),
        ("wrong_type", "{\"kind\":\"mpHello\",\"protocolVersion\":\"4\"}", false),
        ("deep_nesting", new string('[', 70) + new string(']', 70), false),
        ("message_over_cap", new string('x', MultiplayerProtocol.MaxMessageBytes + 1), false),
        ("binary_frame", "{}", true),
        ("unpaired_surrogate", "{\"kind\":\"\\uD800\"}", false)
    }.Select(item => (Name: item.Item1, Data: Encoding.UTF8.GetBytes(item.Item2), Binary: item.Item3)).ToList();
    casesToRun.Add(("invalid_utf8_kind", Convert.FromBase64String("eyJyb29tSWQiOiIiLCJraW5kIjoibdJTdGFydCIsInByb3RvY29sVmVyc2lvbiI6NCwic2Vzc2lvbkVwb2NoIjowLCJyZXF1ZXN0SWQiOjB9"), false));
    foreach (var item in casesToRun)
    {
        using var ws = new ClientWebSocket(); using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(12));
        await ws.ConnectAsync(endpoint, timeout.Token);
        await ws.SendAsync(item.Data, item.Binary ? WebSocketMessageType.Binary : WebSocketMessageType.Text, true, timeout.Token);
        bool rejected = false;
        try { var response = await ws.ReceiveAsync(new ArraySegment<byte>(new byte[32768]), timeout.Token); rejected = response.MessageType == WebSocketMessageType.Close; }
        catch (WebSocketException) { rejected = true; }
        cases.Add(new { name = item.Name, passed = rejected });
        if (!rejected) throw new ProbeFailure("fuzz_accepted_" + item.Name);
    }
}
void Write(string status)
{
    var changed = sources.Where(pair => !File.Exists(pair.Key) || HashFile(pair.Key) != pair.Value).Select(pair => pair.Key).ToArray();
    var receipt = new { schema = 1, runId, status, startedUtc, updatedUtc = DateTimeOffset.UtcNow, requestedSeconds = duration,
        elapsedSeconds = stopwatch.Elapsed.TotalSeconds, endpoint = endpoint.AbsoluteUri, peers = count, gameplayContentHash = GameplayRules.ContentHash,
        cycles, reconnects, storms, protocolCases = cases, clients = clients.Select(p => p.Report()), errorCode,
        correctionTrace = correctionAudit.Report(), diagnosticEvents = journal.Events.ToArray(), diagnosticScope = "Bounded sanitized state, command IDs, epochs, readiness, snapshot age and per-kind message counts; no credentials, names, room codes, raw frames or production logic changes.",
        server = new { detailedHealth, healthUrl = healthUri.AbsoluteUri, lastServiceTick = detailedHealth ? (long?)lastServiceTick : null,
            maxHealthStepMs = detailedHealth ? (double?)maxHealthStepMs : null,
            persistenceFailuresDelta = detailedHealth ? (long?)(latestPersistence - baselinePersistence) : null,
            droppedCatchupTicksDelta = detailedHealth ? (long?)(latestDroppedTicks - baselineDroppedTicks) : null },
        clientProcess = new { workingSetBytes = Process.GetCurrentProcess().WorkingSet64, managedHeapBytes = GC.GetTotalMemory(false) },
        sources, sourceStable = changed.Length == 0, changedSources = changed,
        scope = "Real wall-clock linked production MultiplayerSession via ClientWebSocket and standard TLS validation. Synthetic input peers with a fixed malformed-frame corpus; no Unity rendering, physical LAN, hardware matrix, full security audit or final release acceptance.",
        eightHourGate = completed && duration >= 28800 && stopwatch.Elapsed.TotalSeconds >= 28800 && changed.Length == 0 };
    string temporary = reportPath + ".tmp";
    File.WriteAllText(temporary, JsonSerializer.Serialize(receipt, new JsonSerializerOptions { WriteIndented = true, IncludeFields = true })); File.Move(temporary, reportPath, true);
}
static string HashFile(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

internal sealed class ProbeFailure(string code) : Exception { public string Code { get; } = code; }
internal sealed class Participant(MultiplayerSession session, ProbeTransport transport)
{
    public MultiplayerSession Session { get; } = session; public ProbeTransport Transport { get; } = transport;
    public string Identity = ""; public int Slot, AttemptsAtResume = 1, MaximumPending, ProgressSamples;
    public double MaximumDistance, MaximumRtt, SumRtt, MaximumCorrection, LastProgressAt; private long lastTick = -1;
    public void Observe(double now)
    {
        if (Session.LastResolvedTick == lastTick || Session.Room?.Phase != LobbyPhase.Racing) return;
        lastTick = Session.LastResolvedTick; LastProgressAt = now; ProgressSamples++; MaximumPending = Math.Max(MaximumPending, Session.PendingInputCount);
        MaximumDistance = Math.Max(MaximumDistance, Session.LocalRider.LongitudinalMeters); MaximumRtt = Math.Max(MaximumRtt, Session.RttMs);
        SumRtt += Session.RttMs; MaximumCorrection = Math.Max(MaximumCorrection, Session.MaximumCorrectionMeters);
    }
    public object Report() => new { ProgressSamples, MaximumPending, MaximumDistance, MaximumRtt, MeanRtt = ProgressSamples > 0 ? SumRtt / ProgressSamples : 0,
        MaximumCorrection, Transport.ConnectAttempts, Transport.SentBytes, Transport.ReceivedBytes, Transport.LargestReceivedBytes, Session.InvalidSnapshots };
}
internal sealed class RaceDriver(List<Participant> clients, ProbeClock clock, CorrectionTrace audit)
{
    private double nextInput;
    public void Pump()
    {
        foreach (var p in clients) { p.Session.Poll(); if (p.Session.Status == SessionStatus.Failed) throw new ProbeFailure("client_session_failed"); }
        int catchup = 0;
        while (clock.NowSeconds >= nextInput && catchup++ < 4)
        {
            nextInput += 1.0 / 60;
            foreach (var p in clients)
            {
                var rider = p.Session.LocalRider; float lane = p.Session.RiderId % 2 == 0 ? 1.8f : -1.8f;
                var track = TrackDefinition.ForCourse(p.Session.Room?.CourseIndex ?? 0, p.Session.Room?.LevelIndex ?? 0);
                float curve = track.CurvatureAt((long)(rider.LongitudinalMeters * 1000)); float speed = rider.SpeedMetersPerSecond * 1000;
                float lateral = Math.Clamp((lane - rider.LateralMeters) * 2000, -6500, 6500);
                float steer = Math.Clamp((lateral + speed * curve / 100000) / (1200 + speed / 6), -1, 1);
                p.Session.Step(1, 0, steer, 0); p.Session.SamplePresentation(); audit.Presented(p.Session);
            }
        }
        if (clock.NowSeconds - nextInput > .15) nextInput = clock.NowSeconds;
    }
}
