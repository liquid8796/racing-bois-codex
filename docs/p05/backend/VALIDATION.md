# P05 backend validation

The final local verification is [final-verification.json](final-verification.json). Its runtime/harness SHA-256 is `ca338e6b1be5977bc1d4cd8f6cc48e31dccec15a87b5c193218486aaca72b838`. Runtime and test sources were identical before and after execution. The Web-audit PowerShell helper changed independently during validation and is explicitly listed; it was not executed by the network suite.

| Check | Result |
| --- | --- |
| Room/session/timeline/storage/codec/mailbox tests | 25 PASS |
| Actual Unity Application and prediction tests | 32 PASS |
| Preserved foundation regression | 18 PASS |
| Preserved race integration regression | 14 PASS |
| Native WS, eight player connections + five bots | 9 checks PASS |
| Native trusted WSS, same default roster | 9 checks PASS |
| Ordered stream impairment matrix | 8 scenarios PASS |

Both WS and WSS runs used the production `MultiplayerSession` source. A real attack intent produced authoritative hit event 4 and changed the target health from 4096 to 3648, observed by both clients. Forced transport interruption restored the same session/rider; explicit logout was acknowledged. These are instrumented native client connections, not eight human-operated browsers.

Normal link scenarios covered loopback, 80 ms added round-trip delay, 150 ms with ±20 ms jitter per direction, and 250 ms with ±50 ms jitter per direction. Normal scenarios had zero future inputs; the highest-latency case had one late input on one peer and zero on the other. A 900 ms upstream stall intentionally expired 47 inputs per peer. A 2.6 s downstream stall, connection break and visibility suspension resumed without duplicating membership. The proxy delays bounded ordered TCP byte streams; it does not emulate IP packet loss.

The host now uses a fractional Stopwatch schedule. The former rounded timer produced approximately 62–64 ticks/second on this Windows machine. The new clock fixtures produce exactly 600 steps over ten seconds and bound catch-up to six steps. The live matrix produces approximately 720 race ticks over twelve seconds, with zero dropped catch-up ticks. The observed maximum host step was 12.41 ms and no step exceeded the 16.67 ms budget during the recorded run; this is a maximum observation, not a percentile or a capacity guarantee.

For the default eight-player/five-bot roster, observed payload download peaked near 63.3 KB/s per peer and upload near 15.34 KB/s. These slightly exceed the initial 60 KB/s and 15 KB/s targets; TLS/IP overhead is additional. Packets remained below 3.2 KB and the transport memory bounds passed.

Prediction is not presented as perfect under delay. At the highest-latency/jitter setting, maximum own-player correction was approximately 0.695 m and steady relative-position residual approximately 1.175 m. The raw contact-transition relative residual still reached 15.897 m before the observer received an authoritative crash update. The event cutoff bounds further extrapolation once that update arrives; it cannot retroactively remove earlier uncertainty. Overall, steady and contact metrics remain separately visible in the receipts. Final visual/feel acceptance must account for this limitation.

The storage suite verifies process restart, compaction without duplicate credit, exclusive realm ownership, corruption rejection, private data paths, real file-lock write failures and recovery. A separately blocked persistence completion leaves one room waiting for its result while a second room advances at least 297 ticks across 300 owner steps. Success is emitted only after durable commit. Pending profile retries and stale-epoch reservation completions cannot create duplicate identities or alter a replacement request.

No OCI write or deployment was performed. With one physical PC and no public domain, the required two-machine LAN/WAN-off/cold-cache test, two different Internet networks, native ARM64 execution and public regional latency remain unverified. Browser/build/package receipts are separate from this backend report.
