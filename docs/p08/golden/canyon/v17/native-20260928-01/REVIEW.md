# Canyon V17 candidate05: actual Windows comparison

The fresh bounds-r1 descriptor passed the current Unity importer with exact source binding and all primary-UV/physical-triangle checks. The original V16 collapsed-UV failure and V17 all-LOD-envelope failure remain preserved. Bounds r1 uses the consumed LOD0 vertices with the original +/-0.05 m tolerance; it does not widen the gate.

The Windows64 Mono build `20260928-canyon-v17-01` passed with zero errors/warnings, source binding, settings restoration, original-font preservation and unrelated dirty-asset preservation. Its named build receipt is `docs/p08/golden/unity/build-14368d42e5f640118a9bf83e0113289b.json`. The owned native process exited0 with three hash-verified, independently decoded Direct3D11 PNGs at1536x717. `launch-check.json` binds the exact build receipt and unchanged player files before/after execution.

Root inspected the LOD0 and LOD2 gameplay views against the corresponding top panel of locked `canyon-v2.png` (SHA83273dae6721d9f2c6f5d6bf4a6f39146322d8efeabc5cec0cb332e5a1cfa610). The bottom detail panels are separate comparison views, not part of the gameplay camera image. The new basin is visible, but the asset remains visually unaccepted:

- The far cliffs are tall stretched slabs with overhanging lips. They do not match the reference's fractured, stepped sandstone walls and dense horizontal bedding.
- The right basin lacks the reference's layered terrain detail and vegetation. The left shoulder remains a broad smooth ramp rather than the reference's irregular rubble/ledges.
- The road bend sits too far right; cliff/road framing is not identical. The preserved camera-yaw alternative was not adopted.
- Actual Unity lighting is darker on the road and guardrail than both the concept and Blender source render. Strong repeated rail shadows, foliage edge speckling and the bright sky/haze require separate material/lighting work.
- The rail is a simplified channel with different footings and surface detail. Forced LOD2 further reduces its profile and paint/vegetation detail; those reductions are visible, not accepted by triangle-count checks.

The recorded Unity clip range0.05–2000m differs from Blender0.1–2500m; both cover the measured geometry, but exact camera/lighting parity is not claimed. These are engine-camera review renders, not window/UI captures, gameplay contact tests or performance measurements. No production mapping, masks or acceptance file is promoted.
