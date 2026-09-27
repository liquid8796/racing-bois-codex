# Confirmed remote-immunity defect and narrow fix

Two new task-owned loopback runs reproduced large corrections with unchanged production code, no latency injection and the same eight-peer controller. Both completed180seconds with sourceStable=true: `20260926T203835Z` and `20260926T204559Z`.

The second run's worst recorded case is a deterministic regression fixture:

- Owner rider8, authority tick3755 advancing to3758, equal prediction target3772.
- Raw correction8.512001m; next existing `SamplePresentation` output moves10.285134m over16.69ms. These are application poses, not a measured Unity/GPU frame.
- Neighbor rider4 remounted at3697. Its own server checkpoint at3755 confirms `CollisionUntilTick=3787` (the existing90-tick protection), mode age58. The observing client's proxy instead has `CollisionUntilTick=0`.
- Owner authority retains bikecondition3. The old client prediction invents a high-speed collision, consumes that condition and enters internalWrecked. Replaying with rider4's **observed** protection produces the later corrected checkpoint exactly, across every checkpoint field. Removing rider4 does the same; removing other neighbors does not.

Evidence: `docs/p10/correction-audit/20260926T204559Z/observed-immunity-snapshot.json` and `observed-immunity-replay.json`. The offline test uses unchanged `RiderPredictor`, verifies both original before/after outputs first, then changes only neighbor protection in an isolated prediction instance. The earlier run independently isolates neighbor6 for a7.402976m correction.

## Authority distinction

This is a false local motion/crash prediction, not authority-side damage or an awarded result. `RemoteMotionSampler.WithMotion` already maps speculativeWrecked toFalling and `Make` retains authoritative health/bikecondition/reward/rank. Nevertheless, speculative terminal physics stops local movement and causes the large visible pose correction. Do not change authority damage, outcome rules, collision thresholds, prediction horizon or timeout budgets as a workaround.

## Minimal implementation

1. Append one bounded `collisionProtectionTicksRemaining` integer to each compact remote rider row. Server derives it from the existing `CollisionUntilTick` and snapshot tick; expired protection is0. Current physics emits at most90ticks.
2. Bump multiplayer protocol4→5 because row length and required prediction context change. Keep physics rules/tick rates unchanged.
3. Validate row length27, protection0..90 and checked absolute-expiry construction before committing any client snapshot state. Project immutable prediction context alongside the visual world so legacy/local visual readmodels remain unchanged.
4. Restore the authoritative expiry into each remote `PredictionNeighbors.Riders[i]` checkpoint. `RiderPredictor` already copies it, and `DrivingDynamics.ResolveContacts` already honors it. No collision-physics modification is required.

Tests must cover the captured observed-immunity fixture, expired/one-tick/inclusive-boundary protection, maximum90, negative/91/overflow values, missing/extra row fields, old-protocol rejection and actual server/client snapshots. Preserve the existing authoritative-health presentation rule. After source freeze, repeat independent eight-peer tracing and report remaining correction causes rather than asserting all outliers disappear.

The diagnosis does **not** explain every outlier. Another captured case drops from7.338m to0.248m under observed-immunity replay but is not byte-identical; others remain contact/trajectory disagreements. Retain those traces for subsequent analysis.

Root deliberately superseded the former eight-hour run before authorizing implementation. Its old results remain historical evidence and cannot serve as final acceptance of the repaired protocol. A new soak and OCI/client version alignment follow root's review.
