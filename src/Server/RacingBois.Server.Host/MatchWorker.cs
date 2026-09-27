using System.Diagnostics;
using System.Threading.Channels;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Server.Application;
using RacingBois.Server.Host.Multiplayer;

namespace RacingBois.Server.Host;

internal sealed class Peer(string playerId, bool isRace, int riderId = 0)
{
    public string PlayerId { get; } = playerId;
    public bool IsRace { get; } = isRace;
    public int RiderId { get; } = riderId;
    // Slow readers retain only the most recent authoritative state; no unbounded send queue.
    public Channel<byte[]> Outgoing { get; } = Channel.CreateBounded<byte[]>(new BoundedChannelOptions(4)
    { SingleReader = true, SingleWriter = true, FullMode = BoundedChannelFullMode.DropOldest });
}

internal sealed class MatchWorker(ILogger<MatchWorker> logger) : BackgroundService
{
    private readonly AuthoritativeMatch match = new();
    private readonly AuthoritativeRace race = new();
    private readonly HashSet<Peer> peers = new();
    private readonly Channel<Action> commands = Channel.CreateBounded<Action>(new BoundedChannelOptions(256)
    { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });
    private long publishedTick;
    private int publishedPlayers;
    private long rejectedCommands;
    private long slowTicks;
    private double maximumStepMilliseconds;
    public object Health => new { status = "ok", phase = "P03/P04 gameplay authority", tick = Interlocked.Read(ref publishedTick), players = Volatile.Read(ref publishedPlayers), protocolVersion = RaceProtocol.Version, simulationRulesVersion = RaceProtocol.SimulationRulesVersion, legacyProtocolVersion = WireProtocol.Version, rejectedCommands = Interlocked.Read(ref rejectedCommands), slowTicks = Interlocked.Read(ref slowTicks), maximumStepMilliseconds = Volatile.Read(ref maximumStepMilliseconds) };

    public async Task<Peer?> Join(CancellationToken cancellation, bool isRace = false)
    {
        var result = new TaskCompletionSource<Peer?>(TaskCreationOptions.RunContinuationsAsynchronously);
        await commands.Writer.WriteAsync(() =>
        {
            if (cancellation.IsCancellationRequested) { result.TrySetCanceled(cancellation); return; }
            var id = isRace ? race.Join() : match.Join();
            if (id == null) { result.TrySetResult(null); return; }
            var peer = new Peer(id, isRace, isRace ? race.RiderId(id) : 0);
            peers.Add(peer);
            result.TrySetResult(peer);
        }, cancellation);
        return await result.Task;
    }

    public bool Input(Peer peer, InputMessage message) => commands.Writer.TryWrite(() =>
    {
        if (peer.IsRace || !peers.Contains(peer)) return;
        string? error = match.Apply(peer.PlayerId, message);
        if (error == null) return;
        Interlocked.Increment(ref rejectedCommands);
        peer.Outgoing.Writer.TryWrite(WireJson.Serialize(new ErrorMessage { code = error, message = "Input rejected by authority.", sequence = message.sequence }));
    });

    public bool Input(Peer peer, RaceInputMessage message) => commands.Writer.TryWrite(() =>
    {
        if (!peer.IsRace || !peers.Contains(peer)) return;
        string? error = race.Apply(peer.PlayerId, message);
        if (error == null) return;
        Interlocked.Increment(ref rejectedCommands);
        peer.Outgoing.Writer.TryWrite(WireJson.Serialize(new ErrorMessage
        {
            protocolVersion = RaceProtocol.Version,
            code = error,
            message = "Input rejected by authority.",
            sequence = message.sequence
        }));
    });

    public async Task Leave(Peer peer)
    {
        if (commands.Reader.Completion.IsCompleted) return;
        await commands.Writer.WriteAsync(() =>
        {
            if (peer.IsRace) race.Leave(peer.PlayerId); else match.Leave(peer.PlayerId);
            peers.Remove(peer);
            peer.Outgoing.Writer.TryComplete();
        });
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMilliseconds(4));
        var elapsedClock = Stopwatch.StartNew(); var tickClock = new FixedTickClock();
        try
        {
            while (await timer.WaitForNextTickAsync(stoppingToken))
            {
                int due = tickClock.Advance(elapsedClock.Elapsed.TotalSeconds);
                for (int step = 0; step < due; step++)
                {
                    long start = Stopwatch.GetTimestamp();
                    // Bound work per tick. Flooding cannot keep simulation permanently inside the drain loop.
                    for (int i = 0; i < 256 && commands.Reader.TryRead(out var command); i++) command();
                    match.Step();
                    race.Step();
                    if (match.Tick % (PrototypeRules.TickRate / PrototypeRules.SnapshotRate) == 0)
                        foreach (var peer in peers) peer.Outgoing.Writer.TryWrite(WireJson.Serialize(peer.IsRace ? (object)race.Snapshot(peer.PlayerId) : match.Snapshot(peer.PlayerId)));
                    Interlocked.Exchange(ref publishedTick, match.Tick);
                    Volatile.Write(ref publishedPlayers, peers.Count);
                    double elapsed = Stopwatch.GetElapsedTime(start).TotalMilliseconds;
                    if (elapsed > maximumStepMilliseconds) Volatile.Write(ref maximumStepMilliseconds, elapsed);
                    if (elapsed > 1000.0 / PrototypeRules.TickRate) Interlocked.Increment(ref slowTicks);
                }
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { }
        finally
        {
            commands.Writer.TryComplete();
            foreach (var peer in peers) peer.Outgoing.Writer.TryComplete();
            logger.LogInformation("Match stopped at tick {Tick}.", match.Tick);
        }
    }
}
