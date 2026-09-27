# Unity native WSS failure — confirmed frame-context backlog

The first actual Unity Windows Mono WSS specimen failed:14connections in99seconds although only one resume was planned, low driving progress and no logout acknowledgement. Its immutable report is `docs/p10/native-wss/protocol6-20260927-0640.json`. Successful TLS handshakes and zero malformed snapshots do not accept repeated unplanned reconnects.

Read-only journal aggregation for its exact UTC window records11WebSocketException and3OperationCanceledException peer closes, with no ingress-invalid-data or command-failure records. Current server logs do not publish mailbox close reasons; the sanitized inspector does not invent them. The old probe's final `other` close code loses necessary information, so an enhanced allowlisted observer is staged separately. No server policy or timeout was changed.

All four native transport awaits captured the caller's UnitySynchronizationContext. Network I/O and the semaphore continuation therefore depended on future game frames even though application callbacks already have an explicit `Poll` queue.

The unchanged production transport was compiled and run using the installed Unity Mono6.13 console runtime, a real task-owned loopback WebSocket echo server and200-byte messages at60Hz. This isolates the continuation mechanism; it is not a substitute for the actual Unity player or WAN/TLS rerun.

| Transport/context | Sent/received | Maximum outstanding | Maximum echo delay |
| --- | --- | --- | --- |
| Original, no synchronization context |1199/1199|2|34ms|
| Original, frame-pumped context |1199/434|849|17.54s|
| Candidate, no synchronization context |1200/1200|2|35ms|
| Candidate, frame-pumped context |1200/1200|2|36ms|

The candidate adds `ConfigureAwait(false)` to native connect, receive, send-gate and send operations. Unity-facing callbacks still execute only from `Poll`; framing, cancellation/generation checks, queue limits, server behavior and timeouts are unchanged.

A new real-WebSocket regression holds the calling frame context without pumping it while the handshake is deliberately asynchronous. The original transport fails to open; the candidate opens/sends/receives normally without posting any continuation to that frame context. All five existing transport tests still pass. Evidence is `baseline-context-regression.json` and `candidate-context-regression.json`; original failure is retained.

Root approved and applied the two-file transport/regression manifest at2026-09-27 00:00UTC. [Applied source bindings](applied-source-freeze.json) match manifest `f8850f4fe1290cc23e12ace5a34bacf97e8fd4ff95782ce118c6c8d06c6b565a`. [Fresh full regression](../regression/20260927T000044Z/receipt.json) passes253groups with stable source, including the sixth native-transport regression. Actual Unity WSS success, exactly the planned reconnect count and acknowledged cleanup remain mandatory. This reproduction establishes the frame-bound backlog defect; native after-patch observability must verify whether it explains every reconnect in the original run.

The [actual Unity Windows Mono WSS rerun](../native-wss/transport-fix-20260927-0704.json) now passes96.577seconds with exactly2opens/2welcomes,1planned reconnect/resume,0unexpected reconnects and0invalid snapshots. Both leave and logout are acknowledged;1,604authoritative samples and1,301post-resume samples show real progress (maximum692.347m). The [launcher postcheck](../native-wss/transport-fix-20260927-0704.launch.json) confirms source/player/build bindings unchanged and exit0. This closes the native transport failure in the tested scenario, not visual or eight-hour acceptance. The27recorded `race_epoch` responses during race turnover are retained and handled in a [separate contextual audit](../retired-input-staging/README.md).
