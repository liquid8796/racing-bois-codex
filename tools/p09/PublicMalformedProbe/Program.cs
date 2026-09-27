using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;

if (args.Length != 1 || File.Exists(args[0])) return 2;
var observations = new List<object>();
bool passed = true;
for (int trial = 0; trial < 3; trial++)
{
    using var socket = new ClientWebSocket();
    using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(12));
    var clock = Stopwatch.StartNew();
    string phase = "connect"; double connected = 0, sent = 0;
    try
    {
        await socket.ConnectAsync(new Uri("wss://racing-bois.158.180.59.36.sslip.io/multiplayer"), deadline.Token);
        connected = clock.Elapsed.TotalMilliseconds; phase = "send";
        await socket.SendAsync(Encoding.UTF8.GetBytes("{\"kind\":\"mpHello\",\"kind\":\"mpHello\"}"), WebSocketMessageType.Text, true, deadline.Token);
        sent = clock.Elapsed.TotalMilliseconds; phase = "receive";
        var response = await socket.ReceiveAsync(new ArraySegment<byte>(new byte[32768]), deadline.Token);
        bool rejected = response.MessageType == WebSocketMessageType.Close;
        passed &= rejected;
        observations.Add(new { trial, passed = rejected, phase, connectedMs = connected, sentMs = sent, totalMs = clock.Elapsed.TotalMilliseconds, outcome = response.MessageType.ToString() });
    }
    catch (WebSocketException)
    {
        bool rejected = phase == "receive"; passed &= rejected;
        observations.Add(new { trial, passed = rejected, phase, connectedMs = connected, sentMs = sent, totalMs = clock.Elapsed.TotalMilliseconds, outcome = "WebSocketException" });
    }
    catch (OperationCanceledException)
    {
        passed = false;
        observations.Add(new { trial, passed = false, phase, connectedMs = connected, sentMs = sent, totalMs = clock.Elapsed.TotalMilliseconds, outcome = "timeout" });
    }
    await Task.Delay(300);
}
var report = new { status = passed ? "PASS" : "FAIL", generatedUtc = DateTimeOffset.UtcNow, scenario = "duplicate_kind_handshake_rejection", deadlineSeconds = 12, certificateValidation = "ordinary operating system trust", observations };
string json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[0]))!);File.WriteAllText(args[0], json);Console.WriteLine(json);
return passed ? 0 : 1;
