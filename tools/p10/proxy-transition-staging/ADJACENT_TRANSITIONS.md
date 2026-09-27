# Deterministic proxy-transition audit

The staged change is deliberately separate from production while the OCIe30minute run and the existing eight-hour run remain active.

| Transition/context | Available state and authority rule | Current proxy behavior | Staged/result |
|---|---|---|---|
| Pedestrian Stumbled→Waiting | Mode + age; recovery exactly at180 before contacts; wait120 | Age never advances; actor remains noncollidable | Shared recovery helper; captured9.135m error reduces to5mm, all other owner-checkpoint fields equal |
| Pedestrian Walking along road→Waiting | Mode + age + observed speed; moves then stops at age300 | Walks indefinitely inside prediction horizon | Shared walking helper; boundary test matches authority |
| Crossing pedestrian reaches shoulder | Position, facing, speed, crossing flag and track width; clamp, reverse facing, wait | Hard clamp±7700 but continues Walking and never reverses | Shared walking helper; exact stop/reversal boundary test matches authority |
| Pedestrian Waiting→Walking | Requires already-chosen private WaitTicks and DesiredWalkingSpeed | Snapshot lacks both; holds waiting | **Not solved or guessed.** Explicit test ensures no fabricated120tick start |
| Newly ended walking/recovery waiting period | New recovery waits120; walking-end wait is at least120/180 | Unknown randomized duration | Safe to hold within the existing30tick horizon; predictor does not draw RNG |
| Remote rider Hit→Riding or attack end | Ages/duration known, but future steering/throttle and incoming hits are not | Linear velocity/acceleration proxies; ages not advanced | Collision-active state remains active; trajectory is an approximation, not exact future input simulation |
| Remote rider Falling/Detached/Running/Remounting | Some public poses/ages known; private bike motion/recovery state incomplete | Non-driving proxies hold | New remount receives90tick collision protection; exact recovery motion is not reconstructed from insufficient data |
| Remote rider airborne landing | Height and estimated vertical velocity available; exact private vertical integrator/impact not in remote snapshot | Approximate gravity/height, no exact landing outcome | Not claimed deterministic from present wire data; incoming authority events/checkpoints remain necessary |
| Remote rider crash/wreck/finish already confirmed by reliable event | Event id, actor and tick are known before a later checkpoint | Presentation caps such trajectories, but prediction proxies may retain old active mode | Separate confirmed-event fencing opportunity; the recorded rider6/rider4 wreck interaction illustrates it |
| Traffic movement | Constant speed, position and dimensions available | Linear progression with reset submillimeter remainder | Correct model within quantization; spawns/despawns depend on global frontier but occur outside immediate collision reach under the current interest margins |

Waiting→Walking is missing **current authoritative state**, rather than inherently unknowable future user input. A complete exact waiting forecast would require transmitting validated remaining wait and desired walking speed (or equivalent immutable forecast metadata), with a deliberate protocol change. It should not assume the default `WaitTicks=120` or default speed1400. A pedestrian recovered in the middle of a lane can later begin walking there, so this gap can still affect contact timing even though Waiting is already collidable.

The minimal staged shared helper preserves authority event ordering and RNG consumption: authority alone emits PedestrianRecovered and chooses randomized wait durations after walking ends. Prediction advances mode age once, applies only known transitions, and emits no authority events or RNG draws. The authority3000tick golden remains `FD320D8BD0D9435E`.

Broader prediction uncertainty must remain distinguished from the confirmed age180 defect. Source/field audits alone do not prove that every remaining correction is benign. The immutable captured replay, boundary controls and baseline-failing/candidate-passing receipts are the evidence for this patch only.
