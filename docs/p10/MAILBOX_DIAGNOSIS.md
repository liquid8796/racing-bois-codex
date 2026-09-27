# Unexpected multiplayer close: mailbox notification race

The first requested 8-hour local run [failed after485seconds](network/20260926T175547Z/run.json) while starting its next rematch. It completed5rematches and3planned resumes, but every participant showed more connection attempts than the planned breaks explained. Invalid snapshots, persistence failures and dropped server ticks were all zero. This run lacked a detailed event timeline, so its sole cause cannot be reconstructed conclusively.

Twelve source-bound simulation/client/server rematches with six planned disconnects [passed under a synthetic zero-delay transport](diagnosis/20260926T1832-pure-rematch-bound.json). A separate real-socket diagnostic candidate adds bounded sanitized command, epoch, room readiness, snapshot age and message-rate traces while retaining the original gameplay, retry and timeout behavior. It is under `tools/p10/ProtocolSoakNext`; its launcher is `tools/p10/run-network-diagnostic.py`. This preserves the original harness used by P09's completed30-minute run.

## Confirmed defect

`PeerMailbox` combines a reliable FIFO and one replaceable latest snapshot, with a semaphore used as a notification. A legal interleaving left an extra semaphore notification:

| Step | Actual operation |
| --- | --- |
| 1 | Snapshot A is present and the semaphore has one notification. |
| 2 | Reader consumes the notification, then waits to take the mailbox gate. |
| 3 | Producer replaces A with snapshot B and posts a notification while the reader is waiting. |
| 4 | Reader takes B. The producer's extra notification remains. |
| 5 | The next read consumes that notification, finds an empty open mailbox, and previously returned null. |

The real `MultiplayerEndpoint` sender treats null as end-of-stream, closes that healthy socket, and the service's ordinary disconnect policy can cancel a countdown. Thus the mailbox bug provides a concrete, reproducible mechanism for unexpected reconnects and cancelled starts.

The [pre-fix reproduction](diagnosis/mailbox-before-20260926T1838.json) uses the actual mailbox class and two real threads. It holds the private gate only to schedule the legal ordering deterministically; it does not patch production state. The second read returned null without any close request: `spuriousTermination=true`, resultFAIL.

## Fix and validation

`PeerMailbox.Read` now repeats its wait when a notification arrives but the queue is empty and still open. An intentional close continues to return null after pending reliable controls drain. Queue sizes, snapshot replacement, FIFO fairness, rate limits, timeouts and gameplay rules are preserved.

The [same reproduction after the fix](diagnosis/mailbox-after-20260926T1839.json) waits correctly, accepts the next snapshot and terminates only following an explicit close. Fixed source SHA256:

`1e231c52e99febd2f06354ae6d9a807de41db3d9510ebe86b3498e70a2b1a16e`

The concurrency case is now a permanent part of `tools/p10/run-regression.py`. [All214groups passed](regression/20260926T184121Z/receipt.json) at a stable source snapshot. [Eleven real HTTPS/WSS career checks passed](career/20260926T184132Z/run.json) against newly published isolated hosts after the fix.

The new 8-hour wall-clock run uses the fixed server and `ProtocolSoakNext` tracing. Its supervisor metadata is `_local/p10/soak8h-fixed-20260926T184316Z/supervisor.json`; stdout identifies the actual timestamped `docs/p10/network` receipt. It started around01:43Bangkok on2026-09-27, so it cannot establish eight-hour completion before approximately09:43. RUNNING is not PASS. The previous failure and all earlier receipts remain intact. Any new failure remains a release blocker until investigated.

P09's prior release c30-minute PASS stays bound to its original source and binary. The mailbox fix requires a new deployed backend revision and fresh online checks before current-release acceptance. No claim is made that a successful .NET soak proves Unity rendering, physical LAN, Windows10 hardware or exact concept fidelity.
