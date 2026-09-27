using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using RacingBois.Client.Application;

/// <summary>Test-only native adapter for the real pure application class, not the Unity browser adapter.</summary>
internal sealed class ProbeTransport : IRealtimeTransport
{
    private readonly ConcurrentQueue<Action> callbacks = new();
    private CancellationTokenSource lifetime;
    private ClientWebSocket socket;
    private Channel<string> outgoing;
    private Task connection;
    private bool disposed;
    public event Action Opened;
    public event Action<string> Message;
    public event Action<string> Closed;
    public bool ReceiveEnded { get; private set; }
    public int MaximumQueuedCallbacks { get; private set; }
    public void Connect(string endpoint)
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        Close();
        ReceiveEnded = false;
        lifetime = new CancellationTokenSource();
        socket = new ClientWebSocket();
        outgoing = Channel.CreateBounded<string>(new BoundedChannelOptions(128) { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });
        connection = Run(socket, outgoing, new Uri(endpoint), lifetime.Token);
    }
    private async Task Run(ClientWebSocket current, Channel<string> sendQueue, Uri endpoint, CancellationToken token)
    {
        Task sender = null;
        try
        {
            await current.ConnectAsync(endpoint, token);
            callbacks.Enqueue(() => { if (socket == current) Opened?.Invoke(); });
            sender = Task.Run(async () =>
            {
                await foreach (var text in sendQueue.Reader.ReadAllAsync(token))
                    await current.SendAsync(Encoding.UTF8.GetBytes(text), WebSocketMessageType.Text, true, token);
            }, token);
            while (!token.IsCancellationRequested)
            {
                string text = await ProbeWire.Receive(current, token);
                if (text == null) break;
                callbacks.Enqueue(() => { if (socket == current) Message?.Invoke(text); });
                if (callbacks.Count > 128) throw new InvalidDataException("Probe callback cap exceeded.");
            }
        }
        catch (Exception ex) when (ex is OperationCanceledException or WebSocketException or InvalidDataException)
        {
            callbacks.Enqueue(() => { if (socket == current) Closed?.Invoke(ex.GetType().Name); });
        }
        finally
        {
            sendQueue.Writer.TryComplete();
            current.Abort();
            if (sender != null) { try { await sender; } catch (Exception ex) when (ex is OperationCanceledException or WebSocketException) { } }
            ReceiveEnded = true;
            callbacks.Enqueue(() => { if (socket == current) Closed?.Invoke("closed"); });
        }
    }
    public void Send(string text) { if (outgoing != null && !outgoing.Writer.TryWrite(text)) throw new InvalidDataException("Probe send cap exceeded."); }
    public void Poll()
    {
        MaximumQueuedCallbacks = Math.Max(MaximumQueuedCallbacks, callbacks.Count);
        for (int i = 0; i < 128 && callbacks.TryDequeue(out var callback); i++) callback();
    }
    public void Close() { if (disposed) return; lifetime?.Cancel(); socket?.Abort(); socket = null; outgoing?.Writer.TryComplete(); }
    public void Dispose() { if (disposed) return; Close(); disposed = true; lifetime?.Dispose(); }
}

internal sealed class ProbeCodec : IWireCodec
{
    public string Encode(object message) => JsonSerializer.Serialize(message, message.GetType(), ProbeWire.Options);
    public T Decode<T>(string text) where T : class => JsonSerializer.Deserialize<T>(text, ProbeWire.Options);
}

internal static class ProbeWire
{
    public static readonly JsonSerializerOptions Options = new() { IncludeFields = true };
    public static async Task Send(ClientWebSocket socket, object value, CancellationToken token) => await socket.SendAsync(JsonSerializer.SerializeToUtf8Bytes(value, value.GetType(), Options), WebSocketMessageType.Text, true, token);
    public static async Task<string> Receive(ClientWebSocket socket, CancellationToken token)
    {
        byte[] buffer = new byte[16384]; int count = 0;
        while (true)
        {
            var result = await socket.ReceiveAsync(buffer.AsMemory(count), token);
            if (result.MessageType == WebSocketMessageType.Close) return null;
            count += result.Count;
            if (result.EndOfMessage) return Encoding.UTF8.GetString(buffer, 0, count);
            if (count == buffer.Length) throw new InvalidDataException("Probe frame cap exceeded.");
        }
    }
}
