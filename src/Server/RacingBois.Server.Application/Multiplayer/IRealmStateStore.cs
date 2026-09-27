namespace RacingBois.Server.Application.Multiplayer;

/// <summary>Owns the process lease and atomic state commit. The application never depends on SQLite.</summary>
public interface IRealmStateStore : IDisposable
{
    string RealmKind { get; }
    RealmDocument Load();
    void Save(RealmDocument next);
}
