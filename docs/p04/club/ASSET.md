# Original club prop

The successful `ArtSource/Concepts/P03P04/club-concept-v1.png` was visually
inspected before modeling. Its rounded honey-colored wood body, charcoal fabric
grip and amber collar guide this new mesh. No pixels, meshes or textures from
the reference game were used. The concept image is a design reference, not a
runtime texture. Its image-generator provenance remains in the concept folder.

The pinned Blender MCP executed `tools/p04/club/create_club.py` in safe mode on
Blender 5.2.1 LTS. The initial factory scene was inspected, then saved to a
task-local checkpoint before clearing it. Every texture pixel is authored by
the recipe's analytic grain, knot and fabric-weave functions in Blender.

## Files and attachment contract

- Source: `ArtSource/Weapons/RB_Club.blend`, including packed authored maps.
- Runtime source: `Assets/RacingBois/Art/Weapons/Club/RB_Club.fbx` and maps.
- Prefab: `Assets/RacingBois/Prefabs/RB_Club.prefab`.
- Importer: `RacingBois.Authoring.Editor.ClubAssetBuilder.Setup()`.
- Render: `docs/p04/club/club-render.png`, rendered from the actual mesh.

The prefab's identity root is at the grip/palm attachment point. The prop extends
along local **+Y**, with `ClubTip` at `(0, 0.475, 0)` and `ClubButt` at
`(0, -0.075, 0)`: total length **0.55 m**, maximum diameter **0.09 m**. Parent the
prefab root to the chosen hand anchor and rotate its +Y shaft toward the desired
held direction. Do not replace the imported `Model` child's coordinate basis.
`GripOrigin` is exactly at the root pivot.

The FBX uses the previously verified `FBX_SCALE_ALL` metadata policy, with
experimental `bake_space_transform` off. The authoring helper maps intended
Unity coordinates `(x,y,z)` to Blender `(-x,-z,y)` and recalculates outward
normals. The importer preserves the FBX model rotation under an identity root
and premultiplies its 180° Y conversion. No negative prefab scale is used.

## Budgets and material

| Item | Value |
| --- | --- |
| LOD0 / LOD1 / LOD2 | 1,080 / 384 / 160 triangles |
| Renderers | One per LOD; only selected LOD renders |
| Material | One shared URP Lit material |
| Base color | 512 × 512 |
| Normal / metallic-smoothness / roughness source | 256 × 256 each |
| WebGL texture import | Compressed DXT5 with mipmaps, desktop-browser target |
| Collider | One Y-axis CapsuleCollider, centerY0.20, height0.55, radius0.045 |
| Lighting | Imported smooth normals; Unity Mikk tangent generation; dynamic probes |

Wood is nonmetallic, cloth is rough, and the small amber collar is moderately
reflective. URP smoothness is stored in mask alpha with scalar multiplier1.
The standalone roughness source is retained for DCC interchange; URP uses the
packed metallic/smoothness map. No baked lightmap UV2 or animation rig is needed
for this dynamic rigid hand prop.

The capsule is a conservative simple query/selection proxy. The presentation
must disable it when attaching the prop because the authoritative combat core
decides reach, cooldown and damage. Rendering the prop does not extend hit range.

## Validation and limits

The independent read-only `inspect_club.py` audited all three LODs. Its exact
triangle intersection test found **zero UV overlaps within each LOD**, zero
out-of-bounds UVs and zero degenerate UV triangles. LODs intentionally reuse the
same texture atlas. Wood, fabric and collar have separate atlas rectangles.

Each LOD has three closed components with positive volume. The audit found zero
nonmanifold edges, inconsistent winding, degenerate faces, loose vertices or
duplicate positions within components. Component intersections under the grip
and collar are intentional assembly overlap, not shared or dangling topology.
Results are recorded in `independent-geometry-uv-audit.json`.

`ClubAssetBuilder.Validate()` separately checks the actual imported prefab:
identity root, grip/tip/butt coordinates, expected size, decreasing LOD geometry,
one material, one capsule, normals/tangents/UVs and no missing scripts. It writes
`unity-validation.json` only after passing. The actual Unity 6000.5.7f1 import
check **passed**, with bounds `(0.090001, 0.550001, 0.090001)` meters, the expected
1,080/384/160 triangle LODs, correct grip/tip/butt markers and no missing scripts.
Root integration then attached the prop through `WeaponGripView` to the articulated
left/right palm, preserving the imported model basis and original material.
`unity-left-attack.png` and `unity-right-attack.png` show the actual in-hand
poses; the integration check produced no Unity console warnings or errors.
The collider is disabled while equipped, and Fist/Chain state hides this club.
The P05 browser also displayed the club on an authoritative opponent. These
checks do not claim final P06 animation or visual fidelity acceptance.

This is a game-ready rigid prop within the current P03/P04 art direction. Fine
grain and wrap detail reduce naturally at gameplay distance; the rendered mesh
does not claim pixel-for-pixel parity with the painted concept sheet.

## Reproduce

Run the two scripts using the existing pinned `tools/blender/mcp_client.py`
`execute_blender_code` workflow, first `create_club.py`, then `inspect_club.py`.
Import with `ClubAssetBuilder.Setup()` in Unity. Finally run
`tools/p04/club/write_manifest.py` to bind the concept, recipe, source, export,
maps and available validation evidence by SHA-256.
