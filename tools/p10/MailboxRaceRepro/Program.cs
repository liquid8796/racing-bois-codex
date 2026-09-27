using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Server.Host.Multiplayer;

using var mailbox = new PeerMailbox();
object gate = typeof(PeerMailbox).GetField("gate", BindingFlags.NonPublic | BindingFlags.Instance)!.GetValue(mailbox)!;
var signal = (SemaphoreSlim)typeof(PeerMailbox).GetField("available", BindingFlags.NonPublic | BindingFlags.Instance)!.GetValue(mailbox)!;
if (!mailbox.TryWrite([1], false)) throw new InvalidOperationException("First snapshot not queued");
Task<byte[]?> first;
lock (gate)
{
    first = Task.Run(() => mailbox.Read(CancellationToken.None));
    if (!SpinWait.SpinUntil(() => signal.CurrentCount == 0, TimeSpan.FromSeconds(5))) throw new TimeoutException("Reader did not consume notification");
    // The reader consumed the notification but cannot take the gate. A legal producer
    // replaces the single snapshot and posts another notification before the read proceeds.
    if (!mailbox.TryWrite([2], false)) throw new InvalidOperationException("Replacement snapshot not queued");
}
byte[]? latest = await first.WaitAsync(TimeSpan.FromSeconds(5));
bool spuriousTermination = false, correctlyWaited = false;
using (var timeout = new CancellationTokenSource(TimeSpan.FromMilliseconds(250)))
{
    try { spuriousTermination = await mailbox.Read(timeout.Token) == null; }
    catch (OperationCanceledException) when (timeout.IsCancellationRequested) { correctlyWaited = true; }
}
bool thirdDelivered = false, closeDelivered = false;
if (correctlyWaited)
{
    mailbox.TryWrite([3], false);
    thirdDelivered = (await mailbox.Read(CancellationToken.None))?.SequenceEqual(new byte[] { 3 }) == true;
    mailbox.Close("finished"); closeDelivered = await mailbox.Read(CancellationToken.None) == null;
}
bool passed = latest?.SequenceEqual(new byte[] { 2 }) == true && correctlyWaited && thirdDelivered && closeDelivered;
string output = args.Length == 1 ? args[0] : throw new ArgumentException("Fresh report required");
if (File.Exists(output)) throw new IOException("Preserve prior reproduction");
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
string[] paths = ["src/Server/RacingBois.Server.Host/Multiplayer/PeerMailbox.cs", "tools/p10/MailboxRaceRepro/Program.cs", "tools/p10/MailboxRaceRepro/MailboxRaceRepro.csproj"];
var result = new { generatedUtc = DateTimeOffset.UtcNow, status = passed ? "PASS" : "FAIL", passed = passed ? 1 : 0, failed = passed ? 0 : 1,
    tests = new[] { new { name = "replacement_notification_does_not_close_open_mailbox", passed } }, spuriousTermination, correctlyWaited, thirdDelivered, closeDelivered,
    latestSnapshotIsReplacement = latest?.SequenceEqual(new byte[] { 2 }) == true,
    scope = "Real mailbox concurrent-reader/replacing-writer interleaving. Private-gate inspection controls a legal schedule; no production state/data patched. Null is interpreted as closure by MultiplayerEndpoint sender.",
    sources = paths.Select(path => new { path, sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() }) };
File.WriteAllText(output, JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(result));
return passed ? 0 : 1;
