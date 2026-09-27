# Apex R5 — fairing/belly intersection correction

R5 fixes the demonstrated lower white/black triangular intrusions in the R4 candidate. It remains **visually unaccepted** against the locked [Apex v2 concept](../../../../../ArtSource/Concepts/P08/Golden/apex-v2.png), SHA256 `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`. No new concept or material revision was made.

The defect is visible in both the [R4 Blender render](../r4/final-quarter.png) and the [actual Unity garage](../../ui/continuation-04/garage-apex-before-layout-1920.png). It is authored geometry, not merely Unity lighting or an accidental simultaneous-LOD presentation. R4 independently remapped the main fairing and generated a wider belly shell. Earlier manifold/area checks passed because they did not test intersections between separate closed components.

[Native R4 diagnosis](r4-component-diagnosis.json) found 137 left-fairing/belly triangle pairs, 132 right-fairing/belly pairs, 20 pairs for each lower diagonal vent wall and eight for each plenum: **325 intersecting pairs** in the named scope. Upper intake returns had zero. The direct Blender MCP diagnosis uses the actual editable meshes transformed to world space.

Only the belly shell is replaced in R5. Its outer return stays inboard of the unchanged fairing wall and recessed lower vents; a denser continuous section profile prevents the long stepped facets from cutting through the white panel. The shell remains closed and uses the unchanged `Apex_Graphite` finish. The [new native check](seam01.json) finds **zero intersecting pairs** against those same eight components and zero non-manifold belly edges. This is a bounded component test, not a claim that the entire motorcycle has no intersections.

The matched [editable quarter](01-quarter.png), [side](01-side.png), and [assembled LOD0 quarter](02-lod0-quarter.png) show the repaired boundary. Actual reduced views are [LOD1](02-lod1-quarter.png) and [LOD2](02-lod2-quarter.png). The source and assembled quarter cameras use R4's exact position, aim and 68 mm lens; side uses the same orthographic framing. R5 uses Cycles CPU, four threads and 24 samples. The studio lighting and finish textures are retained. These are source renders; the separate Unity follow-up is recorded below.

The [strict assembled audit](audit01.json) and [real FBX roundtrip](roundtrip01.json) pass without relaxing thresholds:

| Measurement | R5 result |
|---|---:|
| LOD0 / LOD1 / LOD2 triangles | 108,102 / 54,050 / 21,374 |
| Exported meshes | 9, with exact per-mesh triangle counts after reimport |
| Non-manifold edges / physical-area failures / UV-area failures | 0 / 0 / 0 across all three LODs |
| Smallest roundtrip world cross squared | 3.1613510299732803e-16, inherited from unchanged R4 geometry |

The LOD generator retains the prior bounded removal of tiny disconnected collapsed fragments in LOD2. This is recorded in [assembly](assemble01-mcp.json). Reduced-mesh views still require normal Unity distance/transition testing; a close studio view does not establish LOD performance or fidelity.

The tank and broad fairing silhouette, optical details, mechanical detail, material response and other concept differences remain. R5 is a seam correction, not a whole-bike fidelity pass. No production availability mask, Unity prefab, scene, runtime, server or UI file was changed by this authoring task. The original R4 source/maps, locked concept and protected Club are bound in [the pre-edit snapshot](preserved-inputs-before.json) and checked again by the handoff script. The user-edited Ash source was never opened or changed.

## Root-owned native handoff

The [handoff manifest](handoff-manifest.json) freezes both `.blend` sources, staged FBX, exact existing R4 map declarations, recipes and renders. Root subsequently published and imported this candidate as recorded below. The reproducible preparation command is `python tools/p08/golden/apex_r5_manifest.py --publish`: it copies only the new R5 FBX and writes the R5 descriptor, refusing a differing existing destination. It does not import, promote masks or grant acceptance. Shared R4 map bytes remain unchanged.

## Actual Unity follow-up — 2026-09-27

Root's [native import 4d1286bf9e05493d84785e737fa89f4f](../../unity/import-4d1286bf9e05493d84785e737fa89f4f.json) passed at 16:45:07 UTC in Unity 6000.5.7f1, with `passed=true` and `sourceBindingPassed=true`. The generated R5 prefab remains a separate candidate.

The actual [1920 × 1080 Unity garage capture](unity-garage-r5-1920.png) was independently inspected against the [R4 garage capture](../../ui/continuation-04/garage-apex-before-layout-1920.png): the black triangular intrusions through the lower white fairing are absent and the boundary is continuous. This confirms the bounded seam repair survived FBX import and the real garage presentation. The tank/fairing proportions, broad simplified surfaces, optics, mechanical detail and finish still differ substantially from the locked concept.

The separate [native quarter capture receipt](../../../promotion/captures/apex-r5-continuation04/quarter.capture.json) at 16:50:04 UTC binds the descriptor, exact native import, prefab, locked concept and [1536 × 1024 PNG](../../../promotion/captures/apex-r5-continuation04/quarter.png), using a fresh LOD0 instance. Root's capture/decode path succeeded, and the actual PNG was independently inspected. Its neutral staging plane, lighting, reflections and framing differ from the concept; it proves a functioning real native capture path, not visual acceptance. One quarter capture also does not supply the remaining required review views.

The immutable authoring handoff, five Blender renders and earlier source-check receipt remain unchanged. This follow-up supersedes only the earlier statement that native import/review was pending. It does not accept the motorcycle, expand production masks or close P08.

All Blender work used the pinned direct MCP on dedicated port 9878 with safe mode enabled. Initial raw-file-write/lambda scripts were rejected before execution and were rewritten to supported stdout/simple expressions. Two modifier-operator context failures were retained; the successful recipe uses the supported BMesh bevel API. These unsuccessful attempts are not counted as asset checks. There was no Jarvis MCP or paid generation.
