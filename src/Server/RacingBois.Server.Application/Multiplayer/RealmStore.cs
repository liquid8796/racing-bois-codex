using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Server.Domain;

namespace RacingBois.Server.Application.Multiplayer;

public sealed class RealmProfile
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string CapabilityHash { get; set; } = "";
    public int Credits { get; set; }
    public CareerProgress Career { get; set; } = new();
}
public sealed class RealmGrant
{
    public string SessionId { get; set; } = "";
    public string ProfileId { get; set; } = "";
    public string Name { get; set; } = "";
    public int RiderId { get; set; }
    public int Outcome { get; set; }
    public int Rank { get; set; }
    public int Reward { get; set; }
    public int Credits { get; set; }
    public long FinishTick { get; set; }
    public bool Guest { get; set; }
    public string BikeId { get; set; } = "";
    public int BikeCondition { get; set; } = 100;
    public int LevelIndex { get; set; }
    public int CourseIndex { get; set; }
    public bool Qualified { get; set; }
}
public sealed class RealmResult
{
    public long Number { get; set; }
    public string MatchId { get; set; } = "";
    public RealmGrant[] Grants { get; set; } = [];
}
public sealed class AppliedRange { public long First { get; set; } public long Last { get; set; } }
public sealed class MatchReservation { public long Match { get; set; } public string ProfileId { get; set; } = ""; }
public sealed class RealmDocument
{
    public int Version { get; set; } = 1;
    public string RealmId { get; set; } = Guid.NewGuid().ToString("N");
    public string RealmKind { get; set; } = "offline";
    public string ExportSigningKey { get; set; } = "";
    public long Revision { get; set; }
    public long NextMatch { get; set; } = 1;
    public List<RealmProfile> Profiles { get; set; } = [];
    public List<long> OpenMatches { get; set; } = [];
    public List<MatchReservation> Reservations { get; set; } = [];
    public List<AppliedRange> Applied { get; set; } = [];
    public List<RealmResult> Results { get; set; } = [];
    public List<SecurityAuditEntry> SecurityAudit { get; set; } = [];
}

/// <summary>Serial aggregate commits publish immutable snapshots. The match tick never reads SQLite.</summary>
public sealed class RealmStore : IDisposable
{
    private readonly object gate = new();
    private readonly string? file;
    private readonly FileStream? lease;
    private readonly IRealmStateStore? persistence;
    private readonly TimeProvider clock;
    private RealmDocument document;
    internal static readonly JsonSerializerOptions Json = new() { WriteIndented = false };
    private RealmDocument Snapshot => Volatile.Read(ref document);
    public string RealmId => Snapshot.RealmId;
    public string RealmKind => Snapshot.RealmKind;
    public int ProfileCount => Snapshot.Profiles.Count;
    public int RetainedResults => Snapshot.Results.Count;
    public int IdempotencyRanges => Snapshot.Applied.Count;
    public long NowUnixSeconds => clock.GetUtcNow().ToUnixTimeSeconds();
    public bool DurableCareer => Snapshot.Version == 2;

    /// <summary>Compatibility adapter for P05 fixtures. Production injects IRealmStateStore.</summary>
    public RealmStore(string directory)
    {
        clock = TimeProvider.System;
        Directory.CreateDirectory(directory); file = Path.Combine(Path.GetFullPath(directory), "realm.json");
        lease = new FileStream(Path.Combine(Path.GetFullPath(directory), "realm.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        try
        {
            document = File.Exists(file) ? Deserialize(File.ReadAllText(file)) : new RealmDocument();
            Validate(document); RecoverOpenMatches();
            if (!File.Exists(file)) Save(document);
        }
        catch { lease.Dispose(); throw; }
    }
    public RealmStore(IRealmStateStore persistence, TimeProvider? clock = null)
    {
        this.persistence = persistence; this.clock = clock ?? TimeProvider.System;
        try { document = persistence.Load(); Validate(document); RecoverOpenMatches(); }
        catch { persistence.Dispose(); throw; }
    }
    private void RecoverOpenMatches()
    {
        if (document.OpenMatches.Count == 0) return;
        var next = Clone(document);
        foreach (long number in next.OpenMatches) MarkApplied(next, number);
        next.OpenMatches.Clear(); next.Reservations.Clear(); Save(next);
    }
    public (RealmProfile Profile, string Token) CreateProfile(string name) => Transact(next =>
    {
        if (next.Profiles.Count >= 1024) throw new InvalidOperationException("profile_capacity");
        string token = Capability(); var profile = NewProfile(name, token, next.Version == 2, NowUnixSeconds);
        next.Profiles.Add(profile); return (Clone(profile), token);
    });
    internal static RealmProfile NewProfile(string name, string token, bool durable, long now)
    {
        var profile = new RealmProfile { Id = Guid.NewGuid().ToString("N"), Name = name, CapabilityHash = Hash(token) };
        if (durable)
        {
            InitializeCareer(profile, EconomyRules.StartingCredits, now, "opening");
            profile.Career.Sessions.Add(new ProfileSession { CapabilityHash = Hash(token), ExpiresUnixSeconds = now + 30 * 86400 });
        }
        return profile;
    }
    public RealmProfile? Authenticate(string token)
    {
        if (token == null || token.Length != 43) return null;
        string hash = Hash(token); var snapshot = Snapshot;
        var profile = snapshot.Profiles.FirstOrDefault(item => snapshot.Version == 1 ? item.CapabilityHash == hash :
            item.Career.Sessions.Any(session => session.CapabilityHash == hash && session.ExpiresUnixSeconds > NowUnixSeconds));
        return profile == null ? null : Clone(profile);
    }
    public bool IsTokenActive(string token)
    {
        if (token == null || token.Length != 43) return false;
        var snapshot = Snapshot; string hash = Hash(token); long now = NowUnixSeconds;
        return snapshot.Profiles.Any(item => snapshot.Version == 1 ? item.CapabilityHash == hash :
            item.Career.Sessions.Any(session => session.CapabilityHash == hash && session.ExpiresUnixSeconds > now));
    }
    public RealmProfile? GetProfile(string profileId)
    { var profile = Snapshot.Profiles.FirstOrDefault(item => item.Id == profileId); return profile == null ? null : Clone(profile); }
    public int Credits(string profileId) => Snapshot.Profiles.FirstOrDefault(profile => profile.Id == profileId)?.Credits ?? 0;
    public CareerProfileData GetRaceConfiguration(string profileId)
    {
        var snapshot = Snapshot; return Project(snapshot, snapshot.Profiles.Single(item => item.Id == profileId));
    }
    public string BeginMatch() => BeginMatch([]);
    public string BeginMatch(string[] profileIds) => Transact(next =>
    {
        if (profileIds.Distinct(StringComparer.Ordinal).Count() != profileIds.Length || profileIds.Length > 8)
            throw new InvalidOperationException("duplicate_profile_result");
        foreach (string id in profileIds)
        {
            if (!next.Profiles.Any(profile => profile.Id == id)) throw new InvalidOperationException("unknown_profile");
            if (IsBusy(next, id)) throw new InvalidOperationException("profile_busy");
        }
        long number = next.NextMatch++; next.OpenMatches.Add(number);
        next.Reservations.AddRange(profileIds.Select(id => new MatchReservation { Match = number, ProfileId = id }));
        return next.RealmId + "/" + number;
    });
    public RealmResult Commit(string matchId, RealmGrant[] grants) => Transact(next =>
    {
        if (!matchId.StartsWith(next.RealmId + "/", StringComparison.Ordinal) || !long.TryParse(matchId.AsSpan(next.RealmId.Length + 1), out long number))
            throw new InvalidOperationException("foreign_match");
        var previous = next.Results.FirstOrDefault(result => result.Number == number);
        if (previous != null) return Clone(previous);
        if (IsApplied(next, number)) return new RealmResult { Number = number, MatchId = matchId };
        if (!next.OpenMatches.Contains(number)) throw new InvalidOperationException("unknown_match");
        if (grants.Length > 8 || grants.Select(grant => grant.ProfileId).Distinct(StringComparer.Ordinal).Count() != grants.Length)
            throw new InvalidOperationException("duplicate_profile_result");
        var persisted = new List<RealmGrant>();
        foreach (var original in grants)
        {
            if (original.Reward is < -2000 or > 5000) throw new InvalidOperationException("invalid_reward");
            var grant = Clone(original);
            if (!grant.Guest)
            {
                var profile = next.Profiles.Single(item => item.Id == grant.ProfileId);
                if (next.Version == 2 && grant.BikeId.Length > 0) ApplyCareerResult(next, profile, grant, number);
                else
                {
                    int delta = Math.Max(-profile.Credits, grant.Reward);
                    if (next.Version == 2) AddLedger(profile, "match:" + number, "legacy_result", "", delta, NowUnixSeconds);
                    else profile.Credits = checked(profile.Credits + delta);
                }
                grant.Credits = profile.Credits;
            }
            else grant.Credits = Math.Max(0, grant.Credits + grant.Reward);
            persisted.Add(grant);
        }
        var result = new RealmResult { Number = number, MatchId = matchId, Grants = persisted.ToArray() };
        next.Results.Add(result); while (next.Results.Count > 256) next.Results.RemoveAt(0);
        next.OpenMatches.Remove(number); next.Reservations.RemoveAll(item => item.Match == number); MarkApplied(next, number);
        return Clone(result);
    });
    private void ApplyCareerResult(RealmDocument state, RealmProfile profile, RealmGrant grant, long number)
    {
        if (!state.Reservations.Any(item => item.Match == number && item.ProfileId == profile.Id)) throw new InvalidOperationException("profile_not_reserved");
        if (!BikeCatalog.TryGet(grant.BikeId, out _) || grant.BikeCondition is < 0 or > 100 || grant.LevelIndex != profile.Career.LevelIndex ||
            !CampaignCatalog.IsPlayableRoute(grant.CourseIndex) || grant.BikeId != profile.Career.SelectedBikeId) throw new InvalidOperationException("invalid_career_result");
        var outcome = (MultiplayerOutcome)grant.Outcome;
        int reward = outcome == MultiplayerOutcome.Finished ? EconomyRules.RewardForRank(grant.Rank, grant.LevelIndex) :
            outcome == MultiplayerOutcome.Busted ? -EconomyRules.BustFine(grant.LevelIndex) : 0;
        if (outcome is not (MultiplayerOutcome.Finished or MultiplayerOutcome.Busted or MultiplayerOutcome.Wrecked or MultiplayerOutcome.Dnf) || grant.Reward != reward)
            throw new InvalidOperationException("invalid_reward");
        profile.Career.Bikes.Single(item => item.BikeId == grant.BikeId).Condition = grant.BikeCondition;
        AddLedger(profile, "match:" + number, outcome == MultiplayerOutcome.Busted ? "fine" : "race_result", grant.BikeId,
            Math.Max(-profile.Credits, reward), NowUnixSeconds);
        if (grant.Qualified && outcome == MultiplayerOutcome.Finished && grant.Rank <= CampaignCatalog.QualifyingRank)
        {
            var progress = CampaignRules.ApplyQualification(profile.Career.LevelIndex, profile.Career.QualificationMask,
                profile.Career.CampaignComplete, grant.CourseIndex, grant.Rank);
            profile.Career.LevelIndex = progress.LevelIndex; profile.Career.QualificationMask = progress.QualificationMask;
            profile.Career.CampaignComplete = progress.Completed;
        }
    }
    internal static bool IsBusy(RealmDocument state, string profileId) => state.Reservations.Any(item => item.ProfileId == profileId);
    internal T Transact<T>(Func<RealmDocument, T> action)
    { lock (gate) { var next = Clone(document); T result = action(next); Save(next); return result; } }
    internal T Read<T>(Func<RealmDocument, T> action) => action(Snapshot);
    private void Save(RealmDocument next)
    {
        next.Revision = checked(document.Revision + 1); Validate(next);
        if (persistence != null) persistence.Save(next);
        else
        {
            byte[] bytes = JsonSerializer.SerializeToUtf8Bytes(next, Json); string temporary = file + ".pending";
            using (var stream = new FileStream(temporary, FileMode.Create, FileAccess.Write, FileShare.None)) { stream.Write(bytes); stream.Flush(true); }
            File.Move(temporary, file!, true);
        }
        Volatile.Write(ref document, next);
    }
    public static RealmDocument Deserialize(string json)
    {
        try { return JsonSerializer.Deserialize<RealmDocument>(json, Json) ?? throw new InvalidDataException("Empty realm."); }
        catch (JsonException error) { throw new InvalidDataException("Realm data is invalid; it was not reset.", error); }
    }
    public static void UpgradeLegacy(RealmDocument state, string realmKind, long now)
    {
        Validate(state); if (state.Version != 1) throw new InvalidDataException("Only v1 can be migrated.");
        state.Version = 2; state.RealmKind = realmKind; state.ExportSigningKey = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32));
        foreach (var profile in state.Profiles)
        {
            InitializeCareer(profile, profile.Credits, now, "migration_opening");
            profile.Career.Sessions.Add(new ProfileSession { CapabilityHash = profile.CapabilityHash, ExpiresUnixSeconds = now + 30 * 86400 });
        }
        Validate(state);
    }
    private static void InitializeCareer(RealmProfile profile, int credits, long now, string reason)
    {
        profile.Credits = 0;
        profile.Career = new CareerProgress { SelectedBikeId = BikeCatalog.StarterBikeId, Bikes = [new OwnedBike { BikeId = BikeCatalog.StarterBikeId }] };
        AddLedger(profile, "opening", reason, BikeCatalog.StarterBikeId, credits, now);
    }
    internal static void AddLedger(RealmProfile profile, string transactionId, string reason, string bikeId, int delta, long now)
    {
        if (profile.Career.Ledger.Any(item => item.TransactionId == transactionId)) throw new InvalidOperationException("duplicate_ledger");
        profile.Credits = checked(profile.Credits + delta); if (profile.Credits < 0) throw new InvalidOperationException("insufficient_credits");
        profile.Career.Ledger.Add(new WalletEntry { TransactionId = transactionId, Reason = reason, BikeId = bikeId, Delta = delta,
            Balance = profile.Credits, CreatedUtc = DateTimeOffset.FromUnixTimeSeconds(now).ToString("O") });
        profile.Career.Revision++;
    }
    internal static CareerProfileData Project(RealmDocument state, RealmProfile profile) => new()
    {
        realmId = state.RealmId, realmKind = state.RealmKind, profileId = profile.Id, displayName = profile.Name,
        username = profile.Career.Username, credits = profile.Credits, selectedBikeId = state.Version == 1 ? BikeCatalog.StarterBikeId : profile.Career.SelectedBikeId,
        selectedCharacterId = profile.Career.SelectedCharacterId, levelIndex = profile.Career.LevelIndex, qualificationMask = profile.Career.QualificationMask, campaignComplete = profile.Career.CampaignComplete,
        revision = profile.Career.Revision, bikes = state.Version == 1 ? [new CareerBikeData { bikeId = BikeCatalog.StarterBikeId, condition = 100 }] :
            profile.Career.Bikes.Select(item => new CareerBikeData { bikeId = item.BikeId, condition = item.Condition }).ToArray()
    };
    private static void MarkApplied(RealmDocument state, long value)
    {
        state.Applied.Add(new AppliedRange { First = value, Last = value }); state.Applied.Sort((a, b) => a.First.CompareTo(b.First));
        for (int i = 1; i < state.Applied.Count;)
        {
            if (state.Applied[i].First <= state.Applied[i - 1].Last + 1)
            { state.Applied[i - 1].Last = Math.Max(state.Applied[i - 1].Last, state.Applied[i].Last); state.Applied.RemoveAt(i); }
            else i++;
        }
    }
    private static bool IsApplied(RealmDocument state, long number) => state.Applied.Any(range => number >= range.First && number <= range.Last);
    public static void Validate(RealmDocument state)
    {
        if (state.Version is not (1 or 2) || state.RealmId.Length != 32 || state.NextMatch < 1 || state.Profiles.Count > 1024 ||
            state.OpenMatches.Count > 8 || state.Results.Count > 256 || state.Applied.Count > 1024 || state.SecurityAudit.Count > 1024 ||
            state.Profiles.Select(profile => profile.Id).Distinct().Count() != state.Profiles.Count ||
            state.Profiles.Any(profile => profile.Credits < 0 || profile.CapabilityHash.Length != 64) ||
            state.Applied.Any(range => range.First < 1 || range.Last < range.First || range.Last >= state.NextMatch) ||
            state.OpenMatches.Distinct().Count() != state.OpenMatches.Count || state.OpenMatches.Any(number => number < 1 || number >= state.NextMatch || IsApplied(state, number)) ||
            state.Reservations.Select(item => item.ProfileId).Distinct().Count() != state.Reservations.Count ||
            state.Reservations.Any(item => !state.OpenMatches.Contains(item.Match) || !state.Profiles.Any(profile => profile.Id == item.ProfileId)))
            throw new InvalidDataException("Realm invariants failed; data was not reset.");
        if (state.Version == 1) return;
        if (state.RealmKind is not ("offline" or "online") || Convert.FromBase64String(state.ExportSigningKey).Length != 32 ||
            state.Profiles.Where(profile => profile.Career.Username.Length > 0).Select(profile => profile.Career.Username).Distinct(StringComparer.OrdinalIgnoreCase).Count() !=
            state.Profiles.Count(profile => profile.Career.Username.Length > 0)) throw new InvalidDataException("Realm identity invariants failed.");
        foreach (var profile in state.Profiles) ValidateCareer(profile);
    }
    public static void ValidateCareer(RealmProfile profile)
    {
        var career = profile.Career;
        CampaignRules.ValidateProgress(career.LevelIndex, career.QualificationMask, career.CampaignComplete);
        if (!CharacterCatalog.TryGet(career.SelectedCharacterId, out _) || career.Bikes.Count is < 1 or > 15 || career.Bikes.Select(bike => bike.BikeId).Distinct().Count() != career.Bikes.Count ||
            !career.Bikes.Any(bike => bike.BikeId == career.SelectedBikeId) || career.Bikes.Any(bike => !BikeCatalog.TryGet(bike.BikeId, out _) || bike.Condition is < 0 or > 100) ||
            career.Sessions.Count > 16 || career.Sessions.Any(session => session.CapabilityHash.Length != 64 || session.ExpiresUnixSeconds < 1) ||
            career.Sessions.Select(session => session.CapabilityHash).Distinct().Count() != career.Sessions.Count ||
            career.Receipts.Select(receipt => receipt.TransactionId).Distinct().Count() != career.Receipts.Count || career.Revision < 0 || career.SaveGeneration < 0 ||
            career.Ledger.Select(entry => entry.TransactionId).Distinct().Count() != career.Ledger.Count)
            throw new InvalidDataException("Career invariants failed.");
        long balance = 0;
        foreach (var entry in career.Ledger)
        {
            balance += entry.Delta;
            if (balance < 0 || balance > int.MaxValue || balance != entry.Balance || entry.TransactionId.Length is < 1 or > 128)
                throw new InvalidDataException("Wallet ledger invariants failed.");
        }
        if (balance != profile.Credits || career.Ledger.Count == 0) throw new InvalidDataException("Wallet balance does not match ledger.");
    }
    internal static T Clone<T>(T value) => JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json)!;
    public static string Capability() => Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_');
    public static string Hash(string token) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(token))).ToLowerInvariant();
    public void Dispose() { lock (gate) { persistence?.Dispose(); lease?.Dispose(); } }
}
