using System.Diagnostics;
using System.Text;
using System.Text.Json;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Server.Application.Multiplayer;
using RacingBois.Server.Host;
using RacingBois.Server.Host.Multiplayer;
using RacingBois.Server.Infrastructure;
using RacingBois.Server.Application.Career;

var results = new List<object>(); int failures = 0; var total = Stopwatch.StartNew();
Test("p07_private_rooms_are_unlisted_but_joinable_with_invite", () =>
{
    using var f = new Fixture(); var host = f.Connect(); var peer = f.Connect();
    f.Send(host, new MpCreateRoom { name = "Private crew", publicRoom = false });
    Check(!host.Lobby!.publicRoom, "Private setting was lost.");
    f.Send(peer, new MpListRooms());
    Check(peer.Rooms!.rooms.Length == 0, "Private code leaked to discovery.");
    f.Send(peer, new MpJoinRoom { code = host.Lobby.code });
    Check(peer.Lobby!.roomId == host.Lobby.roomId && peer.Lobby.members.Length == 2, "Code invitation could not join.");
});
Test("p08_invalid_content_and_locked_campaign_rejected_by_authority", () =>
{
    using var f = new Fixture(); var peer = f.Connect(guest: false);
    f.Send(peer, new MpCreateRoom { name = "Unknown course", courseIndex = 5 });
    Check(peer.LastError == "course_unavailable" && f.Service.RoomCount == 0, "Out-of-range course admitted.");
    f.Send(peer, new MpCreateRoom { name = "Locked", levelIndex = 4 });
    Check(peer.LastError == "campaign_locked" && f.Service.RoomCount == 0, "Client forged unlocked level.");
    f.Send(peer, new MpCreateRoom { name = "Invalid", courseIndex = -1 });
    Check(peer.LastError == "course_unavailable", "Negative course admitted.");
});
Test("p07_account_revocation_fences_live_socket_and_resume", () =>
{
    using var f = new Fixture(durable: true); var peer = f.Connect(guest: false); f.Room(peer);
    var welcome = peer.Welcome!;
    var career = new CareerService(f.Store);
    Check(career.Execute(welcome.profileToken, new CareerRequest { operation = "logout" }).ok, "Credential revoke failed.");
    f.Step(60);
    Check(!peer.Connected && f.Service.SessionCount == 0, "Revoked socket remained active.");
    var resumed = f.Connect(resumeToken: welcome.resumeToken);
    Check(resumed.Welcome == null, "Revoked identity resumed through race credential.");
});
Test("p07_one_profile_cannot_reserve_two_races_or_mutate_racing_garage", () =>
{
    using var f = new Fixture(durable: true); var a = f.Connect(guest: false);
    var b = f.Connect(guest: false, profileToken: a.Welcome!.profileToken);
    f.Room(a); f.Room(b); f.ReadyAndStart(a); f.ReadyAndStart(b);
    Check(a.Lobby!.state == (int)MultiplayerRoomState.Countdown && b.LastError == "profile_busy", "Concurrent race reservation accepted.");
    var career = new CareerService(f.Store);
    var mutation = career.Execute(a.Welcome.profileToken, new CareerRequest { operation = "equip", bikeId = BikeCatalog.StarterBikeId, transactionId = Guid.NewGuid().ToString("D") });
    Check(!mutation.ok && mutation.code == "profile_busy", "Garage changed after race configuration reserved.");
    f.Send(a, new MpLeaveRoom { roomId = a.Lobby.roomId });
    var recovered = career.Execute(a.Welcome.profileToken, new CareerRequest { operation = "equip", bikeId = BikeCatalog.StarterBikeId, transactionId = Guid.NewGuid().ToString("D") });
    Check(recovered.ok, "Cancelled countdown kept profile reserved.");
});
Test("p07_start_rechecks_equipped_condition_after_async_reservation", () =>
{
    GatedPersistence? gate = null;
    using var f = new Fixture(store => gate = new GatedPersistence(store), durable: true);
    var peer = f.Connect(guest: false); string id = peer.Welcome!.profileId, token = peer.Welcome.profileToken;
    string funding = f.Store.BeginMatch();
    f.Store.Commit(funding, [new RealmGrant { ProfileId = id, Reward = 5000 }]);
    var career = new CareerService(f.Store);
    Check(career.Execute(token, new CareerRequest { operation = "buy", bikeId = "rb-ember", transactionId = Guid.NewGuid().ToString("D") }).ok, "Fixture second bike unavailable.");
    string wreck = f.Store.BeginMatch([id]);
    f.Store.Commit(wreck, [new RealmGrant { ProfileId = id, BikeId = BikeCatalog.StarterBikeId, BikeCondition = 0, Outcome = (int)MultiplayerOutcome.Wrecked }]);
    Check(career.Execute(token, new CareerRequest { operation = "equip", bikeId = "rb-ember", transactionId = Guid.NewGuid().ToString("D") }).ok, "Fixture healthy equip failed.");
    f.Room(peer); f.Send(peer, new MpSetReady { roomId = peer.Lobby!.roomId, ready = true });
    gate!.HoldReservations = true; f.AutoDrainStorage = false;
    f.Send(peer, new MpStartRace { roomId = peer.Lobby.roomId });
    Check(career.Execute(token, new CareerRequest { operation = "equip", bikeId = BikeCatalog.StarterBikeId, transactionId = Guid.NewGuid().ToString("D") }).ok, "Fixture mutation did not precede reservation.");
    gate.ReleaseReservation(0, false); f.AutoDrainStorage = true; f.DrainStorage();
    Check(peer.LastError == "repair_required" && peer.Lobby.state == (int)MultiplayerRoomState.Lobby, "Asynchronous start admitted a newly equipped wreck.");
    Check(career.Execute(token, new CareerRequest { operation = "equip", bikeId = "rb-ember", transactionId = Guid.NewGuid().ToString("D") }).ok, "Failed eligibility leaked match reservation.");
});
Test("p08_every_route_and_equipped_bike_character_reach_authoritative_checkpoint", () =>
{
    for (int course = 0; course < CampaignCatalog.RouteCount; course++)
    {
        if (!CampaignCatalog.IsPlayableRoute(course)) continue;
        using var f = new Fixture(durable: true); var peer = f.Connect(guest: false); string token = peer.Welcome!.profileToken;
        var career = new CareerService(f.Store);
        Check(career.Execute(token, new CareerRequest { operation = "trade", bikeId = "rb-ember", transactionId = Guid.NewGuid().ToString("N") }).ok, "Fixture equipment failed.");
        Check(career.Execute(token, new CareerRequest { operation = "character", characterId = "rb-kai", transactionId = Guid.NewGuid().ToString("N") }).ok, "Fixture cosmetic failed.");
        f.Send(peer, new MpCreateRoom { name = "Authored course", courseIndex = course, botCount = 0 }); f.ReadyAndStart(peer);
        Check(peer.Snapshot != null && peer.Snapshot.courseIndex == course && peer.Snapshot.trackLengthMillimeters == TrackDefinition.ForCourse(course, 0).LengthMillimeters, "Authority used the wrong route.");
        Check(peer.Snapshot!.own.rider.bikeCatalogIndex == 4 && peer.Snapshot.own.rider.characterCatalogIndex == 7, "Authority ignored equipped profile.");
        var denied = career.Execute(token, new CareerRequest { operation = "character", characterId = "rb-ash", transactionId = Guid.NewGuid().ToString("N") });
        Check(denied.code == "profile_busy", "Cosmetic changed after match roster capture.");
    }
});
Test("previous_multiplayer_protocols_fail_closed_without_profile_allocation", () =>
{
    foreach (int version in new[] { 3, 4, 5 })
    {
        using var f = new Fixture(); var peer = f.Connect(version: version);
        Check(peer.LastError == "version_mismatch" || !peer.Connected, "Old protocol peer admitted.");
        Check(peer.Welcome == null && f.Store.ProfileCount == 0 && f.Service.SessionCount == 0,
            "Rejected protocol allocated a profile or live session.");
    }
});
Test("lobby_capacity_ready_countdown_and_late_join_policy", () =>
{
    using var f = new Fixture(); var host = f.Connect(); f.Send(host, new MpCreateRoom { name = "Coastal crew", botCount = 5 });
    var lobby = host.Lobby!; var peers = new List<Client> { host };
    for (int i = 1; i < 8; i++) { var peer = f.Connect(); f.Send(peer, new MpJoinRoom { code = lobby.code }); peers.Add(peer); }
    var ninth = f.Connect(); f.Send(ninth, new MpJoinRoom { code = lobby.code }); Check(ninth.LastError == "room_full", "Ninth member accepted.");
    f.Send(host, new MpStartRace { roomId = lobby.roomId }); Check(host.LastError == "not_ready", "Unready race started.");
    foreach (var peer in peers) f.Send(peer, new MpSetReady { roomId = lobby.roomId, ready = true });
    f.Send(peers[1], new MpStartRace { roomId = lobby.roomId }); Check(peers[1].LastError == "host_only", "Non-host started race.");
    f.Send(host, new MpStartRace { roomId = lobby.roomId });
    Check(host.Lobby!.state == (int)MultiplayerRoomState.Countdown && host.Snapshot!.tick == 0, "Countdown did not freeze world.");
    f.Send(ninth, new MpJoinRoom { code = lobby.code }); Check(ninth.LastError == "late_join_closed", "Countdown admitted late join.");
    f.Step(179); Check(host.Lobby!.state == (int)MultiplayerRoomState.Countdown, "Countdown shorter than 180 ticks.");
    f.Step(1); Check(host.Lobby!.state == (int)MultiplayerRoomState.Racing, "Countdown never started.");
    Check(peers.Select(peer => peer.Snapshot!.riderId).Distinct().Count() == 8, "Slots not unique.");
});
Test("duplicate_commands_do_not_duplicate_rooms_or_matches", () =>
{
    using var f = new Fixture(); var peer = f.Connect(); var create = new MpCreateRoom { name = "One room" };
    f.Send(peer, create); string room = peer.Lobby!.roomId; f.Raw(peer, create);
    Check(f.Service.RoomCount == 1 && peer.Lobby.roomId == room, "Create replay duplicated room.");
    f.Send(peer, new MpSetReady { roomId = room, ready = true }); var start = new MpStartRace { roomId = room };
    f.Send(peer, start); string match = peer.Lobby.matchId; f.Raw(peer, start);
    Check(peer.Lobby.matchId == match && peer.Lobby.raceEpoch == 1, "Start replay duplicated match.");
});
Test("host_leave_transfers_role_and_cancels_countdown", () =>
{
    using var f = new Fixture(); var a = f.Connect(); var b = f.Connect(); f.Room(a, b);
    f.Send(a, new MpSetReady { roomId = a.Lobby!.roomId, ready = true }); f.Send(b, new MpSetReady { roomId = b.Lobby!.roomId, ready = true });
    f.Send(a, new MpStartRace { roomId = a.Lobby.roomId }); f.Send(a, new MpLeaveRoom { roomId = a.Lobby.roomId });
    Check(b.Lobby!.state == (int)MultiplayerRoomState.Lobby && b.Lobby.hostSessionId == b.Welcome!.sessionId && !b.Lobby.members[0].ready,
        "Host leave retained stale countdown/role/readiness.");
    Check(a.Lobby!.state == (int)MultiplayerRoomState.Closing && a.Lobby.roomId == "", "Leaving peer retained room.");
});
Test("resume_preserves_slot_fences_old_connection_and_reacquires_empty_host", () =>
{
    using var f = new Fixture(); var original = f.Connect(); f.Send(original, new MpCreateRoom { name = "Resume" });
    string room = original.Lobby!.roomId, session = original.Welcome!.sessionId; int epoch = original.Welcome.sessionEpoch;
    f.Disconnect(original); var resumed = f.Connect(resumeToken: original.Welcome.resumeToken, lastAck: original.LastReliable);
    Check(resumed.Welcome!.sessionId == session && resumed.Welcome.sessionEpoch == epoch + 1 && resumed.Lobby!.members.Length == 1 &&
        resumed.Lobby.hostSessionId == session, "Resume duplicated slot or lost host.");
    f.Raw(original, new MpSetReady { requestId = 99, sessionEpoch = epoch, roomId = room, ready = true });
    Check(!resumed.Lobby!.members[0].ready, "Old socket changed readiness.");
    f.Raw(resumed, new MpSetReady { requestId = 1, sessionEpoch = epoch, roomId = room, ready = true });
    Check(resumed.LastError == "session_epoch", "Old epoch accepted on new connection.");
});
Test("lost_initial_welcome_nonce_is_idempotent_and_bound_to_intent", () =>
{
    using var f = new Fixture(); string nonce = Guid.NewGuid().ToString("N"); var first = f.Connect(guest: false, nonce: nonce);
    var retry = f.Connect(guest: false, nonce: nonce);
    Check(f.Store.ProfileCount == 1 && f.Service.SessionCount == 1 && first.Welcome!.profileId == retry.Welcome!.profileId &&
        first.Welcome.profileToken == retry.Welcome.profileToken && retry.Welcome.sessionEpoch == 2, "Lost welcome created a second profile/lease.");
    var changed = f.Connect(guest: true, nonce: nonce); Check(changed.LastError == "hello_nonce_conflict", "Nonce accepted different identity intent.");
});
Test("resume_requires_bearer_and_matching_profile_owner", () =>
{
    using var f = new Fixture(); var a = f.Connect(guest: false); var b = f.Connect(guest: false);
    var invalid = f.Connect(resumeToken: RealmStore.Capability()); Check(invalid.LastError == "resume_expired", "Invalid resume fell back to guest.");
    var foreign = f.Connect(guest: false, resumeToken: a.Welcome!.resumeToken, profileToken: b.Welcome!.profileToken);
    Check(foreign.LastError == "resume_owner", "Foreign profile resumed victim lease.");
});
Test("invalid_initial_ack_cannot_allocate_profile_and_revoked_nonce_cannot_bootstrap_again", () =>
{
    using var f = new Fixture(); var invalid = f.Connect(guest: false, lastAck: 1);
    Check(invalid.LastError == "future_ack" && f.Store.ProfileCount == 0 && f.Service.SessionCount == 0, "Rejected hello consumed durable identity capacity.");
    string nonce = Guid.NewGuid().ToString("N"); var original = f.Connect(guest: false, nonce: nonce); f.Send(original, new MpGoodbye());
    var replay = f.Connect(guest: false, nonce: nonce);
    Check(replay.LastError == "hello_nonce_revoked" && f.Store.ProfileCount == 1 && f.Service.SessionCount == 0, "Revoked bootstrap allocated another profile.");
});
Test("hello_nonce_tombstones_are_bounded_under_connection_churn", () =>
{
    using var f = new Fixture();
    for (int i = 0; i < 256; i++) { var client = f.Connect(); f.Send(client, new MpGoodbye()); }
    var excess = f.Connect(); Check(excess.LastError == "hello_capacity" && f.Service.HelloCacheCount == 256 && f.Service.SessionCount == 0, "Hello cache grew without a bound.");
    f.Step(1801); var available = f.Connect(); Check(available.Welcome != null && f.Service.HelloCacheCount == 1, "Expired tombstones did not release capacity.");
});
Test("goodbye_ack_revokes_lease_immediately", () =>
{
    using var f = new Fixture(); var peer = f.Connect(); f.Send(peer, new MpCreateRoom { name = "Logout" }); string token = peer.Welcome!.resumeToken;
    f.Send(peer, new MpGoodbye());
    Check(peer.Accepted.Contains(peer.RequestId) && f.Service.SessionCount == 0, "Logout did not acknowledge then revoke.");
    var resume = f.Connect(resumeToken: token); Check(resume.LastError == "resume_expired", "Logged-out lease resumed.");
});
Test("exact_tick_inputs_ack_only_processed_frames_and_preserve_short_attack", () =>
{
    using var f = new Fixture(); var peer = f.Connect(); f.Room(peer); f.ReadyAndStart(peer); var lobby = peer.Lobby!;
    f.Raw(peer, Frame(peer, 1, 1, 1000, 1)); f.Raw(peer, Frame(peer, 2, 2, 0, 0)); f.Raw(peer, Frame(peer, 3, 10, 1000, 0));
    Check(peer.Snapshot!.lastProcessedSequence == 0, "Queued frame prematurely acknowledged.");
    f.Step(181); var state = peer.Snapshot!;
    Check(state.tick >= 1 && state.lastProcessedSequence <= 2 && state.own.rider.mode == (int)RiderMode.Attacking,
        "Exact tick press was overwritten or future input acknowledged.");
    f.Step(10); Check(peer.Snapshot!.lastProcessedSequence == 3, "Due future input never acknowledged.");
    CheckpointMapper.Validate(peer.Snapshot.own);
    int before = peer.Snapshot.own.rider.health;
    var invalid = Frame(peer, 4, peer.Snapshot.tick + 100, 1000, 0); f.Raw(peer, invalid);
    Check(peer.LastError == "input_future" && peer.Snapshot.own.rider.health == before, "Future input mutated authority.");
    invalid.targetTick = peer.Snapshot.tick + 2; invalid.sequence = 5; invalid.steerPermille = 1001; f.Raw(peer, invalid);
    Check(peer.LastError == "input_range", "Out-of-range steering accepted.");
});
Test("input_missing_holds_analog_six_ticks_without_replaying_attack", () =>
{
    var timeline = new InputTimeline(); Check(timeline.Add(new MpInput { sequence = 1, targetTick = 1, throttlePermille = 1000, attackSide = 1 }, 0) == null, "Frame rejected.");
    Check(timeline.Sample(1).AttackSide == 1, "Attack frame lost.");
    for (int tick = 2; tick <= 7; tick++) { var input = timeline.Sample(tick); Check(input.ThrottlePermille == 1000 && input.AttackSide == 0, "Fallback repeated attack or stopped too early."); }
    Check(timeline.Sample(8).ThrottlePermille == 0, "Missing input held longer than six ticks.");
    Check(timeline.Add(new MpInput { sequence = 2, targetTick = 4, throttlePermille = 1000 }, 8) == "input_late" && timeline.LastProcessedSequence == 2, "Late input not resolved.");
    timeline.ResetEpoch(); Check(timeline.Count == 0 && timeline.LastProcessedSequence == 0 && timeline.HeldAnalog.ThrottlePermille == 0, "Resume retained old controls.");
});
Test("disconnect_grace_expires_without_duplicate_result_and_host_continues", () =>
{
    using var f = new Fixture(); var a = f.Connect(); var b = f.Connect(); f.Room(a, b); f.ReadyAndStart(a, b); f.Step(183);
    long tick = b.Snapshot!.tick; string token = a.Welcome!.resumeToken; f.Disconnect(a); f.Step(1801);
    Check(b.Snapshot!.tick > tick && b.Lobby!.hostSessionId == b.Welcome!.sessionId && b.Lobby.members.Length == 1,
        "Authority paused or failed host transfer/grace cleanup.");
    var old = f.Connect(resumeToken: token); Check(old.LastError == "resume_expired", "Expired lease resurrected.");
    f.Step(36000); Check(b.Result != null && b.Result.persisted && b.Result.entries.Count(entry => entry.sessionId == a.Welcome.sessionId) == 1,
        "Result lost or duplicated retired participant.");
});
Test("reliable_replay_is_contiguous_and_slow_reader_resets_full_state", () =>
{
    using var f = new Fixture(); var first = f.Connect(); f.Send(first, new MpCreateRoom { name = "Replay" });
    first.AutoAck = false; long oldAck = first.LastReliable;
    for (int i = 0; i < 3; i++) f.Send(first, new MpSetReady { roomId = first.Lobby!.roomId, ready = i % 2 == 0 });
    f.Disconnect(first); var resumed = f.Connect(resumeToken: first.Welcome!.resumeToken, lastAck: oldAck);
    Check(!resumed.Welcome!.reliableReset && resumed.ReceivedReliable.First() == oldAck + 1 &&
        resumed.ReceivedReliable.Zip(resumed.ReceivedReliable.Skip(1), (a, b) => b - a).All(gap => gap == 1), "Reliable resume replay had a gap.");
    resumed.AutoAck = false;
    for (int i = 0; i < 40 && resumed.Connected; i++) { f.Send(resumed, new MpListRooms()); f.Step(7); }
    Check(!resumed.Connected, "Unacknowledged reliable queue unbounded.");
    var reset = f.Connect(resumeToken: resumed.Welcome.resumeToken, lastAck: 0);
    Check(reset.Welcome!.reliableReset && reset.Lobby?.members.Length == 1, "History overflow did not provide full state on resume.");
});
Test("realm_hashes_capability_atomic_restart_and_compacts_without_double_credit", () =>
{
    string folder = Fixture.Directory(); var store = new RealmStore(folder); var (profile, token) = store.CreateProfile("Durable"); string oldest = "";
    for (int i = 0; i < 260; i++)
    {
        string match = store.BeginMatch(); if (i == 0) oldest = match;
        var grants = new[] { new RealmGrant { ProfileId = profile.Id, SessionId = "one", Name = "Durable", RiderId = 1, Reward = 1 } };
        store.Commit(match, grants); store.Commit(match, grants);
    }
    Check(store.Credits(profile.Id) == 260 && store.RetainedResults == 256 && store.IdempotencyRanges == 1, "Result compaction/idempotency failed.");
    store.Commit(oldest, new[] { new RealmGrant { ProfileId = profile.Id, Reward = 5000 } });
    store.Dispose(); var restarted = new RealmStore(folder); Check(restarted.Authenticate(token)?.Credits == 260, "Restart lost credits or old result credited twice.");
    Check(!File.ReadAllText(Path.Combine(folder, "realm.json")).Contains(token, StringComparison.Ordinal), "Raw capability persisted.");
    string abandoned = restarted.BeginMatch(); restarted.Dispose(); var recovered = new RealmStore(folder);
    recovered.Commit(abandoned, new[] { new RealmGrant { ProfileId = profile.Id, Reward = 5000 } });
    Check(recovered.Credits(profile.Id) == 260, "Abandoned pre-restart match accepted a later payout.");
    recovered.Dispose(); File.WriteAllText(Path.Combine(folder, "realm.json"), "{broken"); bool rejected = false;
    try { _ = new RealmStore(folder); } catch (InvalidDataException) { rejected = true; }
    Check(rejected, "Corrupt realm was silently reset.");
});
Test("realm_exclusive_writer_prevents_second_host_abandoning_live_matches", () =>
{
    string folder = Fixture.Directory(); using var owner = new RealmStore(folder); string match = owner.BeginMatch();
    bool rejected = false; try { using var duplicate = new RealmStore(folder); } catch (IOException) { rejected = true; }
    Check(rejected, "Second host acquired a live realm.");
    Check(owner.Commit(match, []).MatchId == match, "Second host altered the original live match.");
});
Test("countdown_cancel_disk_failure_blocks_restart_and_recovers_without_starting_race", () =>
{
    using var f = new Fixture(); var a = f.Connect(); var b = f.Connect(); f.Room(a, b); f.ReadyAndStart(a, b);
    using (var fault = new FileStream(Path.Combine(f.DataRoot, "realm.json.pending"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
    {
        f.Disconnect(a); f.Step(1801);
        Check(b.Lobby!.state == (int)MultiplayerRoomState.Lobby && f.Service.PersistenceFailures > 0, "Persistence failure started race or escaped service.");
        f.Send(b, new MpSetReady { roomId = b.Lobby.roomId, ready = true });
        f.Send(b, new MpStartRace { roomId = b.Lobby.roomId });
        Check(b.LastError == "persistence_pending", "New match bypassed pending cancellation transaction.");
    }
    f.Step(60); f.Send(b, new MpSetReady { roomId = b.Lobby!.roomId, ready = true });
    f.Send(b, new MpStartRace { roomId = b.Lobby.roomId });
    Check(b.Lobby.state == (int)MultiplayerRoomState.Countdown, "Cancellation did not recover after storage became writable.");
});
Test("result_disk_failure_withholds_success_and_retries_exactly_once", () =>
{
    using var f = new Fixture(); var peer = f.Connect(); f.Room(peer); f.ReadyAndStart(peer); f.Step(180 + 35990);
    using (var fault = new FileStream(Path.Combine(f.DataRoot, "realm.json.pending"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
    {
        f.Step(12); Check(peer.Result == null && f.Service.PersistenceFailures > 0 && peer.Connected, "Failed result was reported as persisted or killed connection.");
    }
    f.Step(65); Check(peer.Result != null && peer.Result.persisted && f.Store.RetainedResults == 1, "Pending result failed to recover atomically.");
    f.Step(120); Check(f.Store.RetainedResults == 1, "Recovered result committed twice.");
});
Test("strict_v3_wire_rejects_duplicates_missing_and_state_claims", () =>
{
    string valid = JsonSerializer.Serialize(new MpInput { sessionEpoch = 1, roomId = "room", raceEpoch = 1, sequence = 1, targetTick = 1 }, WireJson.Options);
    Check(MultiplayerJson.Parse(Encoding.UTF8.GetBytes(valid)) is MpInput, "Valid input could not decode.");
    foreach (string invalid in new[] { valid.TrimEnd('}') + ",\"health\":4096}", valid.TrimEnd('}') + ",\"targetTick\":2}",
        valid.Replace("\"targetTick\":1,", ""), valid.Replace("\"steerPermille\":0", "\"steerPermille\":1.5") })
    { bool rejected = false; try { MultiplayerJson.Parse(Encoding.UTF8.GetBytes(invalid)); } catch (JsonException) { rejected = true; } Check(rejected, "Malformed/state-claim input accepted."); }
});
Test("peer_mailbox_bounds_reliable_lane_and_services_latest_snapshot", () =>
{
    using var mailbox = new PeerMailbox();
    for (byte i = 1; i <= 8; i++) Check(mailbox.TryWrite([i], true), "Control rejected unexpectedly.");
    mailbox.TryWrite([9], false); mailbox.TryWrite([10], false);
    var received = Enumerable.Range(0, 9).Select(_ => mailbox.Read(CancellationToken.None).GetAwaiter().GetResult()![0]).ToArray();
    Check(received.SequenceEqual(new byte[] { 1, 2, 3, 4, 10, 5, 6, 7, 8 }), "Snapshot starved or stale snapshot delivered.");
    Check(mailbox.TryWrite(new byte[40000], true) && !mailbox.TryWrite(new byte[40000], true), "Reliable byte limit not enforced.");
    mailbox.Close("done"); Check(mailbox.Read(CancellationToken.None).GetAwaiter().GetResult()!.Length == 40000 &&
        mailbox.Read(CancellationToken.None).GetAwaiter().GetResult() == null, "Close did not drain reliable messages first.");
});
Test("profile_data_cannot_be_served_from_public_webroot", () =>
{
    string root = Fixture.Directory(), web = Path.Combine(root, "web");
    foreach (string invalid in new[] { web, Path.Combine(web, "data"), Path.Combine(root, "other", "..", "web", "profiles") })
    { bool rejected = false; try { RealmPathPolicy.ResolvePrivateDataRoot(invalid, web); } catch (InvalidOperationException) { rejected = true; } Check(rejected, "Public profile data path accepted."); }
    Check(RealmPathPolicy.ResolvePrivateDataRoot(Path.Combine(root, "data"), web) == Path.Combine(root, "data"), "Private sibling data path rejected.");
});
Test("blocked_result_commit_does_not_block_second_race_ticks", () =>
{
    GatedPersistence? gate = null;
    using var f = new Fixture(store => gate = new GatedPersistence(store));
    var a = f.Connect(); f.Room(a); f.ReadyAndStart(a); f.Step(180 + 35500);
    var b = f.Connect(); f.Room(b); f.ReadyAndStart(b); f.Step(180);
    gate!.HoldCommits = true; f.AutoDrainStorage = false;
    try
    {
        f.Step(400); long before = b.Snapshot!.tick;
        Check(gate.BlockedCommits > 0 && a.Result == null && a.Snapshot!.resultsPending, "Slow commit was not held before result publication.");
        var watch = Stopwatch.StartNew(); f.Step(300);
        Check(b.Snapshot!.tick - before >= 297 && watch.ElapsedMilliseconds < 1500 && a.Result == null,
            "Another room stopped advancing while storage was blocked.");
    }
    finally { gate.Release(); f.AutoDrainStorage = true; }
    f.DrainStorage();
    Check(a.Result != null && a.Result.persisted && f.Store.RetainedResults == 1, "Result was not committed after storage recovered.");
});
Test("pending_profile_write_retries_nonce_without_duplicate_identity", () =>
{
    GatedPersistence? gate = null;
    using var f = new Fixture(store => gate = new GatedPersistence(store));
    gate!.HoldProfiles = true; f.AutoDrainStorage = false;
    string nonce = Guid.NewGuid().ToString("N"); var first = f.Connect(guest: false, nonce: nonce);
    var retry = f.Connect(guest: false, nonce: nonce);
    Check(first.Welcome == null && retry.Welcome == null && f.Service.PendingStorageCount == 1 && f.Store.ProfileCount == 0,
        "Pending welcome duplicated or prematurely published profile.");
    gate.Release(); f.AutoDrainStorage = true; f.DrainStorage();
    Check(!first.Connected && retry.Welcome != null && f.Store.ProfileCount == 1 && f.Service.SessionCount == 1,
        "Retried pending hello did not bind one profile to its newest connection.");
});
Test("pending_handshake_rejects_second_identity_on_same_connection", () =>
{
    GatedPersistence? gate = null; using var f = new Fixture(store => gate = new GatedPersistence(store));
    gate!.HoldProfiles = true; f.AutoDrainStorage = false; string nonce = Guid.NewGuid().ToString("N");
    var first = f.Connect(guest: false, nonce: nonce);
    f.Raw(first, new MpHello { requestNonce = Guid.NewGuid().ToString("N"), displayName = "Rider", freshGuest = true });
    Check(first.LastError == "handshake_pending_conflict" && f.Service.PendingStorageCount == 1 && f.Service.SessionCount == 0,
        "One connection opened a second identity while its profile was pending.");
    gate.Release(); f.AutoDrainStorage = true; f.DrainStorage();
    var recovered = f.Connect(guest: false, nonce: nonce);
    Check(recovered.Welcome != null && f.Store.ProfileCount == 1 && f.Service.SessionCount == 1, "Original pending profile was orphaned or duplicated.");
});
Test("old_epoch_storage_completion_cannot_remove_or_fail_new_pending_request", () =>
{
    foreach (bool failOld in new[] { false, true })
    {
        GatedPersistence? gate = null; using var f = new Fixture(store => gate = new GatedPersistence(store));
        var original = f.Connect(); f.Room(original); f.Send(original, new MpSetReady { roomId = original.Lobby!.roomId, ready = true });
        f.Send(original, new MpListRooms()); gate!.HoldReservations = true; f.AutoDrainStorage = false;
        f.Send(original, new MpStartRace { roomId = original.Lobby.roomId }); Check(original.RequestId == 4, "Fixture old request ID wrong.");
        f.Disconnect(original); var resumed = f.Connect(resumeToken: original.Welcome!.resumeToken, lastAck: original.LastReliable);
        f.Send(resumed, new MpLeaveRoom { roomId = resumed.Lobby!.roomId }); f.Send(resumed, new MpCreateRoom { name = "New epoch" });
        f.Send(resumed, new MpSetReady { roomId = resumed.Lobby!.roomId, ready = true });
        f.Send(resumed, new MpStartRace { roomId = resumed.Lobby.roomId }); Check(resumed.RequestId == 4, "Fixture reused request ID wrong.");
        gate.ReleaseReservation(0, failOld); f.DrainStorage(1);
        f.Raw(resumed, new MpStartRace { sessionEpoch = resumed.Welcome!.sessionEpoch, requestId = 4, roomId = resumed.Lobby.roomId });
        Check(resumed.LastError == "" && gate.ReservationCount == 2 && f.Service.PendingStorageCount == 1,
            "Old epoch completion corrupted the new request with the same numeric ID.");
        gate.ReleaseReservation(1, false); f.AutoDrainStorage = true; f.DrainStorage();
        Check(resumed.Lobby.state == (int)MultiplayerRoomState.Countdown, "New epoch reservation failed after stale completion.");
    }
});
Test("fractional_tick_clock_has_no_timer_rounding_drift_and_bounds_catchup", () =>
{
    var clock = new FixedTickClock(); int ticks = 0;
    for (int i = 1; i <= 2500; i++) ticks += clock.Advance(i * .004);
    Check(ticks == 600 && clock.DroppedTicks == 0, "Four-millisecond timer polling did not preserve exactly60Hz.");
    var jitter = new FixedTickClock(); double now = 0; int result = 0, index = 0; double[] intervals = [.004, .011, .023, .005, .018, .030];
    while (now < 20) { now = Math.Min(20, now + intervals[index++ % intervals.Length]); result += jitter.Advance(now); }
    Check(result == 1200 && jitter.DroppedTicks == 0, "Irregular timer wakes changed simulation rate.");
    Check(jitter.Advance(21) == 6 && jitter.DroppedTicks == 54 && jitter.Advance(21) == 0, "Long process stall caused unbounded catch-up.");
});
var report = new { generatedUtc = DateTimeOffset.UtcNow, passed = results.Count - failures, failed = failures, durationMilliseconds = total.Elapsed.TotalMilliseconds,
    tests = results, scope = "Real v3 room/session/timeline/realm code with a synthetic clock, actual strict host codec and mailbox. Live socket/browser/impairment reports are separate." };
string json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }); Console.WriteLine(json);
string reportPath = args.Length > 0 ? args[0] : "docs/p05/backend/domain-validation.json";
System.IO.Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(reportPath))!); File.WriteAllText(reportPath, json);
return failures == 0 ? 0 : 1;

void Test(string name, Action action) { try { action(); results.Add(new { name, status = "PASS" }); } catch (Exception error) { failures++; results.Add(new { name, status = "FAIL", error = error.ToString() }); } }
static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
static MpInput Frame(Client peer, int sequence, long tick, int throttle, int side) => new() { sessionEpoch = peer.Welcome!.sessionEpoch,
    roomId = peer.Lobby!.roomId, raceEpoch = peer.Lobby.raceEpoch, sequence = sequence, targetTick = tick,
    throttlePermille = throttle, attackSide = side, reliableAck = peer.LastReliable };

internal sealed class Client(string id)
{
    public string Id { get; } = id;
    public MpWelcome? Welcome; public MpLobby? Lobby; public MpSnapshot? Snapshot; public MpResult? Result;
    public MpRoomList? Rooms;
    public string LastError = ""; public bool Connected = true, AutoAck = true;
    public int RequestId; public long LastReliable, AckSent;
    public readonly HashSet<int> Accepted = [];
    public readonly List<long> ReceivedReliable = [];
}
internal sealed class GatedPersistence(RealmStore store) : IRealmPersistence
{
    private readonly RealmPersistence inner = new(store);
    private readonly TaskCompletionSource release = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public bool HoldCommits, HoldProfiles, HoldReservations;
    private readonly List<TaskCompletionSource> reservations = [];
    public int ReservationCount => reservations.Count;
    public int BlockedCommits;
    public Task<string> BeginMatch() => BeginMatch([]);
    public async Task<string> BeginMatch(string[] profileIds)
    {
        if (HoldReservations) { var gate = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously); reservations.Add(gate); await gate.Task; }
        return await inner.BeginMatch(profileIds);
    }
    public async Task<(RealmProfile Profile, string Token)> CreateProfile(string name)
    { if (HoldProfiles) await release.Task; return await inner.CreateProfile(name); }
    public async Task<RealmResult> Commit(string id, RealmGrant[] grants)
    { if (HoldCommits) { BlockedCommits++; await release.Task; } return await inner.Commit(id, grants); }
    public void Release() => release.TrySetResult();
    public void ReleaseReservation(int index, bool fail)
    { if (fail) reservations[index].TrySetException(new IOException("Controlled write failure.")); else reservations[index].TrySetResult(); }
    public void Dispose() { release.TrySetResult(); foreach (var gate in reservations) gate.TrySetCanceled(); inner.Dispose(); }
}
internal sealed class Fixture : IMultiplayerSink, IDisposable
{
    public string DataRoot { get; }
    public RealmStore Store { get; }
    public MultiplayerService Service { get; }
    public bool AutoDrainStorage = true;
    private readonly Dictionary<string, Client> clients = new();
    private readonly Queue<string> closed = new();
    public Fixture(Func<RealmStore, IRealmPersistence>? factory = null, bool durable = false)
    { DataRoot = Directory(); Store = durable ? new RealmStore(new SqliteRealmStateStore(DataRoot, "offline")) : new RealmStore(DataRoot); Service = new MultiplayerService(Store, this, WireJson.Serialize, factory?.Invoke(Store)); }
    public static string Directory() => Path.GetFullPath(Path.Combine("_local", "p05-tests", Guid.NewGuid().ToString("N")));
    public Client Connect(bool guest = true, string resumeToken = "", string profileToken = "", long lastAck = 0, string? nonce = null, int version = MultiplayerProtocol.Version)
    {
        var client = new Client(Guid.NewGuid().ToString("N")); clients.Add(client.Id, client);
        Raw(client, new MpHello { protocolVersion = version, freshGuest = guest, resumeToken = resumeToken, profileToken = profileToken,
            requestNonce = nonce ?? Guid.NewGuid().ToString("N"), displayName = "Rider", lastReliableSequence = lastAck });
        return client;
    }
    public void Send(Client client, MpCommand message) { message.requestId = ++client.RequestId; message.sessionEpoch = client.Welcome!.sessionEpoch; Raw(client, message); }
    public void Raw(Client client, object message) { Service.Handle(client.Id, message); Flush(); if (AutoDrainStorage) DrainStorage(); }
    public void Step(int count)
    {
        for (int i = 0; i < count; i++)
        {
            Service.Step(); Flush();
            if (Service.ServiceTick % 120 == 0)
                foreach (var client in clients.Values.Where(client => client.Connected && client.Welcome != null).ToArray())
                    Raw(client, new MpPing { sessionEpoch = client.Welcome!.sessionEpoch, nonce = "test", reliableAck = client.AutoAck ? client.LastReliable : client.AckSent });
        }
        if (AutoDrainStorage) DrainStorage();
    }
    public void Disconnect(Client client) { client.Connected = false; Service.Disconnect(client.Id); Flush(); if (AutoDrainStorage) DrainStorage(); }
    public void Room(params Client[] peers)
    { Send(peers[0], new MpCreateRoom { name = "Fixture" }); foreach (var peer in peers.Skip(1)) Send(peer, new MpJoinRoom { code = peers[0].Lobby!.code }); }
    public void ReadyAndStart(params Client[] peers)
    { foreach (var peer in peers) Send(peer, new MpSetReady { roomId = peer.Lobby!.roomId, ready = true }); Send(peers[0], new MpStartRace { roomId = peers[0].Lobby!.roomId }); }
    public bool Send(string id, byte[] bytes, bool reliable)
    {
        if (!clients.TryGetValue(id, out var client) || !client.Connected) return false;
        using var document = JsonDocument.Parse(bytes); var root = document.RootElement; string kind = root.GetProperty("kind").GetString()!;
        switch (kind)
        {
            case "mpWelcome": client.Welcome = JsonSerializer.Deserialize<MpWelcome>(bytes, WireJson.Options)!; client.RequestId = 0; if (client.Welcome.reliableReset) client.LastReliable = client.AckSent = client.Welcome.reliableSequence; break;
            case "mpLobby": client.Lobby = JsonSerializer.Deserialize<MpLobby>(bytes, WireJson.Options); break;
            case "mpRooms": client.Rooms = JsonSerializer.Deserialize<MpRoomList>(bytes, WireJson.Options); break;
            case "mpSnapshot": client.Snapshot = JsonSerializer.Deserialize<MpSnapshot>(bytes, WireJson.Options); break;
            case "mpResult": client.Result = JsonSerializer.Deserialize<MpResult>(bytes, WireJson.Options); break;
            case "mpError": client.LastError = root.GetProperty("code").GetString()!; break;
            case "mpAccepted": client.Accepted.Add(root.GetProperty("requestId").GetInt32()); break;
        }
        if (kind != "mpWelcome" && root.TryGetProperty("reliableSequence", out var sequence) && sequence.GetInt64() > 0)
        { client.LastReliable = Math.Max(client.LastReliable, sequence.GetInt64()); client.ReceivedReliable.Add(sequence.GetInt64()); }
        return true;
    }
    public void Close(string connectionId, string reason) { closed.Enqueue(connectionId); }
    private void Flush()
    {
        while (closed.TryDequeue(out string? id)) if (clients.TryGetValue(id, out var client)) { client.Connected = false; Service.Disconnect(id); }
        foreach (var client in clients.Values.Where(client => client.Connected && client.AutoAck && client.Welcome != null && client.LastReliable > client.AckSent).ToArray())
        { client.AckSent = client.LastReliable; Service.Handle(client.Id, new MpAck { sessionEpoch = client.Welcome!.sessionEpoch, reliableSequence = client.AckSent }); }
    }
    public void DrainStorage(int maximumPending = 0)
    {
        var watch = Stopwatch.StartNew();
        while (Service.PendingStorageCount > maximumPending)
        {
            Service.PollPersistence(); Flush();
            if (watch.ElapsedMilliseconds > 3000) throw new TimeoutException("Storage completion timed out.");
            Thread.Sleep(1);
        }
    }
    public void Dispose() { Service.Dispose(); Store.Dispose(); }
}
