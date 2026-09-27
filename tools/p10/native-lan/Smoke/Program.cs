using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Runtime.InteropServices;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;
using RacingBois.Protocol;

// Disposable persistent offline-profile capability stays in memory, never in reports/logs.
if (args.Length is not (3 or 4) || args.Length == 4 && args[3] != "--wait-for-termination") return 2;
string package = Path.GetFullPath(args[0]), privateRoot = Path.GetFullPath(args[1]), reportPath = Path.GetFullPath(args[2]);
string executable = Path.Combine(package, "RacingBois.Server.Host.exe");
string publicRoot = Path.Combine(package, "public");
string dataRoot = Path.Combine(privateRoot, "realm");
if (!OperatingSystem.IsWindows() || !File.Exists(executable) || Directory.Exists(privateRoot) || File.Exists(reportPath)
    || privateRoot.StartsWith(package.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) return 2;
Directory.CreateDirectory(privateRoot);
using var ownedHostJob = new OwnedHostJob();
var json = new JsonSerializerOptions { IncludeFields = true };
using var client = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = TimeSpan.FromSeconds(8) };
var checks = new List<object>();
var ownedPids = new List<int>();
Process? process = null;
Task? stdout = null, stderr = null;
StreamWriter? log = null;
int starts = 0, port = 0;
string? errorCode = null;
bool passed = false;
void Check(bool condition, string code)
{
    if (!condition) throw new InvalidOperationException(code);
    checks.Add(new { name = code, passed = true });
}
async Task<JsonElement> Get(string path)
{
    using var response = await client.GetAsync($"http://127.0.0.1:{port}{path}");
    response.EnsureSuccessStatusCode();
    using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
    return document.RootElement.Clone();
}
async Task<CareerResponse> Career(string token, CareerRequest request)
{
    using var message = new HttpRequestMessage(HttpMethod.Post, $"http://127.0.0.1:{port}/api/career");
    message.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
    message.Content = new StringContent(JsonSerializer.Serialize(request, json), System.Text.Encoding.UTF8, "application/json");
    using var response = await client.SendAsync(message);
    response.EnsureSuccessStatusCode();
    return JsonSerializer.Deserialize<CareerResponse>(await response.Content.ReadAsStringAsync(), json)
        ?? throw new InvalidOperationException("career_response_missing");
}
async Task Start()
{
    var reservation = new TcpListener(IPAddress.Loopback, 0); reservation.Start();
    port = ((IPEndPoint)reservation.LocalEndpoint).Port; reservation.Stop();
    var start = new ProcessStartInfo(executable) { WorkingDirectory = package, UseShellExecute = false,
        CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
    foreach (string value in new[] { "--AllowLan", "false", "--Port", port.ToString(), "--EnableTls", "false",
        "--RealmKind", "offline", "--DataRoot", dataRoot, "--WebRoot", publicRoot, "--Logging:LogLevel:Default", "Warning" })
        start.ArgumentList.Add(value);
    // The self-contained app must not rely on an installed .NET location.
    start.Environment["DOTNET_ROOT"] = Path.Combine(privateRoot, "absent-dotnet-runtime");
    start.Environment["DOTNET_ROOT_X64"] = start.Environment["DOTNET_ROOT"];
    start.Environment["DOTNET_MULTILEVEL_LOOKUP"] = "0";
    process = Process.Start(start) ?? throw new InvalidOperationException("owned_host_start_failed");
    ownedHostJob.Attach(process);
    ownedPids.Add(process.Id); starts++;
    log = new StreamWriter(Path.Combine(privateRoot, $"host-{starts}.log"));
    var writer = TextWriter.Synchronized(log);
    async Task Drain(StreamReader stream)
    {
        while (await stream.ReadLineAsync() is string line) await writer.WriteLineAsync(line);
    }
    stdout = Drain(process.StandardOutput); stderr = Drain(process.StandardError);
    var timer = Stopwatch.StartNew();
    while (timer.Elapsed < TimeSpan.FromSeconds(20))
    {
        if (process.HasExited) throw new InvalidOperationException("owned_host_exited_before_ready");
        try
        {
            var ready = await Get("/ready");
            if (ready.GetProperty("status").GetString() == "ready")
            {
                Check(ready.GetProperty("protocolVersion").GetInt32() == MultiplayerProtocol.Version
                    && ready.GetProperty("contentHash").GetString() == MultiplayerProtocol.ContentHash, "runtime_protocol_and_content_" + starts);
                return;
            }
        }
        catch (HttpRequestException) { }
        await Task.Delay(100);
    }
    throw new InvalidOperationException("owned_host_readiness_timeout");
}
async Task Stop()
{
    if (process == null) return;
    // Kill only this exact process handle, deliberately exercising crash recovery.
    if (!process.HasExited) process.Kill();
    await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10));
    if (stdout != null && stderr != null) await Task.WhenAll(stdout, stderr);
    if (log != null) await log.DisposeAsync();
    process.Dispose(); process = null;
}
try
{
    await Start();
    if (args.Length == 4)
    {
        // The publisher opens the exact child handle, then forcibly terminates
        // this probe to prove kernel cleanup also works without finally/Dispose.
        await File.WriteAllTextAsync(reportPath, JsonSerializer.Serialize(new { hostPid = process!.Id, probePid = Environment.ProcessId }));
        await Task.Delay(Timeout.InfiniteTimeSpan);
    }
    var firstHealth = await Get("/multiplayer/health");
    Check(firstHealth.GetProperty("realmKind").GetString() == "offline", "isolated_offline_realm");
    string realmId = firstHealth.GetProperty("realmId").GetString()!;
    using var socket = new ClientWebSocket();
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
    await socket.ConnectAsync(new Uri($"ws://127.0.0.1:{port}/multiplayer"), timeout.Token);
    // freshGuest=true deliberately creates a temporary profile with no durable
    // capability. The ordinary first-use path creates an anonymous local profile.
    var hello = new MpHello { displayName = "NativeLanSmoke", requestNonce = Guid.NewGuid().ToString("N"), freshGuest = false };
    await socket.SendAsync(JsonSerializer.SerializeToUtf8Bytes(hello, json), WebSocketMessageType.Text, true, timeout.Token);
    var buffer = new byte[32768]; using var body = new MemoryStream();
    WebSocketReceiveResult received;
    do
    {
        received = await socket.ReceiveAsync(new ArraySegment<byte>(buffer), timeout.Token);
        if (received.MessageType != WebSocketMessageType.Text || body.Length + received.Count > 32768)
            throw new InvalidOperationException("profile_handshake_invalid");
        body.Write(buffer, 0, received.Count);
    } while (!received.EndOfMessage);
    var welcome = JsonSerializer.Deserialize<MpWelcome>(body.ToArray(), json)!;
    Check(welcome.kind == "mpWelcome" && welcome.protocolVersion == MultiplayerProtocol.Version
        && welcome.contentHash == MultiplayerProtocol.ContentHash && welcome.realmId == realmId
        && welcome.profileToken.Length > 0 && !welcome.guest, "real_ws_persistent_offline_profile_created");
    var initial = await Career(welcome.profileToken, new CareerRequest());
    Check(initial.ok && initial.profile.realmKind == "offline" && initial.profile.profileId == welcome.profileId, "offline_profile_career_view");
    var equip = new CareerRequest { operation = "equip", transactionId = Guid.NewGuid().ToString("D"), bikeId = initial.profile.selectedBikeId };
    var changed = await Career(welcome.profileToken, equip);
    Check(changed.ok && changed.code == "equipped" && changed.profile.revision > initial.profile.revision, "durable_transaction_before_restart");
    string savedProfile = JsonSerializer.Serialize(changed.profile, json), savedLedger = JsonSerializer.Serialize(changed.ledger, json);
    socket.Abort();
    await Stop();
    Check(File.Exists(Path.Combine(dataRoot, "realm.sqlite3")), "sqlite_file_exists_outside_package");
    await Start();
    var secondHealth = await Get("/multiplayer/health");
    Check(secondHealth.GetProperty("realmId").GetString() == realmId && secondHealth.GetProperty("realmKind").GetString() == "offline", "realm_identity_after_crash_restart");
    var restored = await Career(welcome.profileToken, new CareerRequest());
    Check(restored.ok && JsonSerializer.Serialize(restored.profile, json) == savedProfile
        && JsonSerializer.Serialize(restored.ledger, json) == savedLedger, "profile_wallet_inventory_ledger_after_restart");
    var replay = await Career(welcome.profileToken, equip);
    Check(replay.ok && replay.code == changed.code && JsonSerializer.Serialize(replay.profile, json) == savedProfile
        && JsonSerializer.Serialize(replay.ledger, json) == savedLedger, "transaction_replay_after_restart_is_idempotent");
    var privateResponse = await client.GetAsync($"http://127.0.0.1:{port}/realm.sqlite3");
    Check(privateResponse.StatusCode == HttpStatusCode.NotFound, "private_database_not_public");
    Check(secondHealth.GetProperty("persistenceFailures").GetInt64() == 0, "no_reported_persistence_failures");
    passed = true;
}
catch (Exception error)
{
    // Only our fixed check codes may be reported; never exception bodies or tokens.
    errorCode = error is InvalidOperationException && error.Message.All(c => char.IsAsciiLetterOrDigit(c) || c == '_')
        ? error.Message : error.GetType().Name;
}
finally { await Stop(); }
var report = new { schema = 1, passed, errorCode, checks, starts, ownedPids,
    protocolVersion = MultiplayerProtocol.Version, contentHash = MultiplayerProtocol.ContentHash,
    privateRealmRetained = true, credentialsWrittenToReport = false, allOwnedHostsStopped = process == null,
    ownedHostsBoundToKillOnCloseJob = true,
    physicalLanAccepted = false, releaseAccepted = false,
    scope = "Actual self-contained Windows x64 host, loopback HTTP/WS anonymous local profile, isolated private SQLite transaction and abrupt restart recovery. Not a Unity player, physical two-PC offline LAN or Internet test." };
await File.WriteAllTextAsync(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(new { passed, errorCode, checks = checks.Count, starts }));
return passed ? 0 : 1;

internal sealed class OwnedHostJob : IDisposable
{
    private readonly SafeFileHandle handle;
    public OwnedHostJob()
    {
        handle = CreateJobObject(IntPtr.Zero, null);
        if (handle.IsInvalid) throw new InvalidOperationException("owned_job_creation_failed");
        var limits = new ExtendedLimits { Basic = new BasicLimits { LimitFlags = 0x2000 } }; // KILL_ON_JOB_CLOSE
        if (!SetInformationJobObject(handle, 9, ref limits, (uint)Marshal.SizeOf<ExtendedLimits>()))
        { handle.Dispose(); throw new InvalidOperationException("owned_job_configuration_failed"); }
    }
    public void Attach(Process process)
    {
        if (!AssignProcessToJobObject(handle, process.Handle))
            throw new InvalidOperationException("owned_host_job_attachment_failed");
    }
    public void Dispose() => handle.Dispose();
    [StructLayout(LayoutKind.Sequential)] private struct BasicLimits
    {
        public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)] private struct IoCounters
    { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
    [StructLayout(LayoutKind.Sequential)] private struct ExtendedLimits
    { public BasicLimits Basic; public IoCounters Io; public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateJobObject(IntPtr attributes, string? name);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetInformationJobObject(SafeFileHandle job, int informationClass, ref ExtendedLimits limits, uint length);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool AssignProcessToJobObject(SafeFileHandle job, IntPtr process);
}
