# P06 canyon environment — Unity integration

## Authorship and source boundary

The seven FBX models and five procedural PBR texture sets are authored by the parent agent's `tools/p06/create_environment.py`, following the inspected `ArtSource/Concepts/P06/canyon-v1.png` concept. The script is executed through the live Blender MCP by the parent agent. This Unity integration does not copy original-game meshes or textures and does not edit the P03/P04 asset sources. It reuses the approved RockB mesh at its lowest LOD for distant mesa silhouettes.

## Import and prefab contract

Run `RacingBois.Authoring.Editor.P06EnvironmentAssetBuilder.Setup()` after the Blender export is finished. It imports only `Assets/RacingBois/Art/P06/Environment/`, writes materials under `Assets/RacingBois/Materials/P06/` and prefabs under `Assets/RacingBois/Prefabs/P06/`.

| Prefab | Material set | Collider when dragged into a scene |
|---|---|---|
| RB_P06_RockA | Sandstone | One conservative BoxCollider |
| RB_P06_RockB | Sandstone | One conservative BoxCollider |
| RB_P06_Sage | Foliage | None: non-solid foliage |
| RB_P06_DryGrass | Foliage | None: non-solid foliage |
| RB_P06_Guardrail | Roadside | One BoxCollider |
| RB_P06_Chevron | Roadside | One BoxCollider |
| RB_P06_UtilityPole | Roadside | One vertical CapsuleCollider for the main pole |

Every prefab has an identity root, a preserved FBX conversion basis with the established +Y180 correction, three descending LODs, one mesh renderer/material per LOD and static batching/occludee/reflection flags. The scenery is dynamically lit: no baked lightmaps or required lightmap UV are claimed. Normals import from Blender; Unity calculates Mikk tangents. Source meshes remain CPU-readable only because the ribbon combines placements once at startup. The generated runtime meshes discard their CPU copy after upload.

Sandstone and Roadside maps are 1024 square; Foliage, Asphalt and Gravel are 512 square. BaseColor is sRGB; normal/mask/roughness are linear. Normal maps use Unity's NormalMap importer. URP Lit uses the metallic RGB/red and smoothness alpha map with smoothness texture channel zero. Roughness maps are retained as source interchange data, not sampled redundantly by the Unity material. WebGL overrides use DXT1 for opaque color/roughness and DXT5 for normal/metallic-smoothness; mipmaps are enabled. Roadside/Foliage atlas edges clamp; tiled ground/rock surfaces repeat. No duplicate material is created per placement.

`Validate()` writes `unity-validation.json` after checking root identity, imported scale/pivot bounds, three descending LODs, renderer/submesh/material counts, normals/tangents/UV/readability, atlas UV bounds, texture importer flags, collider budget, static flags and missing scripts/references. It must be run against the real imported kit. No PASS receipt is fabricated before that run. Topology and intentional component UV reuse remain covered by the Blender receipt and visual inspection; this Unity validator does not claim an independent exact UV-overlap audit.

## TrackRibbonView assignments

Retained fields and assignments:

- `Asphalt` → `RB_P06_Asphalt`; `Shoulder` and `Landscape` → `RB_P06_Gravel`.
- `SandstonePrefab` → `RB_P06_RockA`; `SageScrubPrefab` → `RB_P06_Sage`.
- Existing Paint/YellowPaint remain the previous road-marking materials.

New fields:

- `RockBPrefab`, `DryGrassPrefab`, `GuardrailPrefab`, `ChevronPrefab`, `UtilityPolePrefab` → corresponding P06 prefabs.
- `WireMaterial` → `RB_P06_Roadside`. Cables sample the dark tile of this existing atlas.
- `ViewCamera` → the gameplay camera. If unassigned, Build resolves Camera.main once.
- `SetSceneryQuality(int)` → 0/1/2 chooses 440/650/850 m chunk distance; the composition root's existing graphics quality service still owns global LOD bias, shadows, render scale and camera far plane.

No rideable-road changes are made: centerline, track sampling, asphalt ±6.5 m, shoulders to ±9 m, edge/center markings, physical simulation and contact rules are preserved. Ground variation begins beyond 10 m. Ground ribbons stay within ±110 m, safely inside the shared route's tightest 139 m inner bend radius. Far mesas are separate source-mesh placements; their footprints are rejected if too close to sampled road sections, including bends that bring another part of the route nearby.

Visible additions: varying-height eroded tower groups, broader rock shelves, clumped sage and dry verge grass, outer-bend guardrails and chevrons, a continuous utility line with 64 m pole spacing and three sagging wires. Pole axes stay vertical on road grades. Guardrails/signs sit outside the gameplay shoulder. These render-only placements do not create a second collision authority.

## Bounded rendering and evidence

The 2.2 km route is built once in 160 m chunks. Each asset type becomes at most three combined mesh renderers per chunk, one per LOD; individual instances do not become GameObjects. Low-poly distant mesas use the existing RockB LOD2 source and one material batch. Chunk bounds are checked at 5 Hz and only change active state when needed. Existing Unity frustum culling and per-batch LOD continue within active chunks. There is no mesh rebuild, per-prop update, scatter randomization, allocation or object churn in LateUpdate.

Scenery adds a deliberate startup/memory and triangle cost relative to the sparse P05 track. Runtime evidence is exposed through `ChunkCount`, `ActiveChunkCount`, `RuntimeMeshCount` and `RuntimeTriangleCount` (all allocated LOD triangle counts, not the camera's rendered-triangle count). The parent report must measure browser frame times, memory and draw calls with the actual imported kit at Low/Medium/High; none is marked PASS from source inspection alone.

Remaining coordinated acceptance: parent runs Unity import/validation, inspects daylight normals/materials/sign direction/pivot scale, drives the full route for silhouette placement and culling transitions, and captures both Unity and Web results. Physical LAN, worldwide networking and P05 remote-contact residual limitations are unaffected.
