using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

internal static class LiveRaceProbe
{
    public static async Task<int> Run(string endpoint, string reportPath)
    {
        var sessions = new List<RaceSession>(); var observations = new List<Observation>();
        var checks = new List<object>(); string failure = null;
        float? attackLateralSeparation = null, attackLongitudinalSeparation = null;
        int? firstAttackClientStep = null;
        try
        {
            for (int i = 0; i < 8; i++)
            {
                var session = new RaceSession(new ProbeSocketTransport(), new TestCodec());
                sessions.Add(session); observations.Add(new Observation()); session.Connect(endpoint);
            }
            await Until(() => sessions.All(session => session.Status == SessionStatus.Connected), 5000);
            sessions.Sort((left, right) => left.RiderId.CompareTo(right.RiderId));
            Check(sessions.Select(session => session.RiderId).Distinct().Count() == 8, "eight_unique_human_riders");
            using (var ninth = new ClientWebSocket())
            {
                await ninth.ConnectAsync(new Uri(endpoint), CancellationToken.None); await Send(ninth, new RaceHelloMessage());
                var message = await Receive(ninth); var error = JsonSerializer.Deserialize<ErrorMessage>(message, TestCodec.Options);
                Check(error?.code == "match_full", "ninth_race_peer_rejected");
            }
            var timer = Stopwatch.StartNew(); int steps = 0; bool combatObserved = false;
            while (steps < 360)
            {
                foreach (var session in sessions) session.Poll();
                if (timer.Elapsed.TotalSeconds >= steps / 60.0)
                {
                    var attacker = sessions[0].LocalRider; var victim = sessions[1].LocalRider;
                    combatObserved |= sessions[0].LatestWorld != null && sessions[0].LatestWorld.Events.Any(item =>
                        item.Kind == RaceEventKind.Hit && item.SourceId == attacker.Id && item.TargetId == victim.Id);
                    float targetSteer = 0; int attackSide = 0;
                    if (!combatObserved && attacker.Id != 0 && victim.Id != 0)
                    {
                        float lateral = victim.LateralMeters - attacker.LateralMeters;
                        float longitudinal = victim.LongitudinalMeters - attacker.LongitudinalMeters;
                        // Network input samples are not simulation ticks. Establish range from observations,
                        // including steering filter settling, instead of assuming 18 sends move a fixed distance.
                        targetSteer = lateral > 1.35f ? -.65f : lateral < 1.12f ? .65f : 0;
                        if (lateral > 1.05f && lateral < 1.55f && Math.Abs(longitudinal) < 1 && attacker.Mode == RiderMode.Riding)
                        {
                            attackSide = 1;
                            if (!firstAttackClientStep.HasValue)
                            { firstAttackClientStep = steps; attackLateralSeparation = lateral; attackLongitudinalSeparation = longitudinal; }
                        }
                    }
                    for (int i = 0; i < sessions.Count; i++)
                    {
                        var session = sessions[i];
                        session.Step(combatObserved && steps >= 70 ? 1 : 0, 0, i == 1 ? targetSteer : 0, i == 0 ? attackSide : 0);
                        Record(session, observations[i], sessions[0].RiderId, sessions[1].RiderId);
                    }
                    steps++;
                }
                else await Task.Delay(1);
                if (sessions.Any(session => session.Status != SessionStatus.Connected))
                    throw new InvalidOperationException("Session failed: " + string.Join("; ", sessions.Select(s => s.Error)));
            }
            await Until(() => sessions.All(session => session.PendingCount <= 3), 1000);
            for (int i = 0; i < sessions.Count; i++) Record(sessions[i], observations[i], sessions[0].RiderId, sessions[1].RiderId);
            Check(observations.All(value => value.Snapshots > 30 && value.Monotonic && value.SawEight), "eight_peers_receive_monotonic_authority_snapshots");
            Check(observations.All(value => value.SawPedestrians), "all_peers_observe_authoritative_pedestrians");
            Check(sessions.All(session => session.LocalRider.LongitudinalMeters > 10 && session.LatestWorld.AcknowledgedInputSequence >= 350), "movement_and_ack_from_actual_client_application");
            Check(observations[0].Hits.Count > 0 && observations[0].Hits.Overlaps(observations[1].Hits), "same_authoritative_hit_event_reaches_both_humans");
            Check(observations[1].MinimumOwnHealth <= GameplayRules.InitialHealth - 448, "remote_target_receives_fist_damage");
            foreach (var session in sessions) session.Dispose(); sessions.Clear();
            await Task.Delay(150);
            using var malformed = new ClientWebSocket(); await malformed.ConnectAsync(new Uri(endpoint), CancellationToken.None);
            await Send(malformed, new RaceHelloMessage()); var welcome = JsonSerializer.Deserialize<RaceWelcomeMessage>(await Receive(malformed), TestCodec.Options);
            string injection = JsonSerializer.Serialize(new RaceInputMessage { playerId = welcome.playerId, sequence = 1 }, TestCodec.Options).TrimEnd('}') + ",\"damage\":999999}";
            await malformed.SendAsync(Encoding.UTF8.GetBytes(injection), WebSocketMessageType.Text, true, CancellationToken.None);
            bool closed = false;
            for (int i = 0; i < 20 && !closed; i++) closed = await Receive(malformed) == null;
            Check(closed, "wire_damage_injection_closes_connection");
        }
        catch (Exception ex) { failure = ex.Message; }
        finally { foreach (var session in sessions) session.Dispose(); }
        var report = new { generatedUtc = DateTimeOffset.UtcNow, status = failure == null ? "PASS" : "FAIL", endpoint,
            humanPeers = 8, protocolVersion = RaceProtocol.Version, simulationRulesVersion = RaceProtocol.SimulationRulesVersion,
            contentHash = RaceProtocol.ContentHash, checks, observations = observations.Select(value => new { value.Snapshots, value.SawEight, value.SawPedestrians,
                value.Monotonic, value.MinimumOwnHealth, distinctHitEventIds = value.Hits.Order().ToArray() }),
            combatSetup = new { firstAttackClientStep, attackLateralSeparationMeters = attackLateralSeparation,
                attackLongitudinalSeparationMeters = attackLongitudinalSeparation, control = "Steer from validated authority observations, then attack within strict reach." },
            error = failure, scope = "Real loopback WebSocket and actual RaceSession source. This is not browser rendering, WAN latency or separate LAN machines." };
        string json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(reportPath))); await File.WriteAllTextAsync(reportPath, json);
        Console.WriteLine(json); return failure == null ? 0 : 1;

        void Check(bool condition, string name) { checks.Add(new { name, passed = condition }); if (!condition) throw new InvalidOperationException(name); }
        async Task Until(Func<bool> condition, int timeout)
        {
            var watch = Stopwatch.StartNew();
            while (!condition())
            {
                foreach (var session in sessions) session.Poll();
                if (sessions.Any(s => s.Status == SessionStatus.Failed)) throw new InvalidOperationException(string.Join(";", sessions.Select(s => s.Error)));
                if (watch.ElapsedMilliseconds > timeout) throw new TimeoutException("Race session condition timed out.");
                await Task.Delay(2);
            }
        }
    }

    private static void Record(RaceSession session, Observation observation, int attackerId, int victimId)
    {
        var world = session.LatestWorld; if (world == null || world.Tick == observation.LastTick) return;
        observation.Monotonic &= world.Tick > observation.LastTick; observation.LastTick = world.Tick; observation.Snapshots++;
        observation.SawEight |= world.Riders.Count(rider => rider.Kind == RiderKind.Player) == 8;
        observation.SawPedestrians |= world.Pedestrians.Count > 0;
        observation.MinimumOwnHealth = Math.Min(observation.MinimumOwnHealth, session.LocalRider.Health);
        foreach (var item in world.Events)
            if (item.Kind == RaceEventKind.Hit && item.SourceId == attackerId && item.TargetId == victimId) observation.Hits.Add(item.Id);
    }
    private static Task Send(ClientWebSocket socket, object message) => socket.SendAsync(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(message, message.GetType(), TestCodec.Options)), WebSocketMessageType.Text, true, CancellationToken.None);
    private static async Task<string> Receive(ClientWebSocket socket)
    {
        using var timeout = new CancellationTokenSource(3000); var bytes = new byte[32768]; int count = 0;
        while (true)
        {
            var result = await socket.ReceiveAsync(new ArraySegment<byte>(bytes, count, bytes.Length - count), timeout.Token);
            if (result.MessageType == WebSocketMessageType.Close) return null;
            count += result.Count;
            if (result.EndOfMessage) return Encoding.UTF8.GetString(bytes, 0, count);
            if (count == bytes.Length) throw new InvalidOperationException("Snapshot exceeds client transport budget.");
        }
    }
    private sealed class Observation
    {
        public long LastTick = -1;
        public int Snapshots, MinimumOwnHealth = GameplayRules.InitialHealth;
        public bool SawEight, SawPedestrians, Monotonic = true;
        public readonly HashSet<long> Hits = new();
    }

    private sealed class ProbeSocketTransport : IRealtimeTransport
    {
        private readonly ConcurrentQueue<Action> callbacks = new();
        private ClientWebSocket socket;
        private CancellationTokenSource lifetime;
        public event Action Opened;
        public event Action<string> Message;
        public event Action<string> Closed;
        public void Connect(string endpoint)
        {
            Close(); socket = new ClientWebSocket(); lifetime = new CancellationTokenSource();
            var current = socket; var cancellation = lifetime.Token;
            _ = Task.Run(async () =>
            {
                try
                {
                    await current.ConnectAsync(new Uri(endpoint), cancellation);
                    callbacks.Enqueue(() => { if (socket == current) Opened?.Invoke(); });
                    while (!cancellation.IsCancellationRequested && current.State == WebSocketState.Open)
                    {
                        string text = await Receive(current); if (text == null) break;
                        callbacks.Enqueue(() => { if (socket == current) Message?.Invoke(text); });
                    }
                }
                catch (Exception ex) when (ex is WebSocketException or OperationCanceledException or ObjectDisposedException) { }
                finally { callbacks.Enqueue(() => { if (socket == current) Closed?.Invoke("Transport closed."); }); }
            }, cancellation);
        }
        public void Send(string text)
        {
            if (socket?.State == WebSocketState.Open)
                socket.SendAsync(Encoding.UTF8.GetBytes(text), WebSocketMessageType.Text, true, lifetime.Token).GetAwaiter().GetResult();
        }
        public void Close() { var old = socket; socket = null; lifetime?.Cancel(); old?.Dispose(); lifetime?.Dispose(); lifetime = null; }
        public void Poll() { while (callbacks.TryDequeue(out var action)) action(); }
        public void Dispose() => Close();
    }
}
