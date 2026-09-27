# Correction metric diagnosis — read-only, 2026-09-27

The existing receipts cannot attribute a7–16m maximum to a crash, neighbor approximation, mode transition or implementation defect. They report an aggregate prediction correction, not proof of a visible16m jump and not proof that the correction is harmless.

## What is measured

`MultiplayerSession.Messages.cs:89-119` saves the old predicted rider and its target tick, installs the new authoritative checkpoint and fresh neighbor proxies, removes resolved pending inputs, then replays the remaining input history. If the old and new prediction target ticks match, `LastCorrectionMeters` is the Euclidean difference in longitudinal and lateral position between those two predicted results. Height and separate bike position are excluded. It is not a comparison of the arriving authoritative checkpoint against historical prediction at that checkpoint's tick.

Mode changes are counted. The same-mode and under4m tests only decide whether to smooth the offset over0.12seconds; they do not exclude an observation from the maximum. `SamplePresentation` may additionally freeze beyond the30-tick proxy horizon or cap an unreflected crash/landing at its confirmed event tick. Consequently this metric is also not a direct measurement of the rendered jump.

`ClearRace` resets the session maximum on new races and accepted reconnect welcomes. `Participant.Observe` in `ProtocolSoakNext/Program.cs` retains its own maximum across the whole run, sampled when a new authoritative tick is observed during Racing.

## Concrete receipt evidence

- `docs/p10/network/20260926T190256Z/probe.json`: protocol PASS,1800.304seconds,22cycles,14resumes, sourceStable=true; eight participant correction maxima9.3528–16.5530m. Its diagnostic journal has the2048-entry cap.
- `docs/p10/network/20260926T190006Z/probe.json`: protocol PASS,92.459seconds, one cycle/resume, sourceStable=true; maxima0.3624–11.0676m.
- The soak failure conditions check progress, protocol/queue/size bounds and reconnect identity; they do **not** enforce a correction-quality threshold. Protocol PASS therefore does not accept prediction smoothness.

`DiagnosticJournal` records epochs, message counts, ready/member counts, snapshot age, resolved tick and pending count. It does not retain per-correction position, own/neighbor mode, crash event, replay endpoint or contact context. Its bounded tail cannot reconstruct an older run-wide outlier even if that outlier had been timestamped, which it was not.

## Plausible mechanisms, not an attribution

The soak sends full throttle to all peers and steers them into only two lanes (`RiderId` parity, ±1.8m), without traffic/pedestrian/neighbor avoidance. It steers from `LocalRider`, which may be the smoothed/capped presentation pose. This is a collision-heavy synthetic controller, not a normal human driving sample.

The production predictor uses `RiderPredictor`/`DrivingDynamics`; the older `RoadSpaceSimulation` is used by `FoundationSession`, not this multiplayer path. Prediction replays owner locomotion/contact pose with snapshot neighbors extrapolated from sampled acceleration/lateral/vertical velocities. Proxies have a30-tick lifetime and omit authoritative neighbor inputs/private contact state. Damage/combat authority is not fully simulated. A contact decision can therefore differ and later reconcile.

`DrivingDynamics.Crash` changes the owner speed to one third and starts the falling/recovery sequence. Rider and bike subsequently follow different paths. `Recover` explicitly avoids a timeout teleport; its remount positional snap is limited to one running step. Thus the code does not establish that7–16m is an intentional recovery teleport. Same-mode corrections can still follow different crash ages or collision histories. These mechanisms are candidates to trace, not grounds to dismiss a bug.

## Recommended isolated outlier trace

Keep the running eight-hour probe and all production sources untouched. A separate diagnostic project can link the same immutable production sources and use a diagnostic-only partial class exposing read-only state, with before/after `mpSnapshot` observers in its own transport copy. Capture bounded sanitized windows around corrections≥1m and every new maximum:

- Equal-target-tick decision, old/new authority tick and prediction endpoint, pending input ticks, RTT/lead/snapshot age, race/session epochs as integers.
- Old/new owner position/speed/mode/mode-age/recovery/contact-immunity state and separate bike position; authoritative checkpoint and replay inputs.
- Nearby rider/traffic/pedestrian states, velocity estimates/proxy age, and relevant Crash/Landed/Remounted/contact events before/after.
- Presentation pose, smoothing offset, event cap/frozen flag separately from raw prediction correction.

Bind the trace to source hashes; omit credentials, session tokens, names and raw welcome/control frames. Classify outliers by observed transitions first, and replay suspect checkpoints/inputs offline before deciding whether behavior must change. Do not relax a timeout, modify gameplay or start another load against the live realm as part of this diagnosis.

No server, shared simulation, application, active probe file or running process was changed by this audit. This document makes no visual-quality or release-acceptance claim.
