using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using RacingBois.Client.Application;

internal sealed class ProbeClock : IMonotonicClock
{ private readonly Stopwatch watch = Stopwatch.StartNew(); public double NowSeconds => watch.Elapsed.TotalSeconds; }
internal sealed class ProbeCodec : IWireCodec
{
    internal static readonly JsonSerializerOptions Options = new() { IncludeFields = true };
    public string Encode(object message) => JsonSerializer.Serialize(message, message.GetType(), Options);
    public T Decode<T>(string text) where T : class => JsonSerializer.Deserialize<T>(text, Options);
}
internal sealed class ProbeResumeStore : IResumeReceiptStore
{
    private readonly Dictionary<string, ResumeReceipt> values = new();
    public ResumeReceipt Load(string endpoint) => values.TryGetValue(endpoint, out var value) ? value : null;
    public void Save(string endpoint, ResumeReceipt receipt) => values[endpoint] = receipt;
    public void Clear(string endpoint) => values.Remove(endpoint);
}
internal sealed class ProbeCredentialStore : IProfileCredentialStore
{
    private readonly Dictionary<string, ProfileCredential> values = new();
    public ProfileCredential Load(string endpoint) => values.TryGetValue(endpoint, out var value) ? value : null;
    public void Save(string endpoint, ProfileCredential value) => values[endpoint] = value;
    public void Clear(string endpoint) => values.Remove(endpoint);
}
internal sealed class ProbeTransport : IRealtimeTransport
{
    private readonly ConcurrentQueue<Action> callbacks = new();
    private ClientWebSocket socket;
    private CancellationTokenSource lifetime;
    private Channel<string> outgoing;
    public event Action Opened;
    public event Action<string> Message;
    public event Action<string> Closed;
    public long SentBytes, ReceivedBytes, InputFramesSent;
    public int ConnectAttempts, LargestReceivedBytes;
    public void Connect(string endpoint)
    {
        Close(); ConnectAttempts++;
        var current = new ClientWebSocket(); socket = current; lifetime = new CancellationTokenSource(); var token = lifetime.Token;
        var sends = Channel.CreateBounded<string>(new BoundedChannelOptions(256) { SingleReader = true, FullMode = BoundedChannelFullMode.Wait }); outgoing = sends;
        _ = Task.Run(async () =>
        {
            Task sender = null;
            try
            {
                await current.ConnectAsync(new Uri(endpoint), token);
                callbacks.Enqueue(() => { if (socket == current) Opened?.Invoke(); });
                sender = Task.Run(async () =>
                {
                    await foreach (string text in sends.Reader.ReadAllAsync(token))
                    {
                        byte[] bytes = Encoding.UTF8.GetBytes(text); using var timeout = CancellationTokenSource.CreateLinkedTokenSource(token); timeout.CancelAfter(5000);
                        await current.SendAsync(bytes, WebSocketMessageType.Text, true, timeout.Token); Interlocked.Add(ref SentBytes, bytes.Length);
                        if (text.IndexOf("\"kind\":\"mpInput\"", StringComparison.Ordinal) >= 0) Interlocked.Increment(ref InputFramesSent);
                    }
                }, token);
                var buffer = new byte[32768];
                while (!token.IsCancellationRequested && current.State == WebSocketState.Open)
                {
                    int used = 0; WebSocketReceiveResult reply;
                    do
                    {
                        reply = await current.ReceiveAsync(new ArraySegment<byte>(buffer, used, buffer.Length - used), token);
                        if (reply.MessageType == WebSocketMessageType.Close) break;
                        used += reply.Count;
                        if (used == buffer.Length && !reply.EndOfMessage) throw new InvalidDataException("Client receive cap exceeded.");
                    } while (!reply.EndOfMessage);
                    if (reply.MessageType == WebSocketMessageType.Close) break;
                    Interlocked.Add(ref ReceivedBytes, used); LargestReceivedBytes = Math.Max(LargestReceivedBytes, used);
                    string text = Encoding.UTF8.GetString(buffer, 0, used);
                    if (callbacks.Count >= 256) throw new InvalidDataException("Client callback cap exceeded.");
                    callbacks.Enqueue(() => { if (socket == current) Message?.Invoke(text); });
                }
            }
            catch (Exception error) when (error is WebSocketException or OperationCanceledException or ObjectDisposedException or InvalidDataException) { }
            finally
            {
                sends.Writer.TryComplete();
                callbacks.Enqueue(() => { if (socket == current) Closed?.Invoke("Transport closed."); });
                current.Dispose();
                if (sender != null) { try { await sender; } catch (Exception error) when (error is WebSocketException or OperationCanceledException or ObjectDisposedException) { } }
            }
        }, token);
    }
    public void Send(string text)
    {
        if (outgoing != null && !outgoing.Writer.TryWrite(text)) socket?.Abort();
    }
    public void Poll() { int budget = 128; while (budget-- > 0 && callbacks.TryDequeue(out var callback)) callback(); }
    public void BreakConnection() => socket?.Abort();
    public void Close()
    {
        var previous = socket; socket = null; outgoing?.Writer.TryComplete(); outgoing = null;
        lifetime?.Cancel(); previous?.Dispose(); lifetime?.Dispose(); lifetime = null;
    }
    public void Dispose() => Close();
}
