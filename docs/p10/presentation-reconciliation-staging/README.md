# Visible reconciliation diagnosis and isolated renderer candidates

**Production, probe, authority and physics sources remain unchanged. No Unity
Editor or OCI operation was performed for this task. Neither renderer candidate
is visually accepted.** The completed e receipts and firewall-baseline limitation
remain intact.

## What the retained episodes actually show

| Evidence | Maximum correction episode | Speculative-neighbor episode |
|---|---:|---:|
| Equal-target raw prediction correction | 16.258 m | 9.815 m |
| Recorded `SamplePresentation` rider displacement | 4.996 m over 31.40 ms | 10.396 m over 16.22 ms |
| Derived stage rider-root displacement | 5.337 m | 10.087 m |
| Derived stage bike-root displacement | 13.234 m | 6.154 m |
| Actual Unity frame/camera capture | unavailable | unavailable |

The stage-root values include its existing attached/detached offsets and the
actual track geometry. The retained compact presentation pose does not contain
every visual field; these fixtures have zero height/bike height, and neutral
lean is used for controlled orientation tests. They are not screenshots or a
claim about exact on-screen pixels.

The 16.258 m case already had a confirmed Crash event before its checkpoint:
the cached visible S was **2125.688**, while raw prediction S was **2146.830**.
The unchanged production `SamplePresentation` was reconstructed from the full
checkpoint, pending inputs and neighbors. Adding the captured events at the
same clock/tick reproduces a **21.142 m** cap-induced displacement without
changing the gameplay-state digest. This demonstrates a reachable discontinuity;
the preceding native Unity frame was not captured, so it must not be described
as an observed 21.142 m screen jump.

### Classification

- **Predictable missing state/order:** the 9.815 m case is the separately staged
  contact-order defect. Authority lets lower-ID rider1 soft-contact owner3 and
  establish immunity before the traffic pass; the old owner-first predictor
  crashes owner3 on traffic first. See the other agent's
  [contact-order diagnostic](../proxy-transition-staging/contact-order-diagnostic.json).
- **Already-started combat information:** at tick4733, police2001 is already
  Attacking at age7 with a club; impact age is8. Local4 has512 health. Hit+Crash
  arrive at4734. The old predictor does not advance/resolve incoming active
  combat and its proxy defaults omit required metadata. This is not wholly
  unknowable information; the separate protocol6 staging owns that repair.
- **Unavoidable new information still exists:** a new remote input or contact
  after the latest checkpoint cannot generally be known exactly. Fixing the
  demonstrated deterministic gaps does not justify pretending all prediction
  uncertainty is zero.
- **Presentation policy amplifies corrections:** `Snapshot` resets its visual
  offset on any mode change or correction at least4 m. `SamplePresentation`
  can rewind to an event tick. `RaceBootstrap` then passes
  `actorsAlreadyInterpolated=true`, so `RaceStageView.RenderRider` uses blend1
  for actor transforms, while its camera independently damps at7 Hz.

Deleting the four-metre check inside `MultiplayerSession` is not this proposal.
The headless driver steers from `Session.LocalRider`; altering that output would
also change its future input stream and invalidate a purely visual comparison.

## Tested candidates

[35 isolated checks pass](validation.json), with full-checkpoint replay and
production source hashes verified. The tests cover20/30/60/120 Hz, stationary
and declared constant-motion continuations, normal motion, event-cap reversal,
repeat correction, freeze/resume, and explicit reset. Post-event continuation
is a controlled step-response fixture, not invented WAN frame history.

1. **Speed-capped offset:** preserves the first visible transform and consumes
   correction at20 m/s. It takes1.25–1.8 s to settle the retained cases. This
   leaves a long visible alignment error and is retained as a rejected/default-
   unsuitable comparison; [its original result](validation-speed-cap.json) is
   preserved.
2. **Finite-duration offset with camera rebasing:** ordinary target motion is
   unchanged. A large/mode-changing target keeps the previous displayed root,
   then removes only the render offset with zero endpoint slope over120–300 ms.
   The camera's filter coordinate is rebased by the raw target change before
   applying the same local display offset. This prevents the independently
   damped camera from remaining far ahead of a correcting actor.

At60 Hz, the second variant has zero root displacement on the discontinuity
sample and settles the two retained pairs in **0.217/0.200 s**, or **0.300 s**
for the reproduced event cap. Controlled maximum rider steps are approximately
**0.980/1.390/1.810 m** for held targets. It keeps the controlled rider root in
front of the near plane. The cost is real: additional correction speed can
reach **108.6 m/s**, especially visible in the environment. Lower frame rates
produce larger individual steps. These figures demonstrate continuity and a
finite error window, not comfort or imperceptibility.

## Staged integration and remaining gates

Sources are under `tools/p10/presentation-reconciliation-staging`:

- `TimedVisualTransformReconciler.cs`: pure renderer state with no dependency
  on authority, input or read models.
- `UnityVisualTransformReconciler.cs`: Unity/System.Numerics conversion only.
- `UnityStage/RaceStageView.cs`: proposed local actor/camera integration copied
  outside Assets. Mode, health, outcomes, animation inputs and wheel state remain
  the current read-model values. Only visible transforms change.
- `bootstrap-callsite.txt`: one presentation-only argument carries
  `PresentationFrozen` to the renderer. No Application edit is proposed.
- `integration-inputs.json`: exact source/staged hashes.

[Offline Unity API compilation](unity-preflight.json) passes with zero warnings
and errors against installed Unity6000.5.7f1. Nothing was copied into Assets or
run in the Editor.

**Apply deterministic prediction fixes first.** Then evaluate the renderer
candidate with real Game-view captures and motion traces. Record raw correction
and the exposed `LocalVisualCorrectionMeters`, `LocalBikeVisualCorrectionMeters`
and cumulative stage `LocalVisualReconciliationCount` separately. The read-only
`TryGetRenderedActorPose` exists for actual visible local/remote distance checks.
The existing session-level near-combat metric cannot see these transform
offsets and must not be passed off as rendered alignment.

Native acceptance still needs: actual rider/bike vertices and camera/frustum,
terrain/corner/occlusion behavior, HUD/animation consistency, reduced-motion
comfort, and hit/smoke/skid/audio alignment. Built-in stage impacts use the
rendered rider transform, but the external `RaceEffectsView` still consumes
the unmodified read model; that VFX alignment remains unresolved. A temporary
local visual offset also changes visible relationships to remote actors until
settled. Do not promote this candidate solely because numerical tests compile
or pass.

## Promotion decision after protocol6

The candidate remains **rejected for production promotion**. Its 35-case
historical result is preserved as `validation-e-bound.json`; it covers the
protocol5/e sources and must not be described as a current protocol6 replay.
Root applied the deterministic protocol6 fixes independently. A subsequent
pre-impulse-guard 30-minute run still recorded 7 thresholded correction
outliers (8 retained episode records), maximum 4.619 m raw / 5.331 m sampled.
Those residuals have not been validated through this renderer or a native
Game-view capture.

The timed candidate avoids a discontinuity only by temporarily separating
local actor transforms from remote actors and raw read-model VFX. No native
evidence establishes acceptable steering responsiveness, nearby contact
alignment or comfort. It must not conceal uncertain Falling/Wrecked state
transitions or be installed as a prerequisite for the final network soak.

Historical isolated command (do not overwrite its evidence with protocol6
sources; create a fresh source-bound harness/receipt first):

```powershell
dotnet run --project tools/p10/presentation-reconciliation-staging/presentation-tests.csproj -c Release -- docs/p10/presentation-reconciliation-staging/validation.json
```
