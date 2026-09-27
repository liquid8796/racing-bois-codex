using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Threading.Channels;

/// <summary>Delays bounded ordered byte streams. No packet drops or UDP loss claims.</summary>
internal sealed class ImpairedStreamProxy : IAsyncDisposable
{
    private readonly TcpListener listener;
    private readonly int upstreamPort, latency, jitter, stallStart, stallDuration;
    private readonly bool stallUpstream;
    private readonly CancellationTokenSource stopping = new();
    private readonly List<Task> links = new();
    private readonly Task accept;
    public readonly Stopwatch Clock = new();
    public int Port { get; }
    public ImpairedStreamProxy(int upstreamPort, int latency, int jitter, int stallStart, int stallDuration, bool stallUpstream)
    {
        this.upstreamPort = upstreamPort; this.latency = latency; this.jitter = jitter;
        this.stallStart = stallStart; this.stallDuration = stallDuration; this.stallUpstream = stallUpstream;
        listener = new TcpListener(IPAddress.Loopback, 0); listener.Start(16); Port = ((IPEndPoint)listener.LocalEndpoint).Port; accept = Accept();
    }
    private async Task Accept()
    {
        try
        {
            while (!stopping.IsCancellationRequested)
            {
                var incoming = await listener.AcceptTcpClientAsync(stopping.Token);
                lock (links) links.Add(Relay(incoming, links.Count));
            }
        }
        catch (Exception error) when (error is OperationCanceledException or SocketException) { }
    }
    private async Task Relay(TcpClient incoming, int number)
    {
        using (incoming)
        using (var outgoing = new TcpClient { NoDelay = true })
        using (var lifetime = CancellationTokenSource.CreateLinkedTokenSource(stopping.Token))
        {
            try
            {
                incoming.NoDelay = true; await outgoing.ConnectAsync(IPAddress.Loopback, upstreamPort, lifetime.Token);
                var up = Pump(incoming.GetStream(), outgoing.GetStream(), true, number, lifetime.Token);
                var down = Pump(outgoing.GetStream(), incoming.GetStream(), false, number, lifetime.Token);
                await Task.WhenAny(up, down); await lifetime.CancelAsync(); await Task.WhenAll(up, down);
            }
            catch (Exception error) when (error is IOException or SocketException or OperationCanceledException or ObjectDisposedException) { }
        }
    }
    private async Task Pump(NetworkStream from, NetworkStream to, bool upstream, int number, CancellationToken token)
    {
        using var pumpLifetime = CancellationTokenSource.CreateLinkedTokenSource(token); token = pumpLifetime.Token;
        var queue = Channel.CreateBounded<(byte[] Bytes, double Due)>(new BoundedChannelOptions(128) { SingleReader = true, SingleWriter = true, FullMode = BoundedChannelFullMode.Wait });
        var reader = Task.Run(async () =>
        {
            var random = new Random(911 + number * 13 + (upstream ? 1 : 2)); var buffer = new byte[8192]; double lastDue = 0;
            try
            {
                while (!token.IsCancellationRequested)
                {
                    int count = await from.ReadAsync(buffer, token); if (count == 0) break;
                    double now = Clock.Elapsed.TotalMilliseconds, due = now;
                    if (Clock.IsRunning)
                    {
                        due += Math.Max(0, latency + (jitter == 0 ? 0 : random.Next(-jitter, jitter + 1)));
                        if (upstream == stallUpstream && now >= stallStart && now < stallStart + stallDuration) due = Math.Max(due, stallStart + stallDuration);
                    }
                    due = Math.Max(due, lastDue); lastDue = due;
                    await queue.Writer.WriteAsync((buffer.AsSpan(0, count).ToArray(), due), token);
                }
            }
            finally { queue.Writer.TryComplete(); }
        }, token);
        try
        {
            await foreach (var chunk in queue.Reader.ReadAllAsync(token))
            {
                double wait = chunk.Due - Clock.Elapsed.TotalMilliseconds;
                if (Clock.IsRunning && wait > 0) await Task.Delay(TimeSpan.FromMilliseconds(wait), token);
                await to.WriteAsync(chunk.Bytes, token);
            }
        }
        finally { await pumpLifetime.CancelAsync(); try { await reader; } catch (OperationCanceledException) { } }
    }
    public async ValueTask DisposeAsync()
    {
        await stopping.CancelAsync(); listener.Stop(); await accept;
        Task[] current; lock (links) current = links.ToArray(); await Task.WhenAll(current); stopping.Dispose();
    }
}
