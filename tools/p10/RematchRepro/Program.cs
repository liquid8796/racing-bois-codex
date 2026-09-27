using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;

var sourcePaths = Directory.GetFiles("Packages/com.racingbois.foundation/Runtime", "*.cs", SearchOption.AllDirectories)
    .Concat(Directory.GetFiles("Assets/RacingBois/Client/Application", "*.cs"))
    .Concat(Directory.GetFiles("src/Server/RacingBois.Server.Application", "*.cs", SearchOption.AllDirectories).Where(path => !path.Split(Path.DirectorySeparatorChar).Any(part => part is "bin" or "obj")))
    .Concat(new[] { "src/Tests/RacingBois.P05Client.Tests/NetworkHarness.cs", "tools/p10/RematchRepro/Program.cs", "tools/p10/RematchRepro/RematchRepro.csproj" }).ToArray();
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
var sources = sourcePaths.ToDictionary(path => path, Hash);
var watch = Stopwatch.StartNew(); var cycles = new List<object>(); int failures = 0;
var net = new TestNetwork { ClientFrameSeconds = 1.0 / 60, JitterSeconds = 0, BlockClientUntil = 0 };
var peers = Enumerable.Range(0, 8).Select(i => net.Add("Repro " + i)).ToArray();
foreach (var peer in peers) { peer.Attack = 0; peer.BlockUplinkUntil = 0; }
net.InputController = peer =>
{
    var rider = peer.Session.LocalRider; float lane = peer.Session.RiderId % 2 == 0 ? 1.8f : -1.8f;
    var track = TrackDefinition.ForCourse(peer.Session.Room?.CourseIndex ?? 0, peer.Session.Room?.LevelIndex ?? 0);
    float curve = track.CurvatureAt((long)(rider.LongitudinalMeters * 1000)), speed = rider.SpeedMetersPerSecond * 1000;
    float lateral = Math.Clamp((lane - rider.LateralMeters) * 2000, -6500, 6500);
    peer.Throttle = 1; peer.Steer = Math.Clamp((lateral + speed * curve / 100000) / (1200 + speed / 6), -1, 1);
};
bool Until(Func<bool> condition, int maxTicks) { for (int i = 0; i < maxTicks; i++) { if (condition()) return true; net.Run(1); } return condition(); }
void Need(bool value, string reason) { if (!value) throw new InvalidOperationException(reason); }
try
{
    Need(Until(() => peers.All(p => p.Session.Status == SessionStatus.Connected), 480), "connect");
    peers[0].Session.CreateLobby(new LobbyOptions("Rematch reproduction", 5, publicRoom: false));
    Need(Until(() => peers[0].Session.Room != null, 240), "create");
    foreach (var peer in peers.Skip(1)) peer.Session.JoinLobby(peers[0].Session.Room.Code);
    Need(Until(() => peers.All(p => p.Session.Room?.Members.Count == 8), 360), "join");
    for (int cycle = 0; cycle < 12; cycle++)
    {
        foreach (var peer in peers) peer.Session.SetReady(true);
        Need(Until(() => peers.All(p => p.Session.Room?.Members.All(m => m.Ready) == true), 600), "ready_cycle_" + cycle);
        peers.First(p => p.Session.IsHost).Session.StartRace();
        Need(Until(() => peers.All(p => p.Session.Room?.Phase == LobbyPhase.Racing), 720), "start_cycle_" + cycle);
        if (cycle % 2 == 1)
        {
            net.Run(300); var target = peers[cycle % peers.Length]; int attempts = target.Connections; target.Drop();
            Need(Until(() => target.Connections > attempts && target.Session.Status == SessionStatus.Connected && !target.Session.IsReconnecting, 1200), "resume_cycle_" + cycle);
        }
        Need(Until(() => peers.All(p => p.Session.Result != null && p.Session.Room?.Phase == LobbyPhase.Results), 12000), "results_cycle_" + cycle);
        cycles.Add(new { cycle, serverTick = net.Server.ServiceTick, simulationSeconds = net.Clock.NowSeconds, connections = peers.Select(p => p.Connections).ToArray(), invalidSnapshots = peers.Sum(p => p.Session.InvalidSnapshots) });
        Console.WriteLine("PASS pure rematch " + cycle);
        peers.First(p => p.Session.IsHost).Session.ReturnToLobby();
        Need(Until(() => peers.All(p => p.Session.Room?.Phase == LobbyPhase.Lobby), 720), "return_cycle_" + cycle);
    }
}
catch (Exception error) { failures++; cycles.Add(new { failure = error.Message }); Console.WriteLine("FAIL " + error.Message); }
string output = args.Length > 0 ? args[0] : throw new ArgumentException("Fresh report path required");
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
if (File.Exists(output)) throw new IOException("Keep existing evidence");
File.WriteAllText(output, JsonSerializer.Serialize(new { status = failures == 0 ? "PASS" : "FAIL", elapsedSeconds = watch.Elapsed.TotalSeconds, cycles,
    sources, sourceStable = sources.All(pair => Hash(pair.Key) == pair.Value),
    peers = peers.Select(p => new { p.Connections, status = p.Session.Status.ToString(), phase = p.Session.Room?.Phase.ToString(), p.Session.Error, p.Session.InvalidSnapshots, trace = p.Trace.TakeLast(32) }),
    scope = "Twelve actual simulation/client/server application rematches under synthetic zero-delay transport and clock, six planned disconnects. No real TCP mailbox, HTTP ingress rate limiter, wall-clock soak, visuals or release acceptance." }, new JsonSerializerOptions { WriteIndented = true }));
foreach (var peer in peers) peer.Session.Dispose(); net.Server.Dispose(); net.Realm.Dispose();
return failures == 0 ? 0 : 1;
