using System.Diagnostics;
using System.Net.WebSockets;
using System.Text.Json;
using RacingBois.Protocol;

string endpoint = args.Length > 0 ? args[0] : "ws://127.0.0.1:17877/ws";
string output = args.Length > 1 ? args[1] : "docs/p02/backend/transport-evidence.json";
var options = new JsonSerializerOptions { IncludeFields = true };
var reports = new List<object>();
var matrix = new[] { new Scenario("loopback", 0, 0, 0), new Scenario("rtt150_jitter20_drop2pct", 150, 20, 0.02), new Scenario("rtt250_jitter40_drop5pct", 250, 40, 0.05) };
var checks = new List<object>();
try
{
    await ProtocolAbuseChecks();
    foreach (var scenario in matrix)
    {
        var peers = new List<ProbePeer>();
        for (int i = 0; i < 8; i++) peers.Add(await Connect());
        using (var ninth = new ClientWebSocket())
        {
            await ninth.ConnectAsync(new Uri(endpoint), CancellationToken.None);
            await Send(ninth, new HelloMessage());
            var full = JsonSerializer.Deserialize<ErrorMessage>((await Receive(ninth))!, options)!;
            Check(full.code == "match_full", "ninth_peer_rejected");
        }
        var samples = await Task.WhenAll(peers.Select((peer, index) => RunPeer(peer, scenario, index)));
        foreach (var peer in peers) peer.Socket.Dispose();
        double[] latency = samples.SelectMany(s => s.Latencies).Order().ToArray();
        reports.Add(new
        {
            scenario = scenario.Name, syntheticPeers = peers.Count, durationSeconds = 7,
            nominalApplicationRttMilliseconds = scenario.Rtt, applicationJitterMillisecondsPerDirection = scenario.Jitter,
            applicationMessageDropProbabilityPerDirection = scenario.Drop,
            acceptedInputObservations = latency.Length, ackLatencyMilliseconds = new { p50 = Percentile(latency, .50), p95 = Percentile(latency, .95), maximum = latency.LastOrDefault() },
            maximumPresentedSnapshotGapMilliseconds = samples.Max(s => s.MaximumGap),
            snapshotsPresented = samples.Sum(s => s.Snapshots), inputsDroppedBeforeSend = samples.Sum(s => s.InputDrops), snapshotsDroppedAfterReceive = samples.Sum(s => s.SnapshotDrops),
            allPeersObservedEightEntities = samples.All(s => s.SawEight), snapshotsMonotonic = samples.All(s => s.Monotonic), allPeersAdvanced = samples.All(s => s.LastDistance > 1),
            status = samples.All(s => s.Monotonic && s.SawEight && s.LastDistance > 1 && s.Latencies.Count > 0) ? "PASS" : "FAIL"
        });
        if (samples.Any(s => !s.Monotonic || !s.SawEight || s.LastDistance <= 1 || s.Latencies.Count == 0)) throw new InvalidOperationException("Transport scenario failed.");
        Console.WriteLine($"PASS {scenario.Name}: 8 peers; ack p95 {Percentile(latency, .95):F1} ms.");
        await Task.Delay(300);
    }
    await WriteReport("PASS", null);
    return 0;
}
catch (Exception ex) { await WriteReport("FAIL", ex.ToString()); Console.Error.WriteLine(ex); return 1; }

async Task<ProbePeer> Connect()
{
    var socket = new ClientWebSocket();
    await socket.ConnectAsync(new Uri(endpoint), CancellationToken.None);
    await Send(socket, new HelloMessage());
    var welcome = JsonSerializer.Deserialize<WelcomeMessage>((await Receive(socket))!, options)!;
    if (welcome.kind != "welcome" || string.IsNullOrWhiteSpace(welcome.playerId)) throw new InvalidOperationException("No welcome.");
    return new ProbePeer(socket, welcome.playerId);
}

async Task ProtocolAbuseChecks()
{
    using (var incompatible = new ClientWebSocket())
    {
        await incompatible.ConnectAsync(new Uri(endpoint), CancellationToken.None);
        await Send(incompatible, new HelloMessage { protocolVersion = 999 });
        var error = JsonSerializer.Deserialize<ErrorMessage>((await Receive(incompatible))!, options)!;
        Check(error.code == "version_mismatch", "version_mismatch_rejected");
    }
    var peer = await Connect();
    using (peer.Socket)
    {
        await Send(peer.Socket, new InputMessage { playerId = "another-player", sequence = 1, throttle = 1 });
        await ExpectError(peer.Socket, "not_owner");
        await Send(peer.Socket, new InputMessage { playerId = peer.Id, sequence = 1, throttle = 2 });
        await ExpectError(peer.Socket, "input_out_of_range");
        await Send(peer.Socket, new InputMessage { playerId = peer.Id, sequence = 1, throttle = 1 });
        await Send(peer.Socket, new InputMessage { playerId = peer.Id, sequence = 1, throttle = 1 });
        await ExpectError(peer.Socket, "invalid_sequence");
    }
    var malformed = await Connect();
    using (malformed.Socket)
    {
        await malformed.Socket.SendAsync("{\"kind\":\"input\",\"sequence\":1}"u8.ToArray(), WebSocketMessageType.Text, true, CancellationToken.None);
        byte[]? reply;
        do { reply = await Receive(malformed.Socket); } while (reply != null);
        Check(true, "missing_fields_closed");
    }
    await Task.Delay(200);
}

async Task ExpectError(ClientWebSocket socket, string expected)
{
    for (int i = 0; i < 40; i++)
    {
        var data = await Receive(socket) ?? throw new InvalidOperationException("Peer closed before rejection.");
        var error = JsonSerializer.Deserialize<ErrorMessage>(data, options)!;
        if (error.kind == "error") { Check(error.code == expected, expected + "_rejected"); return; }
    }
    throw new InvalidOperationException("No rejection received.");
}

async Task<Sample> RunPeer(ProbePeer peer, Scenario scenario, int index)
{
    var sample = new Sample();
    var randomSend = new Random(1301 + index);
    var randomReceive = new Random(2301 + index);
    var clock = Stopwatch.StartNew();
    var sentAt = new System.Collections.Concurrent.ConcurrentDictionary<int, double>();
    var inbound = System.Threading.Channels.Channel.CreateUnbounded<(byte[], double)>();
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(12));
    var receiver = Task.Run(async () =>
    {
        try
        {
            while (!timeout.IsCancellationRequested)
            {
                var bytes = await Receive(peer.Socket, timeout.Token);
                if (bytes == null) break;
                if (randomReceive.NextDouble() < scenario.Drop) { Interlocked.Increment(ref sample.SnapshotDrops); continue; }
                double due = clock.Elapsed.TotalMilliseconds + Delay(randomReceive, scenario);
                await inbound.Writer.WriteAsync((bytes, due), timeout.Token);
            }
        }
        catch (OperationCanceledException) when (timeout.IsCancellationRequested) { }
        finally { inbound.Writer.TryComplete(); }
    });
    var pendingSend = new Queue<(InputMessage Input, double Due)>();
    // FIFO delivery is intentional: this WebSocket application delay proxy preserves TCP order.
    var pendingReceive = new Queue<(byte[] Bytes, double Due)>();
    double nextInput = 0, lastPresented = 0;
    long lastTick = -1;
    int sequence = 0, lastAck = 0;
    while (clock.Elapsed.TotalSeconds < 7)
    {
        double now = clock.Elapsed.TotalMilliseconds;
        if (now >= nextInput)
        {
            nextInput = now + 1000.0 / 30;
            var input = new InputMessage { playerId = peer.Id, sequence = ++sequence, throttle = 1, steer = index % 2 == 0 ? 0.1f : -0.1f };
            if (randomSend.NextDouble() < scenario.Drop) sample.InputDrops++;
            else { sentAt[input.sequence] = now; pendingSend.Enqueue((input, now + Delay(randomSend, scenario))); }
        }
        while (pendingSend.TryPeek(out var scheduled) && scheduled.Due <= now)
        {
            pendingSend.Dequeue();
            await Send(peer.Socket, scheduled.Input);
        }
        while (inbound.Reader.TryRead(out var item)) pendingReceive.Enqueue(item);
        while (pendingReceive.TryPeek(out var item) && item.Due <= now)
        {
            pendingReceive.Dequeue();
            var snapshot = JsonSerializer.Deserialize<SnapshotMessage>(item.Bytes, options)!;
            if (snapshot.kind == "error") continue;
            if (snapshot.kind != "snapshot") throw new InvalidOperationException("Unexpected message.");
            sample.Monotonic &= snapshot.tick > lastTick;
            lastTick = snapshot.tick;
            sample.SawEight |= snapshot.entities.Length == 8;
            var own = snapshot.entities.Single(e => e.id == peer.Id);
            if (!float.IsFinite(own.s) || own.speed < 0 || own.speed > 60 || Math.Abs(own.d) > 6) throw new InvalidOperationException("Authoritative state outside bounds.");
            sample.LastDistance = own.s;
            sample.Snapshots++;
            if (lastPresented > 0) sample.MaximumGap = Math.Max(sample.MaximumGap, now - lastPresented);
            lastPresented = now;
            if (snapshot.ackSequence > lastAck && sentAt.TryGetValue(snapshot.ackSequence, out double issued)) sample.Latencies.Add(now - issued);
            lastAck = Math.Max(lastAck, snapshot.ackSequence);
        }
        await Task.Delay(2, timeout.Token);
    }
    await timeout.CancelAsync();
    peer.Socket.Abort();
    try { await receiver; } catch (WebSocketException) { }
    return sample;
}

async Task Send(ClientWebSocket socket, object value) => await socket.SendAsync(JsonSerializer.SerializeToUtf8Bytes(value, value.GetType(), options), WebSocketMessageType.Text, true, CancellationToken.None);
static async Task<byte[]?> Receive(ClientWebSocket socket, CancellationToken token = default)
{
    using var limit = CancellationTokenSource.CreateLinkedTokenSource(token);
    limit.CancelAfter(TimeSpan.FromSeconds(5));
    byte[] buffer = new byte[16384]; int count = 0;
    while (true)
    {
        var result = await socket.ReceiveAsync(buffer.AsMemory(count), limit.Token);
        if (result.MessageType == WebSocketMessageType.Close) return null;
        count += result.Count;
        if (result.EndOfMessage) return buffer.AsSpan(0, count).ToArray();
        if (count == buffer.Length) throw new InvalidDataException("Oversized server frame.");
    }
}
void Check(bool pass, string name) { checks.Add(new { name, status = pass ? "PASS" : "FAIL" }); if (!pass) throw new InvalidOperationException(name); }
static double Delay(Random random, Scenario scenario) => Math.Max(0, scenario.Rtt / 2.0 + (random.NextDouble() * 2 - 1) * scenario.Jitter);
static double Percentile(double[] values, double percentile) => values.Length == 0 ? 0 : Math.Round(values[Math.Min(values.Length - 1, (int)Math.Ceiling(values.Length * percentile) - 1)], 2);
async Task WriteReport(string status, string? failure)
{
    var report = new { generatedUtc = DateTimeOffset.UtcNow, endpoint, status, failure, scope = "Eight native ClientWebSocket synthetic peers on loopback; application-layer scheduling/drop. NOT TCP packet loss, router emulation, real WAN, Unity browser throughput, or head-of-line blocking measurement. WSS uses normal certificate validation when endpoint is wss.", tickRate = 60, inputRate = 30, snapshotRate = 20, checks, scenarios = reports };
    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
    await File.WriteAllTextAsync(output, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
}
record Scenario(string Name, int Rtt, int Jitter, double Drop);
record ProbePeer(ClientWebSocket Socket, string Id);
sealed class Sample
{
    public readonly List<double> Latencies = [];
    public int InputDrops, SnapshotDrops, Snapshots;
    public bool Monotonic = true, SawEight;
    public double MaximumGap, LastDistance;
}
