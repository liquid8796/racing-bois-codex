# P03/P04 gameplay authority and application boundary

Validated on 2026-09-21. This extends the local gameplay slice; Internet matchmaking, production accounts/economy, reconciliation and multi-machine LAN acceptance remain in later phases.

## Runtime contract

- `RaceProtocol` v2 uses `GameplayRules.Version` 2 and content token `p03p04-ribbon-v1`. The preserved P02 fixture still uses its independent v1 contract.
- The existing `/ws` route selects the race world only after a valid `raceHello` handshake. Race traffic uses `raceWelcome`, `raceInput`, and `raceSnapshot`. Old `hello/input/snapshot` traffic remains in a separate fixture world.
- The host owns the simulation at 60 ticks/second and publishes 20 snapshots/second. Eight human slots share the same core with bounded opponents, police, traffic and at most six pedestrians. Inputs provide throttle, brake, steering, left/right attack and kick intent. Clients cannot set position, health, weapon ownership, damage, pedestrian state or results.
- Validation rejects foreign ownership, stale or excessive sequence jumps, nonfinite/out-of-range controls, invalid attack sides, unknown fields, duplicate JSON fields and missing fields. The existing 2 KiB ingress limit, token bucket, bounded command queue and bounded outbound channel remain active.
- Input silence expires after 30 ticks. Empty race rooms stop; their next first join starts a fresh race. Connection IDs are never reused within the host process, although freed rider slots can be reused.
- A nonzero attack press is retained until the next authority tick samples it, even if a neutral packet arrives first. The latest movement remains independent; held attacks still obey the core cooldown. Disconnect and input timeout clear pending action state.
- Events are collected every simulation tick, retained for up to two seconds and capped at 128. Stable event IDs allow effects to deduplicate overlapping 20 Hz snapshots.

## Unity Application API

`RaceSession` owns the pure Application workflow without Unity APIs. `StartLocal(seed, botCount, level)` creates the same `RaceSimulation` used by `AuthoritativeRace`, without opening a socket. `Connect(endpoint)` uses the provided transport/codec ports. `Step(throttle, brake, steer, attackSide, kick)` supplies fixed-tick input in either mode.

`LatestWorld` and `LocalRider` expose immutable values; views cannot mutate simulation state or wire DTOs. Local full-world readmodels publish at 20 Hz, while the local rider struct refreshes at 60 Hz without allocating a full world every tick. Online snapshots are validated completely before committing the world or acknowledging inputs. Missing ACKs are bounded at 120 input ticks; a failure closes the connection.

Online presentation currently interpolates authoritative snapshots. It does not use the P02 linear simulator for prediction. Proper input-timeline reconciliation remains a P05 task.

`LocalCampaign` is temporary in-memory session progress, retained across local restarts. Completed/busted results apply once per monotonically assigned run. Only authored playable course index 0 is credited; custom level practice cannot manufacture campaign progress. The other four course bits and full campaign content remain unavailable until their routes are authored. This is not the online wallet and is not persisted to OCI.

## Evidence

- `final-backend-verification.json` binds the final native checks to a 49-file source manifest and the tested native binaries. The manifest hash was identical before and after execution; every linked receipt carries that source hash. Browser rendering and the final Web build remain separately evidenced.
- `application-integration.json`: fourteen tests of the actual shared authority and linked Unity Application source. Includes 1,800-tick local/core equality, immutable 20 Hz publication, a real authoritative fist hit with recovered Q8 damage (4096 to 3648), authority validation, 20,000 ticks of valid client-bound snapshots, strict JSON parsing and lifecycle/ACK limits. Press/release sampling tests prove exactly one kick, latest movement, latest nonzero side, cooldown repetition, side/range rejection and timeout/disconnect cleanup. Pedestrian tests verify immutable mapping, both walking axes, bounded counts/positions/speed, mode, facing and rejection without corrupting the last valid world. A maximum legal snapshot with 16 riders, 12 traffic vehicles, six pedestrians and 128 events is 28,027 bytes, within the 32,768-byte client budget with 4,741 bytes of headroom.
- `foundation-regression.json`: all 18 P02 regression tests pass, including the original 300-tick integer golden fixture.
- `live-ws.json` and `live-wss.json`: each passes eight checks with eight real loopback socket clients using the actual `RaceSession` source. All receive monotonic snapshots, authoritative pedestrians and the same hit event ID 4; the remote target loses 448 health, the ninth peer is refused, and a client JSON damage injection closes the connection. WSS uses the user's already trusted localhost certificate without a certificate bypass.
- The live probes use ports 17920/17921, which were stopped after validation. They do not establish browser rendering, real Internet latency or independent LAN-machine acceptance.

## Reproduce

```powershell
dotnet run --project src/Tests/RacingBois.RaceIntegration.Tests -- docs/p03p04/backend/application-integration.json
dotnet run --project src/Tests/RacingBois.Foundation.Tests -- docs/p03p04/backend/foundation-regression.json
dotnet run --project src/Server/RacingBois.Server.Host -- --SelfTest
```

For a separately started current host on an unused loopback port:

```powershell
dotnet run --project src/Tests/RacingBois.RaceIntegration.Tests -- --live ws://127.0.0.1:17920/ws docs/p03p04/backend/live-ws.json
dotnet run --project src/Tests/RacingBois.RaceIntegration.Tests -- --live wss://localhost:17921/ws docs/p03p04/backend/live-wss.json
```

Run the WS/WSS scenarios sequentially because each requires all eight human slots in the race world. The probe sorts asynchronously assigned rider identities before targeting a combat pair, so connection completion order cannot change the test's attacker/victim. It steers using observed authoritative separation before attacking, and records that separation; client send counts are not assumed to be simulation ticks.
