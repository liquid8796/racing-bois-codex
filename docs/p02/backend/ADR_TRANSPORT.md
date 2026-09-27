# ADR P02: provisional WSS transport with bounded failure behavior

Status: accepted for the foundation spike; production transport selection remains conditional. Local date: 2026-09-21.

## Decision

Keep authoritative WS/WSS behind the client transport adapter for P02/P03. The same simulation/protocol runs in the native host, Unity Web client and LAN host. This decision does not approve public Internet deployment, final combat latency or a promise of low ping worldwide.

Use 60 Hz simulation and local prediction, 20 Hz snapshots, and explicit version/identity/sequence/range validation. Ingress has a token bucket at 90 messages per second with capacity 180; the existing 256-command queue and bounded per-peer outgoing queue remain unchanged. The bucket is large enough for the tested delayed valid 60 Hz burst and finite enough to reject sustained flooding. It is not permission to submit arbitrary positions or more simulation ticks.

## Evidence and repair

1. The initial 8-peer WS tests passed with application-level delay/jitter/message dropping. Those tests do not emulate TCP retransmission.
2. Native WSS completed handshake, submitted a valid input and received its authoritative ACK with an explicit public development-certificate trust anchor. SHA-256 pin, real TLS hostname matching, validity and server-auth chain validation were required. Deterministic negative controls reject wrong pin, wrong hostname and an empty scoped trust-anchor set, including after the user trusts the certificate in the operating system. Ordinary OS trust is recorded as the current environment rather than assumed to fail. Backend tooling exports no private key and never changes machine trust.
3. A raw TCP forwarding proxy introduced ordered byte-stream delays and stalls using one 8 KiB buffer per direction. Each scenario has one affected rider and one direct observer connection, which independently sees authoritative speed/slot release. This demonstrates consequences of queued ordered delivery; it is not packet-level loss, routing or WAN emulation. Simultaneous backlog release by all eight riders, kernel send-buffer saturation and total process-memory backpressure were not established. The earlier eight-peer application-message impairment test is a distinct test.
4. A 900 ms upstream stall caused the server to coast after stale input. The old fixed one-second rate window disconnected a valid 60 Hz stream after the buffered inputs arrived. `stream-tls-before-burst-fix.json` preserves that reproduction. Replacing the fixed window with the bounded token bucket repaired this case: both 30 Hz and 60 Hz valid streams recover and remain connected after the stall. A sustained valid-shape, owned input flood still disconnects; the measured case sent 276 inputs in about 1.08 seconds.
5. A 2.6-second downstream stall prevented ACK delivery to the actual `FoundationSession` (using a native test adapter). The session reached its 120-pending-input cap and failed closed about two seconds after the last ACK; the authority released the slot. This is deliberate bounded failure, not seamless reconnect or successful continued gameplay.

The latest exact timings and assertions are in [stream-tls-evidence.json](stream-tls-evidence.json); [server-health-after-stream-probe.json](server-health-after-stream-probe.json) captures server workload after the probe. ACK age for the latest newly acknowledged command can look small after a stall because the server samples the newest intent and skips intervening commands. Therefore the probe also records **maximum ACK-progress silence**; do not interpret ACK-age p95 alone as absence of stalls.

The certificate was untrusted during initial preflight; those observations remain in `stream-tls-before-user-trust.json`. The user subsequently trusted the existing localhost development certificate explicitly. A normal browser then loaded the real Unity build over HTTPS/WSS, reached Connected state, received authoritative ACKs, passed the shared fixture and moved after an actual input pulse with no browser errors/warnings. See [browser validation](../BROWSER_VALIDATION.md) for the current direct evidence. Native scoped validation and real-browser acceptance remain separate tests; no certificate validation was bypassed. Public Internet deployment still requires its own trusted hostname certificate and browser verification.

## When WSS remains suitable

Retain it if real-browser driving/combat and reconciliation tests meet explicit gameplay tolerances under the required 30/80/150/250 ms, jitter and packet-loss matrix, and reconnect/tab-suspend/load tests stay within bounded queue and recovery policies. Server capacity, packet loss, client render frame time and per-region latency must each be measured; one cannot stand in for another. No final combat delay/correction tolerance has been accepted in P02.

## When to run the WebRTC alternative

Run the planned authoritative WebRTC DataChannel comparison before P05 sign-off if measured ordered-delivery stalls prevent fresh movement/combat state from meeting the agreed tolerances despite snapshot coalescing, bounded queues and corrected prediction/reconciliation. Compare with the same rules, inputs, peers, hardware, impairment and regions. The browser still connects to an authoritative worker; do not move authority to another player to obtain a lower apparent ping.

The alternative must also prove signaling, ICE/STUN/TURN, UDP-restricted networks, fallback, authentication, bandwidth costs and LAN-offline operation. A different transport does not repair the current approximate input-tick mapping, persistent identity/reconnect, regional distance or application validation. See the existing [architecture](../../TECHNICAL_ARCHITECTURE.md) for those planned boundaries.

## Reproduction

```powershell
.\tools\foundation\test-foundation.bat
.\tools\foundation\test-stream-tls.bat
.\tools\foundation\publish-lan.bat -Runtime win-x64
.\tools\foundation\publish-lan.bat -Runtime linux-arm64
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\foundation\update-publish-evidence.ps1
```

The TLS script binds only separate loopback 179xx ports and uses the specified existing local development certificate. Deterministic scoped-trust negative controls work whether or not the user has trusted that certificate; the ordinary OS-trust result is recorded without modifying the trust store. Published Windows launchers offer local-only or explicit LAN binding. Packaging removes obsolete web payload inside its verified output directory and excludes every `_DoNotShip` path. Offline cold-cache multi-machine play is still a P05 gate.
