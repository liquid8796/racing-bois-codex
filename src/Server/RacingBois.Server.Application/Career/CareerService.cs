using System.Security.Cryptography;
using System.Data.Common;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Server.Application.Multiplayer;
using RacingBois.Server.Domain;

namespace RacingBois.Server.Application.Career;

/// <summary>Server-owned account and commerce commands. No command accepts a target profile or an amount.</summary>
public sealed class CareerService
{
    private readonly RealmStore realm;
    private readonly PasswordHasher<RealmProfile> passwords = new(Options.Create(new PasswordHasherOptions { IterationCount = 210_000 }));
    private readonly string dummyPasswordHash;
    private static readonly JsonSerializerOptions SaveJson = new() { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, MaxDepth = 12 };
    private const int MaximumSaveBytes = 96 * 1024;
    public CareerService(RealmStore realm)
    {
        this.realm = realm;
        dummyPasswordHash = passwords.HashPassword(new RealmProfile(), RealmStore.Capability());
    }

    public CareerResponse Execute(string bearer, CareerRequest request)
    {
        bearer ??= "";
        if (!realm.DurableCareer) return Failure("career_unavailable");
        if (request == null || !ValidateRequest(request) || bearer.Length > 256) return Failure("invalid_request");
        try
        {
            if (request.operation == "view") return realm.Read(state => Response(state, RequireProfile(state, bearer)));
            if (request.operation == "export") return realm.Read(state => Export(state, RequireProfile(state, bearer)));
            if (request.operation == "logout" && !realm.IsTokenActive(bearer)) return new CareerResponse { ok = true, code = "logged_out" };
            return realm.Transact(state => ExecuteMutation(state, bearer, request));
        }
        catch (CommandRejected rejected) { return Failure(rejected.Code); }
        catch (OverflowException) { return Failure("balance_limit"); }
        catch (Exception error) when (error is DbException or IOException) { return Failure("storage_unavailable"); }
    }
    private CareerResponse ExecuteMutation(RealmDocument state, string bearer, CareerRequest request)
    {
        bool accountOperation = request.operation is "register" or "login" or "recover" or "rotateRecovery" or "logout" or "logoutAll";
        CareerResponse response;
        string profileId = FindProfile(state, bearer)?.Id ?? "";
        try
        {
            response = request.operation switch
            {
                "register" => Register(state, bearer, request),
                "login" => Login(state, request),
                "recover" => Recover(state, request),
                "rotateRecovery" => RotateRecovery(state, RequireProfile(state, bearer), request),
                "logout" => Logout(state, RequireProfile(state, bearer), bearer, false),
                "logoutAll" => Logout(state, RequireProfile(state, bearer), bearer, true),
                "buy" or "trade" or "equip" or "repair" or "character" or "import" or "restartCareer" => Commerce(state, RequireProfile(state, bearer), request),
                _ => Failure("unknown_operation")
            };
        }
        catch (CommandRejected rejected) when (accountOperation) { response = Failure(rejected.Code); }
        if (accountOperation)
        {
            state.SecurityAudit.Add(new SecurityAuditEntry { CreatedUtc = DateTimeOffset.FromUnixTimeSeconds(realm.NowUnixSeconds).ToString("O"),
                ProfileId = response.profile.profileId.Length > 0 ? response.profile.profileId : profileId, Operation = request.operation, Code = response.code });
            while (state.SecurityAudit.Count > 1024) state.SecurityAudit.RemoveAt(0);
        }
        return response;
    }
    private static bool ValidateRequest(CareerRequest request) => request.operation != null && request.operation.Length is > 0 and <= 24 &&
        request.transactionId != null && request.transactionId.Length <= 80 && request.bikeId != null && request.bikeId.Length <= 64 && request.characterId != null && request.characterId.Length <= 64 &&
        request.username != null && request.username.Length <= 64 && request.password != null && request.password.Length <= 128 &&
        request.recoveryCode != null && request.recoveryCode.Length <= 128 && request.saveJson != null && Encoding.UTF8.GetByteCount(request.saveJson) <= MaximumSaveBytes;

    private CareerResponse Register(RealmDocument state, string bearer, CareerRequest request)
    {
        string username = NormalizeUsername(request.username); ValidatePassword(request.password);
        var caller = FindProfile(state, bearer);
        if (bearer.Length > 0 && caller == null) throw Reject("unauthorized");
        var existing = state.Profiles.SingleOrDefault(profile => profile.Career.Username == username);
        if (existing != null)
        {
            // A lost registration response is recoverable with the chosen credentials; do not expose an old recovery code.
            if ((caller == null || caller.Id == existing.Id) && VerifyPassword(existing, request.password))
                return IssueResponse(state, existing, "authenticated", false);
            throw Reject("username_unavailable");
        }
        if (caller?.Career.Username.Length > 0) throw Reject("already_registered");
        if (caller == null)
        {
            if (state.Profiles.Count >= 1024) throw Reject("profile_capacity");
            caller = RealmStore.NewProfile(username, RealmStore.Capability(), true, realm.NowUnixSeconds); state.Profiles.Add(caller);
        }
        caller.Career.Username = username; caller.Career.PasswordHash = passwords.HashPassword(caller, request.password);
        caller.Career.Revision++;
        return IssueResponse(state, caller, "registered", true);
    }
    private CareerResponse Login(RealmDocument state, CareerRequest request)
    {
        string username;
        try { username = NormalizeUsername(request.username); } catch (CommandRejected) { username = ""; }
        var profile = state.Profiles.SingleOrDefault(item => item.Career.Username == username && username.Length > 0);
        if (profile == null)
        {
            passwords.VerifyHashedPassword(new RealmProfile(), dummyPasswordHash, request.password);
            throw Reject("invalid_credentials");
        }
        if (!VerifyPassword(profile, request.password)) throw Reject("invalid_credentials");
        return IssueResponse(state, profile, "authenticated", false);
    }
    private bool VerifyPassword(RealmProfile profile, string password)
    {
        if (profile.Career.PasswordHash.Length == 0) return false;
        var result = passwords.VerifyHashedPassword(profile, profile.Career.PasswordHash, password);
        if (result == PasswordVerificationResult.SuccessRehashNeeded) profile.Career.PasswordHash = passwords.HashPassword(profile, password);
        return result != PasswordVerificationResult.Failed;
    }
    private CareerResponse Recover(RealmDocument state, CareerRequest request)
    {
        ValidatePassword(request.password);
        string username;
        try { username = NormalizeUsername(request.username); } catch (CommandRejected) { throw Reject("invalid_credentials"); }
        var profile = state.Profiles.SingleOrDefault(item => item.Career.Username == username);
        if (profile == null || request.recoveryCode.Length != 43 || !ConstantHashEqual(profile.Career.RecoveryHash, RealmStore.Hash(request.recoveryCode)))
            throw Reject("invalid_credentials");
        profile.Career.PasswordHash = passwords.HashPassword(profile, request.password); profile.Career.Revision++;
        return IssueResponse(state, profile, "recovered", true);
    }
    private CareerResponse RotateRecovery(RealmDocument state, RealmProfile profile, CareerRequest request)
    {
        if (!VerifyPassword(profile, request.password)) throw Reject("invalid_credentials");
        profile.Career.Revision++; return IssueResponse(state, profile, "recovery_rotated", true);
    }
    private CareerResponse IssueResponse(RealmDocument state, RealmProfile profile, string code, bool revokeAndRotate)
    {
        string recoveryCode = "", token = RealmStore.Capability();
        if (revokeAndRotate)
        {
            profile.Career.Sessions.Clear(); recoveryCode = RealmStore.Capability(); profile.Career.RecoveryHash = RealmStore.Hash(recoveryCode);
        }
        profile.Career.Sessions.RemoveAll(session => session.ExpiresUnixSeconds <= realm.NowUnixSeconds);
        while (profile.Career.Sessions.Count >= 8) profile.Career.Sessions.RemoveAt(0);
        profile.Career.Sessions.Add(new ProfileSession { CapabilityHash = RealmStore.Hash(token), ExpiresUnixSeconds = realm.NowUnixSeconds + 30 * 86400 });
        var response = Response(state, profile, code); response.profileToken = token; response.recoveryCode = recoveryCode; return response;
    }
    private static CareerResponse Logout(RealmDocument state, RealmProfile profile, string bearer, bool all)
    {
        if (all) profile.Career.Sessions.Clear();
        else profile.Career.Sessions.RemoveAll(session => session.CapabilityHash == RealmStore.Hash(bearer));
        return new CareerResponse { ok = true, code = all ? "all_sessions_revoked" : "logged_out" };
    }
    private CareerResponse Commerce(RealmDocument state, RealmProfile profile, CareerRequest request)
    {
        if (!Guid.TryParseExact(request.transactionId, "D", out var transaction) && !Guid.TryParseExact(request.transactionId, "N", out transaction)) throw Reject("invalid_transaction_id");
        string transactionId = transaction.ToString("D");
        string fingerprint = RealmStore.Hash(request.operation + "\n" + request.bikeId + "\n" + request.saveJson +
            (request.operation == "character" ? "\n" + request.characterId : ""));
        var prior = profile.Career.Receipts.SingleOrDefault(receipt => receipt.TransactionId == transactionId);
        if (prior != null)
        {
            if (prior.Fingerprint != fingerprint) throw Reject("transaction_conflict");
            var replay = Response(state, profile, prior.Code); replay.ok = prior.Ok; return replay;
        }
        // Failed attempts also bind their transaction IDs. Retry a corrected command with a new ID.
        if (profile.Career.Receipts.Count >= 100_000) throw Reject("transaction_capacity");
        string code; bool success;
        try
        {
            if (RealmStore.IsBusy(state, profile.Id)) throw Reject("profile_busy");
            code = request.operation switch
            {
                "import" => Import(state, profile, request),
                "restartCareer" => RestartCareer(profile, transactionId),
                "character" => SelectCharacter(profile, request.characterId),
                _ => ApplyBikeCommand(profile, request, transactionId)
            };
            success = true;
        }
        catch (CommandRejected rejected) { code = rejected.Code; success = false; }
        profile.Career.Receipts.Add(new CareerReceipt { TransactionId = transactionId, Fingerprint = fingerprint, Code = code, Ok = success });
        var response = Response(state, profile, code); response.ok = success; return response;
    }
    private static string SelectCharacter(RealmProfile profile, string characterId)
    {
        if (!CharacterCatalog.TryGet(characterId, out _)) throw Reject("unknown_character");
        profile.Career.SelectedCharacterId = characterId; profile.Career.Revision++;
        return "character_selected";
    }
    private string ApplyBikeCommand(RealmProfile profile, CareerRequest request, string transactionId)
    {
        if (!BikeCatalog.TryGet(request.bikeId, out var definition)) throw Reject("unknown_bike");
        var owned = profile.Career.Bikes.SingleOrDefault(item => item.BikeId == request.bikeId);
        int delta = 0; string code;
        switch (request.operation)
        {
            case "buy":
                if (owned != null) throw Reject("already_owned");
                if (profile.Credits < definition.PriceCredits) throw Reject("insufficient_credits");
                delta = -definition.PriceCredits; profile.Career.Bikes.Add(new OwnedBike { BikeId = definition.Id }); code = "purchased"; break;
            case "trade":
                if (owned != null) throw Reject("already_owned");
                var selected = profile.Career.Bikes.Single(item => item.BikeId == profile.Career.SelectedBikeId);
                if (selected.Condition == 0) throw Reject("repair_required");
                delta = BikeCatalog.Get(selected.BikeId).TradeInCredits - definition.PriceCredits;
                if ((long)profile.Credits + delta < 0) throw Reject("insufficient_credits");
                if ((long)profile.Credits + delta > int.MaxValue) throw Reject("balance_limit");
                profile.Career.Bikes.Remove(selected); profile.Career.Bikes.Add(new OwnedBike { BikeId = definition.Id });
                profile.Career.SelectedBikeId = definition.Id; code = "traded"; break;
            case "equip":
                if (owned == null) throw Reject("bike_not_owned");
                profile.Career.SelectedBikeId = owned.BikeId; code = "equipped"; break;
            case "repair":
                if (owned == null) throw Reject("bike_not_owned");
                if (owned.Condition == 100) throw Reject("already_repaired");
                if (profile.Credits < definition.RepairCredits) throw Reject("insufficient_credits");
                delta = -definition.RepairCredits; owned.Condition = 100; code = "repaired"; break;
            default: throw Reject("unknown_operation");
        }
        RealmStore.AddLedger(profile, "command:" + transactionId, request.operation, request.bikeId, delta, realm.NowUnixSeconds);
        return code;
    }

    private string RestartCareer(RealmProfile profile, string transactionId)
    {
        int cheapestRepair = profile.Career.Bikes.Min(bike => BikeCatalog.Get(bike.BikeId).RepairCredits);
        if (profile.Career.Bikes.Any(bike => bike.Condition > 0) || profile.Credits >= cheapestRepair) throw Reject("not_bankrupt");
        profile.Career.Bikes = [new OwnedBike { BikeId = BikeCatalog.StarterBikeId, Condition = 100 }];
        profile.Career.SelectedBikeId = BikeCatalog.StarterBikeId;
        profile.Career.LevelIndex = 0; profile.Career.QualificationMask = 0; profile.Career.CampaignComplete = false;
        profile.Career.SaveGeneration++;
        RealmStore.AddLedger(profile, "command:" + transactionId, "restartCareer", BikeCatalog.StarterBikeId, -profile.Credits, realm.NowUnixSeconds);
        return "career_restarted";
    }

    private CareerResponse Export(RealmDocument state, RealmProfile profile)
    {
        if (state.RealmKind != "offline") throw Reject("offline_only");
        if (RealmStore.IsBusy(state, profile.Id)) throw Reject("profile_busy");
        var payload = new LocalSavePayload { Version = 2, RealmId = state.RealmId, ProfileId = profile.Id, Generation = profile.Career.SaveGeneration,
            Revision = profile.Career.Revision, Credits = profile.Credits, SelectedBikeId = profile.Career.SelectedBikeId, SelectedCharacterId = profile.Career.SelectedCharacterId, LevelIndex = profile.Career.LevelIndex,
            QualificationMask = profile.Career.QualificationMask, CampaignComplete = profile.Career.CampaignComplete,
            Bikes = RealmStore.Clone(profile.Career.Bikes), Ledger = RealmStore.Clone(profile.Career.Ledger) };
        string serialized = JsonSerializer.Serialize(payload, SaveJson);
        var envelope = new LocalSaveEnvelope { Payload = serialized, Signature = Sign(state, serialized) };
        string output = JsonSerializer.Serialize(envelope, SaveJson);
        if (Encoding.UTF8.GetByteCount(output) > MaximumSaveBytes) throw Reject("save_too_large_use_host_backup");
        var response = Response(state, profile, "exported"); response.exportJson = output; return response;
    }
    private string Import(RealmDocument state, RealmProfile profile, CareerRequest request)
    {
        if (state.RealmKind != "offline") throw Reject("offline_only");
        LocalSavePayload payload;
        try
        {
            RejectDuplicateProperties(request.saveJson);
            var envelope = JsonSerializer.Deserialize<LocalSaveEnvelope>(request.saveJson, SaveJson);
            if (envelope == null || envelope.Payload == null || envelope.Signature == null || !ConstantHashEqual(envelope.Signature, Sign(state, envelope.Payload))) throw Reject("invalid_save");
            RejectDuplicateProperties(envelope.Payload);
            payload = JsonSerializer.Deserialize<LocalSavePayload>(envelope.Payload, SaveJson) ?? throw Reject("invalid_save");
        }
        catch (Exception error) when (error is JsonException or ArgumentException or FormatException) { throw Reject("invalid_save"); }
        if (payload.Version is not (1 or 2) || payload.RealmId != state.RealmId || payload.ProfileId != profile.Id) throw Reject("foreign_save");
        if (payload.Revision != profile.Career.Revision || payload.Generation != profile.Career.SaveGeneration) throw Reject("stale_save");
        if (payload.Bikes == null || payload.Ledger == null || payload.Ledger.Count > 1000) throw Reject("invalid_save");
        var candidate = RealmStore.Clone(profile);
        candidate.Credits = payload.Credits; candidate.Career.Bikes = payload.Bikes; candidate.Career.Ledger = payload.Ledger;
        candidate.Career.SelectedBikeId = payload.SelectedBikeId; candidate.Career.SelectedCharacterId = payload.SelectedCharacterId; candidate.Career.LevelIndex = payload.LevelIndex;
        candidate.Career.QualificationMask = payload.QualificationMask; candidate.Career.CampaignComplete = payload.CampaignComplete;
        try { RealmStore.ValidateCareer(candidate); } catch (Exception error) when (error is InvalidDataException or ArgumentException) { throw Reject("invalid_save"); }
        // A local checkpoint cannot rewind a settled transaction. Full host recovery uses a consistent database backup.
        if (JsonSerializer.Serialize(candidate.Career.Ledger) != JsonSerializer.Serialize(profile.Career.Ledger) || candidate.Credits != profile.Credits)
            throw Reject("stale_save");
        profile.Career.Bikes = candidate.Career.Bikes; profile.Career.SelectedBikeId = candidate.Career.SelectedBikeId;
        profile.Career.SelectedCharacterId = candidate.Career.SelectedCharacterId;
        profile.Career.LevelIndex = candidate.Career.LevelIndex; profile.Career.QualificationMask = candidate.Career.QualificationMask;
        profile.Career.CampaignComplete = candidate.Career.CampaignComplete;
        profile.Career.SaveGeneration++; profile.Career.Revision++;
        return "imported";
    }
    private static void RejectDuplicateProperties(string input)
    {
        using var document = JsonDocument.Parse(input, new JsonDocumentOptions { MaxDepth = 12 });
        void Check(JsonElement value)
        {
            if (value.ValueKind == JsonValueKind.Object)
            {
                var names = new HashSet<string>(StringComparer.Ordinal);
                foreach (var property in value.EnumerateObject()) { if (!names.Add(property.Name)) throw Reject("invalid_save"); Check(property.Value); }
            }
            else if (value.ValueKind == JsonValueKind.Array) foreach (var child in value.EnumerateArray()) Check(child);
        }
        Check(document.RootElement);
    }
    private static string Sign(RealmDocument state, string payload) => Convert.ToHexString(HMACSHA256.HashData(Convert.FromBase64String(state.ExportSigningKey), Encoding.UTF8.GetBytes(payload))).ToLowerInvariant();
    private static bool ConstantHashEqual(string left, string right) => left.Length == 64 && right.Length == 64 &&
        CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(left), Encoding.ASCII.GetBytes(right));
    private RealmProfile RequireProfile(RealmDocument state, string bearer) => FindProfile(state, bearer) ?? throw Reject("unauthorized");
    private RealmProfile? FindProfile(RealmDocument state, string bearer)
    {
        if (bearer.Length != 43) return null;
        string hash = RealmStore.Hash(bearer);
        return state.Profiles.SingleOrDefault(profile => profile.Career.Sessions.Any(session => session.CapabilityHash == hash && session.ExpiresUnixSeconds > realm.NowUnixSeconds));
    }
    private static CareerResponse Response(RealmDocument state, RealmProfile profile, string code = "ok") => new()
    {
        ok = true, code = code, profile = RealmStore.Project(state, profile), ledger = profile.Career.Ledger.TakeLast(40).Reverse().Select(entry => new CareerLedgerEntry
        { transactionId = entry.TransactionId, reason = entry.Reason, bikeId = entry.BikeId, delta = entry.Delta, balance = entry.Balance, createdUtc = entry.CreatedUtc }).ToArray()
    };
    private static string NormalizeUsername(string input)
    {
        string value = input.Trim().ToLowerInvariant();
        if (value.Length is < 3 or > 24 || value.Any(character => character is not (>= 'a' and <= 'z') and not (>= '0' and <= '9') and not '_' and not '-')) throw Reject("invalid_username");
        return value;
    }
    private static void ValidatePassword(string password) { if (password.Length is < 12 or > 128) throw Reject("weak_password"); }
    private static CareerResponse Failure(string code) => new() { ok = false, code = code };
    private static CommandRejected Reject(string code) => new(code);
    private sealed class CommandRejected(string code) : Exception(code) { public string Code { get; } = code; }
    private sealed class LocalSaveEnvelope { public string Payload { get; set; } = ""; public string Signature { get; set; } = ""; }
    private sealed class LocalSavePayload
    {
        public int Version { get; set; }
        public string RealmId { get; set; } = "";
        public string ProfileId { get; set; } = "";
        public long Generation { get; set; }
        public long Revision { get; set; }
        public int Credits { get; set; }
        public string SelectedBikeId { get; set; } = "";
        public string SelectedCharacterId { get; set; } = CharacterCatalog.DefaultId;
        public int LevelIndex { get; set; }
        public int QualificationMask { get; set; }
        public bool CampaignComplete { get; set; }
        public List<OwnedBike> Bikes { get; set; } = [];
        public List<WalletEntry> Ledger { get; set; } = [];
    }
}
