using System.Net.Http.Headers;
using System.Net.WebSockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

// This probe creates disposable QA identities on explicitly supplied loopback hosts.
// Credentials, capabilities, recovery codes and exported save payloads stay in process memory only.
if (args.Length < 3 || args.Length > 5)
{
    Console.Error.WriteLine("Usage: Career.LiveProbe <https://localhost:7878/> <http://127.0.0.1:7877/> <report.json> [online-https-base] [online-http-base]");
    return 2;
}

var https = ProbeUrls.RequireLoopback(args[0], "https");
var http = ProbeUrls.RequireLoopback(args[1], "http");
Uri? onlineHttps = args.Length > 3 ? ProbeUrls.RequireLoopback(args[3], "https") : null;
Uri? onlineHttp = args.Length > 4 ? ProbeUrls.RequireLoopback(args[4], "http") : null;
string output = Path.GetFullPath(args[2]);
var json = new JsonSerializerOptions { IncludeFields = true };
using var client = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = TimeSpan.FromSeconds(15) };
var checks = new List<object>();
var publicProfiles = new List<object>();
int failures = 0, requests = 0, exactLengthResponses = 0, executedTests = 0, skippedTests = 0;
string suffix = Guid.NewGuid().ToString("N")[..12];
string username = "qa_" + suffix;
string password = NewPassword();
string recoveryPassword = NewPassword();
string savedExport = "";
ProfileCredential? alpha = null, bravo = null;

void Check(bool passed, string safeMessage)
{
    if (!passed) throw new ProbeFailure(safeMessage);
}
async Task Test(string name, Func<Task> action)
{
    executedTests++;
    try
    {
        await action();
        checks.Add(new { name, passed = true });
        Console.WriteLine("PASS " + name);
    }
    catch (Exception error)
    {
        failures++;
        // Never copy server bodies, headers, exception messages or command payloads into the report.
        string safeError = error is ProbeFailure failure ? failure.SafeMessage : error is WebSocketException socketError
            ? "WebSocketException:" + socketError.WebSocketErrorCode : error.GetType().Name;
        checks.Add(new { name, passed = false, error = safeError });
        Console.WriteLine("FAIL " + name + ": " + safeError);
        throw new ProbeStopped();
    }
}
async Task<HttpResult> Post(Uri origin, string? token, object request, string? originHeader = null)
    => await PostRaw(origin, token, JsonSerializer.Serialize(request, json), originHeader);
async Task<HttpResult> PostRaw(Uri origin, string? token, string body, string? originHeader = null, string contentType = "application/json")
{
    using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(origin, "api/career"));
    if (!string.IsNullOrEmpty(token)) request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
    request.Headers.TryAddWithoutValidation("Origin", originHeader ?? origin.GetLeftPart(UriPartial.Authority));
    request.Content = new StringContent(body, Encoding.UTF8, contentType);
    using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);
    Interlocked.Increment(ref requests);
    // Capture the actual wire header before buffering; HttpContent can otherwise infer its length locally.
    long? advertisedLength = response.Content.Headers.TryGetValues("Content-Length", out var lengthValues) &&
        long.TryParse(lengthValues.SingleOrDefault(), out long declared) ? declared : null;
    byte[] raw = await response.Content.ReadAsByteArrayAsync();
    bool exactLength = advertisedLength > 0 && advertisedLength == raw.LongLength;
    if (exactLength) Interlocked.Increment(ref exactLengthResponses);
    CareerResponse? parsed = null;
    try { parsed = JsonSerializer.Deserialize<CareerResponse>(raw, json); }
    catch (JsonException) { }
    return new HttpResult((int)response.StatusCode, parsed,
        response.Headers.CacheControl?.NoStore == true,
        response.Headers.TryGetValues("X-Content-Type-Options", out var values) && values.Contains("nosniff"), exactLength);
}
CareerResponse Expect(HttpResult actual, bool ok, params string[] codes)
{
    Check(actual.Status == 200, "Unexpected HTTP status " + actual.Status);
    Check(actual.Value != null && actual.Value.ok == ok, "Unexpected success state.");
    Check(codes.Length == 0 || codes.Contains(actual.Value!.code, StringComparer.Ordinal), "Unexpected career result code.");
    Check(actual.NoStore && actual.NoSniff, "Sensitive response cache/security headers missing.");
    Check(actual.ExactContentLength, "Explicit positive Content-Length is missing or differs from received bytes.");
    return actual.Value!;
}
void ExpectHttp(HttpResult actual, int status, string code)
{
    Check(actual.Status == status && actual.Value?.code == code && actual.Value.ok == false, "Malformed request was not rejected with the expected status/code.");
    Check(actual.NoStore && actual.NoSniff, "Rejected response cache/security headers missing.");
    Check(actual.ExactContentLength, "Rejected response lacks an exact positive Content-Length.");
}
CareerRequest Command(string operation, string bikeId = "", string? transactionId = null)
    => new() { operation = operation, bikeId = bikeId, transactionId = transactionId ?? Guid.NewGuid().ToString("D") };

try
{
    await Test("persistent_profiles_created_over_real_trusted_wss", async () =>
    {
        alpha = await ProfileCredential.Create(https, "QA Alpha " + suffix);
        bravo = await ProfileCredential.Create(https, "QA Bravo " + suffix);
        Check(alpha.ProfileId != bravo.ProfileId && alpha.RealmId == bravo.RealmId, "Profiles did not receive distinct identities in one realm.");
        publicProfiles.Add(new { role = "alpha", profileId = alpha.ProfileId, realmId = alpha.RealmId });
        publicProfiles.Add(new { role = "bravo", profileId = bravo.ProfileId, realmId = bravo.RealmId });
    });

    await Test("view_has_exact_new_profile_balance_and_starter_inventory", async () =>
    {
        var a = Expect(await Post(https, alpha!.Token, new CareerRequest()), true);
        var b = Expect(await Post(https, bravo!.Token, new CareerRequest()), true);
        Check(a.profile.profileId == alpha.ProfileId && b.profile.profileId == bravo.ProfileId, "Bearer resolved another profile.");
        Check(a.profile.realmKind == "offline" && a.profile.credits == 1000 && b.profile.credits == 1000, "Expected isolated offline realm with new-profile grant.");
        Check(a.profile.selectedBikeId == BikeCatalog.StarterBikeId && a.profile.bikes.Length == 1 && a.profile.bikes[0].condition == 100, "Starter inventory is not pristine and singular.");
    });

    await Test("strict_http_schema_origin_and_credential_transport_rejection", async () =>
    {
        Expect(await Post(https, null, new CareerRequest()), false, "unauthorized");
        foreach (string malformed in new[]
        {
            "{\"operation\":\"view\",\"credits\":999999}",
            "{\"operation\":\"view\",\"operation\":\"export\"}",
            "{\"operation\":null}",
            "{\"operation\":3}",
            "[]"
        }) ExpectHttp(await PostRaw(https, alpha!.Token, malformed), 400, "bad_request");
        ExpectHttp(await PostRaw(https, alpha!.Token, "{}", contentType: "text/plain"), 415, "bad_request");
        ExpectHttp(await Post(https, alpha!.Token, new CareerRequest(), "https://untrusted.invalid"), 403, "origin_rejected");
        foreach (string operation in new[] { "register", "login", "recover", "rotateRecovery" })
            ExpectHttp(await Post(http, null, new CareerRequest { operation = operation, username = username, password = password }), 403, "https_required");
        // Local LAN profile commerce works over HTTP; account passwords do not.
        var view = Expect(await Post(http, alpha!.Token, new CareerRequest()), true);
        Check(view.profile.profileId == alpha.ProfileId, "LAN HTTP view changed identity.");
    });

    await Test("insufficient_buy_and_pristine_repair_cannot_debit_wallet", async () =>
    {
        var buy = Command("buy", "rb-viper");
        Expect(await Post(https, alpha!.Token, buy), false, "insufficient_credits");
        Expect(await Post(https, alpha.Token, buy), false, "insufficient_credits");
        Expect(await Post(https, alpha.Token, Command("repair", BikeCatalog.StarterBikeId)), false, "already_repaired");
        var view = Expect(await Post(https, alpha.Token, new CareerRequest()), true);
        Check(view.profile.credits == 1000 && view.profile.bikes.Length == 1, "Rejected commerce mutated money or inventory.");
    });

    await Test("concurrent_trade_has_one_atomic_debit_and_replay_is_idempotent", async () =>
    {
        var trade = Command("trade", "rb-ember");
        var replies = await Task.WhenAll(Post(https, alpha!.Token, trade), Post(https, alpha.Token, trade));
        var first = Expect(replies[0], true);
        var second = Expect(replies[1], true);
        Check(first.profile.credits == 248 && second.profile.credits == 248, "Trade debit or replay balance incorrect.");
        Check(second.profile.selectedBikeId == "rb-ember" && second.profile.bikes.Length == 1 && second.profile.bikes[0].bikeId == "rb-ember", "Trade did not atomically replace ownership.");
        Check(second.ledger.Count(item => item.transactionId == "command:" + trade.transactionId) == 1, "Trade replay duplicated ledger entry.");
        Expect(await Post(https, alpha.Token, Command("buy", "rb-kestrel", trade.transactionId)), false, "transaction_conflict");
    });

    await Test("equip_ownership_and_cross_profile_object_access_are_enforced", async () =>
    {
        var equip = Command("equip", "rb-ember");
        Expect(await Post(https, alpha!.Token, equip), true);
        Expect(await Post(https, alpha.Token, equip), true);
        Expect(await Post(https, alpha.Token, Command("equip", "rb-apex")), false, "bike_not_owned");
        string targeted = JsonSerializer.Serialize(new { operation = "view", profileId = alpha.ProfileId });
        ExpectHttp(await PostRaw(https, bravo!.Token, targeted), 400, "bad_request");
        var b = Expect(await Post(https, bravo.Token, new CareerRequest()), true);
        Check(b.profile.profileId == bravo.ProfileId && b.profile.credits == 1000 && b.profile.selectedBikeId == BikeCatalog.StarterBikeId, "Another profile's commerce leaked into this profile.");
    });

    await Test("register_and_login_preserve_profile_and_do_not_regrant_currency", async () =>
    {
        var registration = Expect(await Post(https, alpha!.Token, new CareerRequest { operation = "register", username = username, password = password }), true);
        Check(registration.recoveryCode.Length >= 24, "Registration did not issue recovery material.");
        alpha.RecoveryCode = registration.recoveryCode;
        if (registration.profileToken.Length > 0) alpha.Token = registration.profileToken;
        var invalid = await Post(https, null, new CareerRequest { operation = "login", username = username, password = NewPassword() });
        Expect(invalid, false, "invalid_credentials");
        var login = Expect(await Post(https, null, new CareerRequest { operation = "login", username = username, password = password }), true);
        Check(login.profileToken.Length == 43 && login.profile.profileId == alpha.ProfileId && login.profile.credits == 248, "Login re-created profile or changed balance.");
        alpha.PreviousToken = alpha.Token;
        alpha.Token = login.profileToken;
    });

    await Test("offline_signed_save_export_import_and_tamper_rejection", async () =>
    {
        var exported = Expect(await Post(https, alpha!.Token, new CareerRequest { operation = "export" }), true);
        savedExport = exported.exportJson;
        Check(savedExport.Length > 100, "Export payload is empty.");
        var import = Command("import"); import.saveJson = savedExport;
        var accepted = Expect(await Post(https, alpha.Token, import), true);
        Check(accepted.profile.profileId == alpha.ProfileId && accepted.profile.credits == 248, "Same-state import changed wallet.");
        Expect(await Post(https, alpha.Token, import), true);
        var foreign = Command("import"); foreign.saveJson = savedExport;
        Expect(await Post(https, bravo!.Token, foreign), false, "foreign_save");
        var corrupt = Command("import"); corrupt.saveJson = savedExport[..^1] + "x";
        Expect(await Post(https, alpha.Token, corrupt), false, "invalid_save");
    });

    await Test("recovery_rotates_recovery_code_and_revokes_old_sessions", async () =>
    {
        string oldRecovery = alpha!.RecoveryCode;
        string oldLogin = alpha.Token;
        var recovered = Expect(await Post(https, null, new CareerRequest
        { operation = "recover", username = username, password = recoveryPassword, recoveryCode = oldRecovery }), true);
        Check(recovered.profileToken.Length == 43 && recovered.recoveryCode.Length >= 24 && recovered.recoveryCode != oldRecovery, "Recovery did not rotate credentials.");
        Check(recovered.profile.profileId == alpha.ProfileId && recovered.profile.credits == 248, "Recovery lost profile or wallet.");
        alpha.Token = recovered.profileToken; alpha.RecoveryCode = recovered.recoveryCode;
        Expect(await Post(https, oldLogin, new CareerRequest()), false, "unauthorized");
        Expect(await Post(https, alpha.PreviousToken, new CareerRequest()), false, "unauthorized");
        Expect(await Post(https, null, new CareerRequest { operation = "recover", username = username, password = password, recoveryCode = oldRecovery }), false, "invalid_credentials");
        Expect(await Post(https, null, new CareerRequest { operation = "login", username = username, password = password }), false, "invalid_credentials");
    });

    await Test("revoke_blocks_http_bearer_and_live_websocket_session", async () =>
    {
        await using var session = await LiveSession.Connect(https, "QA Revoke " + suffix, alpha!.Token);
        Check(session.Welcome.profileId == alpha.ProfileId, "Existing token did not attach expected profile.");
        Expect(await Post(https, alpha.Token, new CareerRequest { operation = "logoutAll" }), true);
        Expect(await Post(https, alpha.Token, new CareerRequest()), false, "unauthorized");
        Check(await session.WaitForClose(TimeSpan.FromSeconds(5)), "Revoked WebSocket remained active.");
        Check(session.LastCloseStatus == WebSocketCloseStatus.NormalClosure && session.LastCloseReason == "profile_revoked",
            "WebSocket ended without the server's explicit normal profile_revoked close frame.");
    });

    if (onlineHttps != null)
        await Test("online_realm_rejects_offline_save_import_and_foreign_bearers", async () =>
        {
            var online = await ProfileCredential.Create(onlineHttps, "QA Online " + suffix);
            publicProfiles.Add(new { role = "online", profileId = online.ProfileId, realmId = online.RealmId });
            Check(online.RealmId != alpha!.RealmId, "Expected isolated online and offline realm identities.");
            var view = Expect(await Post(onlineHttps, online.Token, new CareerRequest()), true);
            Check(view.profile.realmKind == "online" && view.profile.credits == 1000, "Second host is not a new online realm.");
            var import = Command("import"); import.saveJson = savedExport;
            Expect(await Post(onlineHttps, online.Token, import), false, "offline_only");
            Expect(await Post(onlineHttps, bravo!.Token, new CareerRequest()), false, "unauthorized");
            if (onlineHttp != null) ExpectHttp(await Post(onlineHttp, online.Token, new CareerRequest()), 403, "https_required");
        });
    else
    {
        skippedTests++;
        checks.Add(new { name = "online_realm_rejects_offline_save_import_and_foreign_bearers", passed = (bool?)null, skipped = "No online loopback host argument supplied." });
    }
}
catch (ProbeStopped) { }

var sourcePaths = new[]
{
    "src/Tests/RacingBois.Career.LiveProbe/Program.cs",
    "src/Server/RacingBois.Server.Host/CareerEndpoint.cs",
    "src/Server/RacingBois.Server.Application/Career/CareerService.cs",
    "src/Server/RacingBois.Server.Application/Multiplayer/RealmStore.cs",
    "src/Server/RacingBois.Server.Application/Multiplayer/MultiplayerService.cs",
    "Packages/com.racingbois.foundation/Runtime/Protocol/CareerMessages.cs"
};
var sourceFiles = sourcePaths.Where(File.Exists).Select(path => new
{ path, sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() }).ToArray();
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
File.WriteAllText(output, JsonSerializer.Serialize(new
{
    generatedAtUtc = DateTimeOffset.UtcNow,
    passed = failures == 0,
    failures,
    tests = checks.Count,
    executedTests,
    skippedTests,
    requests,
    exactLengthResponses,
    endpoints = new { offlineHttps = https.AbsoluteUri, offlineHttp = http.AbsoluteUri, onlineHttps = onlineHttps?.AbsoluteUri, onlineHttp = onlineHttp?.AbsoluteUri },
    tls = "Ordinary OS certificate validation; no bypass or custom trust callback.",
    scope = "Real HTTP and ClientWebSocket loopback interactions on generated QA profiles. Not browser, physical LAN, WAN, restart or database failure-injection evidence.",
    sourceBinding = "Source hashes describe the checkout at probe time. Pair this report with the host publish/session receipt; these hashes alone do not identify the running executable's build.",
    sensitiveData = "No tokens, passwords, recovery codes, save envelopes, raw bodies or private database values are written by this probe.",
    publicProfiles,
    sourceFiles,
    checks
}, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine(failures == 0 ? "PASS career live probe" : "FAIL career live probe");
return failures == 0 ? 0 : 1;

static string NewPassword() => "P07!qa" + Convert.ToHexString(RandomNumberGenerator.GetBytes(18));
sealed record HttpResult(int Status, CareerResponse? Value, bool NoStore, bool NoSniff, bool ExactContentLength);
sealed class ProbeFailure(string safeMessage) : Exception { public string SafeMessage { get; } = safeMessage; }
sealed class ProbeStopped : Exception { }
static class ProbeUrls
{
    public static Uri RequireLoopback(string value, string scheme)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) || uri.Scheme != scheme || !uri.IsLoopback ||
            uri.UserInfo.Length > 0 || uri.Query.Length > 0 || uri.Fragment.Length > 0 || uri.AbsolutePath != "/")
            throw new ArgumentException("Provide an explicit loopback base URL with the required scheme and no credentials, query or path.");
        return uri;
    }
}

sealed class ProfileCredential
{
    public string ProfileId = "", RealmId = "", Token = "", PreviousToken = "", RecoveryCode = "";
    public static async Task<ProfileCredential> Create(Uri origin, string displayName)
    {
        await using var session = await LiveSession.Connect(origin, displayName, "");
        if (session.Welcome.guest || session.Welcome.profileToken.Length != 43) throw new ProbeFailure("Persistent WSS bootstrap did not return a capability.");
        var result = new ProfileCredential { ProfileId = session.Welcome.profileId, RealmId = session.Welcome.realmId, Token = session.Welcome.profileToken };
        await session.Logout();
        return result;
    }
}

sealed class LiveSession : IAsyncDisposable
{
    private static readonly JsonSerializerOptions Json = new() { IncludeFields = true };
    private readonly ClientWebSocket socket = new();
    public MpWelcome Welcome { get; private set; } = new();
    public WebSocketCloseStatus? LastCloseStatus { get; private set; }
    public string LastCloseReason { get; private set; } = "";
    public static async Task<LiveSession> Connect(Uri origin, string displayName, string token)
    {
        var result = new LiveSession();
        result.socket.Options.SetRequestHeader("Origin", origin.GetLeftPart(UriPartial.Authority));
        var endpoint = new UriBuilder(origin) { Scheme = origin.Scheme == "https" ? "wss" : "ws", Path = "/multiplayer" }.Uri;
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(12));
        try
        {
            await result.socket.ConnectAsync(endpoint, timeout.Token);
            await result.Send(new MpHello { requestNonce = Guid.NewGuid().ToString("N"), displayName = displayName, profileToken = token, freshGuest = false }, timeout.Token);
            for (int i = 0; i < 32; i++)
            {
                var payload = await result.Read(timeout.Token);
                if (payload == null) break;
                using var parsed = JsonDocument.Parse(payload);
                string? kind = parsed.RootElement.GetProperty("kind").GetString();
                if (kind == "mpError") throw new ProbeFailure("WSS profile handshake was rejected.");
                if (kind == "mpWelcome")
                {
                    result.Welcome = JsonSerializer.Deserialize<MpWelcome>(payload, Json)!;
                    return result;
                }
            }
            throw new ProbeFailure("WSS did not return welcome.");
        }
        catch { result.socket.Dispose(); throw; }
    }
    public async Task Logout()
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(8));
        await Send(new MpGoodbye { sessionEpoch = Welcome.sessionEpoch, requestId = 1 }, timeout.Token);
        bool accepted = false;
        for (int i = 0; i < 64; i++)
        {
            var payload = await Read(timeout.Token);
            if (payload == null)
            {
                if (accepted && LastCloseStatus == WebSocketCloseStatus.NormalClosure && LastCloseReason == "logout") return;
                break;
            }
            using var parsed = JsonDocument.Parse(payload);
            if (parsed.RootElement.GetProperty("kind").GetString() == "mpAccepted" && parsed.RootElement.GetProperty("requestId").GetInt32() == 1) accepted = true;
        }
        throw new ProbeFailure("WSS logout lacked its accepted command and normal logout close frame.");
    }
    public async Task<bool> WaitForClose(TimeSpan limit)
    {
        using var timeout = new CancellationTokenSource(limit);
        try
        {
            while (socket.State == WebSocketState.Open)
                if (await Read(timeout.Token) == null) return true;
            return socket.State != WebSocketState.Open;
        }
        catch (OperationCanceledException) { return false; }
    }
    private Task Send(object value, CancellationToken cancellation)
        => socket.SendAsync(JsonSerializer.SerializeToUtf8Bytes(value, Json), WebSocketMessageType.Text, true, cancellation);
    private async Task<byte[]?> Read(CancellationToken cancellation)
    {
        byte[] buffer = new byte[MultiplayerProtocol.MaxSnapshotBytes];
        int total = 0;
        while (true)
        {
            var result = await socket.ReceiveAsync(new ArraySegment<byte>(buffer, total, buffer.Length - total), cancellation);
            if (result.MessageType == WebSocketMessageType.Close)
            {
                LastCloseStatus = result.CloseStatus;
                LastCloseReason = result.CloseStatusDescription ?? "";
                if (socket.State == WebSocketState.CloseReceived)
                    await socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "QA close acknowledged", cancellation);
                return null;
            }
            if (result.MessageType != WebSocketMessageType.Text) throw new ProbeFailure("Unexpected binary WSS message.");
            total += result.Count;
            if (result.EndOfMessage) return buffer[..total];
            if (total == buffer.Length) throw new ProbeFailure("WSS response exceeded bounded buffer.");
        }
    }
    public ValueTask DisposeAsync()
    {
        socket.Abort(); socket.Dispose();
        return ValueTask.CompletedTask;
    }
}
