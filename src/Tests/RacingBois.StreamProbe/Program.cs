using System.Diagnostics;
using System.Net;
using System.Net.Http;
using System.Net.Security;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Protocol;

int serverPort = args.Length > 0 ? int.Parse(args[0]) : 17977;
int tlsPort = args.Length > 1 ? int.Parse(args[1]) : 17978;
string certPath = args.Length > 2 ? args[2] : "docs/p02/backend/localhost-development-public.cer";
string reportPath = args.Length > 3 ? args[3] : "docs/p02/backend/stream-tls-evidence.json";
var tlsChecks = new List<object>();
var ingressChecks = new List<object>();
var scenarios = new List<object>();
try
{
    await CheckTls("scoped_public_certificate_chain_hostname_pin", "localhost", true, false, true);
    await CheckTls("wrong_fingerprint_rejected", "localhost", true, true, false);
    await CheckTls("wrong_hostname_rejected", "mismatch.invalid", true, false, false);
    await CheckTls("empty_scoped_trust_anchor_rejected", "localhost", true, false, false, emptyTrustAnchor: true);
    await CheckTls("ordinary_os_trust_current_environment", "localhost", false, false, null);
    await SustainedFloodRejected();
    await RunScenario("stream_rtt150", 17981, 75, 0, 0, true, 30, false);
    await RunScenario("stream_rtt250", 17982, 125, 0, 0, true, 30, false);
    await RunScenario("upstream900ms_stall_30hz", 17983, 0, 1500, 900, true, 30, false);
    await RunScenario("upstream900ms_stall_60hz", 17984, 0, 1500, 900, true, 60, false);
    await RunScenario("downstream2600ms_stall_actual_client", 17985, 0, 1500, 2600, false, 60, true);
    await Save("PASS", null);
    return 0;
}
catch (Exception ex) { await Save("FAIL", ex.ToString()); Console.Error.WriteLine(ex); return 1; }

async Task CheckTls(string name, string hostname, bool scoped, bool wrongPin, bool? expectedConnection, bool emptyTrustAnchor = false)
{
    using var trust = new ScopedCertificateTrust(certPath, wrongPin, emptyTrustAnchor);
    using var handler = new SocketsHttpHandler { UseProxy = false };
    handler.ConnectCallback = async (context, token) =>
    {
        // Test route stays on loopback; URI hostname is still validated by the real TLS handshake.
        var tcp = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        await tcp.ConnectAsync(IPAddress.Loopback, tlsPort, token);
        return new NetworkStream(tcp, ownsSocket: true);
    };
    if (scoped) handler.SslOptions.RemoteCertificateValidationCallback = trust.Validate;
    using var invoker = new HttpMessageInvoker(handler, disposeHandler: false);
    using var socket = new ClientWebSocket();
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(8));
    bool connected = false, acknowledged = false; string observedError = null;
    try
    {
        await socket.ConnectAsync(new Uri($"wss://{hostname}:{tlsPort}/ws"), invoker, timeout.Token);
        connected = true;
        await ProbeWire.Send(socket, new HelloMessage(), timeout.Token);
        var welcome = JsonSerializer.Deserialize<WelcomeMessage>(await ProbeWire.Receive(socket, timeout.Token), ProbeWire.Options);
        await ProbeWire.Send(socket, new InputMessage { playerId = welcome.playerId, sequence = 1, throttle = 1 }, timeout.Token);
        for (int i = 0; i < 20; i++)
        {
            var snapshot = JsonSerializer.Deserialize<SnapshotMessage>(await ProbeWire.Receive(socket, timeout.Token), ProbeWire.Options);
            if (snapshot.kind == "snapshot" && snapshot.ackSequence == 1) { acknowledged = true; break; }
        }
    }
    catch (Exception ex) when (ex is WebSocketException or HttpRequestException or System.Security.Authentication.AuthenticationException) { observedError = ex.GetType().Name; }
    bool pass = (!expectedConnection.HasValue || connected == expectedConnection.Value) && (!connected || acknowledged);
    string status = pass ? expectedConnection.HasValue ? "PASS" : "OBSERVED" : "FAIL";
    tlsChecks.Add(new { name, hostname, expectedConnection, connected, authoritativeAckObserved = acknowledged,
        trustMode = scoped ? emptyTrustAnchor ? "empty_custom_anchor_set" : "supplied_public_certificate_anchor" : "unchanged_operating_system_trust",
        expectedCertificateSha256Pin = scoped ? trust.PublicSha256 : null, status, observedError });
    Console.WriteLine($"{status} {name}: connected={connected}");
    if (!pass) throw new InvalidOperationException(name);
    await Task.Delay(100);
}

async Task SustainedFloodRejected()
{
    using var socket = new ClientWebSocket();
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(6));
    await socket.ConnectAsync(new Uri($"ws://127.0.0.1:{serverPort}/ws"), timeout.Token);
    await ProbeWire.Send(socket, new HelloMessage(), timeout.Token);
    string id = JsonSerializer.Deserialize<WelcomeMessage>(await ProbeWire.Receive(socket, timeout.Token), ProbeWire.Options).playerId;
    bool closed = false; int sent = 0;
    var clock = Stopwatch.StartNew();
    var receive = Task.Run(async () =>
    {
        try { while (await ProbeWire.Receive(socket, timeout.Token) != null) { } }
        catch (Exception ex) when (ex is OperationCanceledException or WebSocketException) { }
        finally { closed = true; }
    }, timeout.Token);
    while (!closed && clock.Elapsed.TotalSeconds < 4)
    {
        // Batch four intents because Windows timer granularity may turn Task.Delay(2) into ~16ms.
        // The measured send count/rate is recorded; this remains a sustained flood above 90/s.
        try { for (int batch = 0; batch < 4; batch++) await ProbeWire.Send(socket, new InputMessage { playerId = id, sequence = ++sent, throttle = 1 }, timeout.Token); }
        catch (WebSocketException) { break; }
        await Task.Delay(2, timeout.Token);
    }
    bool pass = closed && sent >= 180 && clock.Elapsed.TotalSeconds < 4;
    ingressChecks.Add(new { name = "sustained_valid_shape_owned_input_flood_disconnected", status = pass ? "PASS" : "FAIL", sentInputs = sent, elapsedMilliseconds = Math.Round(clock.Elapsed.TotalMilliseconds, 2), closed, burstCapacity = 180, sustainedRatePerSecond = 90, queueCapacityUnchanged = 256 });
    await timeout.CancelAsync(); socket.Abort(); await receive;
    if (!pass) throw new InvalidOperationException("Sustained flood was not rejected.");
    Console.WriteLine($"PASS sustained flood rejected after {sent} inputs / {clock.Elapsed.TotalMilliseconds:F1}ms.");
    await Task.Delay(100);
}

async Task RunScenario(string name, int proxyPort, int delay, int stallStart, int stallDuration, bool upstream, int inputRate, bool actualClient)
{
    await using var proxy = new OrderedStreamProxy(proxyPort, serverPort, delay, stallStart, stallDuration, upstream);
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(12));
    var observations = new System.Collections.Concurrent.ConcurrentQueue<(double Time, SnapshotMessage Snapshot)>();
    using var observer = new ClientWebSocket();
    await observer.ConnectAsync(new Uri($"ws://127.0.0.1:{serverPort}/ws"), timeout.Token);
    await ProbeWire.Send(observer, new HelloMessage(), timeout.Token);
    await ProbeWire.Receive(observer, timeout.Token);
    var observerReader = Task.Run(async () =>
    {
        try
        {
            while (!timeout.IsCancellationRequested)
            {
                string text = await ProbeWire.Receive(observer, timeout.Token);
                if (text == null) break;
                var snapshot = JsonSerializer.Deserialize<SnapshotMessage>(text, ProbeWire.Options);
                if (snapshot.kind == "snapshot") observations.Enqueue((proxy.Clock.Elapsed.TotalMilliseconds, snapshot));
            }
        }
        catch (Exception ex) when (ex is OperationCanceledException or WebSocketException) { }
    }, timeout.Token);
    string id; long previousTick = -1; bool monotonic = true, closed = false;
    double maxGap = 0, previousSnapshotTime = 0, failedAt = 0, previousAckProgressTime = 0, maximumAckProgressSilence = 0;
    int snapshots = 0, maxPending = 0, sent = 0;
    string clientFailure = null;
    var acknowledgements = new List<double>();
    var sentAt = new Dictionary<int, double>();
    using var native = new ClientWebSocket();
    var incoming = new System.Collections.Concurrent.ConcurrentQueue<string>();
    Task receiver = Task.CompletedTask;
    using var adapter = new ProbeTransport();
    using var session = new FoundationSession(adapter, new ProbeCodec());
    if (actualClient)
    {
        session.Connect($"ws://127.0.0.1:{proxyPort}/ws");
        while (session.Status == SessionStatus.Connecting && !timeout.IsCancellationRequested) { adapter.Poll(); await Task.Delay(2, timeout.Token); }
        if (session.Status != SessionStatus.Connected) throw new InvalidOperationException("Application did not connect.");
        id = session.PlayerId;
    }
    else
    {
        await native.ConnectAsync(new Uri($"ws://127.0.0.1:{proxyPort}/ws"), timeout.Token);
        await ProbeWire.Send(native, new HelloMessage(), timeout.Token);
        id = JsonSerializer.Deserialize<WelcomeMessage>(await ProbeWire.Receive(native, timeout.Token), ProbeWire.Options).playerId;
        receiver = Task.Run(async () =>
        {
            try
            {
                while (!timeout.IsCancellationRequested)
                {
                    string text = await ProbeWire.Receive(native, timeout.Token);
                    if (text == null) break;
                    incoming.Enqueue(text);
                }
            }
            catch (Exception ex) when (ex is OperationCanceledException or WebSocketException) { }
            finally { closed = true; }
        }, timeout.Token);
    }
    proxy.Clock.Start();
    double nextInput = 0; int lastAck = 0;
    while (proxy.Clock.Elapsed.TotalSeconds < 6.2)
    {
        double now = proxy.Clock.Elapsed.TotalMilliseconds;
        if (actualClient)
        {
            adapter.Poll();
            var world = session.LatestWorld;
            if (world != null && world.Tick > previousTick) Observe(world.Tick, world.AcknowledgedInputSequence, now);
            if (session.Status == SessionStatus.Failed && failedAt == 0) { failedAt = now; clientFailure = session.Error; }
        }
        else while (incoming.TryDequeue(out string text))
        {
            var snapshot = JsonSerializer.Deserialize<SnapshotMessage>(text, ProbeWire.Options);
            if (snapshot.kind == "snapshot") Observe(snapshot.tick, snapshot.ackSequence, now);
        }
        if (now >= nextInput)
        {
            nextInput += 1000.0 / inputRate;
            if (actualClient) { session.Step(1, 0, 0); sent = session.SentInputs; maxPending = Math.Max(maxPending, session.PendingCount); }
            else if (!closed && native.State == WebSocketState.Open)
            {
                sentAt[++sent] = now;
                try { await ProbeWire.Send(native, new InputMessage { playerId = id, sequence = sent, throttle = 1 }, timeout.Token); }
                catch (WebSocketException) { closed = true; }
            }
        }
        await Task.Delay(2, timeout.Token);
    }
    var recorded = observations.ToArray();
    var movement = recorded.Select(item => new { item.Time, Entity = item.Snapshot.entities.FirstOrDefault(e => e.id == id) }).Where(item => item.Entity != null).ToArray();
    bool decelerated = movement.Zip(movement.Skip(1)).Any(pair => pair.First.Time >= stallStart + 450 && pair.Second.Time <= stallStart + stallDuration + 100 && pair.Second.Entity.speed < pair.First.Entity.speed);
    bool released = recorded.Any(item => item.Time > Math.Max(4500, failedAt + 300) && item.Snapshot.entities.All(e => e.id != id));
    double[] latencies = acknowledgements.Order().ToArray();
    scenarios.Add(new
    {
        name, loopbackProxyPort = proxyPort, client = actualClient ? "actual FoundationSession with native test adapter" : "native ClientWebSocket",
        inputRate, delayPerDirectionPerStreamReadMilliseconds = delay, streamReadBufferBytes = 8192,
        streamStall = new { direction = upstream ? "client_to_server" : "server_to_client", startMilliseconds = stallStart, durationMilliseconds = stallDuration },
        sentInputs = sent, snapshots, snapshotsMonotonic = monotonic, maximumObservedSnapshotGapMilliseconds = Math.Round(maxGap, 2),
        maximumSnapshotSilenceIncludingEndMilliseconds = Math.Round(Math.Max(maxGap, proxy.Clock.Elapsed.TotalMilliseconds - previousSnapshotTime), 2),
        maximumAckProgressSilenceMilliseconds = Math.Round(Math.Max(maximumAckProgressSilence, proxy.Clock.Elapsed.TotalMilliseconds - previousAckProgressTime), 2),
        ackAgeMilliseconds = new { samples = latencies.Length, p95 = Percentile(latencies, .95), maximum = latencies.LastOrDefault() },
        authorityCoastingDuringUpstreamStall = decelerated, serverClosedConnection = closed,
        clientFailedAtMilliseconds = Math.Round(failedAt, 2), clientFailure, maximumPendingInputs = maxPending, serverReleasedSlotBeforeProbeEnd = released,
        proxyUpstreamBytes = proxy.ForwardedUpstreamBytes, proxyDownstreamBytes = proxy.ForwardedDownstreamBytes,
        interpretation = actualClient ? "An ordered downstream stall exhausts the real application pending-input bound; fails closed and releases its slot." : closed ? "Transport backlog can trigger ingress burst protection for an otherwise valid fixed-rate input source; this is a P05 gate, not acceptable production recovery." : "Ordered stream delay/stall observed; no packet loss or WAN emulation is claimed."
    });
    if (!monotonic || snapshots == 0) throw new InvalidOperationException(name + " lacks valid monotonic snapshots.");
    if (actualClient && (failedAt == 0 || maxPending > 120 || !released)) throw new InvalidOperationException("Application did not enforce bounded stale-input recovery.");
    if (upstream && stallDuration > 0 && !decelerated) throw new InvalidOperationException("Server did not coast on stale upstream input.");
    if (!actualClient && closed) throw new InvalidOperationException("Valid fixed-rate input was disconnected after ordered-stream delay/stall.");
    Console.WriteLine($"OBSERVED {name}: maxgap={maxGap:F1}ms, coast={decelerated}, closed={closed}, pending={maxPending}, failedAt={failedAt:F1}ms.");
    await timeout.CancelAsync(); native.Abort(); observer.Abort(); adapter.Close();
    await Task.WhenAll(receiver, observerReader);
    await Task.Delay(200);

    void Observe(long tick, int ackSequence, double now)
    {
        monotonic &= tick > previousTick;
        previousTick = tick; snapshots++;
        if (previousSnapshotTime > 0) maxGap = Math.Max(maxGap, now - previousSnapshotTime);
        previousSnapshotTime = now;
        if (ackSequence > lastAck)
        {
            if (previousAckProgressTime > 0) maximumAckProgressSilence = Math.Max(maximumAckProgressSilence, now - previousAckProgressTime);
            previousAckProgressTime = now;
            if (sentAt.TryGetValue(ackSequence, out double issued)) acknowledgements.Add(now - issued);
        }
        lastAck = Math.Max(lastAck, ackSequence);
    }
}
static double Percentile(double[] values, double fraction) => values.Length == 0 ? 0 : Math.Round(values[Math.Min(values.Length - 1, (int)Math.Ceiling(values.Length * fraction) - 1)], 2);
async Task Save(string status, string error)
{
    var report = new { generatedUtc = DateTimeOffset.UtcNow, status, error, scope = "Scoped native WSS validation and raw TCP byte-stream forwarding delay/stalls on loopback. This is not IP packet-loss/retransmission, real WAN, browser TLS acceptance, or complete bandwidth/backpressure profiling. PASS requires valid 30/60Hz streams recover after the 900ms upstream stall; the 2.6s downstream stall intentionally exercises bounded application fail-closed behavior.", certificateTrust = "Only the supplied public certificate is a custom trust anchor; SHA256 pin, real TLS hostname verification, validity and server-auth chain checks are required. No OS trust mutation/private key export/insecure bypass.", tlsChecks, ingressChecks, scenarios };
    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(reportPath)));
    await File.WriteAllTextAsync(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
}
