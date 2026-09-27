# Separate rider/bike presentation envelopes — staged candidate

**No production or frozen soak source was changed. This is not native visual
acceptance.** The source-hash baseline contains all163 inputs from the running
8-hour test. Root owns later integration and the decision about that run.

The retained f WAN trace has39 measured equal-target correction episodes. Its
largest raw correction remains7.850992m. Root's independent classification finds
authority mode unchanged across all39 pairs;34 change forecast mode and32 have
near-zero difference when neighbors are excluded. This is prediction uncertainty,
not proof that authority teleported or that smoothing repairs gameplay state.

## Candidate behavior

- Two independent XYZ/quaternion envelopes act **only on the local Unity rider
  and bike transforms**. Application, authority, prediction, health, economy,
  outcomes and raw correction values/acceptance thresholds remain unchanged.
  Existing small S/D presentation correction remains in place.
- An attached/detached pose change starts continuity. Ordinary riding moves
  directly. A large target discontinuity also starts continuity, with the rider's
  current/previous speed used to avoid delaying normal motion.
- Five same-Falling episodes exposed a second problem: existing shared S/D
  smoothing already corrected the rider while the bike could still step2.234m
  at20fps. A new **presentation-only revision** increments at the existing
  equal-target raw measurement. A newly observed detached correction of at
  least1m rebases both envelopes once. It is not a widened raw error threshold
  and does not turn every snapshot into a movement delay.
- Initial correction preserves the last displayed pose. A cubic decay removes
  the offset in0.12–0.375s, with an additional translation-correction speed bound
  of40m/s and angular bound16rad/s. Offset length cannot exceed10m; uninterrupted
  correction bursts cannot extend beyond0.6s. Budget excess remains an explicit
  hard reset, not a silently clamped gameplay target or endless visual lag.
- Room/race/session-lease/local-rider changes, pooled-view initialization,
  explicit interpolation reset, large frame gaps, clock rewind and teleports
  clear the old display state. Short freeze holds displayed roots; a long frozen
  resume clears the stale offset. Camera filter coordinates rebase with the
  rider's display offset; it does not independently chase a suddenly rebased
  raw target while the rider stays behind.

The diff changes four existing files: StageView, Bootstrap, Session and
Session.Messages. Session adds only readonly epoch access plus the separate
revision increment/reset. Three new presentation classes isolate the pure
envelope, Unity value conversion and render-lifetime metadata. The new metadata
does not alter wire DTOs/protocol, gameplay rules, masks or backend behavior.
Public display-error/reset diagnostics remain separate from raw correction data.

## Actual isolated evidence

See [verification.json](verification.json), its bound logs and
[the detailed result](verified-validation.json):405 checks pass, including78
exact before/after production predictor replays across all39 retained episodes.
Each replay verifies that SamplePresentation/envelope evaluation leaves the
authoritative checkpoint, prediction, pending inputs, health/condition/reward/
qualification and raw correction counters unchanged.

There are312 controlled response scenarios: all39 presented pose pairs at
20/30/60/120fps, with held or explicitly declared constant-motion continuation.
All start with zero rider/bike root step. Maximum temporary display error is
7.210405m; maximum additional correction speed39.985798m/s; maximum settling time
0.30s in these scenarios. The controlled camera reconstruction keeps at least
6.323906m rider-root depth. These numbers **do not reduce the raw7.850992m error**.

The supplied f trace did not record the new revision field, every rendered
frame, camera state, bike height or lean at each displayed sample. The tests use
its exact equal-target observation to supply one synthetic revision signal,
full center checkpoint values for missing height/lean, and source-bound stage
formulas. Continuations and initial camera pose are declared assumptions.
They are not described as captured Unity frames or full30-minute playback.

Controls cover normal-motion latency, separate instances and XYZ offsets,
duplicate revision suppression, epoch/scope reset, finite data, clock errors,
short/long freeze, teleport and persistent correction bursts. Steady pure-envelope
sampling allocates zero managed heap in the isolated .NET test; this is not a
Unity Mono allocation or FPS benchmark. The full staged Client compiles against
installed Unity6000.5.7f1 APIs with zero warnings/errors.

Historical first-validation retains an incorrectly designed burst fixture that
alternated back to the exact displayed pose, legitimately clearing its error.
The corrected control maintains nonzero repeated displacement and verifies the
burst reset. The earlier401-check candidate is superseded: its metrics exposed
the same-Falling bike miss rather than proving all presentation jumps fixed.

## Tradeoffs and remaining proof

The envelope intentionally permits art to differ temporarily from raw motion by
several metres. Other actors, terrain and externally positioned VFX/audio may
therefore intersect or disagree during that window. Fast catch-up is visible;
a zero first-frame step does not establish comfort, correct collision contact,
natural animation blends or improved combat readability. Burst/teleport resets
can still be abrupt by design and must be logged.

Only the local rider/bike uses this candidate. Remote interpolation, pedestrians
and traffic remain unchanged. Render roots and camera mathematics are tested,
but bone animation, cloth, wheel/contact and external VFX alignment require real
native frames. Further prediction improvements remain a separate task; no raw
acceptance gate is weakened here.

Root should review [the manifest](../../../tools/p10/pose-envelope-staging/candidate-manifest.json)
and [diff](../../../tools/p10/pose-envelope-staging/review.diff), preserve the
current source freeze, then integrate only in an explicit new validation window.
Required next proof is an actual Unity Windows capture with raw targets and
rendered rider/bike/camera positions, correction offsets/reasons, real combat/
fall/remount/reconnect/epoch cases and animation/VFX/terrain review. Repeat source-
bound gameplay/network regression and the appropriate soak after runtime edits.
Do not mark this candidate, P10 or the game accepted from these tests.
