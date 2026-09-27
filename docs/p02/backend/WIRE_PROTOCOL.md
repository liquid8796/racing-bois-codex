# P02 wire contract v1

Endpoint: `/ws` on the same origin as the Unity Web build. `ws://127.0.0.1:7777/ws` is the loopback default; `wss://localhost:7778/ws` is available when `--EnableTls true` and a trusted HTTPS certificate are configured. HTTPS pages must use WSS. Configurable `AllowedOrigins` is a comma-separated exact origin list; the default browser policy is same-origin. Missing Origin is allowed for native probes.

Public fields, lower camel case, UTF-8 JSON text. No polymorphic type names or reflection registry. Server requires every specified client field, rejects duplicates and unknown fields, enforces 2,048 bytes per message, depth 8 and a 5-second handshake. A per-connection token bucket refills at 90 messages/second with a bounded burst capacity of 180. This allows delayed valid 60 Hz input to arrive in a batch while rejecting sustained flooding. Malformed/binary/oversized/rate-exceeded messages close the session. This is a research host, not Internet production authentication or complete abuse mitigation.

## Handshake

Client sends before any input:

```json
{"kind":"hello","protocolVersion":1,"simulationRulesVersion":1,"contentHash":"p02-foundation-v1"}
```

All versions must match. The development `contentHash` is an explicit compatibility identifier, not a cryptographic asset manifest. The match has eight slots. IDs are assigned by the authority and owned by the connection:

```json
{"kind":"welcome","protocolVersion":1,"simulationRulesVersion":1,"contentHash":"p02-foundation-v1","playerId":"p1","tickRate":60,"snapshotRate":20,"maxPlayers":8}
```

`version_mismatch` or `match_full` is sent as an error and the connection closes. IDs have session lifetime only. Reconnect/persistent identity/account authentication/lobby selection belong to P05/P07.

## Inputs

```json
{"kind":"input","protocolVersion":1,"playerId":"p1","sequence":1,"throttle":1,"brake":0,"steer":0.25}
```

Sequence starts at 1, increases per connection and cannot jump by more than 10,000. Throttle/brake are finite `[0,1]`; steer is finite `[-1,1]`. Server verifies player ownership. No speed, position, health, damage or reward claim is accepted. Commands are quantized to permille, queued to the single match owner and applied at a simulation tick. Multiple accepted commands before a tick use the latest intent. `ackSequence` is the latest accepted intent sequence, not a count of physics substeps.

The simulation runs 60 Hz, snapshots 20 Hz, normal client input 30 Hz. Missing fresh input for 30 ticks (0.5 seconds) returns to coasting. No client wall time drives simulation. The simple `PeriodicTimer` loop does not run unbounded catch-up after a stalled host; overload policy/clock drift/catch-up are P05 work and must be measured before public deployment.

## Snapshots and rejection

```json
{"kind":"snapshot","protocolVersion":1,"tick":120,"ackSequence":59,"playerId":"p1","entities":[{"id":"p1","s":24.2,"d":1.5,"speed":24}]}
```

`s` is longitudinal meters, `d` is signed lateral meters, `speed` is meters/second. Internal simulation uses integer millimeters and integration remainders; wire floats are display/correction values, not the complete exact simulation state. Server snapshot entities are ordered by ordinal ID. Snapshots are authoritative; clients may display/interpolate/predict but must reconcile to authority. State is not persistent across server restart.

```json
{"kind":"error","protocolVersion":1,"code":"not_owner","message":"Input rejected by authority.","sequence":8}
```

Input rejection codes: `protocol_mismatch`, `not_owner`, `invalid_sequence`, `input_out_of_range`. Rejected input never mutates accepted sequence or rider state. The next snapshot corrects the client. Outgoing queue is bounded (four frames, oldest dropped for slow readers); diagnostic errors are best effort. Send timeout is five seconds. Ingress queue is bounded at 256 and drained at most 256 commands per tick; overflow closes the offending socket. Receiver teardown enqueues leave, freeing the slot.

## Serialization fixture

`WireMessages.cs` is shared verbatim through the embedded Unity package and linked .NET project. Native JSON roundtrip is tested in `RacingBois.Foundation.Tests`; Unity stripped Web must deserialize the same fields independently. Unknown server fields should not be used to infer final gameplay features.
