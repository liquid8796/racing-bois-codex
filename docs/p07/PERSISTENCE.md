# P07 durable accounts and economy

The production host injects `SqliteRealmStateStore` into `RealmStore`; `CareerService` is the application command boundary. `Server.Domain` contains persisted career value objects. SQLite is isolated behind the application `IRealmStateStore` port. The old `RealmStore(string directory)` constructor remains the P05 JSON compatibility adapter for existing test fixtures. Production does not select that adapter.

`RealmStore` serializes writes, copies the current aggregate, validates the candidate, commits it, then publishes the new immutable snapshot. The 60 Hz match owner reads that snapshot. Account hashing and SQLite writes execute away from the simulation owner. The existing bounded `RealmPersistence` worker handles match/profile persistence; HTTP career requests share the same aggregate lock.

## Storage and durability

- `realm.sqlite3`: WAL, `synchronous=FULL`, foreign keys, immediate write transactions, five-second busy timeout. A separate process lease rejects a second host for the same realm. The realm kind and identity cannot change through launch configuration or SQL updates.
- Normalized profile, bike, ledger, receipt, session, reservation and security-audit tables accompany the aggregate snapshot. Nonnegative wallet constraints, condition bounds, unique usernames/ownership/transactions, campaign state constraints and foreign keys apply in the database.
- Ledger and transaction receipts are append-only. SQL also rejects an inserted ledger entry whose sequence or running balance does not continue the previous entry. The storage adapter rejects edits to either existing prefix before committing a snapshot.
- Startup validates SQLite integrity, foreign keys and every projected profile, bike, ledger, receipt, session, reservation and security-audit row against the aggregate. Mismatch stops startup; it does not reset the realm.
- A match reserves every persistent participant atomically. Garage mutations, checkpoint import/export and a second match cannot change that profile until settlement/cancellation releases the reservation. Startup fences abandoned match IDs and releases their reservations without paying a result.
- GUID transaction IDs accept `D` or `N` spelling and normalize to `D`. Repeating the same ID and intent returns the recorded outcome; changing the intent returns `transaction_conflict`. Failed commands also bind the ID. Use a new ID for an intentional corrected attempt. Transport/503 retries keep the original ID.
- A result writes wallet delta, condition, campaign qualification, receipt and match fence in one commit. Rewards/fines are recomputed from server definitions and checked against the authority result; the client sends no amount or target profile.

The current implementation is a single-writer realm with at most 1,024 persistent profiles, eight concurrent matches, 100,000 commerce receipts per profile and eight active account capabilities per profile. State snapshots and full ledger history grow with activity; P09 must measure database size, sustained transaction throughput and retention/archival before claiming production scale. A bounded 1,024-event security audit records time, profile ID, operation and result code; it contains no submitted username, password, capability, recovery code or save payload.

## P05 migration

On the first **offline** SQLite open, a valid `realm.json` is migrated transactionally. The original JSON remains untouched. A flushed `realm.v1.migration-<sha256>.json` backup is verified byte-for-byte before the database commit. The `migrations` table records source hash, backup filename, timestamp, profile count and credit total in that same commit. Once a database exists, its state wins; the legacy JSON is never applied again.

Existing realm/profile IDs, capability hashes, credit balances, applied-match fences and retained results survive. Migration creates an opening ledger entry with the exact old balance and supplies the starter bike. It does **not** add the new-profile 1,000-credit grant to migrated profiles. Old capability hashes become 30-day sessions from migration time; bind an account while a migrated capability is still usable.

P05 JSON is an offline realm. Opening it as `RealmKind=online` returns `offline_migration_forbidden`. Copying an existing offline SQLite database and labeling it online also fails. Tests used generated fixture files only; the user's `_local/p05-main-data` was not opened or migrated.

## Account policy

- New persistent profiles receive 1,000 credits and one healthy Spark 450. Ephemeral multiplayer guests do not receive a persistent wallet.
- `register` upgrades the bearer profile without replacing its ID/assets, or creates a new profile if no bearer is supplied. Usernames normalize to lowercase ASCII, 3–24 characters (`a-z`, digits, `_`, `-`). Passwords are 12–128 characters.
- Password hashing uses ASP.NET Core `PasswordHasher`, Identity V3 mode with 210,000 iterations. Rehash-on-success is supported. This follows Microsoft's recommendation to use the framework hasher for account passwords rather than a low-level derivation API. [Microsoft password-hashing guidance](https://learn.microsoft.com/en-us/aspnet/core/security/data-protection/consumer-apis/password-hashing), [implementation](https://source.dot.net/Microsoft.Extensions.Identity.Core/PasswordHasher.cs.html).
- Capability and recovery tokens use 32 random bytes. Only SHA-256 hashes are persisted. Capabilities expire after 30 days; login keeps at most eight active sessions and prunes older/expired ones.
- Registration, recovery and `rotateRecovery` revoke existing capabilities and return a new capability plus a new one-time recovery code. Recovery consumes the old code. `rotateRecovery` requires an authenticated bearer and the current password.
- `logout` revokes the current capability; `logoutAll` revokes every capability. The multiplayer service fences revoked live sockets and resume attempts using snapshot checks.
- If registration's response is lost, the chosen username/password can log in; if recovery's response is lost, the new password can log in. The authenticated `rotateRecovery` operation replaces a lost recovery code. Old plaintext tokens/codes are never stored for replay.
- Credential operations require HTTPS. Online realms require HTTPS/WSS for all authenticated traffic. Offline HTTP/WS remains available for LAN play; that transport does not provide confidentiality against a network observer and is not used for password operations.

The adapter uses Microsoft.Data.Sqlite 10.0.12. `dotnet list ... package --vulnerable --include-transitive` reported no known vulnerabilities from the configured NuGet sources on 2026-09-22. This is a dependency-feed observation, not a penetration-test claim. [Microsoft transaction documentation](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/transactions), [package](https://www.nuget.org/packages/Microsoft.Data.Sqlite/10.0.12).

## Shop and bankruptcy

`buy`, `trade`, `equip` and `repair` use catalog IDs and server quotes. A trade sells the selected non-wrecked bike for half its catalog price and acquires/selects the target bike. Repair charges one tenth of the bike's catalog price and restores condition to 100. Already-owned purchases, unowned equipment and pristine repairs are rejected without a debit.

`restartCareer` is available only when every owned bike is wrecked and credits cannot pay the cheapest owned-bike repair. It is blocked during a match. The atomic operation discards the garage and campaign progress, reduces the remaining wallet to zero through a ledger entry, and supplies one healthy starter bike. It preserves account identity, authentication, the old ledger and all transaction receipts. It grants no new 1,000 credits. The save generation increases, invalidating earlier checkpoints. A repeated transaction cannot supply another bike. The UI requires explicit confirmation before this loss of progress.

There are 15 catalog SKUs and a validated 5-level × 5-route campaign state. P07 does not claim 15 distinct vehicle models or 25 implemented tracks. Only the shipped canyon route is playable; unavailable route IDs cannot earn a result or qualification. Full content remains P08.

## Local checkpoints and host restore

Offline `export` creates an HMAC-signed checkpoint containing only profile-owned economy/campaign data. It includes no account hash, password, token, session or recovery material. Import verifies signature, version, realm, profile ownership, ledger totals, catalog ownership/condition, campaign state, generation and revision. The endpoint and application bound the payload; unknown/duplicate JSON properties are rejected.

A checkpoint belongs to the same offline realm and authenticated profile. It cannot rewind a newer transaction, transfer wealth to another profile or become an online save. A successful import increments generation/revision; the same transaction can be retried, while replay with a different ID fails. This is intentionally a current-checkpoint mechanism, **not a portable account backup or a rollback of settled economic history**. Exports larger than 96 KiB require a host database backup.

For whole-host backup, stop the host, ensure the SQLite connection is closed, then copy the private database and retain its realm identity. The tests restore a database copied after clean close and verify capability, balance and transaction replay. Do not copy only the main `.sqlite3` file while WAL writes are active. A future online backup flow must use SQLite's backup API or a coordinated filesystem snapshot. Backup files and the v1 migration copy contain private authentication hashes and must remain outside the public web root. Unix realm directories are owner-only (0700), database/legacy-backup files 0600; Windows uses the private directory's ACL. OCI backup encryption, retention and restore drills remain P09 work.

## Verification

Run `dotnet run --project src/Tests/RacingBois.Persistence.Tests -- --report docs/p07/persistence-tests.json`.

The suite covers real SQLite constraints, concurrent duplicate and competing purchases, failed-command receipts, server prices, wallet/fine/result idempotency, busy reservations, injected I/O failure, abrupt child-process exits before and after commit, restart fences, byte-preserving migration, offline/online boundaries, account expiry/recovery/revocation, signed-checkpoint tampering/ownership/replay, safe audit contents, projection-corruption rejection and closed-database restore. All fixtures are under `_local/p07-persistence-tests/<random-id>`. Test reports include outcomes and safe error categories; fixture credentials are not printed. HTTP/WSS/browser and whole-server workload checks are reported separately.
