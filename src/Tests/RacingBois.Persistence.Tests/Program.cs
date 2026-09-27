using System.Diagnostics;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Server.Application.Career;
using RacingBois.Server.Application.Multiplayer;
using RacingBois.Server.Infrastructure;

if (args.Length == 2 && args[0] is "--crash-before" or "--crash-after")
{
    string folder = Path.GetFullPath(args[1]);
    string boundary = Path.GetFullPath(Path.Combine("_local", "p07-persistence-tests")) + Path.DirectorySeparatorChar;
    if (!folder.StartsWith(boundary, StringComparison.OrdinalIgnoreCase)) return 90;
    var input = JsonSerializer.Deserialize<CrashInput>(File.ReadAllText(Path.Combine(folder, "crash-input.json")))!;
    using var store = new RealmStore(new SqliteRealmStateStore(folder, "offline", args[0] == "--crash-before" ? () => Environment.Exit(77) : null));
    var result = new CareerService(store).Execute(input.Token, Command("trade", "rb-ember", input.Transaction));
    Environment.Exit(result.ok ? 78 : 91); return 91;
}

var results = new List<object>(); int failed = 0; var started = Stopwatch.StartNew();
Test("new_realm_starter_wallet_and_database_constraints", () =>
{
    using var fixture = new Fixture(); var profile = fixture.Store.GetProfile(fixture.ProfileId)!;
    Check(profile.Credits == 1000 && profile.Career.Bikes.Single().BikeId == BikeCatalog.StarterBikeId, "Starter state mismatch.");
    using var database = Open(fixture.Folder);
    SqlRejected(database, "UPDATE profiles SET credits=-1", "Negative balance accepted.");
    SqlRejected(database, "UPDATE bikes SET condition=101", "Invalid condition accepted.");
    SqlRejected(database, "UPDATE ledger SET delta=9999", "Ledger edit accepted.");
    SqlRejected(database, "DELETE FROM ledger", "Ledger deletion accepted.");
    SqlRejected(database, "INSERT INTO ledger SELECT profile_id,1,'forged','test','',1,99999,created_utc FROM ledger LIMIT 1", "Unbalanced ledger inserted.");
    SqlRejected(database, "UPDATE realm SET kind='online'", "Realm kind changed.");
});
Test("commerce_idempotency_binds_intent_and_guid_representation", () =>
{
    using var fixture = new Fixture(); string transaction = Guid.NewGuid().ToString("D");
    var first = fixture.Api.Execute(fixture.Token, Command("trade", "rb-ember", transaction));
    var replay = fixture.Api.Execute(fixture.Token, Command("trade", "rb-ember", Guid.Parse(transaction).ToString("N")));
    var conflict = fixture.Api.Execute(fixture.Token, Command("buy", "rb-kestrel", transaction));
    Check(first.ok && replay.ok && first.profile.credits == 248 && replay.profile.credits == 248, "Trade retry changed wallet.");
    Check(conflict.code == "transaction_conflict" && fixture.Store.GetProfile(fixture.ProfileId)!.Career.Ledger.Count == 2, "Intent collision was not fenced.");
});
Test("concurrent_same_command_credits_once", () =>
{
    using var fixture = new Fixture(); string transaction = Guid.NewGuid().ToString("D");
    var tasks = Enumerable.Range(0, 16).Select(_ => Task.Run(() => fixture.Api.Execute(fixture.Token, Command("trade", "rb-ember", transaction)))).ToArray();
    Task.WaitAll(tasks);
    Check(tasks.All(task => task.Result.ok && task.Result.profile.credits == 248), "Concurrent replay diverged.");
    var profile = fixture.Store.GetProfile(fixture.ProfileId)!;
    Check(profile.Career.Ledger.Count == 2 && profile.Career.Receipts.Count == 1 && profile.Career.Bikes.Count == 1, "Concurrent command duplicated.");
});
Test("concurrent_different_purchases_cannot_overspend", () =>
{
    using var fixture = new Fixture(credits: 10_000);
    var one = Task.Run(() => fixture.Api.Execute(fixture.Token, Command("buy", "rb-jackal")));
    var two = Task.Run(() => fixture.Api.Execute(fixture.Token, Command("buy", "rb-havoc")));
    Task.WaitAll(one, two);
    Check(new[] { one.Result, two.Result }.Count(result => result.ok) == 1, "Both unaffordable purchases succeeded.");
    Check(fixture.Store.Credits(fixture.ProfileId) is 4511 or 3006 && fixture.Store.GetProfile(fixture.ProfileId)!.Career.Bikes.Count == 2, "Purchase balance/ownership mismatch.");
});
Test("failed_receipt_is_durable_and_does_not_change_inventory", () =>
{
    using var fixture = new Fixture(); string transaction = Guid.NewGuid().ToString("D");
    var failure = fixture.Api.Execute(fixture.Token, Command("buy", "rb-ember", transaction));
    Check(failure.code == "insufficient_credits", "Unaffordable purchase accepted.");
    Reward(fixture, 1000); Reward(fixture, 1000);
    var retry = fixture.Api.Execute(fixture.Token, Command("buy", "rb-ember", transaction));
    Check(!retry.ok && retry.code == "insufficient_credits", "Failed receipt changed meaning.");
    Check(fixture.Api.Execute(fixture.Token, Command("buy", "rb-ember")).ok, "New affordable purchase failed.");
});
Test("equip_and_repair_are_server_quoted_and_idempotent", () =>
{
    using var fixture = new Fixture(credits: 10_000);
    Check(fixture.Api.Execute(fixture.Token, Command("repair", BikeCatalog.StarterBikeId)).code == "already_repaired", "Pristine bike charged.");
    string match = fixture.Store.BeginMatch([fixture.ProfileId]);
    fixture.Store.Commit(match, [Grant(fixture, 1, 1000, 40)]);
    var repaired = fixture.Api.Execute(fixture.Token, Command("repair", BikeCatalog.StarterBikeId));
    Check(repaired.ok && repaired.profile.credits == 10_551 && repaired.profile.bikes.Single().condition == 100, "Repair price/state mismatch.");
    var bought = fixture.Api.Execute(fixture.Token, Command("buy", "rb-ember")); Check(bought.ok, "Buy failed.");
    Check(fixture.Api.Execute(fixture.Token, Command("equip", "rb-ember")).profile.selectedBikeId == "rb-ember", "Equip not persisted.");
    Check(fixture.Api.Execute(fixture.Token, Command("equip", "rb-havoc")).code == "bike_not_owned", "Unowned equipment accepted.");
});
Test("match_reservation_blocks_commerce_and_second_race", () =>
{
    using var fixture = new Fixture(); string match = fixture.Store.BeginMatch([fixture.ProfileId]);
    Check(fixture.Api.Execute(fixture.Token, Command("trade", "rb-ember")).code == "profile_busy", "Racing garage mutated.");
    bool rejected = false; try { fixture.Store.BeginMatch([fixture.ProfileId]); } catch (InvalidOperationException error) { rejected = error.Message == "profile_busy"; }
    Check(rejected, "Two matches reserved the same profile.");
    fixture.Store.Commit(match, []);
    Check(fixture.Api.Execute(fixture.Token, Command("trade", "rb-ember")).ok, "Cancellation did not release reservation.");
});
Test("race_rewards_fines_condition_qualification_and_replay_atomic", () =>
{
    using var fixture = new Fixture(); string match = fixture.Store.BeginMatch([fixture.ProfileId]);
    var result = fixture.Store.Commit(match, [Grant(fixture, 1, 1000, 62)]);
    fixture.Store.Commit(match, [Grant(fixture, 1, 1000, 62)]);
    var profile = fixture.Store.GetProfile(fixture.ProfileId)!;
    Check(result.Grants[0].Credits == 2000 && profile.Credits == 2000 && profile.Career.QualificationMask == 1 && profile.Career.Bikes[0].Condition == 62, "Race settlement mismatch.");
    string busted = fixture.Store.BeginMatch([fixture.ProfileId]); var fine = Grant(fixture, 0, -400, 62); fine.Outcome = (int)MultiplayerOutcome.Busted; fine.Qualified = false;
    fixture.Store.Commit(busted, [fine]); fixture.Store.Commit(busted, [fine]);
    Check(fixture.Store.Credits(fixture.ProfileId) == 1600 && fixture.Store.GetProfile(fixture.ProfileId)!.Career.Ledger.Count == 3, "Fine duplicated or disappeared.");
});
Test("forged_settlement_rolls_back_entire_match", () =>
{
    using var fixture = new Fixture(); string match = fixture.Store.BeginMatch([fixture.ProfileId]);
    var bad = Grant(fixture, 1, 4000, 1); bool rejected = false;
    try { fixture.Store.Commit(match, [bad]); } catch (InvalidOperationException) { rejected = true; }
    Check(rejected && fixture.Store.Credits(fixture.ProfileId) == 1000 && fixture.Store.GetProfile(fixture.ProfileId)!.Career.Bikes[0].Condition == 100, "Invalid reward partly applied.");
    bad = Grant(fixture, 1, 1000, 1); bad.CourseIndex = 1; rejected = false;
    try { fixture.Store.Commit(match, [bad]); } catch (InvalidOperationException) { rejected = true; }
    Check(rejected, "Unavailable campaign route credited.");
    fixture.Store.Commit(match, [Grant(fixture, 1, 1000, 100)]);
});
Test("failed_database_commit_rolls_back_then_retry_exactly_once", () =>
{
    bool fault = false;
    using var fixture = new Fixture(beforeCommit: () => { if (fault) throw new IOException("injected_disk_failure"); });
    string transaction = Guid.NewGuid().ToString("D"); fault = true;
    var failedCommit = fixture.Api.Execute(fixture.Token, Command("trade", "rb-ember", transaction));
    Check(failedCommit.code == "storage_unavailable" && fixture.Store.Credits(fixture.ProfileId) == 1000, "Failed commit was published.");
    fault = false;
    Check(fixture.Api.Execute(fixture.Token, Command("trade", "rb-ember", transaction)).ok, "Retry failed.");
    Check(fixture.Store.Credits(fixture.ProfileId) == 248 && fixture.Store.GetProfile(fixture.ProfileId)!.Career.Ledger.Count == 2, "Retry duplicated money.");
});
Test("process_crash_before_commit_recovers_without_partial_debit", () => Crash(false));
Test("process_crash_after_commit_replay_does_not_double_debit", () => Crash(true));
Test("migration_preserves_identity_credit_capability_and_backup_once", () =>
{
    string folder = Fixture.NewFolder(); string token = RealmStore.Capability(); string id = Guid.NewGuid().ToString("N");
    string legacy = JsonSerializer.Serialize(new RealmDocument { Profiles = [new RealmProfile { Id = id, Name = "Legacy", CapabilityHash = RealmStore.Hash(token), Credits = 257 }] });
    string source = Path.Combine(folder, "realm.json"); File.WriteAllText(source, legacy, new UTF8Encoding(false));
    string hash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(source)));
    string realmId;
    using (var store = new RealmStore(new SqliteRealmStateStore(folder)))
    { realmId = store.RealmId; Check(store.Authenticate(token)?.Id == id && store.Credits(id) == 257, "Migration changed identity/credit/capability."); }
    using (var store = new RealmStore(new SqliteRealmStateStore(folder))) Check(store.RealmId == realmId && store.Credits(id) == 257, "Migration repeated or reset realm.");
    Check(Directory.GetFiles(folder, "realm.v1.migration-*.json").Length == 1 && Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(source))) == hash, "Source changed or backup duplicated.");
    using var database = Open(folder); using var query = database.CreateCommand(); query.CommandText = "SELECT count(*) FROM migrations";
    Check((long)query.ExecuteScalar()! == 1, "Migration provenance missing or duplicated.");
});
Test("migration_rejects_corrupt_and_offline_into_online_without_reset", () =>
{
    string corrupt = Fixture.NewFolder(); File.WriteAllText(Path.Combine(corrupt, "realm.json"), "{broken");
    bool rejected = false; try { using var store = new SqliteRealmStateStore(corrupt); } catch (InvalidDataException) { rejected = true; }
    Check(rejected && File.ReadAllText(Path.Combine(corrupt, "realm.json")) == "{broken", "Corrupt data reset.");
    string offline = Fixture.NewFolder(); using (var legacy = new RealmStore(offline)) legacy.CreateProfile("Offline");
    rejected = false; try { using var store = new SqliteRealmStateStore(offline, "online"); } catch (InvalidDataException error) { rejected = error.Message == "offline_migration_forbidden"; }
    Check(rejected, "Offline profile migrated into online economy.");
});
Test("restart_fences_abandoned_match_and_preserves_completed_receipts", () =>
{
    string folder, token, id, abandoned, transaction = Guid.NewGuid().ToString("D");
    using (var fixture = new Fixture())
    {
        folder = fixture.Folder; token = fixture.Token; id = fixture.ProfileId;
        Check(fixture.Api.Execute(token, Command("trade", "rb-ember", transaction)).ok, "Initial trade failed."); abandoned = fixture.Store.BeginMatch([id]);
    }
    using var restarted = new RealmStore(new SqliteRealmStateStore(folder)); var api = new CareerService(restarted);
    Check(api.Execute(token, Command("trade", "rb-ember", transaction)).profile.credits == 248, "Restart lost receipt.");
    Check(restarted.Commit(abandoned, [new RealmGrant { ProfileId = id, Reward = 5000 }]).Grants.Length == 0 && restarted.Credits(id) == 248, "Abandoned match paid after restart.");
    Check(api.Execute(token, Command("equip", "rb-ember")).ok, "Restart did not release reservation.");
});
Test("accounts_upgrade_login_recovery_rotation_and_expiry", () =>
{
    var clock = new MutableClock(); using var fixture = new Fixture(clock: clock);
    string password = "Fixture-only passphrase 01!", replacement = "Fixture-only passphrase 02!";
    var registered = fixture.Api.Execute(fixture.Token, new CareerRequest { operation = "register", username = "fixture_user", password = password });
    Check(registered.ok && registered.profile.profileId == fixture.ProfileId && registered.recoveryCode.Length == 43 && !fixture.Store.IsTokenActive(fixture.Token), "Upgrade/rotation failed.");
    var login = fixture.Api.Execute("", new CareerRequest { operation = "login", username = "FIXTURE_USER", password = password });
    Check(login.ok && fixture.Store.IsTokenActive(registered.profileToken), "Login failed or unexpectedly revoked another session.");
    var recovered = fixture.Api.Execute("", new CareerRequest { operation = "recover", username = "fixture_user", password = replacement, recoveryCode = registered.recoveryCode });
    Check(recovered.ok && !fixture.Store.IsTokenActive(login.profileToken) && !fixture.Store.IsTokenActive(registered.profileToken), "Recovery did not revoke sessions.");
    Check(!fixture.Api.Execute("", new CareerRequest { operation = "recover", username = "fixture_user", password = replacement, recoveryCode = registered.recoveryCode }).ok, "Recovery code reused.");
    var retry = fixture.Api.Execute("", new CareerRequest { operation = "login", username = "fixture_user", password = replacement });
    Check(retry.ok, "Lost recovery response cannot be recovered by login.");
    var rotated = fixture.Api.Execute(retry.profileToken, new CareerRequest { operation = "rotateRecovery", password = replacement });
    Check(rotated.ok && rotated.recoveryCode.Length == 43 && !fixture.Store.IsTokenActive(recovered.profileToken), "Recovery-code regeneration failed.");
    clock.Advance(TimeSpan.FromDays(31));
    Check(!fixture.Store.IsTokenActive(rotated.profileToken) && fixture.Api.Execute(rotated.profileToken, new CareerRequest()).code == "unauthorized", "Expired capability accepted.");
});
Test("login_session_cap_and_logout_all_are_durable", () =>
{
    string folder, first = "", last = "";
    using (var fixture = new Fixture())
    {
        folder = fixture.Folder;
        var registered = fixture.Api.Execute(fixture.Token, new CareerRequest { operation = "register", username = "cap_user", password = "Fixture-only password" }); first = registered.profileToken;
        for (int i = 0; i < 10; i++) last = fixture.Api.Execute("", new CareerRequest { operation = "login", username = "cap_user", password = "Fixture-only password" }).profileToken;
        Check(!fixture.Store.IsTokenActive(first) && fixture.Store.IsTokenActive(last) && fixture.Store.GetProfile(fixture.ProfileId)!.Career.Sessions.Count == 8, "Session cap failed.");
        Check(fixture.Api.Execute(last, new CareerRequest { operation = "logoutAll" }).ok, "Logout all failed.");
    }
    using var store = new RealmStore(new SqliteRealmStateStore(folder)); Check(!store.IsTokenActive(last), "Revocation lost after restart.");
});
Test("signed_save_auth_free_ownership_validation_and_replay", () =>
{
    using var fixture = new Fixture(); var other = fixture.Store.CreateProfile("Other");
    var exported = fixture.Api.Execute(fixture.Token, new CareerRequest { operation = "export" });
    Check(exported.ok && !exported.exportJson.Contains(fixture.Token, StringComparison.Ordinal) && !exported.exportJson.Contains("PasswordHash", StringComparison.Ordinal) &&
        !exported.exportJson.Contains("CapabilityHash", StringComparison.Ordinal) && !exported.exportJson.Contains("RecoveryHash", StringComparison.Ordinal), "Export contains authentication material.");
    Check(fixture.Api.Execute(other.Token, new CareerRequest { operation = "import", transactionId = Guid.NewGuid().ToString("D"), saveJson = exported.exportJson }).code == "foreign_save", "Other profile imported save.");
    string transaction = Guid.NewGuid().ToString("D"); var command = new CareerRequest { operation = "import", transactionId = transaction, saveJson = exported.exportJson };
    Check(fixture.Api.Execute(fixture.Token, command).ok && fixture.Api.Execute(fixture.Token, command).ok, "Fresh save or idempotent retry failed.");
    command.transactionId = Guid.NewGuid().ToString("D");
    Check(fixture.Api.Execute(fixture.Token, command).code == "stale_save", "Save replay with new ID was accepted.");
    command.transactionId = Guid.NewGuid().ToString("D"); command.saveJson = exported.exportJson.Replace("1000", "9999", StringComparison.Ordinal);
    Check(fixture.Api.Execute(fixture.Token, command).code == "invalid_save", "Tampered signed save accepted.");
});
Test("online_separation_rejects_local_save_and_realm_relabel", () =>
{
    using var offline = new Fixture(); string exported = offline.Api.Execute(offline.Token, new CareerRequest { operation = "export" }).exportJson;
    using var online = new Fixture(kind: "online");
    Check(online.Api.Execute(offline.Token, new CareerRequest()).code == "unauthorized", "Cross-realm token accepted.");
    Check(online.Api.Execute(online.Token, new CareerRequest { operation = "export" }).code == "offline_only", "Online save exported.");
    Check(online.Api.Execute(online.Token, new CareerRequest { operation = "import", transactionId = Guid.NewGuid().ToString("D"), saveJson = exported }).code == "offline_only", "Offline assets imported online.");
    string path = online.Folder; online.Dispose(); bool rejected = false;
    try { using var store = new SqliteRealmStateStore(path, "offline"); } catch (InvalidDataException error) { rejected = error.Message == "realm_kind_mismatch"; }
    Check(rejected, "Realm relabeled by launch configuration.");
});
Test("closed_database_backup_restore_retains_identity_wallet_and_receipts", () =>
{
    string folder, token, id, transaction = Guid.NewGuid().ToString("D");
    using (var fixture = new Fixture())
    { folder = fixture.Folder; token = fixture.Token; id = fixture.ProfileId; Check(fixture.Api.Execute(token, Command("trade", "rb-ember", transaction)).ok, "Trade failed."); }
    string restored = Fixture.NewFolder(); File.Copy(Path.Combine(folder, "realm.sqlite3"), Path.Combine(restored, "realm.sqlite3"));
    using var store = new RealmStore(new SqliteRealmStateStore(restored)); var api = new CareerService(store);
    Check(store.Authenticate(token)?.Id == id && api.Execute(token, Command("trade", "rb-ember", transaction)).profile.credits == 248, "Restore changed identity or paid replay.");
});
Test("exclusive_owner_does_not_fence_other_live_host", () =>
{
    using var fixture = new Fixture(); string match = fixture.Store.BeginMatch([fixture.ProfileId]); bool rejected = false;
    try { using var duplicate = new SqliteRealmStateStore(fixture.Folder); } catch (IOException) { rejected = true; }
    Check(rejected, "Second writer acquired realm.");
    Check(fixture.Store.Commit(match, [Grant(fixture, 1, 1000, 100)]).Grants.Length == 1, "Rejected owner affected live match.");
});
Test("security_audit_contains_safe_codes_not_credentials", () =>
{
    using var fixture = new Fixture(); string password = "Fixture-only audit password";
    var registered = fixture.Api.Execute(fixture.Token, new CareerRequest { operation = "register", username = "audit_user", password = password });
    fixture.Api.Execute("", new CareerRequest { operation = "login", username = "audit_user", password = "Wrong fixture password" });
    using var database = Open(fixture.Folder); using var query = database.CreateCommand();
    query.CommandText = "SELECT operation,code,profile_id FROM security_audit ORDER BY rowid";
    using var reader = query.ExecuteReader(); var audit = new List<string>();
    while (reader.Read()) audit.Add(reader.GetString(0) + ":" + reader.GetString(1) + ":" + reader.GetString(2));
    Check(audit.Count == 2 && audit[0].StartsWith("register:registered:", StringComparison.Ordinal) && audit[1] == "login:invalid_credentials:", "Security outcome audit missing.");
    string output = string.Join("\n", audit);
    Check(!output.Contains(password, StringComparison.Ordinal) && !output.Contains(fixture.Token, StringComparison.Ordinal) &&
        !output.Contains(registered.profileToken, StringComparison.Ordinal) && !output.Contains(registered.recoveryCode, StringComparison.Ordinal), "Credentials escaped into audit.");
});
Test("restart_rejects_divergent_database_projection_without_reset", () =>
{
    string folder;
    using (var fixture = new Fixture()) folder = fixture.Folder;
    using (var database = Open(folder))
    { using var change = database.CreateCommand(); change.CommandText = "UPDATE bikes SET condition=50"; change.ExecuteNonQuery(); }
    bool rejected = false; try { using var database = new SqliteRealmStateStore(folder); } catch (InvalidDataException error) { rejected = error.Message == "database_inventory_mismatch"; }
    Check(rejected, "Divergent normalized state silently accepted/reset.");
});
Test("startup_compares_profile_session_reservation_and_receipt_rows", () =>
{
    string[] changes = ["UPDATE profiles SET username='forged'", "UPDATE profiles SET level_index=1", "UPDATE profiles SET qualification_mask=2",
        "UPDATE profiles SET revision=999", "UPDATE sessions SET expires_unix=expires_unix+1", "UPDATE reservations SET match_number=match_number+1"];
    foreach (string sql in changes)
    {
        string folder;
        using (var fixture = new Fixture()) { folder = fixture.Folder; fixture.Store.BeginMatch([fixture.ProfileId]); }
        using (var database = Open(folder)) { using var update = database.CreateCommand(); update.CommandText = sql; update.ExecuteNonQuery(); }
        bool rejected = false; try { using var database = new SqliteRealmStateStore(folder); } catch (InvalidDataException) { rejected = true; }
        Check(rejected, "A divergent normalized profile/session/reservation row was accepted.");
    }
    string receiptFolder;
    using (var fixture = new Fixture()) { receiptFolder = fixture.Folder; fixture.Api.Execute(fixture.Token, Command("equip", BikeCatalog.StarterBikeId)); }
    using (var database = Open(receiptFolder))
    {
        using var query = database.CreateCommand(); query.CommandText = "SELECT state_json FROM realm";
        var state = RealmStore.Deserialize((string)query.ExecuteScalar()!); state.Profiles[0].Career.Receipts[0].Fingerprint = new string('a', 64);
        using var update = database.CreateCommand(); update.CommandText = "UPDATE realm SET state_json=$json"; update.Parameters.AddWithValue("$json", JsonSerializer.Serialize(state)); update.ExecuteNonQuery();
    }
    bool receiptRejected = false; try { using var database = new SqliteRealmStateStore(receiptFolder); } catch (InvalidDataException error) { receiptRejected = error.Message == "database_receipt_mismatch"; }
    Check(receiptRejected, "Divergent receipt fingerprint accepted.");
});
Test("storage_port_cannot_rewrite_existing_receipt_prefix", () =>
{
    string folder;
    using (var fixture = new Fixture()) { folder = fixture.Folder; fixture.Api.Execute(fixture.Token, Command("equip", BikeCatalog.StarterBikeId)); }
    using var database = new SqliteRealmStateStore(folder); var state = database.Load(); string original = state.Profiles[0].Career.Receipts[0].Fingerprint;
    state.Revision++; state.Profiles[0].Career.Receipts[0].Fingerprint = new string('b', 64);
    bool rejected = false; try { database.Save(state); } catch (InvalidDataException error) { rejected = error.Message == "immutable_receipt"; }
    Check(rejected && database.Load().Profiles[0].Career.Receipts[0].Fingerprint == original, "Receipt rewrite changed state snapshot.");
});
Test("bankrupt_restart_is_gated_atomic_and_replay_safe", () =>
{
    using var fixture = new Fixture(credits: 100);
    Check(fixture.Api.Execute(fixture.Token, Command("restartCareer", "")).code == "not_bankrupt", "Healthy career reset accepted.");
    string match = fixture.Store.BeginMatch([fixture.ProfileId]);
    Check(fixture.Api.Execute(fixture.Token, Command("restartCareer", "")).code == "profile_busy", "Active career reset accepted.");
    var wreck = Grant(fixture, 0, 0, 0); wreck.Outcome = (int)MultiplayerOutcome.Wrecked; wreck.Qualified = false;
    fixture.Store.Commit(match, [wreck]);
    string transaction = Guid.NewGuid().ToString("D");
    var restarted = fixture.Api.Execute(fixture.Token, Command("restartCareer", "", transaction));
    var replay = fixture.Api.Execute(fixture.Token, Command("restartCareer", "", transaction));
    var profile = fixture.Store.GetProfile(fixture.ProfileId)!;
    Check(restarted.ok && replay.ok && restarted.code == "career_restarted" && restarted.profile.credits == 0 && profile.Career.Bikes.Single().Condition == 100 &&
        profile.Career.SelectedBikeId == BikeCatalog.StarterBikeId && profile.Career.LevelIndex == 0 && profile.Career.QualificationMask == 0 && !profile.Career.CampaignComplete &&
        profile.Career.SaveGeneration == 1 && profile.Career.Ledger.Count(entry => entry.Reason == "restartCareer") == 1 && fixture.Store.IsTokenActive(fixture.Token), "Bankrupt reset lost identity or duplicated assets.");
    Check(fixture.Api.Execute(fixture.Token, Command("restartCareer", "")).code == "not_bankrupt", "Healthy post-reset career reset accepted.");
    using var affordable = new Fixture(); string second = affordable.Store.BeginMatch([affordable.ProfileId]);
    wreck = Grant(affordable, 0, 0, 0); wreck.Outcome = (int)MultiplayerOutcome.Wrecked; wreck.Qualified = false;
    affordable.Store.Commit(second, [wreck]);
    Check(affordable.Api.Execute(affordable.Token, Command("restartCareer", "")).code == "not_bankrupt", "Affordable repair was bypassed with free restart.");
});

var report = new { generatedUtc = DateTimeOffset.UtcNow, passed = results.Count - failed, failed, durationMilliseconds = started.Elapsed.TotalMilliseconds,
    scope = "Real SQLite WAL/FULL transactions, isolated fixture realms only, injected I/O failure, abrupt child-process exit before/after commit, concurrency, closed-database restore, account expiry/recovery and signed offline save boundaries. No user P05 data opened.", tests = results };
string json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }); Console.WriteLine(json);
string reportPath = args.Length == 2 && args[0] == "--report" ? args[1] : Path.Combine("docs", "p07", "persistence-tests.json");
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(reportPath))!); File.WriteAllText(reportPath, json, new UTF8Encoding(false));
return failed == 0 ? 0 : 1;

void Test(string name, Action action)
{
    try { action(); results.Add(new { name, status = "PASS" }); }
    catch (Exception error) { failed++; results.Add(new { name, status = "FAIL", error = error.GetType().Name + ": " + error.Message }); }
}
static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
static CareerRequest Command(string operation, string bike, string? transaction = null) => new() { operation = operation, bikeId = bike, transactionId = transaction ?? Guid.NewGuid().ToString("D") };
static RealmGrant Grant(Fixture fixture, int rank, int reward, int condition) => new()
{
    ProfileId = fixture.ProfileId, SessionId = "test", Name = "Fixture", RiderId = 1, Rank = rank, Reward = reward, BikeCondition = condition,
    BikeId = BikeCatalog.StarterBikeId, LevelIndex = 0, CourseIndex = 0, Outcome = (int)MultiplayerOutcome.Finished, Qualified = rank is > 0 and <= 3
};
static void Reward(Fixture fixture, int reward)
{ string match = fixture.Store.BeginMatch([fixture.ProfileId]); fixture.Store.Commit(match, [Grant(fixture, 1, reward, 100)]); }
static SqliteConnection Open(string folder)
{ var result = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(folder, "realm.sqlite3"), Pooling = false }.ToString()); result.Open(); return result; }
static void SqlRejected(SqliteConnection database, string sql, string message)
{ using var command = database.CreateCommand(); command.CommandText = sql; bool rejected = false; try { command.ExecuteNonQuery(); } catch (SqliteException) { rejected = true; } Check(rejected, message); }
static void Crash(bool afterCommit)
{
    string folder, token, profileId, transaction = Guid.NewGuid().ToString("D");
    using (var fixture = new Fixture()) { folder = fixture.Folder; token = fixture.Token; profileId = fixture.ProfileId; }
    File.WriteAllText(Path.Combine(folder, "crash-input.json"), JsonSerializer.Serialize(new CrashInput { Token = token, Transaction = transaction }));
    string launcher = Environment.ProcessPath ?? throw new InvalidOperationException("Cannot resolve test process launcher.");
    var info = new ProcessStartInfo(launcher) { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden,
        RedirectStandardOutput = true, RedirectStandardError = true };
    if (string.Equals(Path.GetFileNameWithoutExtension(launcher), "dotnet", StringComparison.OrdinalIgnoreCase))
        info.ArgumentList.Add(Assembly.GetExecutingAssembly().Location);
    info.ArgumentList.Add(afterCommit ? "--crash-after" : "--crash-before"); info.ArgumentList.Add(folder);
    using var process = Process.Start(info)!;
    if (!process.WaitForExit(20_000)) { process.Kill(true); throw new InvalidOperationException("Crash child timed out."); }
    Check(process.ExitCode == (afterCommit ? 78 : 77), "Child did not terminate at expected durability boundary.");
    using var store = new RealmStore(new SqliteRealmStateStore(folder)); var api = new CareerService(store);
    Check(store.Credits(profileId) == (afterCommit ? 248 : 1000), "Restart recovered a partial or missing commit.");
    Check(api.Execute(token, Command("trade", "rb-ember", transaction)).ok && store.Credits(profileId) == 248 && store.GetProfile(profileId)!.Career.Ledger.Count == 2, "Crash retry duplicated transaction.");
}

sealed class CrashInput { public string Token { get; set; } = ""; public string Transaction { get; set; } = ""; }
sealed class MutableClock : TimeProvider
{
    private DateTimeOffset now = DateTimeOffset.UtcNow;
    public override DateTimeOffset GetUtcNow() => now;
    public void Advance(TimeSpan interval) => now += interval;
}
sealed class Fixture : IDisposable
{
    public string Folder { get; }
    public RealmStore Store { get; }
    public CareerService Api { get; }
    public string ProfileId { get; } = "";
    public string Token { get; } = "";
    private bool disposed;
    public Fixture(int credits = 1000, string kind = "offline", Action? beforeCommit = null, TimeProvider? clock = null)
    {
        Folder = NewFolder();
        if (credits != 1000)
        {
            Token = RealmStore.Capability(); ProfileId = Guid.NewGuid().ToString("N");
            File.WriteAllText(Path.Combine(Folder, "realm.json"), JsonSerializer.Serialize(new RealmDocument { Profiles =
                [new RealmProfile { Id = ProfileId, Name = "Fixture", CapabilityHash = RealmStore.Hash(Token), Credits = credits }] }));
        }
        Store = new RealmStore(new SqliteRealmStateStore(Folder, kind, beforeCommit), clock);
        if (credits == 1000) { var issued = Store.CreateProfile("Fixture"); Token = issued.Token; ProfileId = issued.Profile.Id; }
        Api = new CareerService(Store);
    }
    public static string NewFolder()
    { string folder = Path.GetFullPath(Path.Combine("_local", "p07-persistence-tests", Guid.NewGuid().ToString("N"))); Directory.CreateDirectory(folder); return folder; }
    public void Dispose() { if (disposed) return; disposed = true; Store.Dispose(); }
}
