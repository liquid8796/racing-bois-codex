using System.Diagnostics;
using System.Net;
using System.Net.WebSockets;
using System.Text.Json;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.Extensions.FileProviders;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Server.Host;
using RacingBois.Server.Application;
using RacingBois.Simulation;
using RacingBois.Server.Host.Multiplayer;
using RacingBois.Server.Application.Multiplayer;
using RacingBois.Server.Application.Career;
using RacingBois.Server.Infrastructure;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Data.Sqlite;

if (args.Contains("--SelfTest", StringComparer.OrdinalIgnoreCase))
{
    RiderState state = default;
    for (int i = 0; i < 300; i++) state = RoadSpaceSimulation.Step(state, new RiderInput(1000, 0, 0));
    var hello = WireJson.Parse<HelloMessage>(WireJson.Serialize(new HelloMessage()), "kind", "protocolVersion", "simulationRulesVersion", "contentHash");
    var raceHello = WireJson.Parse<RaceHelloMessage>(WireJson.Serialize(new RaceHelloMessage()), "kind", "protocolVersion", "simulationRulesVersion", "contentHash");
    var race = new AuthoritativeRace(); string rider = race.Join()!;
    for (int i = 1; i <= 300; i++) { race.Apply(rider, new RaceInputMessage { playerId = rider, sequence = i, throttle = 1 }); race.Step(); }
    var raceSnapshot = race.Snapshot(rider); var own = raceSnapshot.riders.Single(entity => entity.id == race.RiderId(rider));
    var multiplayerHello = MultiplayerJson.Parse(WireJson.Serialize(new MpHello { requestNonce = new string('a', 32), displayName = "SelfTest", freshGuest = true })) as MpHello;
    var timeline = new InputTimeline();
    bool timelinePass = timeline.Add(new MpInput { sequence = 1, targetTick = 1, throttlePermille = 1000, attackSide = 1 }, 0) == null
        && timeline.Sample(1).AttackSide == 1 && timeline.Sample(2).AttackSide == 0;
    using var sqlite = new SqliteConnection("Data Source=:memory:"); sqlite.Open();
    using var sqliteCommand = sqlite.CreateCommand();
    sqliteCommand.CommandText = "CREATE TABLE smoke (id INTEGER PRIMARY KEY, credits INTEGER CHECK(credits >= 0)); INSERT INTO smoke VALUES (1,100);";
    sqliteCommand.ExecuteNonQuery();
    using (var transaction = sqlite.BeginTransaction())
    {
        sqliteCommand.Transaction = transaction; sqliteCommand.CommandText = "UPDATE smoke SET credits=0 WHERE id=1";
        sqliteCommand.ExecuteNonQuery(); transaction.Rollback(); sqliteCommand.Transaction = null;
    }
    sqliteCommand.CommandText = "SELECT credits FROM smoke WHERE id=1";
    bool sqlitePass = Convert.ToInt32(sqliteCommand.ExecuteScalar()) == 100;
    bool pass = state.DistanceMillimeters == 150500 && state.SpeedMillimetersPerSecond == 60000 && hello.protocolVersion == 1 &&
        raceHello.protocolVersion == RaceProtocol.Version && raceSnapshot.tick == 300 && raceSnapshot.ackSequence == 300 && own.distanceMillimeters > 0 &&
        multiplayerHello?.protocolVersion == MultiplayerProtocol.Version && timelinePass && sqlitePass;
    Console.WriteLine(JsonSerializer.Serialize(new { status = pass ? "PASS" : "FAIL", architecture = System.Runtime.InteropServices.RuntimeInformation.ProcessArchitecture.ToString(), framework = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription, ticks = 300, distanceMillimeters = state.DistanceMillimeters, speedMillimetersPerSecond = state.SpeedMillimetersPerSecond, protocolRoundtrip = hello.protocolVersion,
        raceProtocolRoundtrip = raceHello.protocolVersion, raceTick = raceSnapshot.tick, raceDistanceMillimeters = own.distanceMillimeters,
        multiplayerProtocolRoundtrip = multiplayerHello?.protocolVersion, exactTickInputSmoke = timelinePass, sqliteNativeRollback = sqlitePass,
        scope = "No listener or filesystem writes; shared gameplay/protocol smoke and P07 native SQLite in-memory rollback." }));
    Environment.ExitCode = pass ? 0 : 1;
    return;
}

var builder = WebApplication.CreateBuilder(args);
int port = builder.Configuration.GetValue("Port", 7777);
int tlsPort = builder.Configuration.GetValue("TlsPort", 7778);
bool enableTls = builder.Configuration.GetValue("EnableTls", false);
bool allowLan = builder.Configuration.GetValue("AllowLan", false);
var proxyPolicy = ProxyPolicy.Create(builder.Configuration.GetValue("TrustLocalProxy", false), allowLan);
string webRoot = Path.GetFullPath(builder.Configuration["WebRoot"] ?? Path.Combine(Environment.CurrentDirectory, "Build", "Web"));
builder.WebHost.ConfigureKestrel(options =>
{
    options.Limits.MaxRequestBodySize = WireProtocol.MaximumMessageBytes;
    var address = allowLan ? IPAddress.Any : IPAddress.Loopback;
    options.Listen(address, port);
    if (enableTls) options.Listen(address, tlsPort, listen => listen.UseHttps());
});
builder.Services.AddSingleton<MatchWorker>();
string realmKind = builder.Configuration["RealmKind"] ?? "offline";
if (realmKind is not ("offline" or "online")) throw new InvalidOperationException("RealmKind must be offline or online.");
string dataRoot = RealmPathPolicy.ResolvePrivateDataRoot(builder.Configuration["DataRoot"] ?? Path.Combine(AppContext.BaseDirectory, "realm-data"), webRoot);
builder.Services.AddSingleton(_ => new RealmStore(new SqliteRealmStateStore(dataRoot, realmKind)));
builder.Services.AddSingleton<CareerService>();
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy("career", context => RateLimitPartition.GetFixedWindowLimiter(context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions { PermitLimit = 60, Window = TimeSpan.FromMinutes(1), QueueLimit = 0, AutoReplenishment = true }));
    options.AddPolicy("multiplayer-handshake", context => RateLimitPartition.GetFixedWindowLimiter(context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions { PermitLimit = 30, Window = TimeSpan.FromMinutes(1), QueueLimit = 0, AutoReplenishment = true }));
    options.OnRejected = async (context, cancellation) =>
    {
        context.HttpContext.Response.Headers.CacheControl = "no-store";
        byte[] payload = JsonSerializer.SerializeToUtf8Bytes(new CareerResponse { code = "rate_limited" }, new JsonSerializerOptions { IncludeFields = true });
        context.HttpContext.Response.ContentType = "application/json; charset=utf-8";
        context.HttpContext.Response.ContentLength = payload.Length;
        await context.HttpContext.Response.Body.WriteAsync(payload, cancellation);
    };
});
builder.Services.AddHostedService(service => service.GetRequiredService<MatchWorker>());
builder.Services.AddSingleton<MultiplayerWorker>();
builder.Services.AddHostedService(service => service.GetRequiredService<MultiplayerWorker>());
var app = builder.Build();

if (proxyPolicy != null) app.UseForwardedHeaders(proxyPolicy);

app.Use(async (context, next) =>
{
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    // Required for Unity builds with cross-origin isolation; same-origin assets remain usable without threads.
    context.Response.Headers["Cross-Origin-Opener-Policy"] = "same-origin";
    context.Response.Headers["Cross-Origin-Embedder-Policy"] = "require-corp";
    await next(context);
});
app.UseWebSockets(new WebSocketOptions { KeepAliveInterval = TimeSpan.FromSeconds(20) });
app.UseRateLimiter();
CareerEndpoint.Map(app, builder.Configuration);
app.MapGet("/ready", (MultiplayerWorker worker) => Results.Json(new
{
    status = worker.IsReady ? "ready" : "starting",
    protocolVersion = MultiplayerProtocol.Version,
    contentHash = GameplayRules.ContentHash
}, statusCode: worker.IsReady ? 200 : 503));
app.MapGet("/health", (MatchWorker worker, MultiplayerWorker multiplayer) =>
{
    var health = JsonSerializer.SerializeToNode(worker.Health)!.AsObject();
    health["multiplayer"] = JsonSerializer.SerializeToNode(multiplayer.Health);
    return Results.Json(health);
});
app.MapGet("/multiplayer/health", (MultiplayerWorker worker) => Results.Json(worker.Health));
MultiplayerEndpoint.Map(app, builder.Configuration);

app.Map("/ws", async (HttpContext context, MatchWorker worker) =>
{
    if (!context.WebSockets.IsWebSocketRequest) { context.Response.StatusCode = 400; return; }
    // Same-origin is the default. Cross-origin development must be explicitly configured.
    string origin = context.Request.Headers.Origin.ToString();
    string expectedOrigin = $"{context.Request.Scheme}://{context.Request.Host}";
    string[] extraOrigins = (builder.Configuration["AllowedOrigins"] ?? "").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
    if (origin.Length > 0 && !string.Equals(origin, expectedOrigin, StringComparison.OrdinalIgnoreCase) && !extraOrigins.Contains(origin, StringComparer.OrdinalIgnoreCase))
    { context.Response.StatusCode = 403; return; }
    using var socket = await context.WebSockets.AcceptWebSocketAsync();
    using var lifetime = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);
    Peer? peer = null;
    Task? sender = null;
    try
    {
        using var handshake = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token);
        handshake.CancelAfter(TimeSpan.FromSeconds(5));
        byte[]? first = await WireJson.Receive(socket, handshake.Token);
        if (first == null) return;
        // Both contracts have exactly these fields; route to separate worlds after checking all versions.
        var hello = WireJson.Parse<HelloMessage>(first, "kind", "protocolVersion", "simulationRulesVersion", "contentHash");
        bool isRace = hello.kind == "raceHello";
        bool validHello = isRace
            ? hello.protocolVersion == RaceProtocol.Version && hello.simulationRulesVersion == RaceProtocol.SimulationRulesVersion && hello.contentHash == RaceProtocol.ContentHash
            : hello.kind == "hello" && hello.protocolVersion == WireProtocol.Version && hello.simulationRulesVersion == PrototypeRules.Version && hello.contentHash == PrototypeRules.ContentHash;
        if (!validHello)
        {
            await Send(new ErrorMessage { code = "version_mismatch", message = "Client protocol/rules/content must match this server." });
            return;
        }
        peer = await worker.Join(lifetime.Token, isRace);
        if (peer == null) { await Send(new ErrorMessage { code = "match_full", message = "This prototype supports eight riders." }); return; }
        await Send(isRace ? (object)new RaceWelcomeMessage { playerId = peer.PlayerId, riderId = peer.RiderId } : new WelcomeMessage { playerId = peer.PlayerId });
        sender = Task.Run(async () =>
        {
            try
            {
                await foreach (var message in peer.Outgoing.Reader.ReadAllAsync(lifetime.Token))
                {
                    using var sendTimeout = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token);
                    sendTimeout.CancelAfter(TimeSpan.FromSeconds(5));
                    await socket.SendAsync(message, WebSocketMessageType.Text, true, sendTimeout.Token);
                }
            }
            finally { await lifetime.CancelAsync(); }
        }, lifetime.Token);
        long ingressStart = Stopwatch.GetTimestamp();
        var ingressBudget = new InputRateBudget();
        while (!lifetime.IsCancellationRequested && socket.State == WebSocketState.Open)
        {
            var bytes = await WireJson.Receive(socket, lifetime.Token);
            if (bytes == null) break;
            if (!ingressBudget.TryConsume(Stopwatch.GetElapsedTime(ingressStart).TotalSeconds))
                throw new InvalidDataException("Input rate budget exceeded.");
            bool queued;
            if (isRace)
            {
                var input = WireJson.Parse<RaceInputMessage>(bytes, "kind", "protocolVersion", "playerId", "sequence", "throttle", "brake", "steer", "attackSide", "kick");
                if (input.kind != "raceInput") throw new JsonException("Expected race input.");
                queued = worker.Input(peer, input);
            }
            else
            {
                var input = WireJson.Parse<InputMessage>(bytes, "kind", "protocolVersion", "playerId", "sequence", "throttle", "brake", "steer");
                if (input.kind != "input") throw new JsonException("Expected input.");
                queued = worker.Input(peer, input);
            }
            if (!queued) throw new InvalidDataException("Ingress queue full.");
        }
    }
    catch (Exception ex) when (ex is WebSocketException or OperationCanceledException or JsonException or InvalidDataException)
    {
        app.Logger.LogInformation("Prototype peer closed: {Reason}", ex.GetType().Name);
    }
    finally
    {
        await lifetime.CancelAsync();
        if (sender != null)
        {
            try { await sender; } catch (Exception ex) when (ex is WebSocketException or OperationCanceledException) { }
        }
        if (peer != null) await worker.Leave(peer);
        if (socket.State is WebSocketState.Open or WebSocketState.CloseReceived)
        {
            using var closeTimeout = new CancellationTokenSource(TimeSpan.FromSeconds(1));
            try { await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Session ended.", closeTimeout.Token); }
            catch (Exception ex) when (ex is WebSocketException or OperationCanceledException) { }
        }
    }
    async Task Send(object message) => await socket.SendAsync(WireJson.Serialize(message), WebSocketMessageType.Text, true, lifetime.Token);
});

if (Directory.Exists(webRoot))
{
    var files = new PhysicalFileProvider(webRoot);
    app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = files });
    var types = new FileExtensionContentTypeProvider();
    types.Mappings[".wasm"] = "application/wasm";
    types.Mappings[".data"] = "application/octet-stream";
    types.Mappings[".unityweb"] = "application/octet-stream";
    types.Mappings[".bundle"] = "application/octet-stream";
    types.Mappings[".assetbundle"] = "application/octet-stream";
    types.Mappings[".ogg"] = "audio/ogg";
    types.Mappings[".br"] = "application/octet-stream";
    types.Mappings[".gz"] = "application/octet-stream";
    app.UseStaticFiles(new StaticFileOptions
    {
        FileProvider = files,
        ContentTypeProvider = types,
        OnPrepareResponse = context =>
        {
            string name = context.File.Name;
            if (name.EndsWith(".br", StringComparison.OrdinalIgnoreCase) || name.EndsWith(".gz", StringComparison.OrdinalIgnoreCase))
            {
                context.Context.Response.Headers.ContentEncoding = name.EndsWith(".br", StringComparison.OrdinalIgnoreCase) ? "br" : "gzip";
                string underlying = Path.GetFileNameWithoutExtension(name);
                if (types.TryGetContentType(underlying, out var contentType)) context.Context.Response.ContentType = contentType;
            }
            context.Context.Response.Headers.CacheControl = "no-cache";
        }
    });
}
else app.Logger.LogWarning("Unity Web directory does not exist yet: {WebRoot}", webRoot);
app.Run();
