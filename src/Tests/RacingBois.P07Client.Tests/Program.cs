using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

var results = new List<object>(); int failures = 0;
void Check(bool condition, string reason) { if (!condition) throw new Exception(reason); }
void Test(string name, Action run)
{ try { run(); results.Add(new { name, passed = true }); Console.WriteLine("PASS " + name); }
  catch (Exception error) { failures++; results.Add(new { name, passed = false, error = error.Message }); Console.WriteLine("FAIL " + name + " " + error.Message); } }
(CareerSession session, FakeTransport wire, Store store) Fixture(string endpoint = "wss://localhost:7778/multiplayer", bool credential = true)
{
    var wire = new FakeTransport(); var store = new Store();
    if (credential) store.Save(endpoint, new ProfileCredential("old-capability", "profile-a", "Rider", "realm-a", 1000));
    var session = new CareerSession(wire, store, store); session.SetEndpoint(endpoint); return (session, wire, store);
}
CareerResponse Snapshot(int credits = 1000, string token = "") => new CareerResponse { ok = true, profileToken = token,
    profile = new CareerProfileData { profileId = "profile-a", realmId = "realm-a", realmKind = "offline", displayName = "Rider", credits = credits,
        selectedBikeId = BikeCatalog.StarterBikeId, bikes = new[] { new CareerBikeData { bikeId = BikeCatalog.StarterBikeId } } } };

Test("api_endpoint_preserves_authority_and_uses_tls", () =>
{
    Check(CareerSession.ApiEndpoint("wss://localhost:7778/multiplayer") == "https://localhost:7778/api/career", "TLS mapping");
    Check(CareerSession.ApiEndpoint("ws://192.168.1.2:7777/multiplayer") == "http://192.168.1.2:7777/api/career", "LAN mapping");
    foreach (var value in new[] { "https://host", "wss://user:pass@host/multiplayer", "ws://host/multiplayer?token=x", "ws://host/#x" })
    { bool rejected = false; try { CareerSession.NormalizeEndpoint(value); } catch (ArgumentException) { rejected = true; } Check(rejected, "Unsafe endpoint accepted"); }
});
Test("invite_only_prefills_six_ascii_letters_or_digits", () =>
{
    Check(CareerSession.InviteCode("https://host/?room=abc123") == "ABC123", "Valid invite not parsed");
    foreach (var url in new[] { "https://host/?room=AB%3C123", "https://host/?room=abc12", "https://host/?room=ABC12é", "https://host/?redirect=ABC123", "garbage" })
        Check(CareerSession.InviteCode(url) == "", "Invalid invite accepted");
});
Test("no_profile_means_no_financial_request", () =>
{ var f = Fixture(credential: false); f.session.Execute(new CareerIntent("buy", "rb-ember")); Check(f.wire.Count == 0 && f.session.ErrorCode == "auth_required", "Unauthenticated commerce sent"); });
Test("uncertain_purchase_retries_same_intent_without_optimistic_funds", () =>
{
    var f = Fixture(); f.session.Refresh(); f.wire.Complete(Snapshot());
    f.session.Execute(new CareerIntent("buy", "rb-ember")); string transaction = f.wire.Last.transactionId;
    Check(transaction.Length == 36 && f.session.Profile.Credits == 1000, "Optimistic funds or absent intent");
    f.wire.Complete(null, true); Check(f.session.CanRetry && f.session.Profile.Credits == 1000, "Uncertain state lost");
    f.session.Retry(); Check(f.wire.Last.transactionId == transaction, "Retry generated a second transaction");
    f.wire.Complete(Snapshot(600)); Check(f.session.Profile.Credits == 600 && !f.session.CanRetry, "Authority not applied");
});
Test("duplicate_submit_during_flight_is_ignored", () =>
{ var f = Fixture(); f.session.Execute(new CareerIntent("repair")); f.session.Execute(new CareerIntent("repair")); Check(f.wire.Count == 1, "Double submit"); });
Test("definitive_rejection_does_not_offer_automatic_retry", () =>
{ var f = Fixture(); f.session.Execute(new CareerIntent("buy")); f.wire.Complete(new CareerResponse { code = "insufficient_credits" }); Check(!f.session.CanRetry && f.session.ErrorCode == "insufficient_credits", "Definitive failure retried"); });
Test("new_intent_has_new_transaction_id", () =>
{ var f = Fixture(); f.session.Execute(new CareerIntent("equip")); var id = f.wire.Last.transactionId; f.wire.Complete(Snapshot()); f.session.Execute(new CareerIntent("equip")); Check(id != f.wire.Last.transactionId, "Intent ID reused"); });
Test("account_ops_require_https_even_offline_lan", () =>
{
    foreach (var operation in new[] { "register", "login", "recover", "rotateRecovery" })
    { var f = Fixture("ws://192.168.1.2:7777/multiplayer"); var request = new CareerIntent(operation, password: "not-a-real-password", recoveryCode: "not-a-real-code");
      f.session.Execute(request); Check(f.wire.Count == 0 && f.session.ErrorCode == "https_required", "Password sent over plaintext"); }
});
Test("login_does_not_require_prior_capability_and_rotates_lease", () =>
{
    var f = Fixture(credential: false); ((IResumeReceiptStore)f.store).Save(f.session.Endpoint, new ResumeReceipt("room", "AAAAAA", "player", "old-lease"));
    f.session.Execute(new CareerIntent("login", username: "rider", password: "temporary-secret"));
    Check(f.wire.Bearer == "", "Unexpected authorization"); f.wire.Complete(Snapshot(token: "new-capability"));
    Check(f.store.Load(f.session.Endpoint).ProfileToken == "new-capability", "Credential not rotated");
    Check(((IResumeReceiptStore)f.store).Load(f.session.Endpoint) == null, "Old lease survived identity change");
    Check(f.wire.Last.password == "", "Password retained after response");
});
Test("credential_failures_require_reentry_and_never_retain_retry", () =>
{ var f = Fixture(); f.session.Execute(new CareerIntent("login", password: "temporary-secret", recoveryCode: "temporary-code")); f.wire.Complete(null, true); Check(!f.session.CanRetry && f.wire.Last.password == "" && f.wire.Last.recoveryCode == "", "Secret retained for retry"); });
Test("endpoint_switch_rejects_stale_response_and_keeps_realms_separate", () =>
{
    var f = Fixture(); f.session.Refresh(); var first = f.wire.Callback;
    f.session.SetEndpoint("wss://other.example/multiplayer"); first(Snapshot(token: "wrong-realm-capability"), false);
    Check(f.session.Profile == null && !f.session.HasCredential && !f.session.Busy, "Stale endpoint changed current identity");
    Check(f.store.Load("wss://localhost:7778/multiplayer").ProfileToken == "old-capability", "Source credential mutated");
});
Test("logout_only_clears_after_server_acknowledges_revocation", () =>
{
    var f = Fixture(); f.session.Execute(new CareerIntent("logout"));
    Check(f.session.HasCredential, "Credential removed before acknowledgement"); f.wire.Complete(null, true); Check(f.session.HasCredential && f.session.CanRetry, "Unknown logout cannot retry");
    f.session.Retry(); f.wire.Complete(new CareerResponse { ok = true }); Check(!f.session.HasCredential && f.session.Profile == null, "Logout acknowledgement not applied");
});
Test("secret_outputs_are_ephemeral_and_not_in_credential_storage", () =>
{
    var f = Fixture(); f.session.Execute(new CareerIntent("register", password: "temporary-secret"));
    var response = Snapshot(); response.recoveryCode = "one-time-recovery"; response.exportJson = "private-backup"; f.wire.Complete(response);
    Check(f.session.RecoveryCode == "one-time-recovery", "Recovery missing"); f.session.ClearSensitiveOutput();
    Check(f.session.RecoveryCode == "" && f.session.ExportJson == "", "Secret output remained");
    Check(f.store.Load(f.session.Endpoint).ProfileToken == "old-capability", "Recovery polluted credential");
});
Test("offline_export_import_remain_server_intents", () =>
{
    var f = Fixture("ws://192.168.1.2:7777/multiplayer"); f.session.Execute(new CareerIntent("import", saveJson: "opaque-server-validated-backup"));
    Check(f.wire.Count == 1 && f.wire.Last.saveJson == "opaque-server-validated-backup" && f.session.Profile == null, "Import trusted client data");
});
Test("room_options_preserve_private_campaign_selection", () =>
{ var options = new LobbyOptions("Canyon", 5, false, 0, 2); Check(!options.PublicRoom && options.CourseIndex == 0 && options.LevelIndex == 2 && options.BotCount == 5, "Room selection lost"); });

Test("authoritative_projection_is_detached_from_mutable_wire_data", () =>
{
    var f = Fixture(); f.session.Refresh(); var response = Snapshot();
    response.ledger = new[] { new CareerLedgerEntry { reason = "opening", balance = 1000, delta = 1000 } };
    f.wire.Complete(response); response.profile.credits = 999999; response.profile.bikes[0].condition = 0; response.ledger[0].balance = 999999;
    Check(f.session.Profile.Credits == 1000 && f.session.Profile.Bikes[0].Condition == 100 && f.session.Ledger[0].Balance == 1000, "Mutable wire data leaked into readmodel");
});
Test("malformed_garage_snapshot_does_not_replace_last_authority", () =>
{
    var f = Fixture(); f.session.Refresh(); f.wire.Complete(Snapshot()); f.session.Refresh(); var response = Snapshot(999999); response.profile.selectedBikeId = "not-owned";
    f.wire.Complete(response); Check(f.session.ErrorCode == "invalid_response" && f.session.Profile.Credits == 1000, "Invalid garage replaced authority");
});

Test("forget_expired_credential_is_local_and_scoped_to_endpoint", () =>
{
    var f = Fixture(); string other="wss://other.example/multiplayer";
    f.store.Save(other,new ProfileCredential("other-capability","other-profile","Other","other-realm",500));
    ((IResumeReceiptStore)f.store).Save(f.session.Endpoint,new ResumeReceipt("old-room","ABC123","old-player","old-lease"));
    f.session.Refresh();f.wire.Complete(new CareerResponse { code="unauthorized" });
    int sent=f.wire.Count;f.session.Execute(new CareerIntent("forget"));
    Check(f.wire.Count==sent&&!f.session.HasCredential&&((IResumeReceiptStore)f.store).Load(f.session.Endpoint)==null,"Forget reached server or kept old lease");
    Check(f.store.Load(other).ProfileToken=="other-capability"&&CareerSession.ChangesIdentity("forget"),"Forget crossed realm boundary or missed disconnect contract");
});
Test("gameover_restart_waits_for_authority_and_retries_same_transaction", () =>
{
    var f=Fixture();f.session.Refresh();var initial=Snapshot(5);initial.profile.bikes[0].condition=0;f.wire.Complete(initial);
    f.session.Execute(new CareerIntent("restartCareer"));string id=f.wire.Last.transactionId;
    Check(f.session.Profile.Credits==5&&f.session.Profile.Bikes[0].Condition==0,"Client reset state before authority");
    f.wire.Complete(null,true);f.session.Retry();Check(f.wire.Last.transactionId==id,"Restart replay got second ID");
    f.wire.Complete(Snapshot(0));Check(f.session.Profile.Credits==0&&f.session.Profile.Bikes[0].Condition==100,"Server reset not projected");
});

Directory.CreateDirectory("docs/p07");
var paths = Directory.GetFiles("Assets/RacingBois/Client/Application", "*.cs").Concat(new[] { "src/Tests/RacingBois.P07Client.Tests/Program.cs", "Packages/com.racingbois.foundation/Runtime/Protocol/CareerMessages.cs" }).OrderBy(p => p).ToArray();
File.WriteAllText(args.Length > 0 ? args[0] : "docs/p07/client-validation.json", JsonSerializer.Serialize(new { generatedAtUtc = DateTimeOffset.UtcNow, passed = failures == 0, tests = results.Count, failed = failures,
    sources = paths.Select(path => new { path = path.Replace('\\','/'), sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() }), results }, new JsonSerializerOptions { WriteIndented = true }));
return failures == 0 ? 0 : 1;

sealed class FakeTransport : ICareerTransport
{
    public int Count; public CareerRequest Last; public string Bearer; public Action<CareerResponse, bool> Callback;
    public void Send(string endpoint, string bearer, CareerRequest request, Action<CareerResponse, bool> completed) { Count++; Last = request; Bearer = bearer; Callback = completed; }
    public void Complete(CareerResponse response, bool transient = false) => Callback(response, transient);
}
sealed class Store : IProfileCredentialStore, IResumeReceiptStore
{
    private readonly Dictionary<string, ProfileCredential> credentials = new();
    private readonly Dictionary<string, ResumeReceipt> leases = new();
    public ProfileCredential Load(string endpoint) => credentials.TryGetValue(endpoint, out var value) ? value : null;
    public void Save(string endpoint, ProfileCredential value) => credentials[endpoint] = value;
    public void Clear(string endpoint) => credentials.Remove(endpoint);
    ResumeReceipt IResumeReceiptStore.Load(string endpoint) => leases.TryGetValue(endpoint, out var value) ? value : null;
    void IResumeReceiptStore.Save(string endpoint, ResumeReceipt value) => leases[endpoint] = value;
    void IResumeReceiptStore.Clear(string endpoint) => leases.Remove(endpoint);
}
