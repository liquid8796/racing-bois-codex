# Apex V8 — rejected visual candidate, isolated for inspection

This is a local/free Blender authoring iteration against the preserved Apex v2 concept. It is **not accepted for production and does not meet the user's 100% concept-fidelity requirement**. Neither the mesh observations nor the Unity descriptor grants visual acceptance. No production mask or production bike prefab was promoted.

Reference: `ArtSource/Concepts/P08/Golden/apex-v2.png`, SHA256 `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`. The existing `apex-v2-review.md` supplies wheelbase1.43m, tyre diameter0.63m, seat0.82m and two under-seat outlets. The concept was inspected before new geometry.

## Exact candidate

- `ArtSource/P08/Golden/Apex/V8/RB_Golden_Apex_v8.blend`: frozen runtime assembly and hidden editable source components.
- `ArtSource/P08/Golden/Apex/V8/RB_Golden_Apex_v8_editable.blend`: pre-assembly version of iteration05.
- `Assets/RacingBois/Art/P08/Golden/Apex/V8/RB_Golden_Apex_v8.fbx`: isolated candidate export.
- `descriptor.json`: explicit hash-bound material, axis, LOD, contact and collider contract for root-owned Unity inspection.
- `geometry-observations.json`: freshly measured meshes and exact input hashes.
- `apex-*-final.png`: actual Cycles renders of the frozen runtime assembly, not generated mockups.

Only the task-owned Blender5.2.1 session on port9878 was used, through the pinned stdio Blender MCP client in safe mode. Initial scene inspection recorded Cube/Light/Camera and task PID21868. All rendering used CPU, four threads. No Jarvis MCP, paid generation service, GPU rendering, old production prefab replacement or original-game asset extraction was used.

## What changed

The dominant body surfaces were replaced: authored curved tank and tail sections; a continuous fairing surface with a real diagonal through-opening, recessed walls and grille; a fitted nose with separate hollow lamp cavities; separate clear optical-lens and smoked windscreen materials; new angular mirrors. Appropriate manufactured wheel, brake, engine and chassis components were retained and adapted. Upper nose/tail overhangs were shortened after tracing their relationship to the reference axle positions; wheelbase, wheels and central rider contacts stayed fixed.

The first four V8 render iterations remain as diagnostic evidence. They exposed disconnected nose edges, overly proud optics, excessive upper-body overhang, a hidden-projector material error, an exposed under-seat pipe after silhouette changes, and a belly/fairing intersection. Iteration05 corrects those concrete construction issues but does not resolve overall concept fidelity.

## Visual differences still preventing acceptance

The final beauty view still differs visibly from the reference:

- The nose eyebrows and central cowl have the wrong curvature and visual mass; they read as simple broad strips.
- The front view's central graphite wedge is too narrow, and the mirror faces/cases are too square. The rear view also lacks the reference's compact fairing around the two outlets.
- Tank shoulders, knee recesses, tail and saddle do not reproduce the reference's exact sculpted profile and crease placement.
- The fairing opening, lower relief, main panel boundaries and graphite/white material hierarchy still differ.
- The chassis/subframe remains too exposed and skeletal in the three-quarter composition.
- Mirror silhouette, fork/caliper details, tyre/rim finishes and machined component richness remain simplified.
- Paint and physical finish maps do not reproduce all reference surface detail. Uniform finish maps are useful PBR inputs, not evidence of equivalent texture design.

Do not spread this candidate to the remaining roster. Further visual work is required against the same reference; do not silently redefine the prototype to match the candidate.

## Structural observations, separate from visual quality

Final measured LOD triangles: **102,912 / 45,280 / 14,404** across three renderers per level. All nine exported meshes have zero non-manifold edges, zero degenerate geometry triangles and zero degenerate UV triangles in the fresh Blender audit. The LOD0 count is above the earlier45–65k proposal; native cost and whether that detail is justified are unaccepted.

Approximate bounds: **0.822793 × 1.177296 × 2.063391m**. Root and wheel mesh transforms have unit scale; wheel meshes use axle-centered parents. Ground markers are at0. Shallow tyre surface detail extends about1.7mm below that nominal plane, which remains part of the gameplay clearance review.

Nine purposeful material groups use BaseColor, Normal and MetallicSmoothness(R/A) plus saved Roughness source maps; optics also use emission. Pearl is2048px, structural surfaces1024px, optics512px. Colour maps are sRGB and data maps linear. Maps were completed, then explicitly reloaded before Blender packing. Scalar maps here are generated as normalized8-bit data; no16-bit channel packing was used.

Component UV charts intentionally share seamless physical finishes. Small bevel-face charts were recentered after a fresh precision audit; this is not a claim of a unique non-overlapping decal unwrap. The source audit initially found collapsed lens bevel vertices. Repair was limited to affected body assemblies; an over-broad weld that joined touching wheel parts was rejected and the exact pre-repair source restored before the final body-only repair. The final audit covers the repaired export.

The intended mapping is Blender `(semanticX, semanticForward, semanticUp)` exported with FBX `-Z` forward and `Y` up. `Forward`, `Semantic_Left`, `Semantic_Right`, ground, seat, grips and feet are explicit markers. **Unity must prove +Z forward, negative-X left and positive-X right together**; rotating a wrong-forward model180degrees is not an acceptable substitute.

Remaining gates: actual Unity axis/material/prefab validation, LOD silhouette and transition review, steering/wheel clearance, Ash seat/grip/foot contacts, native gameplay/camera appearance, memory/FPS measurement and independent concept comparison. Collider is an explicit inspection proxy. This file reports no FPS, memory, handedness or fidelity PASS without those observations.

The protected `ArtSource/Weapons/RB_Club.blend` remained untouched; SHA256 rechecked as `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`.
