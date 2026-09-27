using System.Collections.Concurrent;
using System.Diagnostics;
using System.Threading.Channels;
using RacingBois.Protocol;
using RacingBois.Server.Application.Multiplayer;

namespace RacingBois.Server.Host.Multiplayer;

internal sealed class MultiplayerPeer
{
    public string Id { get; } = Guid.NewGuid().ToString("N");
    public PeerMailbox Mailbox { get; } = new();
    public int PendingCommands;
}
internal sealed record MultiplayerCommand(string ConnectionId, object? Message, bool Disconnect = false);

internal sealed class MultiplayerWorker : BackgroundService, IMultiplayerSink
{
    private readonly ConcurrentDictionary<string, MultiplayerPeer> peers = new(StringComparer.Ordinal);
    private readonly Channel<MultiplayerCommand> commands = Channel.CreateBounded<MultiplayerCommand>(new BoundedChannelOptions(2048)
    { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });
    private readonly MultiplayerService service;
    private readonly RealmStore realm;
    private readonly ILogger<MultiplayerWorker> logger;
    private int connections, publishedRooms, publishedSessions;
    private long publishedTick, rejectedCommands, slowTicks, persistenceFailures, droppedCatchupTicks;
    private double maximumStepMilliseconds;
    private readonly TickDurationHistogram tickDurations = new();
    private long lastStepTimestamp;
    public bool IsReady => Interlocked.Read(ref lastStepTimestamp) is var timestamp && timestamp > 0
        && Stopwatch.GetElapsedTime(timestamp) < TimeSpan.FromSeconds(5);
    public MultiplayerWorker(RealmStore realm, ILogger<MultiplayerWorker> logger)
    {
        this.logger = logger;
        this.realm = realm;
        service = new MultiplayerService(realm, this, WireJson.Serialize);
    }
    public object Health => new
    {
        protocolVersion = MultiplayerProtocol.Version,
        serviceTick = Interlocked.Read(ref publishedTick),
        roomCount = Volatile.Read(ref publishedRooms),
        sessionCount = Volatile.Read(ref publishedSessions),
        realmId = service.RealmId,
        realmKind = realm.RealmKind,
        profilePersistence = true,
        rejectedCommands = Interlocked.Read(ref rejectedCommands),
        slowTicks = Interlocked.Read(ref slowTicks),
        persistenceFailures = Interlocked.Read(ref persistenceFailures),
        droppedCatchupTicks = Interlocked.Read(ref droppedCatchupTicks),
        maximumStepMilliseconds = Volatile.Read(ref maximumStepMilliseconds),
        tickDurationHistogram = tickDurations.Snapshot()
    };
    public MultiplayerPeer? Register()
    {
        if (Interlocked.Increment(ref connections) > 96) { Interlocked.Decrement(ref connections); return null; }
        var peer = new MultiplayerPeer(); peers.TryAdd(peer.Id, peer); return peer;
    }
    public bool Input(MultiplayerPeer peer, object message)
    {
        if (Interlocked.Increment(ref peer.PendingCommands) > 128)
        { Interlocked.Decrement(ref peer.PendingCommands); Interlocked.Increment(ref rejectedCommands); return false; }
        if (commands.Writer.TryWrite(new MultiplayerCommand(peer.Id, message))) return true;
        Interlocked.Decrement(ref peer.PendingCommands); Interlocked.Increment(ref rejectedCommands); return false;
    }
    public async Task Unregister(MultiplayerPeer peer)
    {
        if (!peers.TryRemove(peer.Id, out _)) return;
        Interlocked.Decrement(ref connections);
        try { await commands.Writer.WriteAsync(new MultiplayerCommand(peer.Id, null, true)); }
        catch (ChannelClosedException) { }
    }
    bool IMultiplayerSink.Send(string connectionId, byte[] bytes, bool reliable) => peers.TryGetValue(connectionId, out var peer) && peer.Mailbox.TryWrite(bytes, reliable);
    void IMultiplayerSink.Close(string connectionId, string reason) { if (peers.TryGetValue(connectionId, out var peer)) peer.Mailbox.Close(reason); }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMilliseconds(4));
        var elapsedClock = Stopwatch.StartNew(); var tickClock = new FixedTickClock();
        try
        {
            while (await timer.WaitForNextTickAsync(stoppingToken))
            {
                int due = tickClock.Advance(elapsedClock.Elapsed.TotalSeconds);
                Interlocked.Exchange(ref droppedCatchupTicks, tickClock.DroppedTicks);
                for (int step = 0; step < due; step++)
                {
                    long start = Stopwatch.GetTimestamp();
                    for (int i = 0; i < 512 && commands.Reader.TryRead(out var command); i++)
                    {
                        if (command.Disconnect) { service.Disconnect(command.ConnectionId); continue; }
                        if (!peers.TryGetValue(command.ConnectionId, out var peer)) continue;
                        Interlocked.Decrement(ref peer.PendingCommands);
                        try { service.Handle(command.ConnectionId, command.Message!); }
                        catch (Exception error) when (error is ArgumentException or InvalidOperationException or IOException)
                        { logger.LogWarning("Multiplayer command failed: {Type}", error.GetType().Name); peer.Mailbox.Close("command_failed"); service.Disconnect(peer.Id); }
                    }
                    service.Step(); Interlocked.Exchange(ref publishedTick, service.ServiceTick);
                    Interlocked.Exchange(ref lastStepTimestamp, Stopwatch.GetTimestamp());
                    Interlocked.Exchange(ref persistenceFailures, service.PersistenceFailures);
                    Volatile.Write(ref publishedRooms, service.RoomCount); Volatile.Write(ref publishedSessions, service.SessionCount);
                    double elapsed = Stopwatch.GetElapsedTime(start).TotalMilliseconds;
                    tickDurations.Record(elapsed);
                    if (elapsed > maximumStepMilliseconds) Volatile.Write(ref maximumStepMilliseconds, elapsed);
                    if (elapsed > 1000.0 / 60) Interlocked.Increment(ref slowTicks);
                }
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { }
        finally { commands.Writer.TryComplete(); foreach (var peer in peers.Values) peer.Mailbox.Close("server_stopping"); }
    }
    public override void Dispose() { base.Dispose(); service.Dispose(); }
}
