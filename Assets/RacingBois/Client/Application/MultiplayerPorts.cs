using System;

namespace RacingBois.Client.Application
{
    public interface IMonotonicClock { double NowSeconds { get; } }
    public interface IPlayerProfileStore { LocalPlayerProfile LoadOrCreate(); void Save(LocalPlayerProfile profile); }
    public interface IResumeReceiptStore
    { ResumeReceipt Load(string endpoint); void Save(string endpoint, ResumeReceipt receipt); void Clear(string endpoint); }
    public interface IProfileCredentialStore
    { ProfileCredential Load(string endpoint); void Save(string endpoint, ProfileCredential credential); void Clear(string endpoint); }

    public sealed class LocalPlayerProfile
    {
        public string ProfileId { get; }
        public string DisplayName { get; }
        public int ColorIndex { get; }
        public LocalPlayerProfile(string profileId, string displayName, int colorIndex)
        {
            ProfileId = profileId ?? ""; DisplayName = displayName ?? ""; ColorIndex = colorIndex;
        }
    }
    /// <summary>Opaque per-tab lease credential. Never include in presentation readmodels or telemetry.</summary>
    public sealed class ResumeReceipt
    {
        public string RoomId { get; }
        public string RoomCode { get; }
        public string PlayerId { get; }
        public string ResumeToken { get; }
        public ResumeReceipt(string roomId, string roomCode, string playerId, string resumeToken)
        { RoomId = roomId ?? ""; RoomCode = roomCode ?? ""; PlayerId = playerId ?? ""; ResumeToken = resumeToken ?? ""; }
    }
    /// <summary>Server-issued local profile credential scoped to one endpoint/realm, not an online-account password.</summary>
    public sealed class ProfileCredential
    {
        public string ProfileToken { get; }
        public string ProfileId { get; }
        public string DisplayName { get; }
        public string RealmId { get; }
        public int Credits { get; }
        public ProfileCredential(string profileToken, string profileId, string displayName, string realmId, int credits)
        { ProfileToken = profileToken ?? ""; ProfileId = profileId ?? ""; DisplayName = displayName ?? ""; RealmId = realmId ?? ""; Credits = credits; }
    }
}
