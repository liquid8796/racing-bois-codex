# Racing Bois — P07 accounts and progression

Updated 2026-09-22. Release **0.7.0**, final compiled runtime `3cac900`,
packaging verifier `d5a4e93`. Implementation, local Web/browser acceptance and
Windows/ARM64 distribution packaging are complete. The broader human, physical
network and production deployment gates below remain open. Earlier development
probe failures are retained separately from final release evidence.

## Delivered behavior

- The host uses a private SQLite realm through an infrastructure adapter. WAL,
  full synchronous transactions, foreign keys and database constraints protect
  wallet, inventory, campaign, ledger, receipts, sessions and match reservations.
  Startup compares every normalized projection against the aggregate and rejects
  corruption without resetting data. Ledger and receipt prefixes are immutable.
- Existing P05 offline JSON can migrate once with a verified byte-for-byte
  backup, preserving IDs, credentials and balances. Migration does not grant
  another starting wallet. Tests use generated fixtures; the existing user
  `_local/p05-main-data` has not been migrated by P07 validation.
- Persistent profiles start with 1,000 credits and a healthy Spark 450. Account
  registration upgrades a profile, login restores it, and one-time recovery
  codes replace an email recovery dependency. Capabilities expire after 30 days;
  logout, logout-all, recovery and recovery-code rotation revoke the appropriate
  credentials and fence live race sockets/resume attempts. Password operations
  require HTTPS; passwords, capabilities and recovery codes are absent from
  gameplay telemetry and security-audit records.
- Purchases, trade-ins, repairs, equipment, rewards, fines and damage are
  authoritative. Retrying an uncertain transaction preserves its UUID and
  cannot pay twice; a new intent must use a new ID. Concurrent requests cannot
  overspend. Match reservations prevent a second race or garage mutation from
  changing a racing profile. Start also rechecks eligibility after asynchronous
  reservation before applying the selected bike.
- If every owned bike is wrecked and the wallet cannot repair the cheapest
  owned bike, an explicitly confirmed `restartCareer` resets garage/campaign
  to a healthy starter and **zero credits**. It retains identity, account, ledger
  and receipts. This is an atomic, idempotent game-over reset, not a recurring
  currency grant. It is unavailable during a reserved match.
- Offline export/import uses signed checkpoints bound to the same realm,
  profile, revision and generation. It rejects tampering, foreign ownership,
  replay and rollback of settled transactions. It is not a portable account
  backup. Online and offline realm kinds are immutable and cannot exchange
  economy data. Whole-host backup/restore uses a safely closed database.

Implementation detail and policy: [persistence](p07/PERSISTENCE.md),
[economy evidence and decisions](p07/ECONOMY_RULES.md),
[implementation plan](p07/IMPLEMENTATION_PLAN.md).

## Client, lobby and content scope

The **GARAGE / HỒ SƠ** panel is accessible from the menu and lobby and contains
garage, shop, campaign, ledger and account views. It uses P06's graphite/amber
design, immutable application readmodels, keyboard focus, loading states,
actionable errors and transaction confirmations. It never changes wallet or
ownership before server acknowledgement. Expired anonymous credentials can be
explicitly forgotten for the selected endpoint after disconnect; account login
and recovery remain available. New sessions refresh the current career level,
while guests use level 1.

Public/private rooms support code/link invitations. `?room=ABC123` only prefills
a validated code; it does not connect or join automatically. A private room is
excluded from the public list and remains joinable by its invite. Campaign room
selection is restricted to the profile's current level.

There are **15 catalog SKUs and a 5-level × 5-route campaign data model**.
All bikes currently share the P06 motorcycle art and handling; the shop states
this explicitly. **Only Canyon Run is playable.** The other four routes remain
locked for P08. Catalog entries, level slots and variants do not establish
15 distinct production models or 25 completed tracks. This phase creates no
new 3D assets; the existing concept-first rule continues to apply to future art.

UI flows and boundaries: [P07 UI](p07/UI.md).

## Verified native and application tests

| Suite | Passing checks | Evidence |
| --- | ---: | --- |
| SQLite, account, migration, transactions and recovery | 26 | [Persistence](p07/persistence-tests.json) |
| Career client authority, identity, retry and immutable projection | 19 | [P07 client](p07/client-validation.json) |
| Multiplayer, private rooms, reservations and live-session revocation | 30 | [Multiplayer integration](p07/multiplayer-integration.json) |
| Existing multiplayer client behavior | 32 | [Client regressions](p07/client-regressions.json) |
| Foundation, protocol and dependency boundaries | 18 | [Foundation](p07/foundation-regressions.json) |
| Existing race/session integration | 14 | [Race integration](p07/race-regressions.json) |
| Catalog, prices and campaign rules | 11 | [Economy rules](p07/economy-rules-validation.json) |
| Existing gameplay, AI, combat and cross-runtime golden | 31 | [Gameplay regressions](p07/gameplay-regressions.json) |

Persistence tests include concurrent spending/replay, injected commit failure,
actual child-process termination before/after commit, byte-preserving migration,
offline/online separation, signed-checkpoint rejection, expired/revoked sessions,
safe audit contents, projection corruption, immutable receipts and closed-database
restore. These are bounded local fixtures, not production load or OCI recovery
drills. Read each report for its source binding and test scope.

The [final packaged-host probe](p07/career-live-validation.json) passed
**11/11 groups over 46 real HTTP requests**, with **46/46 exact positive
Content-Length headers**, plus real ClientWebSocket profile/bootstrap/revocation
flows. Separate offline/online QA realms used normal OS TLS verification.
Earlier dev1/dev2 reports remain historical candidate evidence. The premature
WebSocket-close race found in dev1 was fixed and final normal close frames were
verified; a broken socket was not treated as success.

## Final delivery and browser acceptance

- [Unity build](p07/unity/build.json): `Build/Web-p07-v4`, 21,592,410 bytes,
  release IL2CPP/gzip, 164.77 seconds, zero errors/warnings; direct Unity output.
- [Browser QA](p07/BROWSER_VALIDATION.md): real trade 1,000 → 248 credits,
  one −752 ledger entry, readable dates/signs, reload preserving Ember/248,
  campaign/private-room creation, unlisted invite/link/Enter join, two clients
  racing over WSS and condition 100 → 49 persisted after leaving. Account forms,
  long-list layout and 1080p HUD were inspected; captured console errors/warnings
  were empty. Password/recovery execution is covered by the separate real API
  probe, not a browser credential-entry claim. All testing used one physical PC.
- [Packages and SHA-256](p07/backend/DELIVERY.md): Windows ZIP 70,845,697 bytes,
  ARM64 tar 67,233,694 bytes. Native Windows SQLite rollback, both exact Web
  payloads and every archive file hash pass. ARM ELF and executable permissions
  pass; native ARM execution remains unverified.
- [HTTPS demo](https://localhost:7888/) and [HTTP demo](http://127.0.0.1:7887/)
  run the final packaged executable on loopback with a new private QA realm.
  Separate online QA uses 7987/7988. Existing preview processes and P05 data were
  not replaced. The standard local-session record now identifies the final demo.

The verifier recipe was updated after the runtime was built to support separate
loopback ports and distinguish SQLite libraries from private database files.
It verifies that no runtime/build input changed from `3cac900`, binds its own
commit/hash separately, and requires the exact Unity receipt. These recipe-only
changes did not modify the compiled game, server or Web payload.

## Gates carried forward

P01 still has reverse/parity gaps. [P05](P05_STATUS.md) still requires two physical
LAN machines with WAN disconnected and cold caches, plus clients on separate
Internet networks. Remote crash-transition presentation has a measured 15.897 m
observer outlier and its network budget remains open; P07 does not claim these
are fixed.

[P06](P06_STATUS.md) still requires final human art/audio/feel review, novice-user
usability, a physical gamepad, lower-end hardware and a sustained browser
performance run. Its approximately 60 FPS measurements are 60-second Editor
samples on one reference laptop, not P07 browser performance evidence.

The user currently has one physical PC and no public domain. No OCI deployment,
public DNS/firewall change, global region matchmaking or cross-region latency
claim is part of this delivery. Native ARM64 execution, operational capacity,
online backup/restore drills and public HTTPS/WSS remain P09 gates. Complete
originally authored content remains P08.
