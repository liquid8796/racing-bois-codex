# V19 candidate06 — local CC0 surface detail on bounded rock groups

**Rendered and visually unaccepted. No Assets export, production binding,
acceptance entry, mask change or budget adjustment.**

The actual image is `candidate06-gameplay.png`. Compared with05, the continuous
fluting is reduced; horizontal stone detail, surface roughness and separate lower
groups are more visible. Some large blank faces and mechanically repeated ledge
profiles remain. The locked concept's dense fractured mesas and deep setbacks are
not matched. Unchanged near cliff, road, Bend/Opposite overhangs, valley, vegetation
and lighting retain their earlier differences.

## Actual local source reuse

The original local CC0 `namaqualand_cliff_01_fbx.fbx` remains byte-identical
(`ee5bb2ab237f3fe8d03330324cee735c3fd07c8ff2c2c5f32e5a00868aceee9b`).
The direct Blender probe temporarily imported it, ray-sampled actual surface
positions and barycentric primary UVs, then removed only its new objects,
meshes, materials and images. Source/scene state was not saved by that probe.

Three disjoint rectangles with complete surface hits and continuous source UVs
were selected. Their physical domains are approximately2.697×1.130m,
1.598×1.130m and1.498×1.130m. The measured data, fitted broad planes and retained
residuals/UVs are in `candidate06-cc0-patches.json`; the original raw probe is
preserved separately. This avoids projecting the entire disconnected texture
atlas across new geometry.

Uniform detail scales range from2.25638 to2.73816. Sampled relief is applied
radially to the existing bounded faces, without changing height ordering; the
CC0 source is not stretched into a whole mountain. Reflected reuse and bilinear
sampling are explicit approximations, not a claim that these masses reproduce
the entire original scan or the locked concept. Mid-bed samples retain some
surface relief while avoiding03's dense uniform mesh. Each long lower mass is
split into two staggered groups. Upper groups and smaller front rocks remain
bounded; the strongly repeated procedural fracture depth is reduced.

Changed Far sides use the existing `Canyon_Cliff01` material and sampled original
UV regions; caps retain `Canyon_Sandstone` with physical UV projection. Neither
material nor image data is edited. Independent cold-file05/06 comparison verifies
all14 material graph/core states and52 linked images, including **135,457,211
exact packed bytes**, unchanged. See `candidate06-material-preservation.json`.

## Saved geometry checks

The36 changed meshes pass the unchanged primary UV cross `>1e-14`, physical
triangle cross squared `>1e-16 m^4`, no duplicate-triangle and closed-manifold
checks. Minima are6.253085604868147e-9 and0.008209921448724344 respectively.

After reloading the saved source, the same vertical ring/connectivity check
passes all90 components: **zero non-increasing edges, all expected connections
present, minimum upward difference1.3149070739746094m**. This preserves05's
demonstrated repair; it is not a complete arbitrary self-intersection test.

Whole-scene triangle totals are **2,017,316 / 996,229 / 403,721**. The extra
surface/group detail costs more than05; there is no native/runtime performance
acceptance or budget increase. The authoring check preserves616 other scene
meshes exactly, along with the fixed camera/light/world/color state and existing
material/image membership. Original source files, all previous candidates and
the protected Club retain their hashes.

The06 freeze manifest binds the source, actual render, CC0 inputs, scripts and
receipts. Work used only the owned direct pinned Blender MCP in safe mode on
port9877; no Unity, Jarvis, new remote service or paid asset job was used.
