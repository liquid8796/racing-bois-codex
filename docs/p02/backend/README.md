# P02 server foundation and transport evidence

Implemented on 2026-09-21 local date (JSON evidence timestamps use UTC). This is a bounded transport/simulation spike. No original-game code/assets were copied. No OCI service deployment, firewall mutation, account database or production lobby was implemented here.

## Delivered

- Single-source pure C# embedded package, three `.asmdef` boundaries with no Unity engine reference; linked .NET projects target `netstandard2.1`, C# 9.
- .NET 10 host and application layer; a single owner steps the match, callbacks enqueue validated commands, snapshots provide correction, eight-peer capacity, bounded queues and explicit version/ownership/sequence/range checks.
- 60 Hz integer road-space fixture, 20 Hz snapshots, 30 Hz synthetic inputs. The tick rate matches the chosen P02 budget. Acceleration/braking/steering values are newly authored fixture values and **not original parity**.
- HTTP/WS on loopback; opt-in TLS via standard Kestrel certificate configuration; static Unity Web hosting with WASM/data/JS MIME, Brotli/Gzip encoding, same-origin isolation headers; opt-in LAN bind.
- Self-contained Windows x64 / Linux ARM64 / Linux x64 publishing script; no runtime installation required after publish. Unity build must exist to complete the offline payload.
- Native tests, application impairment harness, no-listener native compatibility `--SelfTest`.
- Independent pure-client lifecycle/reconciliation tests (actual Unity application source linked into native runner), scoped WSS validation with negative controls, and raw ordered-stream delay/stall tests. The buffered-valid-input regression is fixed by a bounded token bucket (90/s refill, capacity 180), with flood rejection retained.

## Commands (repository root)

```powershell
.\tools\foundation\test-foundation.bat
.\tools\foundation\test-stream-tls.bat
.\tools\foundation\start-local.bat
# Local HTTPS/WSS requires an already trusted development certificate:
.\tools\foundation\start-local.bat -EnableTls
# Explicit LAN binding; no firewall rule is changed:
.\tools\foundation\start-local.bat -AllowLan
.\tools\foundation\publish-lan.bat -Runtime win-x64
.\tools\foundation\publish-lan.bat -Runtime linux-arm64
```

Open `http://127.0.0.1:7777/` after Unity creates `Build/Web`; health is `/health`. The Web root can be overridden with `-WebRoot`. Test script starts its own hidden host on 17877, verifies ownership of its process, writes JSON evidence and stops only that process. `.bat` wrappers work with Windows PowerShell 5.1. .NET SDK is pinned to `10.0.301` under `src/global.json`; runtime tested locally is 10.0.9. Source tests use no external test-framework packages so runtime/offline restore has fewer dependencies.

Self-contained runtime compatibility smoke (no port, DB or filesystem writes):

```powershell
dotnet src/Server/RacingBois.Server.Host/bin/Release/net10.0/RacingBois.Server.Host.dll --SelfTest
```

On ARM64 Linux, run the published executable with `--SelfTest`. Windows cross-publish alone is not VM execution evidence. OCI deployment and performance must be tracked in the parent P02 report.

## Measured evidence

See [foundation-tests.json](foundation-tests.json), [transport-evidence.json](transport-evidence.json), [server-health-after-probe.json](server-health-after-probe.json). These are machine-readable observed results, not predicted budgets. The current foundation suite passes **17 groups**, including nine pure-client groups and a token-budget regression. The first successful transport run passed the initial seven native behavioral groups and the three 8-peer scenarios:

| Application impairment | ACK age p95 | Maximum presented snapshot gap |
|---|---:|---:|
| Loopback, no added delay/drop | 63.25 ms | 77.76 ms |
| 150 ms nominal RTT, ±20 ms per direction, 2% message drop per direction | 220.66 ms | 124.59 ms |
| 250 ms nominal RTT, ±40 ms per direction, 5% message drop per direction | 343.90 ms | 189.30 ms |

Eight peers advanced and observed eight entities in all scenarios; snapshots were monotonic. The post-run health recorded 1,562 ticks, zero remaining players, three rejected malicious commands, zero tick workloads exceeding 16.67 ms and maximum measured tick workload 8.7438 ms. Timing varies with machine load; rerunning overwrites JSON evidence and those latest files are authoritative.

The harness preserves FIFO ordering while adding scheduling delay and drops selected complete input/snapshot messages before send/after receive. **This does not emulate TCP packet loss or retransmission, does not measure transport head-of-line blocking, and does not prove Internet latency or browser rendering performance.** Native synthetic clients are separate from the real Unity browser roundtrip gate. WSS probe endpoints use normal certificate validation; no insecure bypass is built in.

## Decisions and open gates

Use WS/WSS as the initial browser-compatible transport spike. Keep the transport behind the client adapter; do not declare it production-final until TCP impairment, tab suspend/reconnect, actual browser correction and multi-region tests meet the gameplay budgets. Evaluate WebRTC/datagram transport if measured stalls fail the P05 criterion. No decision about acceptable combat fairness at 250 ms follows from these transport results.

LAN uses the same server and shared rules. Self-contained publish makes runtime distribution feasible; it does not establish cold-cache browser operation on two machines with WAN physically disabled. That P05 gate includes the full web payload and local profile persistence. LAN progress will remain a separate realm from online economy.

The existing local HTTPS developer certificate was untrusted during initial preflight. The user subsequently trusted it explicitly, and the normal browser now passes the real Unity HTTPS/WSS connection, authoritative input/ACK and shared-fixture checks; see [browser validation](../BROWSER_VALIDATION.md). Backend tooling does not change certificate trust. [Scoped native WSS](stream-tls-evidence.json) separately validates pin, hostname, validity and server-auth chain; deterministic wrong-pin, wrong-hostname and empty-anchor controls remain negative after the user's trust change. Ordinary OS trust is recorded as the current environment, not assumed to fail. See [transport ADR](ADR_TRANSPORT.md) for the ordered-stream measurements, repaired burst rejection, bounded client failure and remaining acceptance gates.

Content schema validation, persistent accounts, authentication, lobby state, combat, AI, native/world physics, production asset manifests, delta/quantized snapshots, lag compensation, tick-clock drift handling, replay/reconnect and crash recovery remain later phases. An empty interface/service hierarchy was deliberately not scaffolded for them. See [wire contract](WIRE_PROTOCOL.md) for exact behavior and limits.
