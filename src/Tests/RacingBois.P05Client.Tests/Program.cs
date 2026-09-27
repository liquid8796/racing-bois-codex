using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Simulation;

var reports = new List<object>(); var latency = new List<object>(); var arrivalBudgets = new List<object>(); int failed = 0;
void Check(bool valid, string message) { if (!valid) throw new InvalidOperationException(message); }
void Throws(Action action) { bool threw = false; try { action(); } catch (ArgumentException) { threw = true; } Check(threw, "Expected rejection"); }
void Test(string name, Action test)
{
    try { test(); reports.Add(new { name, passed = true }); Console.WriteLine("PASS " + name); }
    catch (Exception e) { failed++; reports.Add(new { name, passed = false, error = e.Message }); Console.WriteLine("FAIL " + name + ": " + e.Message); }
}
void Connected(TestPeer peer) => Check(peer.Session.Status == SessionStatus.Connected, peer.Session.Status + " / " + peer.Session.Error);

Test("disconnect_before_connect_does_not_access_empty_endpoint_store", () =>
{
    var net = new TestNetwork(); var peer = new TestPeer(net, new MemoryStore());
    peer.Session.Disconnect(); Check(peer.Session.Status == SessionStatus.Offline, "Fresh session did not remain offline");
    peer.Session.Dispose(); Check(peer.Store.Resumes.Count == 0 && peer.Store.Profiles.Count == 0, "Fresh teardown mutated credentials");
});

Test("checkpoint_roundtrip_driving_airborne_recovery_and_own_attack", () =>
{
    foreach (int scenario in new[] { 0, 1, 2 })
    {
        var world = RaceSimulation.CreateDefault(1996, 0); var rider = RaceSimulation.AddPlayer(world, 1);
        RaceSimulation.FindRider(world, GameplayRules.PoliceId).Mode = RiderMode.Wrecked;
        if (scenario == 1) { rider.DistanceMillimeters = 669600; rider.SpeedMillimetersPerSecond = 50000; }
        if (scenario == 2) { rider.Mode = RiderMode.Falling; rider.BikeDistanceMillimeters = 12000; }
        var predictor = new RiderPredictor(0); var codec = new TestCodec();
        for (int tick = 0; tick < 360; tick++)
        {
            var input = scenario == 2 ? default : new RaceInput(800, tick % 80 > 65 ? 230 : 0, tick % 50 < 25 ? 157 : -231, tick % 70 < 30 ? 1 : 0);
            var before = RiderCheckpoints.Capture(rider, world.Tick); var dto = CheckpointMapper.ToDto(before);
            var roundtrip = CheckpointMapper.ToCheckpoint(codec.Decode<OwnPredictionState>(codec.Encode(dto)));
            Check(codec.Encode(CheckpointMapper.ToDto(roundtrip)) == codec.Encode(dto), "Checkpoint field lost");
            predictor.Restore(roundtrip); var predicted = predictor.Advance(world.Tick + 1, input);
            world.TrafficCount = world.PedestrianCount = 0; RaceSimulation.SetInput(world, 1, input); RaceSimulation.Step(world);
            Check(codec.Encode(CheckpointMapper.ToDto(predicted)) == codec.Encode(CheckpointMapper.CaptureDto(rider, world.Tick)), "Pure step diverged scenario" + scenario + " tick" + tick);
        }
    }
});
Test("checkpoint_is_immutable_and_rejects_hostile_internal_fields", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0); var rider = RaceSimulation.AddPlayer(world, 1);
    var checkpoint = RiderCheckpoints.Capture(rider, 0); var copy = checkpoint.Data; copy.Health = 0; rider.Health = 1;
    Check(checkpoint.Data.Health == 4096, "Mutable alias escaped checkpoint");
    var wire = CheckpointMapper.ToDto(checkpoint); wire.speedRemainder = 60; Throws(() => CheckpointMapper.ToCheckpoint(wire));
    wire = CheckpointMapper.ToDto(checkpoint); wire.steeringPermille = int.MaxValue; Throws(() => CheckpointMapper.ToCheckpoint(wire));
    wire = CheckpointMapper.ToDto(checkpoint); wire.appliedInput.throttlePermille = 1001; Throws(() => CheckpointMapper.ToCheckpoint(wire));
});
Test("v2_busted_negative_fine_regression", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0, 2); var rider = RaceSimulation.AddPlayer(world, 1);
    rider.Mode = RiderMode.Busted; rider.Reward = -1200;
    var snapshot = new RaceSnapshotMessage { tick = 100, level = 2, trackLengthMillimeters = world.Track.LengthMillimeters,
        riders = new[] { CheckpointMapper.CaptureDto(rider, 100).rider } };
    RaceSnapshotValidator.Validate(snapshot, 1, 0, 0);
    snapshot.riders[0].reward = -400; bool threw = false; try { RaceSnapshotValidator.Validate(snapshot, 1, 0, 0); } catch (InvalidOperationException) { threw = true; }
    Check(threw, "Wrong-level fine accepted");
});
Test("real_service_create_join_ready_countdown_exact_inputs", () =>
{
    var net = new TestNetwork(); var a = net.Add("An"); var b = net.Add("Binh"); net.PrepareRace(a, b);
    Connected(a); Connected(b); Check(a.Session.Room.Phase == LobbyPhase.Racing && b.Session.Room.Members.Count == 2, "Race not started");
    a.Throttle = b.Throttle = 1; net.Run(120);
    Connected(a); Check(a.Session.LocalRider.SpeedMetersPerSecond > 15 && a.Session.LastResolvedTick > 150, "Inputs not consumed");
    Check(a.Session.FutureInputs == 0 && a.Session.LateInputs <= 2 && a.Session.PendingInputCount < 12, "Timeline scheduling wrong");
});
Test("presentation_cache_reuses_readmodel_and_invalidates_on_event_and_snapshot", () =>
{
    var net = new TestNetwork(); var peer = net.Add("Cache"); net.PrepareRace(peer); Connected(peer);
    var first = peer.Session.SamplePresentation(); var again = peer.Session.SamplePresentation();
    Check(ReferenceEquals(first, again), "Repeated render allocated new immutable world");
    net.Run(3); Check(!ReferenceEquals(first, peer.Session.SamplePresentation()), "Snapshot did not invalidate cache");
    peer.Session.NotifyVisibility(false); Check(!ReferenceEquals(first, peer.Session.SamplePresentation()), "Suspension reused speculative state");
});
Test("remote_interpolation_state_boundaries_interest_topology_and_stale_cap", () =>
{
    RaceRiderReadModel Rider(int id, float s, RiderMode mode = RiderMode.Riding) => new RaceRiderReadModel(id, RiderKind.Player, mode,
        WeaponKind.Fist, WeaponKind.Fist, s, id * 1.2f, 50, 0, 0, s, id * 1.2f, 0, 4096, 4096, 100, 100, 7, id, -1, 0, false, 0, 0, 0, 1);
    RaceWorldReadModel World(long tick, RiderMode mode, bool traffic) => new RaceWorldReadModel(tick, 0, 2200, 0,
        new[] { Rider(1, tick * 50f / 60), Rider(2, tick * 50f / 60, mode) },
        traffic ? new[] { new RaceTrafficReadModel(3001, 0, 30, 3, 20, 2.27f, 1.08f, 1.36f) } : Array.Empty<RaceTrafficReadModel>(), Array.Empty<RaceEventReadModel>());
    var sampler = new RemoteMotionSampler(); sampler.Add(World(0, RiderMode.Riding, true)); sampler.Add(World(3, RiderMode.Riding, false));
    var sample = sampler.Sample(1.5, Rider(1, 0), Array.Empty<RaceEventReadModel>());
    Check(Math.Abs(sample.Riders[1].LongitudinalMeters - 1.25f) < .001 && sample.Traffic.Count == 1, "Interpolation or despawn boundary wrong");
    sample = sampler.Sample(3, Rider(1, 0), Array.Empty<RaceEventReadModel>()); Check(sample.Traffic.Count == 0, "Interest despawn kept ghost");
    var frozen = sampler.Sample(60, Rider(1, 0), Array.Empty<RaceEventReadModel>());
    Check(Math.Abs(frozen.Riders[1].LongitudinalMeters - 27.5f) < .001 && sampler.StaleActors > 0, "Extrapolation exceeded500ms cap");
    sampler.Clear(); sampler.Add(World(0, RiderMode.Riding, false)); sampler.Add(World(3, RiderMode.Falling, true));
    sample = sampler.Sample(1.5, Rider(1, 0), Array.Empty<RaceEventReadModel>());
    Check(sample.Riders[1].Mode == RiderMode.Riding && sample.Riders[1].LongitudinalMeters == 0 && sample.Traffic.Count == 0, "Discrete state/spawn blended across boundary");
});
Test("prediction_never_projects_speculative_health_reward_or_inventory", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0); var rider = RaceSimulation.AddPlayer(world, 1);
    var authoritative = RaceStateProjection.Rider(rider); var d = RiderCheckpoints.Capture(rider, 0).Data;
    d.Health = 0; d.Reward = 1000; d.Weapon = WeaponKind.Chain; d.AttackWeapon = WeaponKind.Kick; d.Mode = RiderMode.Attacking;
    var projected = RemoteMotionSampler.WithMotion(authoritative, new RiderCheckpoint(d));
    Check(projected.Health == 4096 && projected.Reward == 0 && projected.Weapon == WeaponKind.Fist && projected.AttackWeapon == WeaponKind.Kick, "Prediction leaked authority fields or lost local kick pose");
});
Test("early_authority_contact_event_caps_remote_until_fresh_snapshot", () =>
{
    RaceRiderReadModel Rider(int id, float s, RiderMode mode = RiderMode.Riding, float speed = 60) => new RaceRiderReadModel(id, RiderKind.Player, mode,
        WeaponKind.Fist, WeaponKind.Fist, s, id, speed, 0, 0, s, id, 0, 4096, 4096, 100, 100, 7, id, -1, 0, false, 0, 0, 0, 1);
    RaceWorldReadModel World(long tick, float s, RiderMode mode = RiderMode.Riding, float speed = 60) => new RaceWorldReadModel(tick, 0, 2200, 0,
        new[] { Rider(1, 10), Rider(2, s, mode, speed) }, Array.Empty<RaceTrafficReadModel>(), Array.Empty<RaceEventReadModel>());
    var sampler = new RemoteMotionSampler(); sampler.Add(World(10, 10));
    var crash = new RaceEventReadModel(1, 11, RaceEventKind.Crash, 2, 0, 700);
    var capped = sampler.Sample(14, Rider(1, 14), new[] { crash, crash });
    Check(capped.Riders[1].LongitudinalMeters == 11 && sampler.EventCappedActors == 1, "Remote extrapolated through confirmed crash or duplicate changed cap");
    Check(capped.Riders[1].Mode == RiderMode.Riding && capped.Riders[1].Health == 4096 && capped.Riders[0].LongitudinalMeters == 14, "Event cap invented authority state");
    var stale = sampler.Sample(14, Rider(1, 14), new[] { new RaceEventReadModel(2, 10, RaceEventKind.Crash, 2, 0, 700) });
    Check(stale.Riders[1].LongitudinalMeters == 14 && sampler.EventCappedActors == 0, "Stale event overrode fresh authority");
    var busted = sampler.Sample(14, Rider(1, 14), new[] { new RaceEventReadModel(3, 11, RaceEventKind.Busted, 2001, 2, 400) });
    Check(busted.Riders[1].LongitudinalMeters == 11, "Busted cap used police source instead of affected rider");
    sampler.Add(World(12, 11.3f, RiderMode.Falling, 15));
    var fresh = sampler.Sample(14, Rider(1, 14), new[] { crash });
    Check(fresh.Riders[1].LongitudinalMeters > 11.3f && fresh.Riders[1].Mode == RiderMode.Falling && sampler.EventCappedActors == 0, "Fresh snapshot failed to release event cap");
});
Test("event_arrival_invalidates_cached_world_once_without_duplicate_effect", () =>
{
    var net = new TestNetwork(); var p = net.Add("Events"); net.PrepareRace(p); var before = p.Session.SamplePresentation();
    long seq = p.Trace.Where(t => t.StartsWith("recv:") && !t.StartsWith("recv:mpWelcome")).Select(t => long.TryParse(t.Split(':')[2].Split(' ')[0], out var v) ? v : 0).Max();
    var batch = new MpEventBatch { roomId = p.Session.Room.RoomId, matchId = p.Session.Room.MatchId, raceEpoch = p.Session.Room.RaceEpoch,
        reliableSequence = seq + 1, events = new[] { new RaceEventSnapshot { id = 99999, tick = p.Session.LastResolvedTick, kind = (int)RaceEventKind.Attack, sourceId = p.Session.RiderId } } };
    p.Inject(batch); var after = p.Session.SamplePresentation();
    Check(!ReferenceEquals(before, after) && after.Events.Any(e => e.Id == 99999), "Event did not invalidate presentation");
    p.Inject(batch); Check(ReferenceEquals(after, p.Session.SamplePresentation()), "Reliable duplicate replayed presentation effect");
});
Test("malformed_snapshot_rejected_without_partial_commit", () =>
{
    var net = new TestNetwork(); var p = net.Add("Atomic"); net.PrepareRace(p); Connected(p);
    var before = p.Session.LatestAuthoritativeWorld; var own = p.Session.LocalRider;
    var snapshot = net.Codec.Decode<MpSnapshot>(p.LastSnapshot); snapshot.tick += 3; snapshot.resolvedThroughTick = snapshot.own.tick = snapshot.tick;
    snapshot.traffic = new[] { new NumericRow { values = new[] { 3001, 0, int.MaxValue, 0, 1, 200, 100, 140 } } };
    p.Inject(snapshot);
    Check(p.Session.Status == SessionStatus.Failed && ReferenceEquals(before, p.Session.LatestAuthoritativeWorld), "Malformed snapshot partially committed");
    Check(p.Session.LocalRider.Health == own.Health, "Malformed snapshot mutated rider");
});
Test("lost_initial_welcome_reuses_lease_and_persistent_profile", () =>
{
    var net = new TestNetwork { DropWelcomes = 1 }; var peer = net.Add("Welcome", false); net.Run(480);
    Connected(peer); Check(net.Server.SessionCount == 1 && net.Realm.ProfileCount == 1 && peer.Connections == 2, "Lost welcome created duplicate identity");
    Check(peer.Store.Profiles.Count == 1, "Persistent capability not saved");
});
Test("resume_preserves_rider_and_suppresses_stale_epoch", () =>
{
    var net = new TestNetwork(150); var a = net.Add("Resume"); var b = net.Add("Host"); net.PrepareRace(a, b);
    a.Throttle = b.Throttle = 1; net.Run(80); Connected(a); string id = a.Session.PlayerId; int riderId = a.Session.RiderId;
    var stale = net.Codec.Decode<MpSnapshot>(a.LastSnapshot); long before = a.Session.LastResolvedTick;
    a.Drop(); net.Run(140); Connected(a);
    Check(a.Session.PlayerId == id && a.Session.RiderId == riderId && a.Session.Room.Members.Count == 2 && a.Session.LastResolvedTick > before, "Resume created a new rider or rewound race");
    var latest = a.Session.LatestAuthoritativeWorld; stale.tick += 10000; stale.resolvedThroughTick = stale.own.tick = stale.tick;
    a.Inject(stale); Check(ReferenceEquals(latest, a.Session.LatestAuthoritativeWorld), "Old epoch snapshot accepted");
});
Test("suspended_tab_resumes_fresh_without_input_fast_forward", () =>
{
    var net = new TestNetwork(150); var a = net.Add("Tab"); var b = net.Add("Visible"); net.PrepareRace(a, b);
    a.Throttle = 1; net.Run(30); int inputs = a.Session.SentInputs;
    a.Session.NotifyVisibility(false); net.Run(180);
    Check(a.Session.IsSuspended && a.Session.SentInputs <= inputs + 1, "Hidden tab kept generating inputs");
    a.Session.NotifyVisibility(true); net.Run(120); Connected(a);
    Check(a.Session.PendingInputCount < 32 && !a.Session.IsSuspended && a.Session.FutureInputs == 0, "Resumed tab fast-forwarded old inputs");
});
Test("explicit_logout_waits_for_ack_and_transfers_host", () =>
{
    var net = new TestNetwork(150); var a = net.Add("Owner", false); var b = net.Add("Other"); net.Run(45);
    a.Session.CreateLobby("Exit test", 0); net.Run(45); b.Session.JoinLobby(a.Session.Room.Code); net.Run(45);
    a.Session.Disconnect(); Check(a.Session.IsDisconnecting, "Logout closed before acknowledgement"); net.Run(45);
    Check(a.Session.Status == SessionStatus.Offline && !a.Session.IsDisconnecting && a.Store.Resumes.Count == 0 && net.Server.SessionCount == 1, "Logout lease not revoked");
    Check(b.Session.IsHost && b.Session.Room.Members.Count == 1, "Host not transferred on explicit logout");
    var rejoin = net.Add("Saved", false, a.Store); net.Run(45); Connected(rejoin); Check(net.Realm.ProfileCount == 1, "Saved identity replaced on relogin");
});
Test("leave_lobby_fences_input_while_waiting_for_ack", () =>
{
    var net = new TestNetwork(150); var a = net.Add("Leave"); var b = net.Add("Remain"); net.PrepareRace(a, b);
    a.Session.LeaveLobby(); int sent = a.Session.SentInputs;
    a.Session.Step(1, 0, 0, 1); Check(a.Session.SentInputs == sent, "Input escaped pending leave fence");
    net.Run(45); Connected(a); Check(a.Session.Room == null && a.Session.Error == "", "Leave produced stale-room input error");
});
Test("fresh_guest_does_not_overwrite_saved_profile_capability", () =>
{
    var net = new TestNetwork(); var saved = net.Add("Saved", false); net.Run(30); Connected(saved);
    var original = saved.Store.Profiles.Values.Single(); saved.Session.Disconnect(); net.Run(5);
    var guest = net.Add("Guest", true, saved.Store); net.Run(30); Connected(guest);
    Check(guest.Session.IsGuest && ReferenceEquals(original, saved.Store.Profiles.Values.Single()), "Guest replaced saved credential");
});
Test("expired_resume_fails_closed_without_new_guest_or_profile", () =>
{
    var net = new TestNetwork(); var store = new MemoryStore();
    store.Resumes["ws://127.0.0.1:7777/multiplayer"] = new ResumeReceipt("old", "OLD123", "oldplayer", "invalid-capability");
    var peer = net.Add("Expired", false, store); net.Run(60);
    Check(peer.Session.Status == SessionStatus.Failed && net.Server.SessionCount == 0 && net.Realm.ProfileCount == 0 && store.Resumes.Count == 0,
        "Invalid resume silently created a fresh identity");
});
Test("authoritative_results_are_absolute_and_return_to_lobby_clears_race", () =>
{
    var net = new TestNetwork(150); var a = net.Add("FinishA", false); var b = net.Add("FinishB", false); net.PrepareRace(a, b);
    net.InputController = peer =>
    {
        var r = peer.Session.LocalRider; int speed = (int)(r.SpeedMetersPerSecond * 1000);
        int curve = TrackDefinition.Default.CurvatureAt((long)(r.LongitudinalMeters * 1000) + speed / 8);
        int drift = (int)((long)speed * curve / 100000); int desired = peer == a ? -1000 : 1000;
        peer.Throttle = 1; peer.Steer = Math.Clamp(((desired - (int)(r.LateralMeters * 1000)) * 2 + drift) * 1000 / (1200 + speed / 6), -1000, 1000) / 1000f;
    };
    for (int i = 0; i < 9000 && a.Session.Room?.Phase != LobbyPhase.Results; i++) net.Run(1);
    net.Run(30); Connected(a); Connected(b);
    Check(a.Session.Result != null && a.Session.Result.Entries.Count == 2 && a.Session.PendingInputCount == 0, "Race result did not settle");
    int credits = a.Session.CurrentCredits; Check(credits > 0 && a.Store.Profiles.Values.Single().Credits == credits, "Absolute saved credits not updated");
    a.Session.BackToLobby(); net.Run(30);
    Check(a.Session.Room.Phase == LobbyPhase.Lobby && a.Session.LatestAuthoritativeWorld == null && a.Session.SamplePresentation() == null, "Old race leaked into new lobby");
    Check(a.Session.CurrentCredits == credits, "Lobby transition duplicated reward");
});
Test("bounded_uplink_stall_neutralizes_and_recovers_without_history_growth", () =>
{
    var net = new TestNetwork(150); var a = net.Add("Stall"); net.PrepareRace(a); a.Throttle = 1; net.Run(60);
    a.BlockUplinkUntil = net.Clock.NowSeconds + .7; net.Run(120); Connected(a);
    Check(a.Session.PendingInputCount <= 32 && a.Session.MissingInputs > 0 && a.Session.LateInputs > 0, "Stall was not expired/resolved");
    Check(a.Session.LastResolvedTick > 150, "Authority stopped during client stall");
});
Test("twenty_hz_ui_batch_and_six_hundred_ms_stall_do_not_loop_reconnect", () =>
{
    var net = new TestNetwork(20) { ClientFrameSeconds = .05 }; var p = net.Add("LowFPS"); net.PrepareRace(p); p.Throttle = 1;
    net.Run(180); int connections = p.Connections, sent = p.Session.SentInputs;
    net.BlockClientUntil = net.Clock.NowSeconds + .6; net.Run(180); Connected(p);
    Check(p.Connections == connections && p.Session.SentInputs > sent + 100 && p.Session.PendingInputCount < 32, "UI stall restarted session or skipped sustained tick sampling");
    Check(p.Session.FutureInputs == 0 && p.Session.Error == "", "Transient timing diagnostic became sticky UI failure");
});
foreach (var condition in new[] { (rtt: 150, jitter: 20), (rtt: 250, jitter: 50) })
    Test("arrival_deadline_with_twenty_hz_polling_rtt_" + condition.rtt, () =>
    {
        var net = new TestNetwork(condition.rtt) { JitterSeconds = condition.jitter / 1000.0, ClientFrameSeconds = .05 };
        var a = net.Add("BufferedA"); var b = net.Add("BufferedB"); net.PrepareRace(a, b);
        a.Throttle = b.Throttle = 1; net.Run(750); Connected(a); Connected(b);
        foreach (var peer in new[] { a, b })
        {
            double fraction = peer.Session.LateInputs / (double)Math.Max(1, peer.Session.SentInputs);
            arrivalBudgets.Add(new { nominalRttMs = condition.rtt, jitterMsPerDirection = condition.jitter, clientFps = 20,
                peer.Session.SentInputs, peer.Session.LateInputs, peer.Session.FutureInputs, peer.Session.MissingInputs,
                peer.Session.InputLeadTicks, lateFraction = fraction, peer.Connections, measuredRttMs = peer.Session.RttMs });
            Check(peer.Connections == 1 && peer.Session.FutureInputs == 0 && fraction < .05, "Arrival deadline exceeded5%late budget: " + peer.Session.LateInputs + "/" + peer.Session.SentInputs);
        }
    });
Test("old_epoch_reliable_control_replay_advances_cursor_without_action", () =>
{
    var net = new TestNetwork(); var p = net.Add("OldControl"); net.PrepareRace(p); p.Drop(); net.Run(90); Connected(p); var before = p.Session.Room;
    long seq = p.Trace.Where(t => t.StartsWith("recv:") && !t.StartsWith("recv:mpWelcome")).Select(t => long.TryParse(t.Split(':')[2].Split(' ')[0], out var v) ? v : 0).Max();
    int oldEpoch = net.Codec.Decode<MpSnapshot>(p.LastSnapshot).sessionEpoch - 1;
    p.Inject(new MpCommandAccepted { sessionEpoch = oldEpoch, reliableSequence = seq + 1, requestId = 999 });
    p.Inject(new MpError { sessionEpoch = oldEpoch, reliableSequence = seq + 2, terminal = true, code = "old_terminal" });
    p.Inject(new MpRoomList { reliableSequence = seq + 3 });
    Check(p.Session.Status == SessionStatus.Connected && !p.Session.IsReconnecting && ReferenceEquals(before, p.Session.Room), "Old control replay triggered action or reliable gap");
});
Test("result_storage_pending_keeps_connection_and_freezes_input", () =>
{
    var net = new TestNetwork(); var p = net.Add("ResultIO"); net.PrepareRace(p);
    var m = net.Codec.Decode<MpSnapshot>(p.LastSnapshot); m.resultsPending = true; p.Inject(m);
    int sent = p.Session.SentInputs;
    for (int i = 0; i < 360; i++)
    {
        net.Clock.NowSeconds += 1.0 / 60; m.serverServiceTick++; p.Inject(m); p.Session.Step(1, 0, 0); p.Session.SamplePresentation();
    }
    Check(p.Session.ResultsPending && p.Session.Status == SessionStatus.Connected && p.Session.SentInputs == sent && p.Session.PendingInputCount == 0, "Result write retry caused prediction/reconnect");
});
Test("replaced_session_stops_automatic_takeover_fight", () =>
{
    var net = new TestNetwork(); var first = net.Add("Original"); net.Run(30);
    var copy = new MemoryStore(); foreach (var item in first.Store.Resumes) copy.Resumes.Add(item.Key, item.Value);
    var replacement = net.Add("Original", false, copy); net.Run(120);
    Check(first.Session.Status == SessionStatus.Failed && !first.Session.IsReconnecting && replacement.Session.Status == SessionStatus.Connected,
        "Replaced tab kept fighting for the same lease");
});
Test("neighbor_contact_prediction_reduces_future_vehicle_overshoot", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0); var rider = RaceSimulation.AddPlayer(world, 1); rider.SpeedMillimetersPerSecond = 50000;
    RaceSimulation.FindRider(world, GameplayRules.PoliceId).Mode = RiderMode.Wrecked;
    var car = world.Traffic[0]; world.TrafficCount = 1; car.Id = 3001; car.Active = true; car.DistanceMillimeters = 14000; car.SpeedMillimetersPerSecond = -20000;
    var set = new PredictionNeighbors { TrafficCount = 1 }; var proxy = set.Traffic[0];
    proxy.Id = car.Id; proxy.DistanceMillimeters = car.DistanceMillimeters; proxy.SpeedMillimetersPerSecond = car.SpeedMillimetersPerSecond;
    var withContacts = new RiderPredictor(0); var without = new RiderPredictor(0); withContacts.SetNeighbors(set);
    var initial = RiderCheckpoints.Capture(rider, 0); withContacts.Restore(initial); without.Restore(initial);
    for (int i = 1; i <= 24; i++) { var input = new RaceInput(0, 0, 0); withContacts.Advance(i, input); without.Advance(i, input); RaceSimulation.SetInput(world, 1, input); RaceSimulation.Step(world); }
    long withError = Math.Abs(withContacts.Checkpoint.Data.DistanceMillimeters - rider.DistanceMillimeters);
    long withoutError = Math.Abs(without.Checkpoint.Data.DistanceMillimeters - rider.DistanceMillimeters);
    Check(withError < 20 && withoutError > 5000 && withContacts.Checkpoint.Data.Mode == rider.Mode, "Predicted swept contact did not remove vehicle overshoot");
});
Test("wrong_predicted_contact_is_reversible_and_airborne_clearance_matches", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0); var rider = RaceSimulation.AddPlayer(world, 1); rider.SpeedMillimetersPerSecond = 20000;
    var initial = RiderCheckpoints.Capture(rider, 0); var set = new PredictionNeighbors { TrafficCount = 1 }; set.Traffic[0].Id = 3001;
    var predicted = new RiderPredictor(0); predicted.SetNeighbors(set); predicted.Restore(initial); predicted.Advance(1, default);
    Check(predicted.Checkpoint.Data.Mode == RiderMode.Falling, "Contact setup did not trigger");
    set.TrafficCount = 0; predicted.Restore(initial); predicted.Advance(1, default);
    Check(predicted.Checkpoint.Data.Mode == RiderMode.Riding && predicted.Checkpoint.Data.Health == 4096, "Authoritative replacement retained false collision");
    foreach (bool van in new[] { false, true })
    {
        var d = initial.Data; d.Mode = RiderMode.Airborne; d.HeightMillimeters = 2000;
        set.TrafficCount = 1; set.Traffic[0].HeightMillimeters = van ? VehicleDimensions.VanHeight : VehicleDimensions.CoupeHeight;
        predicted.Restore(new RiderCheckpoint(d)); predicted.Advance(1, default);
        Check(van ? predicted.Checkpoint.Data.Mode == RiderMode.Falling : predicted.Checkpoint.Data.Mode == RiderMode.Airborne, "Prediction ignored real obstacle height");
    }
});
Test("fixed_proxy_capacity_and_replay_allocate_no_per_tick_objects", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0); var rider = RaceSimulation.AddPlayer(world, 1); var initial = RiderCheckpoints.Capture(rider, 0);
    var set = new PredictionNeighbors { TrafficCount = 12, PedestrianCount = 6, RiderCount = 15 };
    for (int i = 0; i < 12; i++) { set.Traffic[i].Id = 3001 + i; set.Traffic[i].DistanceMillimeters = 100000 + i * 7000; }
    for (int i = 0; i < 6; i++) { set.Pedestrians[i].Id = 4001 + i; set.Pedestrians[i].DistanceMillimeters = 150000 + i * 5000; }
    for (int i = 0; i < 15; i++) { set.Riders[i].Id = 1001 + i; set.Riders[i].DistanceMillimeters = 180000 + i * 5000; }
    var predictor = new RiderPredictor(0); predictor.SetNeighbors(set); predictor.Restore(initial); for (int i = 1; i <= 40; i++) predictor.Advance(i, default);
    long before = GC.GetAllocatedBytesForCurrentThread();
    for (int pass = 0; pass < 100; pass++) { predictor.Restore(initial); for (int i = 1; i <= 40; i++) predictor.Advance(i, new RaceInput(1000, 0, 0)); }
    Check(GC.GetAllocatedBytesForCurrentThread() == before, "Proxy replay allocated per-tick objects");
});
RemoteImmunityRegression.Register(Test, Check);

foreach (int delay in new[] { 0, 150, 250 })
    Test("near_combat_alignment_rtt_" + delay, () =>
    {
        var net = new TestNetwork(delay); var a = net.Add("Left"); var b = net.Add("Right"); net.PrepareRace(a, b); Connected(a); Connected(b);
        b.Steer = -1; net.Run(18); b.Steer = 0; net.Run(45);
        a.Attack = 1; b.Attack = -1; a.Throttle = b.Throttle = 1; net.Run(360);
        Connected(a); Connected(b);
        Check(a.Session.NearCombatResidualSamples > 10, "No comparable near-combat samples");
        Check(a.Session.PendingInputCount <= 32 && a.Session.FutureInputs == 0, "Unbounded or future input at latency");
        Check(a.Session.MaximumNearCombatResidualMeters < (delay == 0 ? .15f : delay == 150 ? .6f : 1f), "Near-combat residual exceeded scenario tolerance");
        latency.Add(new { configuredRttMs = delay, measuredRttMs = a.Session.RttMs, a.Session.NearCombatResidualSamples,
            maxRelativePositionResidualMeters = a.Session.MaximumNearCombatResidualMeters, latestResidualMeters = a.Session.NearCombatResidualMeters,
            a.Session.SteadyResidualSamples, a.Session.MaximumSteadyResidualMeters, a.Session.ContactResidualSamples, a.Session.MaximumContactResidualMeters,
            a.Session.LastCorrectionMeters, a.Session.MaximumCorrectionMeters, a.Session.LateInputs, a.Session.MissingInputs, a.Session.RemoteExtrapolationMs,
            authorityHealth = a.Session.LocalRider.Health, note = "Synthetic ordered transport using real server/client application; not an external WAN browser test." });
    });

Directory.CreateDirectory("docs/p05");
var sources = new List<object>();
var paths = Directory.GetFiles("Assets/RacingBois/Client/Application", "*.cs").Concat(new[] {
    "Packages/com.racingbois.foundation/Runtime/Simulation/RiderPrediction.cs", "Packages/com.racingbois.foundation/Runtime/Simulation/CombatResolver.cs",
    "Packages/com.racingbois.foundation/Runtime/Simulation/DrivingDynamics.cs", "Packages/com.racingbois.foundation/Runtime/Simulation/PredictionNeighbors.cs",
    "Packages/com.racingbois.foundation/Runtime/NetworkMapping/CheckpointMapper.cs", "Packages/com.racingbois.foundation/Runtime/Protocol/MultiplayerMessages.cs",
    "src/Server/RacingBois.Server.Application/Multiplayer/MultiplayerProjection.cs",
    "src/Tests/RacingBois.P05Client.Tests/Fixtures/remote-immunity-observed.json",
    "src/Tests/RacingBois.P05Client.Tests/RemoteImmunityRegression.cs",
    "src/Tests/RacingBois.P05Client.Tests/Program.cs", "src/Tests/RacingBois.P05Client.Tests/NetworkHarness.cs" }).OrderBy(p => p, StringComparer.Ordinal);
foreach (string path in paths) sources.Add(new { path = path.Replace('\\', '/'), sha256 = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() });
File.WriteAllText(args.Length > 0 ? args[0] : "docs/p05/client-validation.json", JsonSerializer.Serialize(new { generatedAtUtc = DateTimeOffset.UtcNow, passed = failed == 0,
    tests = reports.Count, failed, sources, latency, arrivalBudgets, results = reports }, new JsonSerializerOptions { WriteIndented = true }));
return failed == 0 ? 0 : 1;
