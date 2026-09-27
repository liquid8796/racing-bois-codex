# Protocol6 prediction repair — applied, longer runtime gates pending

The reviewed30-file protocol6 repair was applied at2026-09-26 22:59UTC after isolated241-group regression and90-second/8-peer/fuzz PASS. [Applied source hashes](applied-source-freeze.json) match the reviewed candidate manifest `294f5c105f6be2f939234c2b9c88fc746f330f63c4ac0763e464751c78e3b41b`. [Fresh production regression](../regression/20260926T225938Z/receipt.json) passes241groups with stable source; [fresh HTTPS/WSS career checks](../career/20260926T230104Z/run.json) pass11checks with no skips. OCI deployment and longer runtime acceptance remain separately coordinated by root.

The prior protocol5 run was [intentionally superseded](../network/20260926T213110Z/intentional-supersession.json) at5263.082seconds,64cycles,43reconnects and8storms. Only its verified task-owned probe15344 was stopped; its supervisor cleaned server20968. Source was still stable at supersession. Raw reports are preserved as interrupted/FAIL; this is **not** an eight-hour PASS.

The initial isolated regression at `_local/p10/proxy-transition-staged-tests/20260926T224324Z/docs/p10/regression/20260926T224330Z/receipt.json` is FAIL and remains preserved. A correct local combat forecast exposed a remote presentation mismatch; the later bounded same-tick repair fixes it without changing tolerances. The copy recipe also initially omitted the Economy JSON and legacy source-inventory folder; these diagnostic setup failures were preserved and rerun with unchanged test bodies. The [final isolated full15-suite run](full-regression-20260926T225110Z/receipt.json) passes241groups on source copy `20260926T225102Z`.

## Three captured defects and replay evidence

| Episode | Established cause | Staged replay at the same target tick |
| --- | --- | --- |
| Pedestrian4008, authority2811→2814 | Proxy Stumbled age177 never advanced to recovery180, so the collider stayed absent. | 9.135m → 0.005m; remaining distance/bike-distance5mm matches centimeter wire quantization. |
| Rider3, traffic3001, authority292→295 | Owner-first proxy collision pass crashed into the car before lower-ID rider1 could apply the protection that authority applies first. | 9.815m → 0m; all physical checkpoint fields match, only authority-owned rank remains8 versus7. |
| Rider4, police2001, authority4733→4736 | Police attack already age7; proxy never advanced the known impact8 or received it. | 16.258m → 0m; full resulting checkpoint matches at4757. |

The original immutable episode JSON files remain under `docs/p09/releases/e`. `protocol6-candidate.json` retains replay states, negative controls and outcomes. These are exact offline scenarios, not a claim that all future network corrections vanish or that renderer quality is accepted.

The old police recording did not transmit endurance. Its observed strength7 and Club damage8 uniquely imply endurance1000 within the authoritative500..1000 range; the test enumerates that range. Active age7 precedes its sole impact8 and therefore is unresolved. This is explicitly derived event/invariant evidence. Protocol6 sends the general current state instead of relying on this episode-specific derivation.

## Bounded changes

- Pedestrian rows9→12: already chosen wait duration60..359, exact desired walking speed1200..1600mm/s, signed remainder−59..59. Immutable prediction metadata stays separate from visual readmodels. Waiting, crossing/along-road stop and Stumbled recovery use one shared deterministic transition helper. Authority retains RNG draws and event order. A future randomly selected wait is not forecast; its guaranteed minimum exceeds the remaining30-tick prediction horizon.
- Rider rows27→31: endurance, attack-resolved flag, remaining hit protection0..90 and steal protection0..300. Existing remount collision protection remains validated. Client rejects missing, old-shaped, incoherent or out-of-bound metadata before committing a snapshot.
- Contact roster sorted by actor ID on restore; independent stable proxy references preserve velocity indexing. All bounded known proxy contacts are needed because an earlier pair can affect the owner's later pass. Horizon expiration restores the actual owner slot, independent of its ID/order.
- Known proxy Attack/Hit clocks advance. The combat resolver shares deterministic selection/application order with authority, begins new attacks only for supplied owner input, and skips any uncertain steal RNG branch. No future remote input or authority RNG is invented. Predicted state stays inside the sandbox; health, bike condition, rewards, inventory and terminal outcomes remain authoritative in client presentation.

## Verification and unresolved gates

- `protocol6-candidate.json`:13/13 groups pass, including all three episodes, expiry/impact boundaries, negative controls, owner placement and no caller-snapshot mutation.
- `protocol6-integration.json`:10/10 groups pass, including exact versus centimeter velocity units, hostile metadata/old rows/version rejection, immutable context, atomic missing-context rejection, authority health/outcome preservation and created-only/matched-tick remote motion with reset/expiry negative controls.
- Full unchanged gameplay suite:31/31;20,000-tick golden `BA1786522D59B2D7`,3,000-tick golden `FD320D8BD0D9435E`. Authoritative event/RNG behavior unchanged.
- Maximum proxy capacity16riders/12traffic/6pedestrians:30,000 staged debug prediction ticks, zero allocated bytes after warmup, about70µs/tick on this machine. This is CPU microbenchmark evidence, not Unity/FPS acceptance.
- The initial zero-RTT near-combat failure was0.44999695m versus required0.15m. `near-combat-diagnostic.json` proves simultaneous fatal hits at476: local correctly continued Falling to478 while the remote sampler held its old Attacking trajectory at476. The repair exposes only motion for a transition created inside the bounded sandbox, advances its locally initialized recovery and samples that motion at the matching tick. Authoritative readmodels still supply health/inventory/outcomes. All flags reset at checkpoint restore and expire after30ticks; pre-existing non-driving proxies never qualify. Unchanged0/150/250ms gates now pass with maxima0.030/0.230/0.505m. This is sampled-relative-pose evidence, not downstream renderer acceptance.
- Future proxy steering/acceleration, future AI/input decisions, unseen spawned actors and RNG-dependent weapon stealing remain uncertain. Pre-existing non-driving remote proxies lack recovery-private velocity/state; no claim of exact forecasting those states is made.

The candidate manifest hashes staged replacements and their unchanged production predecessors. Only root coordinates stopping/superseding the old soak, applying a reviewed source freeze, OCI deployment and new short stress/8-hour runs. An unfinished or superseded run must never become a PASS receipt.
