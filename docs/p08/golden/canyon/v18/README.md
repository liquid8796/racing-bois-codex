# Canyon V18 — Far33-only geometry experiment

Status: **candidate 02 rendered, visually unaccepted; no Assets export**.
The locked `canyon-v2.png` reference and frozen V17 candidate05 remain unchanged.
Only `Canyon_L0_Far_33`, `Canyon_L1_Far_33` and `Canyon_L2_Far_33` are replaced.
The approved experiment addresses the stretched scan shelf/backing identified
by `../v17/overhang-audit`, with the candidate05 camera and lighting held fixed.

The new landform is one connected closed volume with an east-facing front toward
the road/camera, retreating terraces, vertical fractures, broken bedding and a
real rear volume. It uses the existing Canyon_Sandstone material and physical
world-space primary UV projection at 2.4 metres per repeat. No new texture,
material datablock or image is introduced. The other modules keep their geometry,
UVs, transforms, materials and visibility exactly.

Candidate 01 removed Far33's thin stretched sheet but its regular joints and
per-block offsets read as manufactured masonry. Its source and full render are
preserved. Candidate 02 removes that regular offset grid, staggers/terminates
secondary fractures, varies their widths/depths and interrupts minor bedding.
Its full gameplay render is `candidate02-gameplay.png`; compare it directly with
`../v17/candidate05-gameplay.png` and the corresponding top panel of the locked
concept. These are actual Blender renders, not image edits.

The visible first Far mass no longer has the old elongated thin shelf. The second
candidate reads less regularly than 01 and exposes the authored front rather than
the scan's added backing. It still needs art review: some surfaces remain broad,
the fracture/terrace balance is not yet identical to the concept, and the unchanged
neighboring Far scan profiles, near cliff, valley, foliage, rail, road and lighting
retain their previously recorded differences. This experiment does not establish
full Canyon fidelity or production acceptance.

## Actual source audit

Both saved candidates pass the unchanged primary UV cross > 1e-14 and physical
triangle cross squared > 1e-16 m^4 rules. For candidate 02:

| LOD | Triangles | Boundary edges | Nonmanifold edges | Connected closed components | Material |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 26,966 | 0 | 0 | 1 | Canyon_Sandstone |
| 1 | 11,324 | 0 | 0 | 1 | Canyon_Sandstone |
| 2 | 4,314 | 0 | 0 | 1 | Canyon_Sandstone |

All three components have positive signed volume. The minimum primary-UV cross
values are 0.00989999, 0.01613251 and 0.04710310. Exact per-mesh values and physical
area minima are retained in `candidate02-audit.json`. There are no epsilon UV
offsets or relaxed thresholds.

The authoring check compares **649 other scene meshes** exactly before/after,
including their vertex arrays, loop topology, UV layers, material assignments,
world matrices and visibility. Camera matrix/projection/clips/resolution, light
transforms/energy/color, world inputs and color-management settings match the
frozen05 snapshot. Existing material/image datablock membership is preserved.
Only the three owned old Far33 mesh datablocks are replaced in the new source.

`candidate02-visible-surface-audit.json` independently checks one outward closed
component at each LOD and the exact material/primary-UV slot usage. Its actual
gameplay-camera rays hit the new Far33 front with mainly positive-X normals,
confirming that the comparison view now sees the authored front. All sampled
Far33 hits face the camera. This is geometry/material evidence, not a visual score.

Whole-scene triangle totals become 1,654,718 / 839,403 / 343,957. No configured
budget or production mask changes. The added detail and LOD transitions still
need native/performance review before any production decision.

## Preserved failure and review boundary

The first 02 attempt loaded frozen05 and immediately tried to apply a modifier in
the same MCP execution. Blender rejected the unsettled operator context. The
script restored frozen05 without saving/exporting a candidate; that failed
receipt is retained as `candidate02-author-load-context-failure.json`. The retry
ran from the settled frozen05 context and passed. The current authoring script
requires the source to be loaded in a separate MCP call first.

Authoring uses only the owned direct pinned Blender MCP port9877 with safe mode
enabled. There are no Unity calls, Assets writes, production bindings or visual
acceptance entries in this experiment. Root must inspect the actual render and
these audits before any Assets export/import. `freeze-manifest.json` binds the
sources, renders, scripts and receipts plus the preserved parent/concept/Club
hashes. A new iteration must use a fresh source and evidence suffix.
