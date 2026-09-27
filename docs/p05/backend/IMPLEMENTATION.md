# P05 server and wire contract

The v3 `/multiplayer` endpoint is separate from the preserved v1/v2 `/ws` fixtures. `MultiplayerMessages.cs` defines the public-field DTOs shared by Unity JsonUtility and System.Text.Json. Remote actor arrays use `NumericRow` objects containing an `int[]`; unsupported jagged JSON containers are not used.

## Rooms and identity

The process accepts at most eight rooms, eight human members per room and 64 logical sessions, with a separate 96-connection handshake/reconnect budget. Up to six opponents can be selected; the shared world retains its own bounded police, traffic and pedestrian populations.

Room commands cover create, code join, ready, start, leave, return to lobby and explicit acknowledged logout. A three-second countdown starts only when every member is connected and ready. New members join only in the lobby. The oldest connected member inherits the lobby role when its host leaves; a countdown is cancelled. The dedicated server remains the race authority when a lobby host leaves during racing.

Resume capabilities are random 256-bit values, kept in memory and never logged or persisted. Disconnect reserves a seat for 30 seconds. Reattachment increments the session epoch and fences old connections and inputs. Each race has an independent epoch. Repeated initial hello requests use a 32-hex nonce bound to the original intent, including while a durable profile write is pending. The nonce cache has a 256-entry budget and keeps revocation tombstones until expiry. Invalid initial ACKs are rejected before profile allocation.

Guest mode creates a temporary identity. Saved local profiles use a separate endpoint/realm capability; only its SHA-256 digest is persisted. A second profile instance cannot occupy two slots in the same room. Explicit logout is acknowledged before the mailbox closes and immediately revokes the lease. Saved-profile capabilities remain usable for a future new session.

## Input and state

The room runs the shared 60 Hz simulation and publishes at 20 Hz. Input controls are integer permille values and specify sequence, exact target tick, room, session epoch and race epoch. The authority accepts a bounded 18-tick future window and a 32-frame queue. Past inputs do not rewind the world. Missing input retains only the last applied analog controls for six ticks, then neutral; a missing frame never repeats an attack.

Simulation deadlines use a monotonic Stopwatch-based fractional clock. The OS timer only wakes the worker; rounding a nominal 16.67 ms timer period must not accelerate the game. Catch-up is bounded at six steps per wake and discarded overload ticks are reported in health telemetry.

A snapshot is stamped after simulation tick S. `resolvedThroughTick` and `lastProcessedSequence` describe processed/expired frames rather than merely received inputs. The exact own-player checkpoint includes integrator remainders, filtered steering, airborne/recovery state and cooldowns. The neutral `NetworkMapping.CheckpointMapper` is shared by server and client, avoiding two different checkpoint conversions.

Remote poses use centimeter units and tenths of degrees. Interest windows are -120/+320 m for riders and -80/+260 m for traffic/pedestrians. Standings remain separate from visual interest. Hard population budgets remain 16 riders, 12 vehicles and six pedestrians. Snapshots exclude the local rider's quantized duplicate and include its exact checkpoint instead.

Lifecycle messages, events, errors and results use a sequenced reliable lane with bounded history. A peer mailbox retains at most 64 reliable messages/64 KiB and one replaceable snapshot. Its sender services a waiting snapshot after at most four reliable messages. Slow readers are disconnected; resume either replays the retained sequence or explicitly resets to a full state. Results can always be reconstructed from the durable ledger. No position, health, damage, inventory or currency claim is accepted as input.

## Local persistence

`--DataRoot` selects a private local realm directory. It must not lie inside public `WebRoot`. The default is `<app directory>/realm-data`; the LAN launcher supplies an explicit stable path. An exclusive process lock prevents a second host from opening the same live realm and invalidating its active matches.

All profile creation, match reservation and result writes pass through `RealmPersistence`, a bounded single-writer queue. Disk operations and `Flush(true)` run outside the 60 Hz owner. Only completed operations are applied by that owner. A finished race stays `resultsPending` until its result is committed; another room continues simulating while storage is slow. Failed saves retry once per second and do not publish success. Countdown cancellation retains a pending durable abort fence and prevents starting another match until it succeeds.

The JSON document atomically commits grants and completed-match ranges together. Result payloads compact to the most recent 256 while the compacted identity ranges continue rejecting duplicate payouts. Startup fences incomplete pre-restart match IDs without granting their uncommitted results. Live rooms and resume leases are intentionally not restored after a process restart. Corrupt data fails closed instead of silently resetting profiles. Atomic process-restart recovery is tested; this does not claim protection against every filesystem or hardware power-loss failure.

## Verification

```powershell
dotnet run --project src/Tests/RacingBois.Multiplayer.Integration.Tests -c Release -- docs/p05/backend/domain-validation.json
dotnet run --project src/Tests/RacingBois.P05Client.Tests -c Release
dotnet run --project src/Server/RacingBois.Server.Host -c Release -- --SelfTest
```

Against an isolated current host, the live probe links the actual Unity Application source:

```powershell
dotnet run --project src/Tests/RacingBois.Multiplayer.LiveProbe -c Release -- ws://127.0.0.1:17950/multiplayer docs/p05/backend/live-ws.json
dotnet run --project src/Tests/RacingBois.Multiplayer.LiveProbe -c Release -- wss://localhost:17951/multiplayer docs/p05/backend/live-wss.json
dotnet run --project src/Tests/RacingBois.Multiplayer.LiveProbe -c Release -- ws://127.0.0.1:17950/multiplayer docs/p05/backend/network-matrix.json matrix
```

The matrix uses bounded ordered TCP delay, jitter, upstream/downstream stalls, connection break and visibility suspension. It reports observed RTT, late/future/missing inputs, correction/residual samples, reconnects, extrapolation and payload bytes. It does not emulate IP packet loss. Steady and contact-transition residuals are distinguished without discarding the overall maximum.

Only one physical PC and no public domain are available. Two physical LAN machines with WAN disconnected/cold caches, two different Internet networks, public deployment and regional latency remain unverified. No OCI deployment or writes are part of this implementation pass.
