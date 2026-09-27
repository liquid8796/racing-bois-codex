using System.Diagnostics;
using System.Net;
using System.Net.Sockets;

/// <summary>Bounded byte-stream forwarding. It delays ordered reads; it does NOT emulate packet loss.</summary>
internal sealed class OrderedStreamProxy : IAsyncDisposable
{
    private readonly TcpListener listener;
    private readonly CancellationTokenSource stopping = new();
    private readonly int upstreamPort;
    private readonly List<Task> connections = [];
    private readonly Task accepting;
    public readonly Stopwatch Clock = new();
    public int DelayPerReadMilliseconds { get; }
    public int StallStartMilliseconds { get; }
    public int StallDurationMilliseconds { get; }
    public bool StallUpstream { get; }
    public long ForwardedUpstreamBytes, ForwardedDownstreamBytes;
    public OrderedStreamProxy(int port, int upstreamPort, int delay, int stallStart, int stallDuration, bool stallUpstream)
    {
        this.upstreamPort = upstreamPort;
        DelayPerReadMilliseconds = delay; StallStartMilliseconds = stallStart; StallDurationMilliseconds = stallDuration; StallUpstream = stallUpstream;
        listener = new TcpListener(IPAddress.Loopback, port); listener.Start(8);
        accepting = Accept();
    }
    private async Task Accept()
    {
        try
        {
            while (!stopping.IsCancellationRequested)
            {
                var client = await listener.AcceptTcpClientAsync(stopping.Token);
                lock (connections) connections.Add(Relay(client));
            }
        }
        catch (OperationCanceledException) when (stopping.IsCancellationRequested) { }
    }
    private async Task Relay(TcpClient incoming)
    {
        using (incoming)
        using (var outgoing = new TcpClient { NoDelay = true })
        using (var link = CancellationTokenSource.CreateLinkedTokenSource(stopping.Token))
        {
            try
            {
                incoming.NoDelay = true;
                await outgoing.ConnectAsync(IPAddress.Loopback, upstreamPort, link.Token);
                var up = Pump(incoming.GetStream(), outgoing.GetStream(), true, link.Token);
                var down = Pump(outgoing.GetStream(), incoming.GetStream(), false, link.Token);
                await Task.WhenAny(up, down);
                await link.CancelAsync();
                await Task.WhenAll(up, down);
            }
            catch (Exception ex) when (ex is IOException or SocketException or OperationCanceledException or ObjectDisposedException) { }
        }
    }
    private async Task Pump(NetworkStream from, NetworkStream to, bool upstream, CancellationToken token)
    {
        byte[] buffer = new byte[8192];
        while (!token.IsCancellationRequested)
        {
            int count = await from.ReadAsync(buffer, token);
            if (count == 0) return;
            if (Clock.IsRunning)
            {
                double now = Clock.Elapsed.TotalMilliseconds;
                if (upstream == StallUpstream && now >= StallStartMilliseconds && now < StallStartMilliseconds + StallDurationMilliseconds)
                    await Task.Delay(TimeSpan.FromMilliseconds(StallStartMilliseconds + StallDurationMilliseconds - now), token);
                if (DelayPerReadMilliseconds > 0) await Task.Delay(DelayPerReadMilliseconds, token);
            }
            await to.WriteAsync(buffer.AsMemory(0, count), token);
            if (upstream) Interlocked.Add(ref ForwardedUpstreamBytes, count); else Interlocked.Add(ref ForwardedDownstreamBytes, count);
        }
    }
    public async ValueTask DisposeAsync()
    {
        await stopping.CancelAsync(); listener.Stop();
        await accepting;
        Task[] current; lock (connections) current = connections.ToArray();
        await Task.WhenAll(current);
        stopping.Dispose();
    }
}
