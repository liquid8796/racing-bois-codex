using System.Text.Json;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Server.Application;
using RacingBois.Simulation;

var results = new List<object>();
int failed = 0;
Test("integer_replay_golden_300_ticks", () =>
{
    RiderState state = default;
    for (int i = 0; i < 300; i++) state = RoadSpaceSimulation.Step(state, new RiderInput(1000, 0, 0));
    Equal(150500L, state.DistanceMillimeters);
    Equal(60000, state.SpeedMillimetersPerSecond);
    Equal(0, state.DistanceRemainder);
    Equal(0, state.AccelerationRemainder);
});
Test("brake_stops_without_reverse_and_road_is_bounded", () =>
{
    RiderState state = default;
    for (int i = 0; i < 600; i++) state = RoadSpaceSimulation.Step(state, new RiderInput(1000, 0, 1000));
    Equal(6000, state.LateralMillimeters);
    for (int i = 0; i < 300; i++) state = RoadSpaceSimulation.Step(state, new RiderInput(0, 1000, -1000));
    Equal(0, state.SpeedMillimetersPerSecond);
    long stopped = state.DistanceMillimeters;
    for (int i = 0; i < 120; i++) state = RoadSpaceSimulation.Step(state, new RiderInput(0, 1000, 0));
    Equal(stopped, state.DistanceMillimeters);
});
Test("authority_rejects_ownership_replay_jump_and_nonfinite", () =>
{
    var match = new AuthoritativeMatch();
    string owner = match.Join()!;
    string other = match.Join()!;
    var command = Input(owner, 1);
    Equal("not_owner", match.Apply(other, command)!);
    True(match.Apply(owner, command) == null, "Valid command rejected.");
    Equal("invalid_sequence", match.Apply(owner, command)!);
    command.sequence = int.MaxValue;
    Equal("invalid_sequence", match.Apply(owner, command)!);
    command.sequence = 2;
    foreach (float invalid in new[] { float.NaN, float.PositiveInfinity, -0.1f, 1.01f })
    {
        command.throttle = invalid;
        Equal("input_out_of_range", match.Apply(owner, command)!);
    }
    command.throttle = 1;
    command.steer = -1.01f;
    Equal("input_out_of_range", match.Apply(owner, command)!);
    command.steer = 0;
    command.protocolVersion = 999;
    Equal("protocol_mismatch", match.Apply(owner, command)!);
    Equal(1, match.Snapshot(owner).ackSequence);
});
Test("eight_rider_capacity_leave_join_and_stable_snapshot_order", () =>
{
    var match = new AuthoritativeMatch();
    var ids = Enumerable.Range(0, 8).Select(_ => match.Join()!).ToArray();
    True(match.Join() == null, "Ninth rider must be rejected.");
    for (int i = 0; i < ids.Length; i++) True(match.Apply(ids[i], Input(ids[i], 1)) == null, "Valid input rejected.");
    match.Step();
    var snapshot = match.Snapshot(ids[0]);
    Equal(8, snapshot.entities.Length);
    True(snapshot.entities.Select(e => e.id).SequenceEqual(ids.Order(StringComparer.Ordinal)), "Order unstable.");
    match.Leave(ids[0]);
    True(match.Join() != null, "Slot did not release.");
});
Test("snapshot_monotonic_and_input_timeout_coasts", () =>
{
    var match = new AuthoritativeMatch();
    string id = match.Join()!;
    match.Apply(id, Input(id, 1));
    long lastTick = 0;
    for (int i = 0; i < 30; i++) { match.Step(); True(match.Tick > lastTick, "Tick not monotonic."); lastTick = match.Tick; }
    float peak = match.Snapshot(id).entities[0].speed;
    for (int i = 0; i < 180; i++) match.Step();
    True(match.Snapshot(id).entities[0].speed < peak, "Stale input keeps accelerating.");
});
Test("protocol_public_fields_golden_roundtrip", () =>
{
    var options = new JsonSerializerOptions { IncludeFields = true };
    const string fixture = "{\"kind\":\"input\",\"protocolVersion\":1,\"playerId\":\"p1\",\"sequence\":7,\"throttle\":1,\"brake\":0,\"steer\":-0.25}";
    var input = JsonSerializer.Deserialize<InputMessage>(fixture, options)!;
    Equal(7, input.sequence); Equal(-0.25f, input.steer);
    Equal(fixture, JsonSerializer.Serialize(input, options));
    var match = new AuthoritativeMatch();
    string id = match.Join()!;
    var snapshot = JsonSerializer.Deserialize<SnapshotMessage>(JsonSerializer.Serialize(match.Snapshot(id), options), options)!;
    Equal(id, snapshot.entities[0].id);
    Equal(60, new WelcomeMessage().tickRate);
});
Test("shared_assemblies_have_no_unity_or_server_dependency", () =>
{
    foreach (var assembly in new[] { typeof(PrototypeRules).Assembly, typeof(RoadSpaceSimulation).Assembly, typeof(InputMessage).Assembly })
        foreach (var reference in assembly.GetReferencedAssemblies())
            True(!reference.Name!.StartsWith("Unity", StringComparison.Ordinal) && !reference.Name.StartsWith("RacingBois.Server", StringComparison.Ordinal), "Dependency escaped shared boundary.");
});
Test("ingress_token_budget_allows_buffered_60hz_but_bounds_flood", () =>
{
    var budget = new InputRateBudget();
    for (int i = 0; i < 60; i++) True(budget.TryConsume(i / 60.0), "Valid sustained rate rejected.");
    // 900 ms of valid 60 Hz input arrives together after a stream stall.
    for (int i = 0; i < 54; i++) True(budget.TryConsume(1.9), "Valid buffered burst rejected.");
    for (int i = 0; i < 600; i++) True(budget.TryConsume(1.9 + i / 60.0), "Recovery at sustained 60 Hz rejected.");
    var flood = new InputRateBudget();
    for (int i = 0; i < InputRateBudget.BurstCapacity; i++) True(flood.TryConsume(0), "Burst capacity differs from contract.");
    True(!flood.TryConsume(0), "Unbounded instantaneous flood accepted.");
    for (int i = 0; i < 45; i++) True(flood.TryConsume(0.5), "Expected refill absent.");
    True(!flood.TryConsume(0.5), "Excess refill granted.");
    True(!flood.TryConsume(0.1), "Clock rollback refilled budget.");
});
ClientSessionTests.Register(Test);
var report = new { generatedUtc = DateTimeOffset.UtcNow, framework = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription, passed = results.Count - failed, failed, tests = results, golden = new { ticks = 300, distanceMillimeters = 150500, speedMillimetersPerSecond = 60000 }, limitations = "Native replay and pure client application fixtures only. Unity Web must run the same golden test before cross-build determinism is accepted; native/JS transport lifetime needs browser integration verification." };
string json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
Console.WriteLine(json);
if (args.Length > 0) { Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[0]))!); File.WriteAllText(args[0], json); }
return failed == 0 ? 0 : 1;

void Test(string name, Action body)
{
    try { body(); results.Add(new { name, status = "PASS" }); }
    catch (Exception ex) { failed++; results.Add(new { name, status = "FAIL", error = ex.Message }); }
}
static InputMessage Input(string id, int sequence) => new() { playerId = id, sequence = sequence, throttle = 1 };
static void Equal<T>(T expected, T actual) where T : notnull { if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new InvalidOperationException($"Expected {expected}; got {actual}."); }
static void True(bool condition, string reason) { if (!condition) throw new InvalidOperationException(reason); }
