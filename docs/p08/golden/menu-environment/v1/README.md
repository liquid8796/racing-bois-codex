# Menu overlook V1 — technical handoff, visually unaccepted

Root subsequently authorized exact file publication. `menu_publish.py --publish`
has copied the frozen FBX to `Assets/RacingBois/Art/P08/Golden/MenuEnvironment/V1`
and rebound `descriptor.json`/`module-lod-mapping.json`; see `publication.json`.
This author still made no Unity calls. The staging-only wording below documents
the initial handoff boundary. The actual standing-plane ray suggests instance
Y offset+0.0249681473m for root's contact review at unchanged actor origin.

The author inspected both the locked `ArtSource/Concepts/P08/Golden/UI/main-v2.png`
(SHA256 `9b7ad175234636c591846552178f2d25a279434763ce5d0f252af738c6c8e95e`)
and the actual `r3-ashv4-main-1920.png` before authoring this environment. The
existing fixture had placed the parked actors on the road and a guardrail across
their background. The new source is a dedicated overlook, derived from frozen
Canyon V16 modules/materials with additional original ground and dry grass.
It is not the complete original route or an accepted replacement family count.

The pullout surrounds actor origin. A curved road and its connected rail,
shoulders and vegetation sit eight or more metres below that plane, toward
screen-left. The left wall and successive landforms are composed for the actual
fixture camera `(2.97608256, 1.50701666, 1.88716865)`, direction from the subject
`(1.6, .32, 1)`, vertical FOV35 and16:9. Blender uses an approximate off-center
shift; Unity's actual posed-actor fitting remains the correct final projection.
Use **zero environment yaw**, not the previous Canyon180-degree rotation.

The first two actual renders exposed excessive skyline height, a cliff/road
intersection and edge-on distant scan placement. Composition03 corrects these
placements and scan front axes. Composition04 adds foreground grass and fixes
1,315 collapsed UV triangles on reused guardrail thickness caps. Only those
caps were locally projected; other source UV corners remain attached to their
vertices. These repeated cap charts deliberately share texture space.

All417 mesh renderers are explicitly triangulated from Blender's loop-triangle
stream before export. A further source check caught downward open road/paint/
terrain winding selected by BMesh's general normal recalculation. It was fixed
geometrically upward, preserving per-corner UVs. The earlier finite-area audit
alone did not catch this; its receipt and provisional export receipt remain
historical evidence. No road material was made double-sided to hide the defect.

The final source audit reports zero physical-area failures, zero collapsed UV
triangles and zero upward-surface winding failures. Explicit FBX roundtrip
preserves all139 module groups/417 renderers/1,938,935 triangles, triangle order
and exact float32 UV values. It reports zero physical or UV failures. Maximum
world-position deviation is0.000112534m over the large landscape, and maximum
normal angular deviation is0.959674degrees. Normals are **not bit exact**.
Triangle-order matching uses `max(0.00002m, maxAbsCoordinate * 2^-21)` to account
for float32 export precision over the far landscape; physical cross-squared
threshold remains1e-16 and UV absolute cross threshold remains1e-14.

`delivery.json`, `descriptor-staged.json` and `module-lod-mapping-staged.json`
bind the current source and staged FBX. Root owns publishing to a fresh Assets
path, rebinding its map/descriptor hashes and actual Unity import/render review.
No live Assets, Unity state or production masks were changed by this authoring
task. Contact colliders are intentionally absent from this passive menu display;
it is not a playable authority track. The pullout's nominal surface is-.025m;
the measured `MENU_STANDING_PLANE` render receipt supplies a small optional
instance-Y offset for root's actual tyre/boot contact review.

Remaining visual differences are explicit: cliff bedding/silhouettes and the
gap between left/central formations differ from the concept; the foreground
edge is too regular; vegetation distribution, surface color/roughness and
depth haze need matched-view review. The hero models are separate unaccepted
candidates and are not included in these background-only renders. Root owns
the Unity HDR/sun/fog calibration. No composition image or technical PASS is a
claim of100% concept fidelity or production acceptance.

All authoring used the assigned direct Blender MCP9877, safe mode enabled,
CPU rendering capped at4 threads. A lambda was rejected before the first
composition04 attempt executed; it was replaced by an explicit loop and the
failed receipt is retained. No Jarvis, paid generation, source-game copy or
concept image pasted into geometry was used. Canyon V16, Garage V7 and the
protected Club source remain unchanged.

Reproduce the authored revision on a dedicated task Blender instance only:
`menu_environment_v3.py` opens the immutable Canyon source and rebuilds the
layout; then `menu_finish_v4.py`, `menu_surface_frontfaces.py`,
`menu_geometry_audit.py`, `menu_export.py`, `menu_roundtrip.py` and
`menu_render_final.py`. Do not rerun the additive finish script against an
already-finished scene. Prior rendered attempts remain unaccepted history.
