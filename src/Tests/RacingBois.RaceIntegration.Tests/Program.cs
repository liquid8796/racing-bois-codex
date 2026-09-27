using System.Text;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Server.Application;
using RacingBois.Server.Host;
using RacingBois.Simulation;

if (args.Length > 0 && args[0] == "--live") return await LiveRaceProbe.Run(args[1], args[2]);

var results = new List<object>(); int failures = 0, maximumSnapshotBytes = 0;
Test("local_session_uses_same_core_for_1800_ticks", () =>
{
    var transport = new TestTransport(); using var session = new RaceSession(transport, new TestCodec());
    session.StartLocal(); var world = RaceSimulation.CreateDefault(); var own = RaceSimulation.AddPlayer(world, 1);
    for (int i = 0; i < 1800; i++)
    {
        float steer = i % 180 < 90 ? 0.125f : -0.125f; int side = i % 120 < 24 ? 1 : 0;
        session.Step(1, 0, steer, side, i % 240 < 24);
        RaceSimulation.SetInput(world, 1, new RaceInput(1000, 0, steer > 0 ? 125 : -125, side, i % 240 < 24));
        RaceSimulation.Step(world);
        Require(session.LocalRider.LongitudinalMeters == own.DistanceMillimeters / 1000f && session.LocalRider.LateralMeters == own.LateralMillimeters / 1000f &&
            session.LocalRider.Mode == own.Mode && session.LocalRider.Health == own.Health && session.LocalRider.BikeCondition == own.BikeCondition, "Local application diverged from shared core.");
    }
    Require(transport.Sent.Count == 0 && transport.ConnectCalls == 0, "Offline practice used a network.");
    session.RestartLocal(); Require(session.LatestWorld.Tick == 0 && session.SentInputs == 0 && session.LocalRider.Health == GameplayRules.InitialHealth, "Restart did not reset local race.");
});
Test("local_readmodel_publishes_20hz_and_retained_snapshots_are_immutable", () =>
{
    using var session = new RaceSession(new TestTransport(), new TestCodec()); session.StartLocal();
    var initial = session.LatestWorld; session.Step(1, 0, 0); session.Step(1, 0, 0);
    Require(ReferenceEquals(initial, session.LatestWorld) && session.LocalRider.SpeedMetersPerSecond > 0, "Full world published more than 20 Hz or local rider stale.");
    session.Step(1, 0, 0); Require(!ReferenceEquals(initial, session.LatestWorld) && initial.Tick == 0 && initial.Riders[0].SpeedMetersPerSecond == 0, "Retained snapshot mutated.");
    Require(session.LatestWorld.Riders is not RaceRiderReadModel[] && ((IList<RaceRiderReadModel>)session.LatestWorld.Riders).IsReadOnly, "Mutable backing collection exposed.");
    foreach (var type in new[] { typeof(RaceWorldReadModel), typeof(RaceRiderReadModel), typeof(RaceTrafficReadModel), typeof(RaceEventReadModel), typeof(RacePedestrianReadModel) })
        Require(type.GetProperties().All(property => property.SetMethod == null || !property.SetMethod.IsPublic), "Public setter escaped presentation boundary.");
    Require(typeof(RaceSession).GetProperties().All(property => property.PropertyType.Namespace != "RacingBois.Protocol" && property.PropertyType.Namespace != "RacingBois.Simulation"), "Mutable core/wire type escaped application.");
});
Test("authority_rejects_foreign_attack_replay_nonfinite_and_bad_side", () =>
{
    var race = new AuthoritativeRace(); string a = race.Join(), b = race.Join();
    var intent = new RaceInputMessage { playerId = a, sequence = 1, attackSide = 1 };
    Require(race.Apply(b, intent) == "not_owner", "Another peer attacked for owner.");
    intent.attackSide = 2; Require(race.Apply(a, intent) == "input_out_of_range", "Bad attack side accepted.");
    intent.attackSide = 1; intent.throttle = float.NaN; Require(race.Apply(a, intent) == "input_out_of_range", "NaN accepted.");
    intent.throttle = 0; Require(race.Apply(a, intent) == null && race.Apply(a, intent) == "invalid_sequence", "Sequence replay accepted.");
    intent.sequence = int.MaxValue; Require(race.Apply(a, intent) == "invalid_sequence", "Sequence overflow/jump accepted.");
    intent.sequence = 2; intent.protocolVersion = 1; Require(race.Apply(a, intent) == "protocol_mismatch", "Wrong protocol accepted.");
    Require(race.Snapshot(a).ackSequence == 1, "Rejected input mutated ACK.");
});
Test("authoritative_attack_intent_resolves_damage_and_replicates_event", () =>
{
    var race = new AuthoritativeRace(); string a = race.Join(), b = race.Join(); int sequenceA = 0, sequenceB = 0;
    for (int i = 0; i < 28; i++)
    {
        Require(race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA }) == null, "Player A input rejected.");
        Require(race.Apply(b, new RaceInputMessage { playerId = b, sequence = ++sequenceB, steer = i < 18 ? -1 : 0 }) == null, "Player B input rejected.");
        race.Step();
    }
    int victimId = race.RiderId(b); int initialHealth = race.Snapshot(b).riders.Single(r => r.id == victimId).health;
    for (int i = 0; i < 12; i++)
    {
        race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA, attackSide = 1 });
        race.Apply(b, new RaceInputMessage { playerId = b, sequence = ++sequenceB }); race.Step();
    }
    var snapshot = race.Snapshot(a); var hit = snapshot.events.SingleOrDefault(e => e.kind == (int)RaceEventKind.Hit && e.targetId == victimId);
    Require(hit != null && hit.value == 7 && snapshot.riders.Single(r => r.id == victimId).health == initialHealth - 448, "Authoritative fist did not apply recovered Q8 damage.");
    Require(snapshot.events.Select(e => e.id).Distinct().Count() == snapshot.events.Length && snapshot.events.All(e => e.tick <= snapshot.tick), "Event identities unstable.");
});
Test("attack_press_release_before_one_tick_preserves_one_kick_and_latest_movement", () =>
{
    var (race, a, b, sequenceA, sequenceB) = ReadyCombatPair();
    race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA, throttle = 1, steer = 1, attackSide = 1, kick = true });
    race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA, brake = 1 });
    race.Step();
    var sampled = race.Snapshot(a).riders.Single(r => r.id == race.RiderId(a));
    Require(sampled.mode == (int)RiderMode.Attacking && sampled.attackSide == 1 && sampled.attackWeapon == (int)WeaponKind.Kick,
        "Neutral packet erased the discrete kick before the authority tick.");
    Require(sampled.speedMillimetersPerSecond == 0 && sampled.lateralMillimeters == 0,
        "Latched attack reused stale throttle or steering instead of the latest movement.");
    for (int i = 0; i < 75; i++) race.Step();
    var snapshot = race.Snapshot(a);
    Require(snapshot.events.Count(e => e.kind == (int)RaceEventKind.Attack && e.sourceId == race.RiderId(a)) == 1,
        "Released pulse repeated after cooldown.");
    var victim = snapshot.riders.Single(r => r.id == race.RiderId(b));
    Require(victim.health == GameplayRules.InitialHealth - 64 && victim.bikeCondition == GameplayRules.InitialBikeCondition - 1,
        "Latched kick did not resolve its authoritative health and bike damage exactly once.");
});
Test("latched_attack_keeps_most_recent_press_and_respects_side_and_range", () =>
{
    var (race, a, b, sequenceA, sequenceB) = ReadyCombatPair();
    race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA, attackSide = 1, kick = true });
    race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA, attackSide = -1, kick = false });
    race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA }); race.Step();
    var attacker = race.Snapshot(a).riders.Single(r => r.id == race.RiderId(a));
    Require(attacker.attackSide == -1 && attacker.attackWeapon == (int)WeaponKind.Fist, "Most recent press did not replace the pending side/kick.");
    for (int i = 0; i < 40; i++) race.Step();
    Require(race.Snapshot(b).riders.Single(r => r.id == race.RiderId(b)).health == GameplayRules.InitialHealth,
        "Wrong-side latched attack damaged a rider.");
    var distant = new AuthoritativeRace(); string x = distant.Join(), y = distant.Join();
    distant.Apply(x, new RaceInputMessage { playerId = x, sequence = 1, attackSide = 1 });
    distant.Apply(x, new RaceInputMessage { playerId = x, sequence = 2 });
    for (int i = 0; i < 40; i++) distant.Step();
    var distantSnapshot = distant.Snapshot(x);
    Require(distantSnapshot.events.Any(e => e.kind == (int)RaceEventKind.Attack && e.sourceId == distant.RiderId(x)) &&
        distantSnapshot.riders.Single(r => r.id == distant.RiderId(y)).health == GameplayRules.InitialHealth,
        "Out-of-range pulse bypassed reach or did not start.");
});
Test("held_attack_repeats_with_cooldown_but_timeout_and_disconnect_clear_intent", () =>
{
    var (race, a, b, sequenceA, sequenceB) = ReadyCombatPair();
    for (int i = 0; i < 90; i++)
    {
        race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA, attackSide = 1 });
        race.Apply(b, new RaceInputMessage { playerId = b, sequence = ++sequenceB }); race.Step();
    }
    var attacks = race.Snapshot(a).events.Where(e => e.kind == (int)RaceEventKind.Attack && e.sourceId == race.RiderId(a)).ToArray();
    Require(attacks.Length == 3 && attacks.Zip(attacks.Skip(1), (left, right) => right.tick - left.tick).All(gap => gap >= 31),
        "Held attack did not respect repeat cooldown.");
    Require(race.Snapshot(b).riders.Single(r => r.id == race.RiderId(b)).health == GameplayRules.InitialHealth - 448 * 3,
        "Held attack did not resolve three valid hits.");
    var (timed, t, _, sequenceT, _) = ReadyCombatPair();
    timed.Apply(t, new RaceInputMessage { playerId = t, sequence = ++sequenceT, attackSide = 1 });
    for (int i = 0; i < 90; i++) timed.Step();
    Require(timed.Snapshot(t).events.Count(e => e.kind == (int)RaceEventKind.Attack && e.sourceId == timed.RiderId(t)) == 1,
        "Expired held intent repeated after input timeout.");
    var retired = new AuthoritativeRace(); string old = retired.Join(); retired.Join();
    retired.Apply(old, new RaceInputMessage { playerId = old, sequence = 1, attackSide = 1 });
    retired.Leave(old); string replacement = retired.Join(); retired.Step();
    Require(!retired.Snapshot(replacement).events.Any(e => e.kind == (int)RaceEventKind.Attack && e.sourceId == retired.RiderId(replacement)),
        "Disconnected peer's pending attack leaked into its replacement slot.");
});
Test("authority_slots_timeout_and_recent_event_bounds", () =>
{
    var race = new AuthoritativeRace(); var players = Enumerable.Range(0, 8).Select(_ => race.Join()).ToArray();
    Require(players.All(id => id != null) && race.Join() == null, "Capacity differs from protocol.");
    string id = players[0]; race.Apply(id, new RaceInputMessage { playerId = id, sequence = 1, throttle = 1 });
    for (int i = 0; i < 30; i++) race.Step(); float peak = race.Snapshot(id).riders.Single(r => r.id == race.RiderId(id)).speedMillimetersPerSecond;
    for (int i = 0; i < 900; i++) race.Step(); var final = race.Snapshot(id);
    Require(final.riders.Single(r => r.id == race.RiderId(id)).speedMillimetersPerSecond < peak, "Stale input accelerates indefinitely.");
    Require(final.riders.Length <= RaceProtocol.MaxRiders && final.traffic.Length <= RaceProtocol.MaxTraffic && final.pedestrians.Length <= RaceProtocol.MaxPedestrians && final.events.Length <= RaceProtocol.MaxEvents, "Unbounded snapshot.");
    race.Leave(id); string replacement = race.Join(); Require(replacement != id && race.Apply(id, new RaceInputMessage { playerId = id, sequence = 2 }) == "not_owner", "Retired peer identity resurrected.");
    foreach (string old in players.Skip(1)) race.Leave(old); race.Leave(replacement); long tick = race.Tick; race.Step(); Require(race.Tick == tick, "Empty authority runs race to completion.");
    Require(race.Join() != null && race.Tick == 0, "New empty room did not reset.");
});
Test("strict_wire_parser_rejects_damage_injection_duplicate_missing_and_nonfinite", () =>
{
    string json = JsonSerializer.Serialize(new RaceInputMessage { playerId = "r1", sequence = 1, attackSide = 1 }, TestCodec.Options);
    var parsed = Parse(json); Require(parsed.attackSide == 1 && parsed.protocolVersion == RaceProtocol.Version, "Race input lost fields.");
    foreach (string invalid in new[] { json.TrimEnd('}') + ",\"damage\":99999}", json.TrimEnd('}') + ",\"sequence\":2}", json.Replace("\"attackSide\":1,", ""), json.Replace("\"throttle\":0", "\"throttle\":\"NaN\"") })
    { bool failed = false; try { Parse(invalid); } catch (JsonException) { failed = true; } Require(failed, "Malformed input accepted: " + invalid); }
});
Test("whole_race_authority_snapshots_stay_inside_client_contract", () =>
{
    var race = new AuthoritativeRace(); string player = race.Join(); bool sawPedestrians = false;
    for (int i = 0; i < 20000; i++)
    {
        race.Step();
        if (race.Tick % 3 == 0)
        {
            var snapshot = race.Snapshot(player);
            RaceSnapshotValidator.Validate(snapshot, race.RiderId(player), 0, 0);
            sawPedestrians |= snapshot.pedestrians.Length > 0;
        }
    }
    Require(sawPedestrians, "Authority never published the bounded pedestrian world.");
});
Test("pedestrian_snapshot_mapping_bounds_and_immutable_publication", () =>
{
    var transport = new TestTransport(); var codec = new TestCodec(); using var session = new RaceSession(transport, codec);
    var race = new AuthoritativeRace(); string player = race.Join();
    session.Connect("ws://localhost/ws"); transport.Open(); transport.Emit(new RaceWelcomeMessage { playerId = player, riderId = race.RiderId(player) });
    race.Step(); var snapshot = race.Snapshot(player);
    snapshot.pedestrians = new[] { new RacePedestrianSnapshot { id = 4501, distanceMillimeters = 180500, lateralMillimeters = -4750,
        walkingSpeedMillimetersPerSecond = 1400, mode = (int)PedestrianMode.Walking, stateTicks = 73, facingSide = 1, isCrossing = true } };
    transport.Emit(snapshot); var valid = session.LatestWorld;
    Require(valid != null && valid.Pedestrians.Count == 1, "Pedestrian not mapped.");
    var pedestrian = valid.Pedestrians[0];
    Require(pedestrian.Id == 4501 && pedestrian.LongitudinalMeters == 180.5f && pedestrian.LateralMeters == -4.75f &&
        pedestrian.WalkingSpeedMetersPerSecond == 1.4f && pedestrian.LateralSpeedMetersPerSecond == 1.4f && pedestrian.LongitudinalSpeedMetersPerSecond == 0 &&
        pedestrian.IsCrossing && pedestrian.Mode == PedestrianMode.Walking && pedestrian.StateTicks == 73 && pedestrian.FacingSide == 1, "Pedestrian units or fields differ.");
    codec.LastSnapshot.pedestrians[0].lateralMillimeters = 99999;
    Require(pedestrian.LateralMeters == -4.75f && ((IList<RacePedestrianReadModel>)valid.Pedestrians).IsReadOnly, "Mutable pedestrian escaped readmodel.");
    Action<RaceSnapshotMessage>[] malformed =
    {
        state => state.pedestrians = new RacePedestrianSnapshot[7],
        state => state.pedestrians[0].id = 4000,
        state => state.pedestrians[0].facingSide = 0,
        state => state.pedestrians[0].heightMillimeters = 1,
        state => state.pedestrians[0].walkingSpeedMillimetersPerSecond = int.MaxValue,
        state => state.pedestrians[0].mode = 999,
        state => state.pedestrians[0].stateTicks = -1,
        state => state.pedestrians = new[] { state.pedestrians[0], state.pedestrians[0] }
    };
    foreach (var corrupt in malformed)
    {
        var invalid = JsonSerializer.Deserialize<RaceSnapshotMessage>(JsonSerializer.Serialize(snapshot, TestCodec.Options), TestCodec.Options);
        invalid.tick = 9999; corrupt(invalid); transport.Emit(invalid);
        Require(ReferenceEquals(valid, session.LatestWorld), "Invalid pedestrian snapshot replaced the world.");
    }
    snapshot.tick = 2; snapshot.pedestrians[0].isCrossing = false; snapshot.pedestrians[0].walkingSpeedMillimetersPerSecond = -1400;
    transport.Emit(snapshot);
    Require(session.LatestWorld.Tick == 2 && session.LatestWorld.Pedestrians[0].LongitudinalSpeedMetersPerSecond == -1.4f &&
        session.LatestWorld.Pedestrians[0].LateralSpeedMetersPerSecond == 0, "Valid sidewalk motion after invalid snapshots was blocked.");
});
Test("maximum_contract_snapshot_fits_native_and_browser_receive_budget", () =>
{
    var snapshot = new RaceSnapshotMessage { playerId = new string('r', 32), riderId = 999, tick = long.MaxValue,
        ackSequence = int.MaxValue, level = 4, trackLengthMillimeters = TrackDefinition.ForCourse(0, 4).LengthMillimeters,
        riders = Enumerable.Range(1, RaceProtocol.MaxRiders).Select(id => new RaceEntitySnapshot
        {
            id = id == 1 ? 999 : 1000 + id, kind = id == 1 ? (int)RiderKind.Player : (int)RiderKind.Opponent, mode = (int)RiderMode.Finished,
            weapon = 3, attackWeapon = 3, distanceMillimeters = -250000, bikeDistanceMillimeters = -250000,
            lateralMillimeters = -50000, bikeLateralMillimeters = -50000, heightMillimeters = -1000000, bikeHeightMillimeters = -1000000,
            bikeCatalogIndex = 14, characterCatalogIndex = 7, leanMillidegrees = -90000, speedMillimetersPerSecond = 61000, health = 4096, bikeCondition = 100, strength = 1000,
            rank = 16, reward = 100000, attackSide = -1, attackAgeTicks = int.MaxValue, modeAgeTicks = int.MaxValue,
            finishTick = long.MaxValue, gear = 7, qualified = false
        }).ToArray(),
        traffic = Enumerable.Range(3001, RaceProtocol.MaxTraffic).Select(id => new RaceTrafficSnapshot { id = id, kind = 1,
            distanceMillimeters = -250000, lateralMillimeters = -50000, speedMillimetersPerSecond = -100000,
            halfLengthMillimeters = 15000, halfWidthMillimeters = 5000, heightMillimeters = 6000 }).ToArray(),
        pedestrians = Enumerable.Range(4001, RaceProtocol.MaxPedestrians).Select(id => new RacePedestrianSnapshot { id = id,
            distanceMillimeters = -250000, lateralMillimeters = -50000, heightMillimeters = 0, walkingSpeedMillimetersPerSecond = -10000,
            mode = (int)PedestrianMode.Stumbled, stateTicks = int.MaxValue, facingSide = -1 }).ToArray(),
        events = Enumerable.Range(1, RaceProtocol.MaxEvents).Select(id => new RaceEventSnapshot { id = long.MaxValue - RaceProtocol.MaxEvents + id,
            tick = long.MaxValue, kind = (int)RaceEventKind.PedestrianRecovered, sourceId = int.MaxValue, targetId = int.MaxValue, value = -1000000 }).ToArray()
    };
    RaceSnapshotValidator.Validate(snapshot, 999, int.MaxValue, 0);
    maximumSnapshotBytes = WireJson.Serialize(snapshot).Length;
    Require(maximumSnapshotBytes <= 32768, "Maximum lawful snapshot exceeds either client receive budget.");
});
Test("online_session_validates_authority_snapshot_atomically", () =>
{
    var transport = new TestTransport(); var codec = new TestCodec(); using var session = new RaceSession(transport, codec);
    var race = new AuthoritativeRace(); string id = race.Join(); session.Connect("ws://localhost/ws"); transport.Open();
    Require(codec.Decode<RaceHelloMessage>(transport.Sent.Single()).protocolVersion == RaceProtocol.Version, "Race handshake wrong.");
    transport.Emit(new RaceWelcomeMessage { playerId = id, riderId = race.RiderId(id) }); session.Step(1, 0, 0, -1, true);
    var input = codec.Decode<RaceInputMessage>(transport.Sent.Last()); Require(input.attackSide == -1 && input.kick, "Attack intent lost in client.");
    race.Apply(id, input); race.Step(); transport.Emit(race.Snapshot(id));
    var valid = session.LatestWorld; Require(valid != null && session.PendingCount == 0 && session.LocalRider.Id == race.RiderId(id), "Valid snapshot rejected.");
    var hostile = race.Snapshot(id); hostile.tick = 9999; hostile.ackSequence = 9999; transport.Emit(hostile);
    Require(ReferenceEquals(valid, session.LatestWorld), "Impossible ACK replaced world.");
    hostile.ackSequence = 1; hostile.riders[0].health = int.MaxValue; transport.Emit(hostile);
    Require(ReferenceEquals(valid, session.LatestWorld), "Invalid health replaced world.");
    hostile.riders[0].health = 100; hostile.riders[1].id = hostile.riders[0].id; transport.Emit(hostile);
    Require(ReferenceEquals(valid, session.LatestWorld), "Duplicate entity replaced world.");
    codec.LastSnapshot.riders[0].health = 0; Require(valid.Riders[0].Health > 0, "Decoded DTO aliases readmodel.");
    session.Step(1, 0, 0); input = codec.Decode<RaceInputMessage>(transport.Sent.Last()); race.Apply(id, input); race.Step(); transport.Emit(race.Snapshot(id));
    Require(session.LatestWorld.Tick == 2 && session.PendingCount == 0, "Valid snapshot after rejection blocked.");
});
Test("online_no_ack_disconnect_late_events_and_version_mismatch", () =>
{
    var transport = new TestTransport(); using var session = new RaceSession(transport, new TestCodec());
    session.Connect("wss://localhost/ws"); transport.Open(); transport.Emit(new RaceWelcomeMessage { playerId = "r1", riderId = 1 });
    for (int i = 0; i < 121; i++) session.Step(1, 0, 0);
    Require(session.Status == SessionStatus.Failed && session.PendingCount == 120, "No-ACK budget unbounded.");
    session.StartLocal(); transport.Emit(new RaceWelcomeMessage { playerId = "late", riderId = 9 }); transport.CloseEvent();
    Require(session.Mode == RaceSessionMode.Local && session.PlayerId == "local" && session.Status == SessionStatus.Connected, "Late socket callback interrupted local race.");
    session.Connect("ws://localhost/ws"); transport.Open(); transport.Emit(new RaceWelcomeMessage { playerId = "r1", riderId = 1, simulationRulesVersion = 999 });
    Require(session.Status == SessionStatus.Failed, "Mismatched simulation accepted.");
    session.Disconnect(); transport.Emit(new RaceWelcomeMessage { playerId = "late", riderId = 2 }); Require(session.Mode == RaceSessionMode.None, "Late welcome resurrected session.");
});
var report = new { generatedUtc = DateTimeOffset.UtcNow, passed = results.Count - failures, failed = failures, tests = results,
    payloadBudget = new { maximumSnapshotBytes, receiveLimitBytes = 32768, headroomBytes = 32768 - maximumSnapshotBytes },
    scope = "Actual shared-core authority and linked Unity Application source; no Unity rendering or live network in this suite." };
string output = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }); Console.WriteLine(output);
if (args.Length > 0) { string path = Path.GetFullPath(args[0]); Directory.CreateDirectory(Path.GetDirectoryName(path)); File.WriteAllText(path, output); }
return failures == 0 ? 0 : 1;

void Test(string name, Action test)
{ try { test(); results.Add(new { name, status = "PASS" }); } catch (Exception ex) { failures++; results.Add(new { name, status = "FAIL", error = ex.Message }); } }
static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
static RaceInputMessage Parse(string json) => WireJson.Parse<RaceInputMessage>(Encoding.UTF8.GetBytes(json), "kind", "protocolVersion", "playerId", "sequence", "throttle", "brake", "steer", "attackSide", "kick");
static (AuthoritativeRace Race, string A, string B, int SequenceA, int SequenceB) ReadyCombatPair()
{
    var race = new AuthoritativeRace(); string a = race.Join(), b = race.Join(); int sequenceA = 0, sequenceB = 0;
    for (int i = 0; i < 28; i++)
    {
        race.Apply(a, new RaceInputMessage { playerId = a, sequence = ++sequenceA });
        race.Apply(b, new RaceInputMessage { playerId = b, sequence = ++sequenceB, steer = i < 18 ? -1 : 0 });
        race.Step();
    }
    return (race, a, b, sequenceA, sequenceB);
}

internal sealed class TestCodec : IWireCodec
{
    internal static readonly JsonSerializerOptions Options = new() { IncludeFields = true };
    internal RaceSnapshotMessage LastSnapshot;
    public string Encode(object message) => JsonSerializer.Serialize(message, message.GetType(), Options);
    public T Decode<T>(string text) where T : class { var message = JsonSerializer.Deserialize<T>(text, Options); if (message is RaceSnapshotMessage snapshot) LastSnapshot = snapshot; return message; }
}
internal sealed class TestTransport : IRealtimeTransport
{
    public event Action Opened;
    public event Action<string> Message;
    public event Action<string> Closed;
    internal readonly List<string> Sent = new();
    internal int ConnectCalls;
    public void Connect(string endpoint) { ConnectCalls++; }
    public void Send(string text) => Sent.Add(text);
    public void Close() { }
    public void Poll() { }
    public void Dispose() { }
    internal void Open() => Opened?.Invoke();
    internal void Emit(object message) => Message?.Invoke(JsonSerializer.Serialize(message, message.GetType(), TestCodec.Options));
    internal void CloseEvent() => Closed?.Invoke("late close");
}
