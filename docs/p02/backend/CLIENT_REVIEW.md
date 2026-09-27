# P02 independent client application review

Review scope: `FoundationSession.cs`, `BrowserSocketTransport.cs`, browser `.jslib`, and the shared server ACK contract. The test executable links the actual application source; it does not emulate/reimplement the session and uses no Unity API. A fake transport and public-field JSON codec isolate lifecycle and reconciliation behavior.

The initial run is retained in `client-review-tests-before-fixes.json`: seven backend groups plus nine client groups, eleven passing and five failing. The final `foundation-tests.json` is the current acceptance result after repairs; the historical failure artifact is intentional evidence, not the current status.

Cases exercised include version negotiation/rejection, stale and foreign snapshots, partial input acknowledgement and bounded replay, no-ACK queue limit, fresh identity/sequence after reconnect, late callback after disconnect, idempotent disposal and use after disposal, invalid snapshot atomicity, unsolicited/empty welcome, and exact half-permille rounding (`0.0625 * 1000 = 62.5`).

## Final presentation boundary

`FoundationSession` exposes `LatestWorld`, an immutable Application `WorldReadModel`, instead of a mutable protocol snapshot. Only a fully validated authoritative snapshot is mapped into this readmodel. Tick and acknowledged input sequence are get-only properties; rider values are readonly structs with ID and explicitly named meter/second fields. The rider collection wraps a private copied array and cannot be changed through an `IList` cast.

`RoadStageView` consumes this Application readmodel. Its assembly no longer references Protocol or Simulation. Bootstrap rendering/telemetry reads the same readmodel and drops its unused Protocol assembly reference; its shared-fixture/prediction references remain intentional. Wire format, interpolation, input timing and simulation behavior are unchanged.

The added boundary test mutates the exact decoder-owned wire DTO and its entity array after mapping, attempts mutation through the exposed collection interface, rejects invalid subsequent state, and verifies that a later valid observation does not alter an older retained readmodel. It also checks that the session has no public Protocol-typed property. Together with the token-budget regression, the current native suite has **18 passing groups**. The native stream harness compiles against the same new Application readmodel; Unity compilation/Web rendering remains a separate parent validation.

## Concrete initial findings

1. Disposing a connected session detached callbacks but left it active. Calling `Step` could still enqueue/send, and `Connect` could reopen transport with no subscribed handlers.
2. Incoming welcome was accepted outside the connecting state. A late callback after explicit disconnect could resurrect the session; an empty player ID was accepted.
3. `LatestSnapshot` was assigned before checking own entity and ACK plausibility. An invalid large-tick snapshot could prevent subsequent valid state from applying, and a forged high ACK could drop pending inputs.
4. Client used midpoint-to-even quantization while server used midpoint-away-from-zero. Exact half-permille inputs therefore predicted different acceleration.

Both native and browser adapters already guard old-connection events by socket identity. The browser implementation uses a single socket per page, which is appropriate for one client session but must not be mistaken for a multi-session transport abstraction.

## Prediction semantics retained as a P02 limitation

The authoritative server samples the latest accepted intent each 60 Hz tick. `ackSequence` identifies that accepted intent; it does not prove each sequence caused one simulation step. Multiple inputs arriving between two ticks collapse to the newest input; an unchanged input may be held for many ticks. The client currently predicts one fixed step per local input and replays each unacknowledged local step once on correction.

For this spike, call the client `Step` at 60 Hz (within the sustained 90-message/second ingress budget, which permits bursts of 180). Calling it at 30 Hz while simulation runs at 60 Hz would make local movement and replay run too slowly. Decoupling send frequency from simulation requires local tick history, not merely fewer `Step` calls.

This approach demonstrates server correction but is not complete deterministic reconciliation under jitter or clock drift. P05 needs an explicit client-tick/applied-server-tick timeline and a tested catch-up/replay policy. Exact snapshot reconstruction also needs internal integration remainders; the current `s/d/speed` float display contract discards them. Native/Web golden replay establishes the shared fixture's arithmetic only and does not close the network prediction gate.

Native transport cleanup on natural close, terminal disposal, callback/send backpressure and tab-suspend behavior need integration checks. A fake application transport cannot prove native socket resource lifetimes or browser callback ordering. The real browser test is a separate P02 artifact, and actual WAN/packet-loss/HoL testing remains P05/P09.
