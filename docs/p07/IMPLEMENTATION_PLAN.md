# P07 implementation and acceptance

Started 2026-09-22. Builds on the P06 `104ebe7` closeout and compiled `efce749`
release. This phase adds progression and account services; it creates no 3D
assets. Existing P06 art remains original, concept-led production source.

## Delivery scope

1. Shared immutable economy/catalog and five-level/five-route campaign rules,
   separating verified source tables from Racing Bois design choices.
2. Durable SQLite transactions behind an application storage port; schema
   constraints, ledger, inventory, campaign, match reservations and idempotency.
   Legacy P05 JSON migration preserves credits and credentials without editing
   the source document. The preview uses a separate P07 private data directory.
3. Account upgrade/login, expiring credentials, logout/revocation and one-time
   recovery codes. Password operations require HTTPS. No password or recovery
   secret enters browser preferences, gameplay telemetry or logs.
4. Server-priced purchase/trade/repair/equip, race damage/rewards/fines and
   campaign qualification. Racing profiles reserve their configuration until
   settlement; neither a concurrent race nor a shop request can alter it.
5. Public/private lobbies and code/link invitations. Each participant must meet
   the selected level's eligibility. Unfinished P08 routes remain unavailable.
6. Garage/shop/account/campaign/ledger UI using the existing graphite/amber
   design, keyboard focus, loading/error feedback and server-confirmed values.
7. Offline save export/import with validation. Online and offline databases
   have immutable distinct realm kinds; offline money never flows into online.
8. Source-bound tests, real HTTP/WSS probes, Unity build and browser acceptance,
   packaged LAN host and operator documentation.

## Acceptance gates

- Retried transactions and results do not double-credit or double-purchase.
- Concurrent spend cannot make balances negative; transaction IDs are bound to
  the original intent and profile, not just used as a global deduplication flag.
- Database/API failures and restart preserve a valid committed state; abandoned
  in-flight matches do not manufacture rewards.
- Authentication binds access to the caller's profile, with no client target
  profile ID or price/amount field. Revocation also fences existing race sockets
  and resume leases. Recovery codes are consumed and credentials rotated.
- Migration/backup/restore, save validation and offline/online isolation have
  concrete tests. Local practice remains separate from a durable host career.
- Actual Unity/Web UI connects to the API and reflects authoritative ownership,
  wallet and errors. Package hashes and native host startup are checked.

P07 does not claim 15 distinct bike models or handling sets, five finished track
environments, global matchmaking regions or a public OCI service. Those remain
P08/P09 deliverables. Physical multi-machine LAN/WAN gates from P05 and human
art/audio/usability gates from P06 remain explicit.

## Technical references

SQLite connections and transactions belong to the infrastructure adapter; the
60 Hz match owner consumes cached immutable state and asynchronous completions.
Relevant primary documentation: [Microsoft.Data.Sqlite concurrency/errors](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/database-errors)
and [transactions](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/transactions).
Account hashing uses the maintained ASP.NET Core password hasher rather than a
custom password format; see [PasswordHasher source](https://source.dot.net/Microsoft.Extensions.Identity.Core/PasswordHasher.cs.html).

The proposed production PostgreSQL deployment remains an infrastructure decision
for P09. The P07 single-host database is SQLite with explicit constraints and
transactions; the application port keeps the database driver out of gameplay.
