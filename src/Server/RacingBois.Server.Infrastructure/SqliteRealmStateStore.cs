using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using RacingBois.Server.Application.Multiplayer;

namespace RacingBois.Server.Infrastructure;

/// <summary>
/// Single-process realm database. WAL + FULL synchronous commit atomically stores wallet, inventory,
/// receipts, sessions and match fences. A process lease prevents competing match authorities.
/// </summary>
public sealed class SqliteRealmStateStore : IRealmStateStore
{
    private readonly FileStream lease;
    private readonly SqliteConnection connection;
    private readonly Action? beforeCommit;
    private RealmDocument current = null!;
    private bool disposed;
    public string RealmKind { get; }
    public string DatabasePath { get; }

    /// <param name="beforeCommit">Failure-injection seam for rollback/crash tests; production omits it.</param>
    public SqliteRealmStateStore(string directory, string realmKind = "offline", Action? beforeCommit = null)
    {
        if (realmKind is not ("offline" or "online")) throw new ArgumentException("Invalid realm kind.", nameof(realmKind));
        RealmKind = realmKind; this.beforeCommit = beforeCommit;
        string root = Path.GetFullPath(directory); Directory.CreateDirectory(root);
        if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(root, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        lease = new FileStream(Path.Combine(root, "realm.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        DatabasePath = Path.Combine(root, "realm.sqlite3");
        connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = DatabasePath, Mode = SqliteOpenMode.ReadWriteCreate,
            Pooling = false, DefaultTimeout = 5 }.ToString());
        try
        {
            connection.Open(); Execute("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;");
            CreateSchema();
            using var read = connection.CreateCommand(); read.CommandText = "SELECT state_json FROM realm WHERE singleton=1";
            var serialized = read.ExecuteScalar() as string;
            if (serialized != null)
            {
                current = RealmStore.Deserialize(serialized);
                if (current.RealmKind != realmKind) throw new InvalidDataException("realm_kind_mismatch");
                RealmStore.Validate(current); ValidateProjection(current);
            }
            else Initialize(root);
            if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(DatabasePath, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        }
        catch { connection.Dispose(); lease.Dispose(); throw; }
    }
    private void CreateSchema()
    {
        using var version = connection.CreateCommand(); version.CommandText = "PRAGMA user_version";
        long existing = (long)version.ExecuteScalar()!;
        if (existing is not (0 or 1)) throw new InvalidDataException("unsupported_database_version");
        Execute("""
            CREATE TABLE IF NOT EXISTS realm(
              singleton INTEGER PRIMARY KEY CHECK(singleton=1), realm_id TEXT NOT NULL UNIQUE CHECK(length(realm_id)=32),
              kind TEXT NOT NULL CHECK(kind IN ('offline','online')), revision INTEGER NOT NULL CHECK(revision>=0), state_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS profiles(
              id TEXT PRIMARY KEY CHECK(length(id)=32), username TEXT COLLATE NOCASE UNIQUE,
              credits INTEGER NOT NULL CHECK(credits>=0 AND credits<=2147483647), selected_bike TEXT NOT NULL,
              level_index INTEGER NOT NULL CHECK(level_index BETWEEN 0 AND 4), qualification_mask INTEGER NOT NULL CHECK(qualification_mask BETWEEN 0 AND 31),
              completed INTEGER NOT NULL CHECK(completed IN (0,1)), revision INTEGER NOT NULL CHECK(revision>=0),
              CHECK((completed=1 AND level_index=4 AND qualification_mask=31) OR (completed=0 AND qualification_mask<31)),
              FOREIGN KEY(id,selected_bike) REFERENCES bikes(profile_id,bike_id) DEFERRABLE INITIALLY DEFERRED);
            CREATE TABLE IF NOT EXISTS bikes(
              profile_id TEXT NOT NULL REFERENCES profiles(id) DEFERRABLE INITIALLY DEFERRED,
              bike_id TEXT NOT NULL, condition INTEGER NOT NULL CHECK(condition BETWEEN 0 AND 100), PRIMARY KEY(profile_id,bike_id));
            CREATE TABLE IF NOT EXISTS ledger(
              profile_id TEXT NOT NULL REFERENCES profiles(id), sequence INTEGER NOT NULL CHECK(sequence>=0),
              transaction_id TEXT NOT NULL CHECK(length(transaction_id) BETWEEN 1 AND 128), reason TEXT NOT NULL, bike_id TEXT NOT NULL,
              delta INTEGER NOT NULL, balance INTEGER NOT NULL CHECK(balance>=0 AND balance<=2147483647), created_utc TEXT NOT NULL,
              PRIMARY KEY(profile_id,sequence), UNIQUE(profile_id,transaction_id));
            CREATE TABLE IF NOT EXISTS receipts(
              profile_id TEXT NOT NULL REFERENCES profiles(id), transaction_id TEXT NOT NULL, fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64),
              ok INTEGER NOT NULL CHECK(ok IN (0,1)), code TEXT NOT NULL, PRIMARY KEY(profile_id,transaction_id));
            CREATE TABLE IF NOT EXISTS sessions(
              capability_hash TEXT PRIMARY KEY CHECK(length(capability_hash)=64), profile_id TEXT NOT NULL REFERENCES profiles(id),
              expires_unix INTEGER NOT NULL CHECK(expires_unix>0));
            CREATE TABLE IF NOT EXISTS reservations(profile_id TEXT PRIMARY KEY REFERENCES profiles(id), match_number INTEGER NOT NULL CHECK(match_number>0));
            CREATE TABLE IF NOT EXISTS migrations(source_sha256 TEXT PRIMARY KEY CHECK(length(source_sha256)=64), backup_file TEXT NOT NULL,
              migrated_utc TEXT NOT NULL, profile_count INTEGER NOT NULL, credits_total INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS security_audit(id TEXT PRIMARY KEY, created_utc TEXT NOT NULL, profile_id TEXT NOT NULL,
              operation TEXT NOT NULL, code TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger BEGIN SELECT RAISE(ABORT,'immutable_ledger'); END;
            CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger BEGIN SELECT RAISE(ABORT,'immutable_ledger'); END;
            CREATE TRIGGER IF NOT EXISTS ledger_balanced_insert BEFORE INSERT ON ledger
              WHEN NEW.sequence<>COALESCE((SELECT max(sequence)+1 FROM ledger WHERE profile_id=NEW.profile_id),0)
                OR NEW.balance<>COALESCE((SELECT balance FROM ledger WHERE profile_id=NEW.profile_id ORDER BY sequence DESC LIMIT 1),0)+NEW.delta
              BEGIN SELECT RAISE(ABORT,'unbalanced_ledger'); END;
            CREATE TRIGGER IF NOT EXISTS receipt_no_update BEFORE UPDATE ON receipts BEGIN SELECT RAISE(ABORT,'immutable_receipt'); END;
            CREATE TRIGGER IF NOT EXISTS receipt_no_delete BEFORE DELETE ON receipts BEGIN SELECT RAISE(ABORT,'immutable_receipt'); END;
            CREATE TRIGGER IF NOT EXISTS realm_identity_immutable BEFORE UPDATE ON realm
              WHEN OLD.realm_id<>NEW.realm_id OR OLD.kind<>NEW.kind BEGIN SELECT RAISE(ABORT,'immutable_realm'); END;
            PRAGMA user_version=1;
            """);
    }
    private void Initialize(string root)
    {
        string legacy = Path.Combine(root, "realm.json"), sourceHash = "", backup = "";
        RealmDocument state;
        if (File.Exists(legacy))
        {
            if (RealmKind == "online") throw new InvalidDataException("offline_migration_forbidden");
            byte[] bytes = File.ReadAllBytes(legacy);
            state = RealmStore.Deserialize(System.Text.Encoding.UTF8.GetString(bytes));
            RealmStore.Validate(state); sourceHash = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
            backup = "realm.v1.migration-" + sourceHash + ".json";
            string backupPath = Path.Combine(root, backup);
            if (!File.Exists(backupPath))
            {
                using var stream = new FileStream(backupPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
                stream.Write(bytes); stream.Flush(true);
            }
            if (!CryptographicOperations.FixedTimeEquals(SHA256.HashData(File.ReadAllBytes(backupPath)), SHA256.HashData(bytes)))
                throw new InvalidDataException("migration_backup_mismatch");
            if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(backupPath, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        }
        else state = new RealmDocument();
        RealmStore.UpgradeLegacy(state, RealmKind, DateTimeOffset.UtcNow.ToUnixTimeSeconds()); state.Revision = 0;
        using var transaction = connection.BeginTransaction(deferred: false);
        WriteProjection(state, null, transaction);
        Command(transaction, "INSERT INTO realm VALUES(1,$id,$kind,$revision,$json)", ("$id", state.RealmId), ("$kind", state.RealmKind),
            ("$revision", state.Revision), ("$json", JsonSerializer.Serialize(state)));
        if (sourceHash.Length > 0)
            Command(transaction, "INSERT INTO migrations VALUES($hash,$backup,$utc,$count,$credits)", ("$hash", sourceHash), ("$backup", backup),
                ("$utc", DateTimeOffset.UtcNow.ToString("O")), ("$count", state.Profiles.Count), ("$credits", state.Profiles.Sum(profile => (long)profile.Credits)));
        transaction.Commit(); current = state;
    }
    public RealmDocument Load() => RealmStore.Deserialize(JsonSerializer.Serialize(current));
    public void Save(RealmDocument next)
    {
        ObjectDisposedException.ThrowIf(disposed, this); RealmStore.Validate(next);
        if (next.RealmKind != RealmKind || next.RealmId != current.RealmId || next.Revision != current.Revision + 1)
            throw new InvalidDataException("database_revision_mismatch");
        using var transaction = connection.BeginTransaction(deferred: false);
        WriteProjection(next, current, transaction);
        int count = Command(transaction, "UPDATE realm SET revision=$revision,state_json=$json WHERE singleton=1 AND revision=$previous",
            ("$revision", next.Revision), ("$json", JsonSerializer.Serialize(next)), ("$previous", current.Revision));
        if (count != 1) throw new InvalidDataException("database_revision_conflict");
        beforeCommit?.Invoke(); transaction.Commit(); current = LoadClone(next);
    }
    private static RealmDocument LoadClone(RealmDocument state) => RealmStore.Deserialize(JsonSerializer.Serialize(state));
    private void WriteProjection(RealmDocument state, RealmDocument? previous, SqliteTransaction transaction)
    {
        if (previous != null && previous.Profiles.Any(old => !state.Profiles.Any(profile => profile.Id == old.Id)))
            throw new InvalidDataException("profile_deletion_not_supported");
        foreach (var profile in state.Profiles)
        {
            var old = previous?.Profiles.SingleOrDefault(item => item.Id == profile.Id);
            if (old != null && JsonSerializer.Serialize(old) == JsonSerializer.Serialize(profile)) continue;
            var career = profile.Career;
            Command(transaction, """
                INSERT INTO profiles VALUES($id,$username,$credits,$bike,$level,$mask,$done,$revision)
                ON CONFLICT(id) DO UPDATE SET username=excluded.username,credits=excluded.credits,selected_bike=excluded.selected_bike,
                level_index=excluded.level_index,qualification_mask=excluded.qualification_mask,completed=excluded.completed,revision=excluded.revision
                """, ("$id", profile.Id), ("$username", career.Username.Length == 0 ? DBNull.Value : career.Username), ("$credits", profile.Credits),
                ("$bike", career.SelectedBikeId), ("$level", career.LevelIndex), ("$mask", career.QualificationMask), ("$done", career.CampaignComplete ? 1 : 0), ("$revision", career.Revision));
            Command(transaction, "DELETE FROM bikes WHERE profile_id=$id", ("$id", profile.Id));
            foreach (var bike in career.Bikes) Command(transaction, "INSERT INTO bikes VALUES($id,$bike,$condition)", ("$id", profile.Id), ("$bike", bike.BikeId), ("$condition", bike.Condition));
            int oldCount = old?.Career.Ledger.Count ?? 0;
            if (career.Ledger.Count < oldCount || (old != null && !career.Ledger.Take(oldCount).Select(item => JsonSerializer.Serialize(item)).SequenceEqual(old.Career.Ledger.Select(item => JsonSerializer.Serialize(item)))))
                throw new InvalidDataException("immutable_ledger");
            for (int i = oldCount; i < career.Ledger.Count; i++)
            {
                var entry = career.Ledger[i];
                Command(transaction, "INSERT INTO ledger VALUES($id,$sequence,$transaction,$reason,$bike,$delta,$balance,$utc)",
                    ("$id", profile.Id), ("$sequence", i), ("$transaction", entry.TransactionId), ("$reason", entry.Reason), ("$bike", entry.BikeId),
                    ("$delta", entry.Delta), ("$balance", entry.Balance), ("$utc", entry.CreatedUtc));
            }
            int receiptCount = old?.Career.Receipts.Count ?? 0;
            if (career.Receipts.Count < receiptCount || (old != null && !career.Receipts.Take(receiptCount).Select(item => JsonSerializer.Serialize(item)).SequenceEqual(old.Career.Receipts.Select(item => JsonSerializer.Serialize(item)))))
                throw new InvalidDataException("immutable_receipt");
            foreach (var receipt in career.Receipts.Skip(receiptCount)) Command(transaction,
                "INSERT INTO receipts VALUES($id,$transaction,$fingerprint,$ok,$code)", ("$id", profile.Id), ("$transaction", receipt.TransactionId),
                ("$fingerprint", receipt.Fingerprint), ("$ok", receipt.Ok ? 1 : 0), ("$code", receipt.Code));
            Command(transaction, "DELETE FROM sessions WHERE profile_id=$id", ("$id", profile.Id));
            foreach (var session in career.Sessions) Command(transaction, "INSERT INTO sessions VALUES($hash,$id,$expires)",
                ("$hash", session.CapabilityHash), ("$id", profile.Id), ("$expires", session.ExpiresUnixSeconds));
        }
        Command(transaction, "DELETE FROM reservations");
        foreach (var reservation in state.Reservations) Command(transaction, "INSERT INTO reservations VALUES($id,$match)", ("$id", reservation.ProfileId), ("$match", reservation.Match));
        var auditIds = state.SecurityAudit.Select(entry => entry.Id).ToHashSet(StringComparer.Ordinal);
        foreach (var removed in previous?.SecurityAudit.Where(entry => !auditIds.Contains(entry.Id)) ?? [])
            Command(transaction, "DELETE FROM security_audit WHERE id=$id", ("$id", removed.Id));
        var previousIds = previous?.SecurityAudit.Select(entry => entry.Id).ToHashSet(StringComparer.Ordinal) ?? [];
        foreach (var entry in state.SecurityAudit.Where(entry => !previousIds.Contains(entry.Id)))
            Command(transaction, "INSERT INTO security_audit VALUES($id,$utc,$profile,$operation,$code)", ("$id", entry.Id), ("$utc", entry.CreatedUtc),
                ("$profile", entry.ProfileId), ("$operation", entry.Operation), ("$code", entry.Code));
    }
    private void ValidateProjection(RealmDocument state)
    {
        using var check = connection.CreateCommand(); check.CommandText = "PRAGMA quick_check";
        if ((string?)check.ExecuteScalar() != "ok") throw new InvalidDataException("database_integrity_failed");
        using var foreign = connection.CreateCommand(); foreign.CommandText = "PRAGMA foreign_key_check";
        using (var reader = foreign.ExecuteReader()) if (reader.Read()) throw new InvalidDataException("database_foreign_key_failed");
        using var identity = connection.CreateCommand(); identity.CommandText = "SELECT realm_id,kind,revision FROM realm WHERE singleton=1";
        using (var reader = identity.ExecuteReader())
            if (!reader.Read() || reader.GetString(0) != state.RealmId || reader.GetString(1) != state.RealmKind || reader.GetInt64(2) != state.Revision)
                throw new InvalidDataException("database_identity_mismatch");
        using var counts = connection.CreateCommand(); counts.CommandText = "SELECT (SELECT count(*) FROM profiles),(SELECT count(*) FROM ledger),(SELECT count(*) FROM receipts),(SELECT count(*) FROM sessions)";
        using (var reader = counts.ExecuteReader())
        {
            reader.Read();
            if (reader.GetInt64(0) != state.Profiles.Count || reader.GetInt64(1) != state.Profiles.Sum(profile => (long)profile.Career.Ledger.Count) ||
                reader.GetInt64(2) != state.Profiles.Sum(profile => (long)profile.Career.Receipts.Count) || reader.GetInt64(3) != state.Profiles.Sum(profile => (long)profile.Career.Sessions.Count))
                throw new InvalidDataException("database_projection_mismatch");
        }
        foreach (var profile in state.Profiles)
        {
            using var query = connection.CreateCommand(); query.CommandText = "SELECT credits,selected_bike,(SELECT COALESCE(sum(delta),0) FROM ledger WHERE profile_id=$id),username,level_index,qualification_mask,completed,revision FROM profiles WHERE id=$id";
            query.Parameters.AddWithValue("$id", profile.Id);
            using var reader = query.ExecuteReader();
            if (!reader.Read() || reader.GetInt32(0) != profile.Credits || reader.GetString(1) != profile.Career.SelectedBikeId || reader.GetInt64(2) != profile.Credits ||
                (reader.IsDBNull(3) ? "" : reader.GetString(3)) != profile.Career.Username || reader.GetInt32(4) != profile.Career.LevelIndex ||
                reader.GetInt32(5) != profile.Career.QualificationMask || reader.GetBoolean(6) != profile.Career.CampaignComplete || reader.GetInt64(7) != profile.Career.Revision)
                throw new InvalidDataException("database_wallet_mismatch");
            reader.Close();
            using var ledger = connection.CreateCommand(); ledger.CommandText = "SELECT transaction_id,reason,bike_id,delta,balance,created_utc,sequence FROM ledger WHERE profile_id=$id ORDER BY sequence";
            ledger.Parameters.AddWithValue("$id", profile.Id);
            using (var rows = ledger.ExecuteReader())
            {
                int sequence = 0;
                foreach (var entry in profile.Career.Ledger)
                    if (!rows.Read() || rows.GetString(0) != entry.TransactionId || rows.GetString(1) != entry.Reason || rows.GetString(2) != entry.BikeId ||
                        rows.GetInt32(3) != entry.Delta || rows.GetInt32(4) != entry.Balance || rows.GetString(5) != entry.CreatedUtc || rows.GetInt32(6) != sequence++)
                        throw new InvalidDataException("database_ledger_mismatch");
                if (rows.Read()) throw new InvalidDataException("database_ledger_mismatch");
            }
            using var bikes = connection.CreateCommand(); bikes.CommandText = "SELECT bike_id,condition FROM bikes WHERE profile_id=$id ORDER BY bike_id";
            bikes.Parameters.AddWithValue("$id", profile.Id);
            using (var rows = bikes.ExecuteReader())
            {
                foreach (var bike in profile.Career.Bikes.OrderBy(item => item.BikeId, StringComparer.Ordinal))
                    if (!rows.Read() || rows.GetString(0) != bike.BikeId || rows.GetInt32(1) != bike.Condition) throw new InvalidDataException("database_inventory_mismatch");
                if (rows.Read()) throw new InvalidDataException("database_inventory_mismatch");
            }
            using var receipts = connection.CreateCommand(); receipts.CommandText = "SELECT transaction_id,fingerprint,ok,code FROM receipts WHERE profile_id=$id ORDER BY transaction_id";
            receipts.Parameters.AddWithValue("$id", profile.Id);
            using (var rows = receipts.ExecuteReader())
            {
                foreach (var receipt in profile.Career.Receipts.OrderBy(item => item.TransactionId, StringComparer.Ordinal))
                    if (!rows.Read() || rows.GetString(0) != receipt.TransactionId || rows.GetString(1) != receipt.Fingerprint || rows.GetBoolean(2) != receipt.Ok || rows.GetString(3) != receipt.Code)
                        throw new InvalidDataException("database_receipt_mismatch");
                if (rows.Read()) throw new InvalidDataException("database_receipt_mismatch");
            }
            using var sessions = connection.CreateCommand(); sessions.CommandText = "SELECT capability_hash,expires_unix FROM sessions WHERE profile_id=$id ORDER BY capability_hash";
            sessions.Parameters.AddWithValue("$id", profile.Id);
            using (var rows = sessions.ExecuteReader())
            {
                foreach (var session in profile.Career.Sessions.OrderBy(item => item.CapabilityHash, StringComparer.Ordinal))
                    if (!rows.Read() || rows.GetString(0) != session.CapabilityHash || rows.GetInt64(1) != session.ExpiresUnixSeconds)
                        throw new InvalidDataException("database_session_mismatch");
                if (rows.Read()) throw new InvalidDataException("database_session_mismatch");
            }
        }
        using var reservations = connection.CreateCommand(); reservations.CommandText = "SELECT profile_id,match_number FROM reservations ORDER BY profile_id";
        using (var rows = reservations.ExecuteReader())
        {
            foreach (var reservation in state.Reservations.OrderBy(item => item.ProfileId, StringComparer.Ordinal))
                if (!rows.Read() || rows.GetString(0) != reservation.ProfileId || rows.GetInt64(1) != reservation.Match)
                    throw new InvalidDataException("database_reservation_mismatch");
            if (rows.Read()) throw new InvalidDataException("database_reservation_mismatch");
        }
        using var audit = connection.CreateCommand(); audit.CommandText = "SELECT id,created_utc,profile_id,operation,code FROM security_audit ORDER BY id";
        using (var rows = audit.ExecuteReader())
        {
            foreach (var entry in state.SecurityAudit.OrderBy(item => item.Id, StringComparer.Ordinal))
                if (!rows.Read() || rows.GetString(0) != entry.Id || rows.GetString(1) != entry.CreatedUtc || rows.GetString(2) != entry.ProfileId ||
                    rows.GetString(3) != entry.Operation || rows.GetString(4) != entry.Code)
                    throw new InvalidDataException("database_security_audit_mismatch");
            if (rows.Read()) throw new InvalidDataException("database_security_audit_mismatch");
        }
    }
    private int Command(SqliteTransaction transaction, string sql, params (string Name, object Value)[] parameters)
    {
        using var command = connection.CreateCommand(); command.Transaction = transaction; command.CommandText = sql;
        foreach (var (name, value) in parameters) command.Parameters.AddWithValue(name, value);
        return command.ExecuteNonQuery();
    }
    private void Execute(string sql) { using var command = connection.CreateCommand(); command.CommandText = sql; command.ExecuteNonQuery(); }
    public void Dispose()
    {
        if (disposed) return; disposed = true;
        connection.Dispose(); lease.Dispose();
    }
}
