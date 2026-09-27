# Racing Bois P07 — persistent career

Version 0.7.0 adds host-persisted profiles, accounts, garage/shop, wallet ledger,
campaign state and public/private lobbies to the P06 Canyon Run slice. All 15
catalog entries currently share the P06 motorcycle art and handling. Four route
environments remain locked until P08. Local practice is separate from the host
career and does not award online/host money.

## Windows and offline LAN

Extract the whole package. `launch-local.bat` serves only this machine;
`launch-lan.bat` serves the LAN and retains the P05 URL/QR helper. Keep the host
running while friends play. No runtime download is needed after extraction.
LAN profile/garage/campaign work over the host's HTTP/WS address without Internet.
Account passwords and recovery operations require trusted HTTPS. Do not reuse a
real account password on a LAN host. No launcher alters certificate trust or
firewall rules. Read `README-P05.md` for detailed LAN and QR operation.

Linux ARM64 launchers are `./launch-local.sh` and `./launch-lan.sh`. The Windows
QR helper is not provided for Linux. See the delivery receipt for whether this
particular artifact was executed natively or only checked statically.

## Data and upgrades

Use one stable private `DataRoot` outside `web`, for example
`RacingBois.Server.Host.exe --WebRoot web --DataRoot D:\RacingBoisData\MyLAN`.
The default package launchers use the adjacent `data` directory. Never publish
or share the data directory, database, WAL, backups, profile credentials or keys.
Keep it separate from immutable package files when replacing a release.

The first P07 open migrates a P05 `realm.json` in that directory to SQLite,
retaining realm identity, profile capabilities and exact credits. It writes a
hash-identified backup before committing migration; the original JSON is left
unchanged. P06 must not reopen that directory after P07 has begun updating the
SQLite database: the old JSON is a migration source, not a current save.

For a full backup or restore, gracefully stop the host, wait for its process to
exit, and copy the entire private data directory. Restore into a separate empty
private directory and run its native host with that DataRoot. Never copy just
the main SQLite file while a host can still have WAL transactions. The career
export/import UI is a validated same-realm/profile save operation, not a portable
account migration or a replacement for a whole-realm backup.

RealmKind is immutable: `offline` for LAN and `online` for a separate authority.
Use a distinct DataRoot for online; `--RealmKind online` requires HTTPS for
player APIs. An offline export cannot import into online. Public OCI deployment,
reverse-proxy configuration and regional acceptance belong to P09.

## Accounts and transactions

Connect a persistent profile, then open Garage. Purchases/trades/repairs use
server prices and a durable transaction ID. After a network interruption use
the displayed retry action so the original intent can be recovered. A profile
cannot reserve two races or alter its garage while a match is active.

Register an account name/password over trusted HTTPS to recover that profile
on another browser. Save the one-time recovery code shown after registration;
it is not emailed or stored in browser preferences. Recovery rotates credentials;
lost recovery output can be replaced after login with the current password.
Logout/revoke also invalidate existing race leases. Guest races and local
practice do not silently become an online wallet.

The browser's previously saved profile capability expires; account login or a
retained recovery code is needed for account recovery. Keep realm backups for
unregistered local profiles. Support operators cannot retrieve plaintext
passwords or recovery codes from the database.

Package verification does not establish physical two-PC offline LAN, global
Internet latency, production capacity or final human art/audio approval.
