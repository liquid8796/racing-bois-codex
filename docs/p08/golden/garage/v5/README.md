# Garage V5 — primary UV repair, visual acceptance still open

The locked garage-environment-v1 and garage-v2 UI concepts were inspected
alongside the actual V4 bake03 1920px image before this repair. Their hashes
remain unchanged. All work used direct pinned Blender MCP on the assigned
9877 process with safe mode enabled. No Jarvis, paid service, Unity operation
or live Assets edit was used.

## What changed

The V4 explanation that UV_MetricTile was unused was incorrect. V3 joins had
stored some real visor/wrench faces in that layer while leaving the same
faces blank in UVMap. The original authoring recipe also selected projection
axes from local face normals but projected world coordinates before applying
some cylinder rotations. This produced collapsed primary UVs on caps/sides.

V5 first restores useful alternate V3 coordinates face by face, then repairs
remaining collapsed faces using metric projection in the correct world-space
plane. The initial whole-polygon audit repaired 5,698 faces: 1,544 from the
preserved alternate layer and 4,154 by projection. A stricter triangle audit
then caught 1,819 degenerate UV triangles inside polygons with nonzero total
area; 886 additional face projections repaired those. The first failing
triangle receipt is preserved as `uv-triangles-first.json`.

Final source and exported/reimported FBX contain zero degenerate UV0 triangles,
zero degenerate authored lightmap triangles and zero physical triangles below
the existing squared-cross threshold1e-16. Coverage remains180 meshes and
132,592/28,712/4,508 triangles at LOD0/1/2. Reopening the preserved V4 and final
V5 sources proves exact equality of vertices, triangle indices, corner
normals, object transforms, material slots/indices and all60 LightmapUV arrays.
This does not claim new topology or improved geometric fidelity.

UV0 is explicitly named `UV0_MetricTile`. Repetition, coordinates outside0..1
and cross-face overlap are intentional for these repeating PBR surfaces:
floor2m tile, wall2.2m tile, remaining material surfaces1m tile. UV1 remains
`LightmapUV` on LOD0 only, with its previously verified non-overlapping atlas
unchanged. LOD1/2 retain one primary channel and use light probes. No UV channel
was swapped to silently replace a missing primary texture with a lightmap.

All53 used PNG images were explicitly reloaded before packing. A packed-byte
FNV1a64 fingerprint plus byte length matches each external source; the receipt
also records external SHA256. No image was edited. The initial unused hashlib
import was rejected by safe mode; that failed receipt remains available and
the unused import was removed without changing permissions.

## Material and lighting review

The default V5 source/FBX retains the original V4 PBR parameters, including
floor normal strength0.55, the existing roughness texture, dielectric floor/
painted cabinets and metallic tools. The final source image is
`uv-final-original-materials.png`. `uv-repaired-no-coat.png` is an intermediate
render before the stricter triangle repair and is not the final artifact.

`RB_Golden_Garage_CoatComparison.blend` and `coated-floor.png` preserve an
actual rendered clear-coat experiment. It is **not accepted**: reflections
become too smooth/glassy and reduce the broken surface response present in the
concept. It is not the default material or an excuse to compensate for missing
native reflections. Exact trial parameters are in
`material-comparison-settings.json`.

Even the unchanged-material Cycles render has strong warm floor reflections,
unlike the native V4 bake03 image. The render paths differ: this authored
Cycles scene includes direct rectangular area-light specular; Unity's baked
rectangle lights and a filtered reflection cubemap are not numerically
equivalent. `authored-lighting.json` records every actual area width, height,
position, orientation, normalized watt value, linear color and specular factor,
plus the lamp emission texture/strength6 and color-management settings.
The root task owns native lighting calibration and actual Game-view review.

Explicit Unity baseline requirements are in `delivery.json`: URP Lit,
metallic workflow, mask red metallic/alpha smoothness with multiplier1,
normal-map import, floor normal scale0.55, repeat sampling and active specular/
environment reflections. If reproducing only the rejected coat experiment,
the installed URP Complex Lit shader uses `_ClearCoat=1`, `_ClearCoatMask`,
`_ClearCoatSmoothness`, `_CLEARCOAT` and no `_CLEARCOATMAP`; the installed
`LitGUI.cs` keyword rules and `ComplexLit.shader` were inspected. That shader
has additional cost and is not requested for the default V5.

## Visual differences still unresolved

The workshop remains unaccepted against the locked concept. Visible remaining
differences include the squared cabinet/prop treatment, toolboard shape and
spacing, simplified vise/helmet/toolbox details, near-left wall proportion,
concrete stains and panel pattern, wall lamp glow/occlusion, floor texture
scale and broken-reflection pattern. Native lighting and the separate UI
camera/bike framing also need actual matched-view comparison. UV correctness,
triangle checks and these Blender renders do not establish100% visual fidelity.

## Handoff

`delivery.json` binds the frozen source and staged FBX hashes. The descriptor
and LOD mapping are explicitly staged outside Assets; their FBX paths currently
refer to `_local/p08-garage-v5-staging`. Root must copy the FBX to a fresh V5
Assets path, verify the same hash and rebind the descriptor/mapping references
before calling the Golden importer. No native import is claimed here.

V3, V4, the locked concepts and protected RB_Club.blend retain their expected
hashes. The UV-only intermediate and coat comparison are preserved; no older
version or failed receipt was deleted.
