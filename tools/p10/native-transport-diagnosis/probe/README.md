# Native WSS observer candidate

Staged outside Assets. Install only `NativeWssProbe.cs` and the new
`NativeProbeObservations.cs` into the native probe Runtime folder after review.
Configuration/store copies are unchanged compilation inputs. No transport,
session, server, timing, input or logout behavior is modified.

Report schema2 adds a bounded 64-entry lifecycle ring and fixed-allowlist
counters for transport close codes, received mpError codes, and exact known
Session.Error literals. Unrecognized strings become `other`; raw payloads,
error text, tokens and player/room identities are not stored in observations.
One-second samples include pending/late/future/missing counts. Session
transitions also retain the immediately preceding observed pending count,
including the observation made just before Step may clear pending inputs.

PASS now requires exactly two opened connections, one planned resume open,
one planned reconnect transition, and zero unexpected opens/transitions.
The existing resume identity/slot/room, authoritative progress and cleanup
acknowledgement checks remain. The final success gate checks connection counts
again after cleanup so an extra reconnect cannot slip through between the
driving gate and Finish. There are no relaxed timeouts or tolerances.

An observed transition counts entry into IsReconnecting. Retries while
already reconnecting are not misreported as new state transitions; every
additional successful transport open is counted independently. Attempts that
never open still fail the original bounded handshake/resume deadlines.
mpError counters describe received allowlisted frames, not a claim that each
frame passed session epoch/reliable-sequence checks.

Managed compile against Unity6000.5.7f1 succeeded with zero warnings/errors.
Eight pure diagnostic tests pass in
`docs/p10/native-probe-observations-tests.json`: successful planned resume,
unexpected reconnects before/after it, repeated state events, unknown-string
redaction, actual server codes, bounded history/pre-reconnect counters and
exact literal matching. These tests do not claim a native WSS pass. Existing
failed native reports remain untouched.

```powershell
dotnet build tools/p10/native-transport-diagnosis/probe/RuntimeCompile.csproj --nologo -v:minimal
dotnet run --project tools/p10/native-transport-diagnosis/probe/tests/Tests.csproj -- docs/p10/native-probe-observations-tests.json
```
