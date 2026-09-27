# Racing Bois staging operations

All paths below belong to Racing Bois. Never stop/change other projects on the shared VM. Production UI, content and Windows release acceptance are outside an operator's backend-health check.

## Layout and recovery identities

| Path/service | Purpose |
|---|---|
| `/srv/racing-bois/releases/<release-id>` | Root-owned immutable published binaries and manifest |
| `/srv/racing-bois/current` | Atomic active-release symlink |
| `/srv/racing-bois/assets/content/<hash>` | Read-only public immutable content origin |
| `/var/lib/racing-bois-staging/realm` | Private live online SQLite database, WAL and exclusive process lease |
| `/var/lib/racing-bois-staging/backup-key` | Private backup encryption passphrase; never print/copy into source or logs |
| `/srv/racing-bois/backups` | Private GPG-encrypted SQLite backup archives and safe latest receipt |
| `/var/lib/racing-bois-staging/restore-drills` | Isolated restored databases for QA, never the live data directory |
| `racing-bois-backup.timer` | Hourly backup plus up to 120 seconds randomized delay |
| `racing-bois-monitor.timer` | Five-minute private health, disk, backup age and trusted-certificate checks |

Database realm identity/type is immutable. Never point an offline LAN database at this online service. Never copy only `realm.sqlite3` while the live WAL is open. Use the online SQLite backup API in `tools/p09/infra/backup.py` or a closed, verified database.

## Publish and activate

1. Run `python tools/p09/package.py <new-lowercase-release-id>` on the development PC. The command publishes self-contained ARM64 server/tests, verifies unchanged source during publish and writes file/archive hashes. Identical runtime files are represented by archive hard links to avoid uploading duplicate runtimes. Use a new ID; overwrite is rejected.
2. Upload the archive and `tools/p09/infra` into a newly created `/tmp/racing-bois-p09.<random>` directory over the exact configured SSH route. Do not use the unrelated `jarvis-oci-02` alias.
3. `sudo bash <stage>/ops/install.sh <release-id> <stage>/release.tar.gz <archive-sha256> <stage>/ops` verifies the archive and every release file, installs only game-specific directories/units and prepares the release. It does not activate it.
4. Run the native ARM tests in an isolated QA working directory. Persistence uses `--report <file>`; multiplayer/gameplay accept the output path as their first argument. `python tools/p09/arm-fixtures.py <release-id>` supplies the exact definitions/simulation source files required by the gameplay report. Test work is CPU/memory capped separately.
5. `sudo bash <stage>/ops/activate.sh <release-id>` takes an exclusive deployment lock, switches the symlink atomically, restarts only `racing-bois-staging`, verifies the actual running executable and waits for `/ready`. It restores the previous target on a failed candidate, including a failed `systemctl restart`. A controlled empty-staging [negative startup drill](failed-start-rollback.json) verified this rollback in 6.31 seconds. Forward-only database migrations require their own compatibility plan; binary rollback is never permission to roll economic history backwards.
6. For the first host setup, `install-proxy.sh` adds only the dedicated game Caddy file, validates the combined config before reload and checks the existing site's status and shared file hashes. Later edits require preserving the previous game site file, validation and a scoped rollback if reload fails.
7. Verify ordinary public HTTPS/WSS, not `curl -k` or custom trust. Public `/health`, `/multiplayer/health`, `/metrics`, `/ws` and database paths must return 404. `/ready` reports only readiness/protocol/content version. Detailed counters are available through SSH at `http://127.0.0.1:18080/health`.

Current certificate renewal belongs to Caddy. Do not install a second process on ports 80/443. The temporary DNS host can later be replaced by a user-owned domain with a new certificate and explicit native runtime-config update.

## Backup and restore drills

`sudo systemctl start racing-bois-backup` makes a consistent live snapshot using SQLite's backup API, verifies integrity/FKs, records database/state SHA-256 and summary counts, encrypts with GPG AES-256, fsyncs and atomically publishes the archive. The latest receipt contains no password/token/account names. `sudo -u racing-bois-staging python3 /srv/racing-bois/ops/restore-drill.py` decrypts only into a fresh private directory and validates exact state. Launch a separate, resource-limited loopback host at 18180 against that directory to validate production startup; disposable QA credentials may be supplied to `validate-restored.py` on stdin for a login check. Never place credentials on the command line or in reports.

Hourly VM backups have an intended snapshot interval of one hour plus scheduling jitter; same-VM archives do not survive total VM/volume loss. Off-VM export is currently an explicit operation, not an automatic replication promise:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/p09/export-recovery.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/p09/verify-local-restore.ps1
```

The export directory `_local/p09-recovery` has inheritance removed and grants only the current Windows identity and SYSTEM. It contains the encrypted archive and `backup-key.dpapi`; the key is wrapped by Windows DPAPI CurrentUser and never saved as plaintext. The restore check uses the Git-distributed GPG executable with a private homedir and passphrase through stdin, authenticates/decrypts the archive, verifies SQLite integrity/state hashes and opens the copy through the production Windows storage adapter. The successful verification removes its plaintext temporary copy.

After complete VM loss, use the preserved encrypted archive and the **same Windows account with its DPAPI master key** to recover the archive/key, prepare the new private server realm directory while the replacement game service is stopped, restore the exact online database and identity, then start a matching release and verify account/receipt/reward continuity. The GPG key must be delivered securely to the replacement VM for future backups. A Windows reinstall/loss of that DPAPI account is a separate failure domain; this is not an independently escrowed recovery key.

Private backups currently accumulate; no automatic retention deletion was enabled. Review archive age/disk use and retain a verified off-VM copy before pruning. The private monitor flags disk free space below 2 GiB or backup age over two hours. This is appropriate for staging; retention/independent key escrow policy needs a deliberate production decision.

## Observability and capacity interpretation

The monitor stores `/var/lib/racing-bois-staging/monitor.json` and emits a short status/issue list to journald. It checks service reachability, persistence-failure counter, histogram p99 bucket upper bound above 12 ms, backup freshness, free disk and trusted TLS certificate age. No external notification destination is configured.

The worker's fixed-size cumulative histogram exposes bucket counts and percentile **upper bounds**, not invented exact percentiles. Compute workload-specific distributions from before/after bucket deltas so idle time does not dilute the result. `tools/p09/observe-soak.py` samples private counters and cgroup memory/CPU while the independent WSS harness runs. Coverage begins at its recorded timestamp; it does not retrospectively measure earlier minutes.

The implemented maximum of eight rooms and 1,024 profiles is a rejection bound, not a measured safe capacity. Current measured traffic is one eight-client room on a shared four-CPU ARM machine with the game capped to 1.5 CPU. Keep that distinction in deployment notes and user-facing claims.

## Known cleanup restriction

Automatic approval review rejected deletion of four earlier failed local-restore artifacts with reason “blocked by policy”. They remain under the private recovery directory; [cleanup-status.json](cleanup-status.json) lists exact paths without contents/keys. No retry through another shell/API was made. An operator may inspect that list and manually remove only the listed failed-attempt plaintext artifacts, retaining the encrypted `.tar.gpg` archive and `backup-key.dpapi`. Do not describe the workspace as entirely cleaned.
