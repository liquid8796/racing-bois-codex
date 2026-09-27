# Canyon V17 — bounded valley-composition candidate

Status: **candidate 05 frozen, rendered and local FBX audit passed; visually unaccepted**.
This directory began with a read-only visual audit. Separate V17 source candidates
now exist. Candidate 05 source/FBX and the hash-bound review-only publication
helper are ready for root-owned Unity import. This handoff contains no native
Unity validation result. Production masks remain
1/1/1. Root owns Unity import and native capture. Authoring uses only the direct
pinned Blender MCP server with safe mode enabled and local/free tools.

## Frozen inputs and inspected evidence

- Locked reference: `ArtSource/Concepts/P08/Golden/canyon-v2.png`, SHA256
  `83273dae6721d9f2c6f5d6bf4a6f39146322d8efeabc5cec0cb332e5a1cfa610`.
- Preserved V16 source: `ArtSource/P08/Golden/Canyon/V16/RB_Golden_Canyon.blend`,
  SHA256 `c7681657df4666b13d22a15adbfaa17b42fd7413b8d4294a3cada4eb485cc01c`.
- V16 FBX: SHA256
  `bc731bbf85aefbd98d12f73a5e6320b4eeb5d33c5981a2ea11e1ab9debde81ea`.
- V13 source gameplay render: `../v13/gameplay-final.png`, SHA256
  `bf0b5a8034b156b327205fff8cef48871f6937ebfe8e7dcf958298fab5b677d2`.
- Also inspected the retained `../v16/unity-opaque.png`, V13 cliff/foliage/rail
  detail renders, V16 descriptor/module map and V14 lighting recipe. These are
  historical candidate views, not a newly captured V16 result.

The protected Club source remains outside this work, with required SHA256
`553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`.

## Observed differences

The reference main panel opens into a continuous deep right-hand valley. Near
terraces descend below the road; a basin/channel and successive opposing
escarpments recede through atmospheric depth. V13 and the retained V16 Unity
image instead place tall, isolated, flat-topped rock masses immediately behind
the guardrail. These occlude the basin and read as separated slabs or islands.
Closing scan backs in V16 fixes a technical defect but does not correct those
placements or silhouettes.

The left roadside has a broad smooth gravel ramp and long rounded vertical scan
forms. The reference has fractured block bedding, eroded ledges and a denser,
irregular transition into the road shoulder. Asphalt lacks the reference's
coarse dark aggregate and warm grazing highlights. Paint reads as regularly
repeating chipped tiles; the right edge reads as a continuous bright curb rather
than a broken asphalt/gravel transition. Rail detail lacks the reference's
weathered corrugated steel, rolled edges, joints/fasteners and substantial rough
footings. Foliage is sparse and uniformly branched compared with compact sage
and flared dry grass. These differences remain open; this candidate does not
attempt to accept or hide them.

## Corresponding camera view

The locked image is1536x1024, including four lower detail panels. The gameplay
region is approximately the top1536x717 pixels, before the horizontal divider;
the full board is not a gameplay viewport. Reference bytes remain unchanged.

The V13 source render is1536x768 (2:1). The V14 recipe uses a28mm lens,36mm sensor
width and aspect2, yielding horizontal FOV65.4705degrees and vertical
FOV35.6378degrees. Position/target correspond to yaw-7.2709degrees and
pitch8.0793degrees downward in Unity. The retained V16 Unity image is1920x1080:
using that same vertical FOV at16:9 narrows horizontal FOV to59.4898degrees.
This mismatch must be recorded and corrected before interpreting framing as an
asset-shape difference. The concept's camera intrinsics are unknown;28mm is a
candidate measurement, not a fact inferred from the concept.

V17 will preserve the original V16 camera comparison and record an explicit
gameplay-panel aspect/camera proposal. New renders must identify their exact
camera transform, projection, resolution and corresponding reference region.

## Bounded next correction

Create a separate V17 source and local Blender renders under the new V17 paths.
The first geometry pass targets only `Bend_07`, `Opposite_20` through `Opposite_32`,
`Far_33` through `Far_44`, and `DistantGround`: replace the obstructing right-wall
arrangement with descending connected terraces, a readable valley floor/channel
and receding opposing cliffs. All corresponding LODs must stay coherent.
Review this macro composition before considering rock microdetail, foliage,
paint or rail material changes.

Before any authoring, inspect the direct Blender server on port9877. If it holds
Garage or another active/unrelated scene, leave it unchanged and stage the
script offline for root coordination. Never overwrite an open unrelated scene,
the V16 source, the concept, or the protected Club file.

No Assets export/import occurs until the frozen local Blender render is
inspected. No numerical similarity score, mesh/UV count, compilation result or
closed-back geometry result can establish the required reference fidelity.

## Current source and native UV diagnosis

Port 9877 was free. A dedicated factory-startup Blender 5.2.1 LTS process
(PID 4892) was started with the pinned direct MCP server and safe mode enabled.
`factory-scene-ownership.json` records the empty-filepath default scene before
loading V16. The first connectivity failures are retained. No unrelated open
scene was replaced. `v16-comparison-original-camera.png` is an actual fresh
local Blender render of V16 with its original camera, without saving V16.

Read-only camera rays (`v16-occluders.json`) identified `Bend_07` as the near
right-hand obstruction, so that single bend module was added to the bounded
scope and lowered 15 metres. The remaining bend and lower-ledge modules,
road, shoulder, rail geometry, left cliff, foliage and all materials remain
unchanged. The 27 changed modules have coherent transforms/deformation across
all three LODs. Candidate 01 records the geometry pass; candidate 02 adds only
the primary-UV repair below. Both are separate files in the V17 source folder.

The candidate camera retains eye position and yaw, proposes 1.5 degrees down
pitch instead of 8.0793, uses explicit horizontal 28 mm/36 mm projection and
1536 x 717 output. This is a recorded framing proposal against the main concept
panel, not recovered concept intrinsics. Lighting/material settings are kept.

The fresh strict Unity V16 import failed guardrail Tile00 triangle 391, with
UVs `(0, 0.166666672), (0, 0), (0, 0)`. V16 Blender source triangle 228 has the
same positions after FBX axis/unit conversion and the same collapsed UVs.
This is a source solidify-cap mapping defect, not float precision loss at export.

`v16-primary-uv-summary.json` audits all 651 source meshes / 2,802,186 triangles:
1,315 collapsed primary-UV triangles across 22 guardrail beam objects and the
three LODs. All other meshes pass the unchanged absolute UV cross > 1e-14 rule.
The first audit script's safe-mode lambda rejection is retained; it did not
execute, and the replacement uses ordinary named functions within safe mode.

`candidate02-uv-summary.json` records the per-face before/after loop values.
Only collapsed triangular guardrail caps receive physical planar UV projection
at one repeat per metre, anchored to their first original UV. It changes no
geometry, topology, transform or material assignment, verified by exact array
equality before/after on all 651 meshes. All 1,315 collapsed triangles are
repaired; no collapsed triangle remains. The smallest absolute UV cross across
all meshes is 8.340999835265706e-9. This verifies source mapping only. Actual FBX
round trips were performed afterward for candidates 04 and 05, as recorded below.
This handoff contains no fresh Unity import result for V17.

## Rendered iterations and remaining differences

| Candidate | Actual rendered result | Decision |
| --- | --- | --- |
| 01 | Composition source before cap UV repair; no separate render | Retained source, never accepted |
| 02 | `candidate02-gameplay.png`: connected but nearly horizontal far wall; mid-bank still crosses the channel | Rejected; preserved |
| 03 | `candidate03-gameplay.png`: basin sightline opens, but near far-chain heights create an oversized stretched wall | Rejected; preserved |
| 04 | `candidate04-gameplay.png`: diagonal receding left chain and right bank converging into a distant basin | Bounded composition improvement only; rejected for final visual acceptance |
| 05 | `candidate05-gameplay.png`: camera far clip raised from 1,000 to 2,500 metres; distant closing ridge becomes visible | Current frozen handoff; all geometry/material/UV/lighting identical to 04; still visually unaccepted |

Candidate 04 preserves the exact candidate 02 UV repair and all road, rail,
left cliff, foliage, material and lighting inputs. Its Far chain recedes from
260 to 1,430 metres, with the nearer skyline at 80–97 metres and the final low
ridge at 55 metres. The right bank converges toward the distant basin instead
of cutting across its near sightline. Bend 07 is 33 metres below its original
position; all other bend modules remain unchanged. Candidate 04 has the same
217 modules / 651 mesh objects and the same triangle counts as V16.

Read-only rays in `candidate04-readonly-probe.json` confirm sampled basin directions
hit actual DistantGround at forward 407–1,028 metres and height -31 to -54 metres.
The nearer samples establish terrain within the original camera range. However,
the inherited far clip was 1,000 metres: the 1,028-metre ground ray and the
1,415-metre Far 44 ray do not establish visible camera output in candidate 04.
The initial atmosphere-only explanation was too broad. Camera-clip-only candidate
05 preserves 04 and shows the formerly clipped distant closing ridge. Basin
washout remains an atmosphere/material discrepancy in 05. The same probe confirms
primary UV index 0 on all 651 meshes; each has one UVMap or UV0_SurfaceMetres layer.

The locked concept still differs substantially: fractured block bedding and
stepped ledges are missing from the stretched rounded scan silhouettes; broad
rock overhangs remain; the ground lacks detailed terrace transitions and dense
vegetation; the near left shoulder is too smooth; asphalt/paint/rail details
remain unresolved. The bright atmospheric treatment washes out depth and a
horizontal fog-sheet boundary is visible in the sky. The original concept
requires warm, textured, connected sandstone terrain, not merely this corrected
placement. No fidelity score or acceptance is claimed.

A temporary camera-only yaw +3 degree preview is retained separately. It moves
the road turn left but makes the near left cliff too narrow, so it was not
adopted. The frozen candidate keeps the recorded original yaw with 1.5 degree
down pitch and explicit 1536 x 717 projection. No shared Unity recipe changed.

The most useful next correction is to replace the Far-chain stretched slab
profiles with proper fractured stepped sandstone forms at these now explicit
depths, then integrate textured descending near/mid terraces. The fog/material
washout needs a separately recorded lighting review. Camera/road framing should
be reconciled together rather than silently treating the yaw preview as a fix.

## Local FBX round trip

After inspecting the frozen full candidate 04 render, the owned direct Blender
session exported `ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_04.fbx`
and reimported it into a temporary set of objects. Only newly imported objects
were removed afterward; original names, visibility and selection were restored.
The frozen .blend was not saved again after this audit.

`candidate04-fbx-summary.json` reports exact renderer coverage and exact per-mesh
triangle counts: 651 meshes, 2,802,186 triangles, zero collapsed primary UVs and
zero physically degenerate triangles. The unchanged strict thresholds are UV
cross > 1e-14 and physical cross squared > 1e-16 m^4, calculated
from transformed local edge vectors without large terrain translations. Minimum
observed values are 8.340999835265706e-9 and 5.749636704244221e-11 respectively.
This is real Blender FBX export/reimport evidence, not native Unity import,
gameplay, performance or visual acceptance.

Peer review found that the first import audit removed imported objects/meshes
but left new orphaned material/image datablocks in the owned live session.
No source save followed that audit. The exact frozen 04 source was reloaded,
and `candidate04-fbx-restoration-audit.json` reran the frozen FBX import with
exact before/after object, mesh, material and image membership restored. The
current exporter performs the same complete owned cleanup. Candidate 05's
actual export/reimport passes those restoration checks as well as all strict
UV/physical checks, with the same 651 meshes and 2,802,186 triangles.

`candidate05-freeze-manifest.json` binds the final source/FBX, actual renders,
scripts and receipts plus unchanged locked concept, V16 and protected Club hashes.
The intermediate .blend files remain available locally at their recorded paths;
the proposed review handoff consists of candidate 05 .blend/.fbx, these docs and
the new `tools/p08/golden/canyon_v17` scripts. Root owns Git publication and any
later Unity import. Never overwrite these frozen outputs when trying another
variant; use a fresh candidate suffix and fresh output paths.

## Root-owned native import handoff

The existing Golden descriptor contract is preserved. `candidate05-descriptor.json`
binds the exact source/FBX, locked concept/review, all material maps and the
217-entry independent module LOD map. Bounds are measured from actual source
vertices: Unity minimum `[-200.004974, -104.059944, -8.001282]`, maximum
`[650.001709, 97.259056, 1530]`, size `[850.006683, 201.319000, 1538.001282]`.
The existing 0.05-metre bounds tolerance and 0.01-metre below-ground margin are
retained. The local strict FBX audit does not replace Unity's validation.

`candidate05-publication.json` binds 61 inputs, including descriptor, module map,
camera recipe, current publication helper, actual render and strict audit receipts.
The verifier rejects changed destination, source hash, descriptor hash or any
visual-acceptance claim; the four read-only negative controls are retained in
`candidate05-publication-checks.json`.

Root can verify, then explicitly publish the one new FBX:

```powershell
& .\_local\blender-env\Scripts\python.exe tools/p08/golden/canyon_v17/publish_candidate05.py verify
& .\_local\blender-env\Scripts\python.exe tools/p08/golden/canyon_v17/publish_candidate05.py publish
```

The publisher requires the exact fresh FBX/meta destination and never writes
production masks, mappings, acceptance data or existing files. It does not invoke
Unity. Root then uses the existing `GoldenSampleBuilder.Import`/`Validate` flow
with `docs/p08/golden/canyon/v17/candidate05-descriptor.json`, and the optional
`CreateEnvironmentReviewScene` flow with `candidate05-camera-recipe.json`.

The measured camera recipe uses 1536 x 717, 28 mm / 36 mm horizontal projection,
the recorded 1.5-degree down pitch and original yaw. Native captures must use
that aspect. The existing native environment builder/controller hardcode near/far
clips 0.05/2,000; Blender 05 uses 0.1/2,500. Both encompass the measured terrain,
but exact clip parity is not claimed and no ignored JSON field is used to imply
that Unity consumed these extra settings. No shared C# or lighting recipe changed.
