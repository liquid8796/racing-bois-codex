using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Protocol;
using RacingBois.Simulation;

/// <summary>Links the actual Unity application source; no Unity API or duplicate session implementation.</summary>
internal static class ClientSessionTests
{
    public static void Register(Action<string, Action> test)
    {
        test("client_handshake_sends_versions_and_rejects_mismatch", () =>
        {
            foreach (var mismatch in new[] { new WelcomeMessage { protocolVersion = 2 }, new WelcomeMessage { simulationRulesVersion = 2 }, new WelcomeMessage { contentHash = "wrong" }, new WelcomeMessage { tickRate = 30 } })
            {
                var transport = new FakeTransport();
                using var session = new FoundationSession(transport, new FieldCodec());
                session.Connect("ws://test/ws");
                transport.EmitOpen();
                var hello = JsonSerializer.Deserialize<HelloMessage>(transport.Sent.Single(), FieldCodec.Options);
                Require(hello.kind == "hello" && hello.protocolVersion == 1, "Handshake missing version.");
                transport.Emit(mismatch);
                Require(session.Status == SessionStatus.Failed && session.PlayerId == "", "Mismatched handshake accepted.");
                Require(transport.CloseCalls >= 2, "Version rejection did not close transport.");
            }
        });
        test("client_ignores_stale_and_foreign_snapshots", () =>
        {
            var (session, transport) = Connected(); using (session)
            {
                transport.Emit(Snapshot(10, 0, 10));
                long distance = session.PredictedState.DistanceMillimeters;
                transport.Emit(Snapshot(9, 0, 999));
                transport.Emit(new SnapshotMessage { playerId = "foreign", tick = 20, entities = [new EntitySnapshot { id = "foreign", s = 999 }] });
                Require(session.LatestWorld.Tick == 10 && session.PredictedState.DistanceMillimeters == distance, "Stale/foreign snapshot changed state.");
            }
        });
        test("client_ack_clears_only_confirmed_inputs_and_replays_pending", () =>
        {
            var (session, transport) = Connected(); using (session)
            {
                session.Step(1, 0, 0); session.Step(1, 0, 0); session.Step(1, 0, 0);
                transport.Emit(Snapshot(2, 2, 0.01f, 0.4f));
                var expected = RoadSpaceSimulation.Step(new RiderState { DistanceMillimeters = 10, SpeedMillimetersPerSecond = 400 }, new RiderInput(1000, 0, 0));
                Require(session.PendingCount == 1, "ACK removed wrong inputs.");
                Require(session.PredictedState.DistanceMillimeters == expected.DistanceMillimeters, "Pending input not replayed once.");
                transport.Emit(Snapshot(3, 3, 0.02f, 0.6f));
                Require(session.PendingCount == 0, "Confirmed queue not released.");
            }
        });
        test("client_no_ack_queue_is_bounded_and_reconnect_resets_identity", () =>
        {
            var (session, transport) = Connected(); using (session)
            {
                for (int i = 0; i < 121; i++) session.Step(1, 0, 0);
                Require(session.Status == SessionStatus.Failed && session.PendingCount <= 120, "No-ACK queue was not capped.");
                session.Connect("ws://test/ws"); transport.EmitOpen(); transport.Emit(new WelcomeMessage { playerId = "p2" });
                Require(session.Status == SessionStatus.Connected && session.PlayerId == "p2" && session.SentInputs == 0 && session.PendingCount == 0 && session.LatestWorld == null, "Reconnect retains previous state.");
                session.Step(1, 0, 0);
                var command = JsonSerializer.Deserialize<InputMessage>(transport.Sent.Last(), FieldCodec.Options);
                Require(command.sequence == 1 && command.playerId == "p2", "New session sequence/ownership wrong.");
            }
        });
        test("client_disconnect_ignores_late_welcome_and_snapshot", () =>
        {
            var (session, transport) = Connected(); using (session)
            {
                session.Step(1, 0, 0); session.Disconnect();
                transport.Emit(new WelcomeMessage { playerId = "stale" });
                transport.Emit(new SnapshotMessage { playerId = "stale", tick = 900, entities = [new EntitySnapshot { id = "stale", s = 99 }] });
                Require(session.Status == SessionStatus.Offline && session.PlayerId == "" && session.PendingCount == 0, "Late callback resurrected disconnected session.");
            }
        });
        test("client_dispose_stops_input_and_cannot_reconnect", () =>
        {
            var (session, transport) = Connected();
            session.Dispose(); session.Dispose();
            int sent = transport.Sent.Count;
            try { session.Step(1, 0, 0); } catch (ObjectDisposedException) { }
            Require(transport.Sent.Count == sent && session.PendingCount == 0, "Disposed session still sends/predicts.");
            try { session.Connect("ws://test/ws"); } catch (ObjectDisposedException) { }
            Require(transport.ConnectCalls == 1, "Disposed session reopened a transport with detached handlers.");
            Require(transport.DisposeCalls == 1, "Disposal not idempotent.");
        });
        test("client_invalid_snapshot_cannot_poison_tick_or_pending_ack", () =>
        {
            var (session, transport) = Connected(); using (session)
            {
                session.Step(1, 0, 0);
                transport.Emit(Snapshot(10, 0, 0));
                transport.Emit(new SnapshotMessage { playerId = "p1", tick = 9999, ackSequence = 9999, entities = [] });
                Require(session.LatestWorld.Tick == 10 && session.PendingCount == 1, "Invalid snapshot committed before validation.");
                transport.Emit(Snapshot(11, 9999, 30));
                Require(session.LatestWorld.Tick == 10 && session.PendingCount == 1, "Impossible ACK discarded pending inputs.");
                transport.Emit(Snapshot(11, 1, 0.003f, 0.2f));
                Require(session.LatestWorld.Tick == 11 && session.PendingCount == 0, "Valid snapshot after invalid one was blocked.");
            }
        });
        test("client_welcome_requires_connection_and_nonempty_identity", () =>
        {
            var transport = new FakeTransport();
            using var session = new FoundationSession(transport, new FieldCodec());
            transport.Emit(new WelcomeMessage { playerId = "unsolicited" });
            Require(session.Status == SessionStatus.Offline, "Unsolicited welcome accepted.");
            session.Connect("ws://test/ws"); transport.EmitOpen(); transport.Emit(new WelcomeMessage { playerId = "" });
            Require(session.Status != SessionStatus.Connected, "Empty assigned identity accepted.");
        });
        test("client_quantization_matches_authority_at_half_permille", () =>
        {
            var (session, transport) = Connected(); using (session)
            {
                session.Step(0.0625f, 0, 0);
                var expected = RoadSpaceSimulation.Step(default, new RiderInput(63, 0, 0));
                Require(session.PredictedState.AccelerationRemainder == expected.AccelerationRemainder, "Client/server rounding disagree at half-permille.");
            }
        });
        test("client_readmodel_is_immutable_and_detached_from_validated_wire_state", () =>
        {
            var transport = new FakeTransport();
            var codec = new FieldCodec();
            using var session = new FoundationSession(transport, codec);
            session.Connect("ws://test/ws"); transport.EmitOpen(); transport.Emit(new WelcomeMessage { playerId = "p1" });
            session.Step(1, 0, 0);
            transport.Emit(new SnapshotMessage { playerId = "p1", tick = 10, ackSequence = 1, entities =
                [new EntitySnapshot { id = "p1", s = 12, d = 1.5f, speed = 4 }, new EntitySnapshot { id = "p2", s = 16, d = -2, speed = 5 }] });
            var world = session.LatestWorld;
            Require(world.Tick == 10 && world.AcknowledgedInputSequence == 1 && world.Riders.Count == 2, "Readmodel envelope mapping incorrect.");
            Require(world.Riders[0].Id == "p1" && world.Riders[0].LongitudinalMeters == 12 && world.Riders[0].LateralMeters == 1.5f && world.Riders[0].SpeedMetersPerSecond == 4, "Rider units/fields mapped incorrectly.");
            var wire = codec.LastDecodedSnapshot;
            wire.tick = 9999; wire.ackSequence = 9999; wire.entities[0].s = 999; wire.entities[1] = new EntitySnapshot { id = "changed" };
            Require(world.Tick == 10 && world.AcknowledgedInputSequence == 1 && world.Riders[0].LongitudinalMeters == 12 && world.Riders[1].Id == "p2", "Mutable wire state leaked through readmodel.");
            Require(world.Riders is not RiderReadModel[], "Backing array is publicly exposed.");
            var collection = world.Riders as IList<RiderReadModel>;
            Require(collection == null || collection.IsReadOnly, "Rider collection is writable.");
            if (collection != null)
            {
                bool rejected = false;
                try { collection[0] = default; } catch (NotSupportedException) { rejected = true; }
                Require(rejected, "Collection allowed replacement of a rider.");
            }
            foreach (var type in new[] { typeof(WorldReadModel), typeof(RiderReadModel) })
                Require(type.GetProperties().All(property => property.SetMethod == null || !property.SetMethod.IsPublic), "Readmodel exposes a setter.");
            Require(typeof(FoundationSession).GetProperties().All(property => property.PropertyType.Namespace != "RacingBois.Protocol"), "Session exposes a wire DTO to views.");
            transport.Emit(new SnapshotMessage { playerId = "p1", tick = 999, ackSequence = 1, entities = [] });
            Require(ReferenceEquals(world, session.LatestWorld), "Invalid wire state replaced the readmodel.");
            transport.Emit(Snapshot(11, 1, 14, 4));
            Require(session.LatestWorld.Tick == 11 && world.Tick == 10 && world.Riders.Count == 2, "A later observation mutated a retained old readmodel.");
        });
    }

    private static (FoundationSession Session, FakeTransport Transport) Connected()
    {
        var transport = new FakeTransport();
        var session = new FoundationSession(transport, new FieldCodec());
        session.Connect("ws://test/ws"); transport.EmitOpen(); transport.Emit(new WelcomeMessage { playerId = "p1" });
        Require(session.Status == SessionStatus.Connected, "Test setup did not connect.");
        return (session, transport);
    }
    private static SnapshotMessage Snapshot(long tick, int ack, float distance, float speed = 0) => new() { playerId = "p1", tick = tick, ackSequence = ack, entities = [new EntitySnapshot { id = "p1", s = distance, speed = speed }] };
    private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }

    private sealed class FieldCodec : IWireCodec
    {
        public static readonly JsonSerializerOptions Options = new() { IncludeFields = true };
        public SnapshotMessage LastDecodedSnapshot;
        public string Encode(object message) => JsonSerializer.Serialize(message, message.GetType(), Options);
        public T Decode<T>(string text) where T : class
        {
            var decoded = JsonSerializer.Deserialize<T>(text, Options);
            if (decoded is SnapshotMessage snapshot) LastDecodedSnapshot = snapshot;
            return decoded;
        }
    }
    private sealed class FakeTransport : IRealtimeTransport
    {
        public event Action Opened;
        public event Action<string> Message;
        public event Action<string> Closed;
        public readonly List<string> Sent = [];
        public int ConnectCalls, CloseCalls, DisposeCalls;
        public void Connect(string endpoint) { ConnectCalls++; }
        public void Send(string text) { Sent.Add(text); }
        public void Close() { CloseCalls++; }
        public void Poll() { }
        public void Dispose() { DisposeCalls++; }
        public void EmitOpen() => Opened?.Invoke();
        public void Emit(object message) => Message?.Invoke(JsonSerializer.Serialize(message, message.GetType(), FieldCodec.Options));
        public void EmitClose() => Closed?.Invoke("test closed");
    }
}
