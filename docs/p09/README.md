# P09 — OCI staging, verified operations

Updated 2026-09-27 (Asia/Bangkok). This is **backend staging**, not a P08 content acceptance or P10 Windows release.

**Current verified state:** release **`p09-20260927-f`**, multiplayer protocol **6**, was independently checked at **2026-09-27 15:59:49 UTC / 22:59:49 Bangkok**. The [read-only audit](readiness/20260927T155938Z.json) verifies all **1,986 deployed files**, the running executable, loopback listener and private data modes. The public `/ready` returned 200 with protocol 6; eight private/legacy routes returned 404. The existing monitor reported no issues, and its latest report and hourly encrypted-backup receipt were fresh. No service was restarted, deployed or load-tested by this audit.

All **68 current backend/shared runtime source files** still match f's runtime source SHA-256 `194d60c159d8978a8520d17df1c900cae09e2614d4b1f620c89b9a5bbcf54c24`. The packaged client/test inventory differs in **10 paths** (six additions, four edits); these are recorded separately. The historical **148 ARM groups** cover f's packaged sources and do not claim to cover those later client/test changes. See [release f evidence](releases/f/DEPLOYMENT_PLAN.md).

| Latest scoped evidence | Result and boundary |
|---|---|
| [f ARM validation](releases/f/arm-validation.json) | 148 groups PASS across six native ARM suites, bound to f's original runtime/test manifests |
| [f WAN capacity](releases/f/capacity.json) | 1,800.269 seconds, eight clients, 21 race cycles, 14 planned reconnects and two storms; zero persistence-failure, dropped-tick and restart deltas; one Windows network origin to Frankfurt |
| [Actual Unity Mono WSS](../p10/native-wss/README.md) | Final 96.594-second player specimen passed one planned resume and acknowledged leave/logout; full rendered gameplay and hardware acceptance remain open |
| [Completed eight-hour socket soak](../p10/network/20260927T003037Z/run.json) | 28,800.058 seconds, eight peers, 359 race cycles, 238 planned reconnects and 47 storms; operational gate PASS, with one dropped catch-up tick and raw correction up to 5.489338 m; this local socket harness is separate from the WAN measurement and a Unity player soak |

The readiness audit is a timestamped observation, not a promise about future uptime. Its cumulative idle-inclusive tick histogram is not a new workload-capacity measurement. Earlier release c/d/e evidence below remains historical and has not been relabelled as f.

The deployed endpoint is **`https://racing-bois.158.180.59.36.sslip.io`**, with native multiplayer at **`wss://racing-bois.158.180.59.36.sslip.io/multiplayer`**. The temporary name uses the public sslip.io DNS service; it is not an owned Racing Bois domain. Ordinary Windows/Python certificate validation succeeds without a custom CA or bypass. The observed certificate is Let's Encrypt YE2, TLS 1.3, valid through 2026-12-25. Caddy manages renewal; the private monitor checks remaining validity.

## Deployed boundary

- Target verified over the exact authorized SSH route: `ubuntu@158.180.59.36`, existing `jarvis_oci_ed25519` key. Host `jarvis01`, `aarch64`, OCI `VM.Standard.A1.Flex`, region `eu-frankfurt-1`, four logical CPUs, approximately 23.4 GiB RAM and 82 GiB free disk at preflight.
- Existing Caddy 2.11.4, PostgreSQL/Mongo and unrelated applications remain in place. Only `/etc/caddy/conf.d/racing-bois.caddy` was added for this host name. Combined configuration was validated before reload; existing main/upstream file hashes and the prior site's HTTP 200 response were preserved. No firewall, paid service, new VM or unrelated application changes were made. No Jarvis MCP was used.
- Service `racing-bois-staging`, private system user of the same name, loopback `127.0.0.1:18080`, online realm under `/var/lib/racing-bois-staging/realm` (0700, database 0600). No database is served by the asset origin.
- Resource limits: 1.5 CPU equivalents, memory high 1 GiB / hard 1.5 GiB, 128 tasks, 8,192 open files. Read-only system/application files, private temporary directory, no additional capabilities. These limits protect the shared VM; they are not a capacity guarantee.
- Historical initial validated release `p09-20260927-c`, source SHA-256 **`fbd8d0b623d9faabd097b23824b33bfead07399c1a2f1097a8ffd29453dea7dc`**. Package [receipt](p09-20260927-c-package.json). The source list includes all backend/shared definitions, simulation, protocol and mapping inputs; a separate test-source list covers test fixtures. No Git cleanliness assumption is used. Current f details are linked above.
- The current SQLite WAL/FULL adapter remains the single writer. The previously documented 1,024-profile/eight-room bounds are implementation limits, not measured production capacity. PostgreSQL was not installed or substituted for this game.

## Historical c operations and recovery evidence

| Evidence | Verified result |
|---|---|
| [Host policy](host-policy-tests.json) | 8 checks: proxy trust is opt-in, exact loopback, one hop, symmetric forwarding headers; direct LAN remains independent; spoofed forwarded host/IP/scheme are rejected appropriately |
| [Native ARM persistence](arm64-persistence-c.json) | 26/26, including real SQLite, concurrent commerce, process-crash durability and restore |
| [Native ARM multiplayer](arm64-multiplayer-c.json) | 32/32 application/authority checks |
| [Native ARM gameplay](arm64-gameplay-c.json) | 31/31, including deterministic replay and allocation checks; not client frame/GPU performance |
| [Live Internet operations](live-ops.json) | Trusted HTTPS, private route rejection, registration, server-priced trade 1,000→248, transaction replay/conflict, realm boundary, origin/input rejection, restart, exact backup/restore and login on the restored server; the receipt records its exact executed check count |
| [Release switch/rollback](activation-rollback.jsonl) | c→b→c, readiness after each switch, same persistent realm. c was active at this historical drill's end. b contains the superseded strict-codec implementation; it is not a recommended future release target |
| [90-second WSS run](../p10/network/20260926T175627Z/probe.json) | Eight Windows .NET clients through the public Internet, one reconnect, ten malformed-protocol cases rejected; production multiplayer session code linked by the harness |
| [Failed-start automatic rollback](failed-start-rollback.json) | A deliberately failing startup on empty staging automatically returned to c in 6.31 seconds; readiness and durable identity/balance/ledger/receipt summaries preserved |
| [Asset origin](asset-origin.json) | Public immutable hash path, exact SHA-256, byte-range HTTP 206 and one-year immutable cache. The object is a clearly labelled synthetic probe; no rejected/unaccepted P08 assets were published |
| [Off-VM encrypted copy](off-vm-backup.json), [local restore](off-vm-local-restore.json) | Encrypted archive copied to the user PC, key protected by Windows DPAPI CurrentUser, real GPG decryption, exact SQLite state/hash and production Windows storage-adapter validation |
| [Deployment verification](deployment-verification.json), [Windows recovery ACLs](recovery-acl.json) | All 1,253 deployed files match the release manifest, root-owned with no group/other write; listener is loopback-only; private realm/key/backup modes and user/SYSTEM-only recovery ACLs checked |
| [NuGet advisory receipt](nuget-audit-receipt.json) | Current host graph and six transitive packages audited; configured feeds returned no known vulnerable packages. This is not a universal security guarantee |

The [30-minute eight-client WSS run](../p10/network/20260926T175901Z/run.json) completed **PASS**, with 21 race cycles, 14 intentional reconnects, two reconnect storms and no source drift. [Capacity receipt](capacity.json): 109,853 server tick samples in the before/after window, p95 bucket upper bound 0.5 ms / p99 1 ms, zero additional slow ticks, dropped catch-up ticks or persistence failures. The sample window includes about 30 seconds of setup/cleanup around the 1,800.26-second client run. A [timestamped Caddy route reload](soak-maintenance-event.json) occurred during the run; clients recovered, and the game process was not restarted.

The private observer covered 22.95 minutes of that run with 43 samples: average CPU 0.152 of one core, maximum cgroup memory 78.5 MiB, no automatic game-service restarts. Observed memory rose from 66.9 to 78.1 MiB during that window, so this is **not proof of absence of a long-term leak**. Mean application RTT across the eight clients was 225.8–231.0 ms; the highest whole-run average download was 56,340 bytes/s. These are one Windows-origin/single-room measurements, not multi-region player feel or Unity rendering performance.

Portability/configuration failures found by the actual drills were fixed: the persistence crash-test launcher supports a self-contained ARM executable without `dotnet` installed; backup staging/final files share a filesystem for atomic rename inside systemd isolation; the local GPG wrapper uses proper MSYS paths and restores close SQLite connections before cleanup. Native gameplay reporting requires its exact source-hash fixtures and positional output argument. Deployed file modes are explicitly normalized to root-owned 0644/0755 because a Windows-authored archive can carry 0666 permissions. Public backend routing is now an allowlist, covering the trailing-slash aliases that the first exact health matcher missed. Initial failures are retained as evidence where applicable.

## Regional reachability

[Three Globalping probes](globalping-http.json) reached `/ready` with HTTP 200 and authorized TLS 1.3:

| Probe | TCP connect | TLS handshake | Entire request | Important context |
|---|---:|---:|---:|---|
| Singapore, SG | 150 ms | 158 ms | 470 ms | Southeast Asian HTTP probe |
| Falkenstein, DE | 6 ms | 11 ms | 930 ms | DNS lookup accounted for 906 ms |
| Buffalo, US | 92 ms | 112 ms | 381 ms | North American HTTP probe |

These are individual public readiness measurements, **not multiplayer RTT, player-perceived latency or regional Unity client acceptance**. Only `/ready` and its public host name were submitted to Globalping; no credentials, source files, private paths or tokens were sent. The Windows eight-client run observed approximately 223–238 ms mean application RTT for the first two sampled clients, which demonstrates why one Frankfurt VM cannot promise LAN-like feel worldwide. See the full client measurements rather than extrapolating from these two values.

## Remaining gates

- Full rendered Unity Windows gameplay against this endpoint remains open after acceptable P08 content. The actual Mono WSS specimen above verifies its transport/session scope; it does not accept the full game.
- Real player machines from SEA/EU/NA, physical offline LAN, target hardware/input coverage and a sustained rendered Unity player soak remain open. The completed eight-hour socket soak is retained as its own operational evidence.
- No full account-population/sustained-commerce or multi-room saturation claim has been made. The shared host was tested with bounded workloads, not destructive exhaustion.
- Full art/content publication awaits P08's concept fidelity and content gates. The backend's source/content fingerprint must be republished whenever those definitions change.
- The current domain is temporary. A branded owned domain and external notification destination have not been supplied. Monitoring currently writes private reports/journald; it does not send email or chat alerts.
- Earlier failed local restore attempts left private plaintext QA restore files. Automatic approval review rejected their cleanup with “blocked by policy”; no equivalent deletion was retried. [Exact retained paths and classification](cleanup-status.json). Successful final-drill temporary files were removed, but **all cleanup is not complete**.

Implementation and operator procedures: [OPERATIONS.md](OPERATIONS.md). Sources: [Microsoft forwarded-header guidance](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/proxy-load-balancer?view=aspnetcore-10.0), [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [Globalping API specification](https://github.com/jsdelivr/globalping/blob/master/public/v1/spec.yaml). Public IP certificates are now an alternative supported by [Let's Encrypt](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability); this deployment chose an isolated host name to avoid replacing the existing shared IP site's TLS/routing configuration.
