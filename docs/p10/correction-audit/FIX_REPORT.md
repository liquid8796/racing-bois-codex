# Remote collision-immunity fix — protocol5, 2026-09-27

The confirmed defect was missing **remote collision protection** in client prediction. An actual server snapshot protected neighbor4 until tick3787, while its client proxy used0. This caused a false local wreck and an8.512001m correction. Replaying with the observed protection reproduced the later correct checkpoint exactly. Source traces and counterfactual evidence are in `20260926T204559Z/observed-immunity-snapshot.json` and `observed-immunity-replay.json`.

The fix appends one validated0..90-tick remaining-protection field to each remote rider row and bumps multiplayer protocol4→5. The client projects immutable prediction metadata beside its visual world, then restores the authoritative expiry into the neighbor checkpoint. Existing collision code already honors the field. Physics rules,60Hz tick rate,20Hz snapshot rate, prediction horizon, timeouts, damage authority and outcome authority were not changed.

Production scope is six files: protocol declarations, server snapshot projection, client snapshot projection, immutable `MultiplayerSnapshotReadModel`, session wiring and `PredictionNeighborBuilder`. Unity's Application asmdef and all projects compiling MultiplayerSession include the Application folder/wildcard, so the new class is included. Foundation/desktop-config subset projects do not compile MultiplayerSession and do not require that class.

## Verification on the final source

| Check | Evidence | Result |
|---|---|---|
| Full existing regression | `docs/p10/regression/20260926T212057Z/receipt.json` |218groups PASS, sourceStable=true |
| Captured immunity regression | P05Client group in that run | Exact corrected checkpoint; original bug negative control; authoritative health/bikecondition preserved |
| Boundaries/adversarial input | P05Client group in that run |0/1/90 accepted; negative/91/overflow/old row shape rejected; expiry inclusive; invalid snapshot atomic |
| Actual old-client rejection | Multiplayer.Integration group in that run | Protocol3 and4 rejected without profile/session allocation |
| Fresh HTTPS/WSS career | `docs/p10/career/20260926T212456Z/run.json` |11checks PASS, no skipped checks, normal certificate validation |
| Final short network/fuzz | `docs/p10/network/20260926T212819Z/run.json` |90.06seconds/eight peers PASS,10/10 malformed-frame cases rejected, sourceStable=true |

P08's production-content gate remains pending. These tests do not approve unfinished assets, native visual quality, physical LAN hardware or global performance.

## Remaining corrections are not dismissed

The separate post-fix180second trace `20260926T210407Z` passed protocol checks but retained three outliers and a3.074591m maximum. Exact offline replay verified all three:

- An unconfirmed predicted Falling→Riding transition:3.075m raw correction and3.659m change in the next existing application presentation sample.
- A real authoritative police Hit/Crash:2.776m raw correction and0.896m sampled-pose change.
- A speculative Wrecked→Riding transition:2.325m raw and2.597m sampled-pose change. The old proxy continued rider6 even though riders4/6 were then authoritatively wrecked; this is distinct from the repaired immunity omission.

The earlier post-fix90second fuzz run `docs/p10/network/20260926T211716Z` also recorded a6.671m raw correction on a confirmed police crash (2.802m sampled-pose change) and an internal speculative-wreck episode. The final90second run happened to peak at0.662m. This variability is **not** evidence that the residual visual problem vanished. These are `SamplePresentation` outputs, not a GPU-frame measurement.

## New actual eight-hour run

`docs/p10/network/20260926T213110Z/run.json` and sibling `probe.json` are the live records. Start:2026-09-26 21:31:16UTC; eight-hour threshold:2026-09-27 05:31:16UTC /12:31:16local. Requested28,800seconds and eight peers. At the startup check it was RUNNING with sourceStable=true,10/10fuzz cases passed and `eightHourGate=false`.

Owned supervisorPID33776 launches only its copied loopback serverPID20968 and ProtocolSoakNextPID15344 on port54997. Exact launcher metadata is `_local/p10/immunity-soak-20260926T213110Z/launch.json`. The supervisor cleans up its own process handles. No existing server or OCI process was changed by this restart.

ProtocolSoakNext now links the tested read-only correction observer, recording bounded top64 sanitized outlier windows and existing presentation samples. Both linked diagnostic sources are included in source drift checks. Controller inputs, retries and timeout budgets are unchanged. Runtime/probe source is frozen for the run.

The eight-hour run verifies stability and protocol behavior. It does not accept the remaining motion/visual discrepancies. The deliberately superseded old eight-hour report is historical evidence and must not be reused as acceptance of protocol5. Root owns subsequent OCI/client version alignment; this task made no OCI changes. Apex V8/R2 assets remain frozen and visually unaccepted.
