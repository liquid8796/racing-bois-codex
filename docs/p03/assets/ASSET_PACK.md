# P03/P04 original gameplay assets

## Authorship and iteration history

All geometry and palette textures in this pack are newly authored. The Blender
recipe does not load any asset, image, mesh, animation or font from the reference
game. The source game remains research material only.

The first graybox was modeled before the user's additional requirement to make
a 2D concept first. Its source, recipe, preview and audit are retained as the
**initial graybox**, not presented as a concept-approved finished asset:

- `ArtSource/Vehicles/Archive/RB_InitialGrayboxPack.blend`
- `tools/p03/assets/archive/create_initial_graybox.py`
- `docs/p03/assets/initial-graybox-pack.png`
- `docs/p03/assets/initial-graybox-blender-receipt.json`
- `docs/p03/assets/initial-graybox-mesh-audit.json`

The subsequent revision followed the actual concept PNGs in
`ArtSource/Concepts/P03P04`, which were generated and visually inspected before
remodeling. `PROMPTS.md` records prompts and provider provenance. The user asked
for GPT Image 2.5; the exposed image-generation tool does not provide a model
selector or confirm that identity. No specific model identity is asserted.

| Concept | Changes made to the real mesh |
| --- | --- |
| Motorcycle | Angular amber tank and ivory stripe; twin circular headlights under graphite cowl; bronze fork; exposed engine fins; spoked wheels; twin short right-side exhausts; red rear lamp. |
| Rider | Ivory helmet with two amber stripes and navy visor; charcoal jacket with amber shoulders and two ivory sleeve bands; indigo jeans, knee armor and ochre gloves. |
| Coupe | Petrol-teal wedge body; tapered roof with sloped glass; modeled open-bottom wheel arches; rectangular headlamps, corner indicators and small rear lip. |
| Van | Tall ivory cargo body with sloped windshield; orange belt; charcoal sill/bumpers; modeled wheel arches; rear cargo door seam/handle; amber roof markers. |
| Pedestrian | New unhelmeted adult head with short dark hair; ivory pocketed vest, sage shirt, indigo trousers and ochre shoes; same articulated joint convention as our own new rider. |
| Canyon | Four layered irregular sandstone slabs and a small sage scrub cluster, with closed low-poly geometry and three authored LODs. |

These are gameplay-scale interpretations of the concepts. Fine fabric, tire
tread, engine mechanics and photoreal concept shading are not represented at
the same level of detail. The updated preview is `original-pack.png`; separate
previews are `pedestrian.png` and `canyon-props.png`.

## Geometry audits

The pinned local Blender MCP server executed the recipe in safe mode against
Blender 5.2.1 LTS. A separate read-only MCP script audited 48 mesh objects across
four vehicle/rider assets and three LODs each. Separate audits covered 33
pedestrian mesh objects and six canyon mesh objects: **87 meshes total**. The
initial graybox receipts remain archived; current independent receipts are
`independent-mesh-audit.json`, `independent-pedestrian-audit.json` and
`independent-canyon-audit.json`. All passed:

- Closed manifold edges and consistent winding.
- Positive signed volume for every disconnected component.
- No loose vertices, degenerate faces or duplicate vertices within components.
- Finite UV coordinates inside 0–1; each face remains within one palette tile.

UVs deliberately reuse flat-color palette tiles across parts and LODs. This is
intentional material reuse; the pack does not claim a unique detail-texture atlas.
Base-color, normal, metallic/smoothness and roughness maps are generated directly
from authored colors and surface values. Vehicle/rider maps are 256px;
pedestrian maps are 128px; canyon base color is 128px and surface maps are 32px.

| Revised asset | LOD0 triangles | LOD1 | LOD2 | Renderers per LOD |
| --- | ---: | ---: | ---: | ---: |
| Motorcycle / police motorcycle | 4,192 | 2,176 | 1,290 | 3 |
| Articulated rider | 3,744 | 1,872 | 892 | 11 |
| Traffic coupe | 5,656 | 3,064 | 1,466 | 1 |
| Traffic van | 7,080 | 3,758 | 1,700 | 1 |
| Pedestrian | 1,624 | 834 | 642 | 11 |
| Sandstone | 112 | 60 | 32 | 1 |
| Sage scrub | 72 | 40 | 20 | 1 |

## Runtime contract

`RaceAssetBuilder.Setup()` imports the authored FBX, configures desktop WebGL
texture compression, creates four distinct URP materials and saves eight prefabs.
Police shares
the motorcycle mesh with a separate navy/ivory palette. Prefab roots use position
zero, identity rotation, unit scale and one simple collider. Dynamic assets use
light probes instead of static lightmaps. The two static canyon props include
secondary UVs and keep their tiny source meshes readable for startup combining.
The presentation layer disables their Unity colliders because shared
authoritative simulation owns collision outcomes.

Rider joints are rigid articulation nodes, not a Humanoid avatar. Each of three
LODs retains the same logical joints:

`RB_Rider_L{0,1,2}_{Hip,Torso,Head,UpperArm_L,UpperArm_R,Forearm_L,Forearm_R,Thigh_L,Thigh_R,Shin_L,Shin_R}`

Wheel nodes are `RB_Moto_L{0,1,2}_Wheel_Front` and `_Wheel_Rear`. Client animation
must apply the pose to every LOD and preserve the imported rest rotation. The
pedestrian uses the equivalent `RB_Ped_L{0,1,2}_` names.

Nested FBX empty joints require explicit coordinate handling: export stores
unit conversion in `FBX_SCALE_ALL` metadata and leaves experimental
`bake_space_transform` off. The prefab has an identity root and a child named
`Model` that preserves the imported rotation and premultiplies a 180° Y turn.
The authoring helper reflects X before writing geometry; normals are rebuilt
outward. No negative-scale prefab workaround is used. The importer validates
that the front wheel points toward gameplay +Z and the left arm remains on −X.
Procedural poses convert the desired Unity rotation through the `Model` basis.

`source-manifest.json` binds source, concepts, export files and current audit
receipts by SHA-256. `unity-validation.json` records actual imported prefab
validation separately; source geometry checks alone do not substitute for it.

Unity 6000.5.7f1 validation **passed for all eight prefabs**: expected three LODs,
identity root, one simple collider, one material per renderer, normals/tangents/
UVs, correct imported meter scale, motorcycle +Z orientation and character
left/right anatomy, and no missing scripts. The report's imported bounds agree
with the independent Blender audit to floating-point/import tolerance.

## Remaining production gates

This is P03/P04 gameplay art. Final P06 quality still requires approved high
detail art direction, deforming character skin/rig, authored and cleaned
animation clips, action silhouettes reviewed at gameplay distance, and measured
browser performance under the final scene/light/VFX budget. The mesh audit does
not prove final animation or frame-rate acceptance.
