namespace RacingBois.Server.Domain;

public sealed class SecurityAuditEntry
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string CreatedUtc { get; set; } = "";
    public string ProfileId { get; set; } = "";
    public string Operation { get; set; } = "";
    public string Code { get; set; } = "";
}

public sealed class OwnedBike
{
    public string BikeId { get; set; } = "";
    public int Condition { get; set; } = 100;
}

public sealed class WalletEntry
{
    public string TransactionId { get; set; } = "";
    public string Reason { get; set; } = "";
    public string BikeId { get; set; } = "";
    public int Delta { get; set; }
    public int Balance { get; set; }
    public string CreatedUtc { get; set; } = "";
}

public sealed class CareerReceipt
{
    public string TransactionId { get; set; } = "";
    public string Fingerprint { get; set; } = "";
    public string Code { get; set; } = "";
    public bool Ok { get; set; }
}

public sealed class ProfileSession
{
    public string CapabilityHash { get; set; } = "";
    public long ExpiresUnixSeconds { get; set; }
}

public sealed class CareerProgress
{
    public string Username { get; set; } = "";
    public string PasswordHash { get; set; } = "";
    public string RecoveryHash { get; set; } = "";
    public long Revision { get; set; }
    public long SaveGeneration { get; set; }
    public string SelectedBikeId { get; set; } = "";
    // Missing in P07 JSON: initializer migrates cosmetics without touching economy or grants.
    public string SelectedCharacterId { get; set; } = "rb-ash";
    public int LevelIndex { get; set; }
    public int QualificationMask { get; set; }
    public bool CampaignComplete { get; set; }
    public List<OwnedBike> Bikes { get; set; } = [];
    public List<WalletEntry> Ledger { get; set; } = [];
    public List<CareerReceipt> Receipts { get; set; } = [];
    public List<ProfileSession> Sessions { get; set; } = [];
}
