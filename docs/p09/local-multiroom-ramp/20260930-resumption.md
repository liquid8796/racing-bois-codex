# Local multiroom evidence resumed on 2026-09-30

The paced eight-room run had already finished successfully on 2026-09-28. Its existing verifier was executed once on 2026-09-30 against the original receipts and retained private binaries. `20260928T021818Z/verification.json` passes: eight raw probe reports, 171 current source files and 60 published binary files match their bindings. An independent source-inventory membership check also found exactly 171 files, with no added or missing inputs.

| Original run | Terminal result | Observed overlap |
| --- | --- | --- |
| `../local-multiroom/20260928T021243Z` | PASS, two rooms and 16 clients | 56.2114459 seconds, 3,373 ticks |
| `../local-multiroom/20260928T021416Z` | FAIL, `room_probe_failed` | Eight rooms launched together; seven reports ended with `client_session_failed`, and the remaining probe was stopped before producing its report |
| `20260928T021818Z` | PASS, eight rooms and 64 clients, launched at 25-second intervals | 175.0108585 seconds, 88 full-occupancy observations, 10,500 ticks |

The eight-room overlap histogram has p50/p95/p99 upper bounds of 0.25/2/4 ms. During that observed window, slow ticks, dropped catch-up ticks and persistence failures each changed by zero. The whole run includes four slow ticks. Maximum **sampled** server private memory was 64,823,296 bytes (61.8203 MiB). Every ramp probe finished normally with exit code 0, recorded real race progress and at least one reconnect, and recorded zero invalid snapshots. These are synthetic socket clients on the shared Windows authoring workstation.

The failed burst is retained. `../local-multiroom/handshake-limit-20260928.json` independently records the existing admission boundary on a fresh host with the same bound server binaries: the first 30 non-upgrade requests return HTTP 400 at the WebSocket check, and request 31 returns HTTP 429 after 0.3027078 seconds. Production `Program.cs` configures 30 handshake requests per minute per IP and queue length zero. This confirms a local admission limit and explains why simultaneous admission must be treated separately from occupied-room simulation. The failed probes report `client_session_failed`; their receipts do not record individual handshake HTTP responses, so the specific response for each failed client cannot be reconstructed.

The original supervisors hold their own `subprocess.Popen` objects and stop only those children in `finally`. Terminal receipts account for all owned children. The servers were intentionally terminated after the probes; their exit code 1 is recorded as supervisor termination. A current command-line process inspection found no matching local multiroom supervisor, published server or probe. No PID from old metadata was killed, and no new backend, load run or admission diagnostic was started during resumption.

Original run, probe, supervisor and diagnostic bytes remain unchanged. The two-room verifier and its 17-control receipt still match their recorded script hashes. All three original runs' 171 bound source hashes and 47 server plus 13 probe binaries also still match. The new JSON resumption report binds the evidence and scripts used for this review.

## Static verifier review

The verifier checks raw probe hashes, current recorded source hashes, complete binary trees, child exit receipts, elapsed time, per-client progress/queue/snapshot conditions and histogram calculations. Three additional assertions are useful for future hardening:

- The loopback scope is currently checked through `externalEndpointUsed`; the endpoint itself is not independently parsed and restricted to loopback.
- Samples are required to keep one offline realm, but the verifier does not explicitly link that identity to both boundary health snapshots or require zero rooms and sessions at those boundaries.
- The main verifier checks all recorded source hashes but does not independently enumerate current inventory membership. The resumption check performed that enumeration separately.

These are static review findings, not observed failures of this run. The original endpoint is `ws://127.0.0.1:56661/multiplayer`, both boundary snapshots have zero rooms and sessions in the same offline realm, and current inventory membership is unchanged. Verifier implementation was preserved in this bounded closeout.

This evidence covers a short paced loopback workload. It does not accept OCI capacity, geographic gameplay, a physical two-computer LAN session, Unity rendering, eight-hour soak, asset fidelity or P09/P10 release completion. The deferred 600-second foreground measurement remains open.

Exact ramp bindings: run `22ff2830965f0138eeeb4a20c9a039e1dba6be11aa76ec52957d76c1be6b0cc5`, verifier `ebdccf38c3edf338a3ebc03b031d3608a8caa3dd893f3ca9487ce8a418c12c7b`, fresh verification receipt `d11d4dcca0c01b9ca6e41afb3cee0194064cd5cb3064b94fe8d4bbc29119761a`.
