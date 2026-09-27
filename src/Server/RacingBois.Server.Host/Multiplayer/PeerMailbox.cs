namespace RacingBois.Server.Host.Multiplayer;

/// <summary>Reliable FIFO plus one replaceable snapshot. Four controls maximum before a waiting snapshot gets service.</summary>
internal sealed class PeerMailbox : IDisposable
{
    private readonly object gate = new();
    private readonly Queue<byte[]> controls = new();
    private readonly SemaphoreSlim available = new(0, 1);
    private byte[]? snapshot;
    private int bytes, controlsSinceSnapshot;
    private bool closing, disposed;
    public string CloseReason { get; private set; } = "Session ended.";
    public bool TryWrite(byte[] message, bool reliable)
    {
        lock (gate)
        {
            if (closing || disposed) return false;
            if (reliable)
            {
                if (controls.Count >= 64 || bytes + message.Length > 65536) return false;
                controls.Enqueue(message); bytes += message.Length;
            }
            else { if (message.Length > 32768) return false; snapshot = message; }
            Signal(); return true;
        }
    }
    public async Task<byte[]?> Read(CancellationToken cancellation)
    {
        while (true)
        {
            await available.WaitAsync(cancellation);
            lock (gate)
            {
                byte[]? message;
                if (controls.Count > 0 && (controlsSinceSnapshot < 4 || snapshot == null))
                { message = controls.Dequeue(); bytes -= message.Length; controlsSinceSnapshot++; }
                else if (snapshot != null) { message = snapshot; snapshot = null; controlsSinceSnapshot = 0; }
                else
                {
                    // A producer can replace the single snapshot after this reader consumed
                    // the signal but before it took the gate, leaving an extra notification.
                    // An empty open queue must wait again; null means an intentional close.
                    if (closing) return null;
                    continue;
                }
                if (controls.Count > 0 || snapshot != null || closing) Signal();
                return message;
            }
        }
    }
    public void Close(string reason)
    { lock (gate) { if (disposed) return; closing = true; CloseReason = reason; snapshot = null; Signal(); } }
    private void Signal() { if (available.CurrentCount == 0) available.Release(); }
    public void Dispose() { lock (gate) { if (disposed) return; disposed = true; closing = true; available.Dispose(); } }
}
