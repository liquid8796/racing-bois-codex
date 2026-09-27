using System.Threading.Channels;

namespace RacingBois.Server.Application.Multiplayer;

public interface IRealmPersistence : IDisposable
{
    Task<(RealmProfile Profile, string Token)> CreateProfile(string name);
    Task<string> BeginMatch();
    Task<string> BeginMatch(string[] profileIds) => BeginMatch();
    Task<RealmResult> Commit(string matchId, RealmGrant[] grants);
}

/// <summary>One bounded disk writer, separate from the 60 Hz owner. Task completions never mutate rooms directly.</summary>
public sealed class RealmPersistence : IRealmPersistence
{
    private interface IWork { void Execute(); }
    private sealed class Work<T>(Func<T> action) : IWork
    {
        public readonly TaskCompletionSource<T> Completion = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public void Execute() { try { Completion.TrySetResult(action()); } catch (Exception error) { Completion.TrySetException(error); } }
    }
    private readonly RealmStore realm;
    private readonly Channel<IWork> queue = Channel.CreateBounded<IWork>(new BoundedChannelOptions(128)
    { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });
    private readonly Task worker;
    private bool disposed;
    public RealmPersistence(RealmStore realm)
    {
        this.realm = realm;
        worker = Task.Run(async () => { await foreach (var job in queue.Reader.ReadAllAsync()) job.Execute(); });
    }
    public Task<(RealmProfile Profile, string Token)> CreateProfile(string name) => Enqueue(() => realm.CreateProfile(name));
    public Task<string> BeginMatch() => Enqueue(realm.BeginMatch);
    public Task<string> BeginMatch(string[] profileIds) => Enqueue(() => realm.BeginMatch(profileIds));
    public Task<RealmResult> Commit(string matchId, RealmGrant[] grants) => Enqueue(() => realm.Commit(matchId, grants));
    private Task<T> Enqueue<T>(Func<T> action)
    {
        if (disposed) return Task.FromException<T>(new ObjectDisposedException(nameof(RealmPersistence)));
        var job = new Work<T>(action);
        if (!queue.Writer.TryWrite(job)) job.Completion.TrySetException(new InvalidOperationException("persistence_queue_full"));
        return job.Completion.Task;
    }
    public void Dispose()
    {
        if (disposed) return; disposed = true; queue.Writer.TryComplete();
        // Lifecycle shutdown only; the match loop never waits on storage.
        worker.GetAwaiter().GetResult();
    }
}
