# P02 — Independent Blender QA: RB_RoadBarrier

Inspected 2026-09-21 through a real MCP `initialize → tools/call` session using Blender 5.2.1 LTS, addon protocol 7, loopback endpoint `127.0.0.1:9876`. Inspection was read-only: no scene operators, topology edits, material edits or `.blend` saves. Derived loop-triangle caches and a detached bmesh copy were used for measurements.

**Result: PASS for Blender source geometry, UVs, materials and texture files.** This is one foundation asset and does not certify the final game's art quality, Unity importer settings, prefab integrity or browser performance.

Evidence: [machine summary](barrier-qa-summary.json), [full geometry/UV inspection](barrier-inspection.json), [MCP receipt](barrier-qa-mcp.json), [root-object MCP receipt](root-object-mcp.json).

| Check | LOD0 | LOD1 | LOD2 |
|---|---:|---:|---:|
| Triangles | 252 | 126 | 50 |
| Vertices | 128 | 65 | 27 |
| Polygon faces | 126 | 80 | 27 |
| Connected mesh components | 1 | 1 | 1 |
| Non-manifold edges | 0 | 0 | 0 |
| Inconsistent winding edges | 0 | 0 | 0 |
| Degenerate faces/triangles | 0 / 0 | 0 / 0 | 0 / 0 |
| Loose / duplicate-position vertices | 0 / 0 | 0 / 0 | 0 / 0 |
| Signed volume, m³ | 0.723528 | 0.714097 | 0.692213 |
| UV islands | 6 | 6 | 6 |
| Positive-area UV triangle overlaps | 0 | 0 | 0 |
| Degenerate / out-of-range UV triangles | 0 / 0 | 0 / 0 | 0 / 0 |
| UV0 occupied triangle area | 68.283% | 67.744% | 66.979% |
| Largest dimension difference from LOD0 target | <0.001 mm | 2.654 mm | 6.948 mm |

Positive signed volume, a single closed component and consistent adjacent winding support outward face orientation. UV overlap checks clipped every potentially intersecting triangle pair in each mesh; shared edges with zero intersection area were allowed, positive overlap area above `1e-9` UV² was rejected. Cross-LOD reuse of the same atlas is intentional and was not falsely flagged as overlapping islands.

The scene uses meters with `scale_length=1`. Root and every LOD have position/rotation zero, scale one, positive transform determinant. LOD0 bounds are `(-1,-0.32,0)` to `(1,0.32,0.9)` in Blender Z-up: **2 m × 0.64 m × 0.9 m, pivot at the ground plane**. Decimation slightly shrinks LOD1/2; their bounds remain within 7 mm of the original dimensions. This is acceptable for the small prototype prop, subject to an actual LOD transition review in Unity.

All three LOD objects use one shared material, `RB_Barrier_PaintedConcrete`, and material index 0. No unapplied modifier remains. Object names unambiguously identify the root and three LODs. Mesh datablocks for LOD1/2 retain Blender's `.001/.002` suffix on the LOD0 base name; this is internal source naming, while exported object names retain explicit LOD numbers.

Texture files were reopened independently with Pillow and their channels checked:

| Map | Resolution / mode | Value or evidence |
|---|---|---|
| Base Color | 512×512 RGB, sRGB | Nonconstant procedural diagonal orange/cream stripe bake |
| Normal | 128×128 RGB, Non-Color | Neutral tangent normal `(128,128,255)` throughout |
| Metallic/Smoothness | 128×128 RGBA, Non-Color | Red metallic 0; alpha smoothness `97/255 ≈ 0.38039` |
| Roughness source | 128×128, Non-Color | Constant `158/255 ≈ 0.61961`; preserved beside `.blend` |

The normal and material-property maps are intentionally constant for this simple prop; they demonstrate a complete import path, not fine surface detail. The Blender material preview links the base-color texture and uses Principled metallic/roughness values; the Unity side must configure the normal/mask maps, URP shader and platform compression explicitly.

The source recipe was inspected: it defines a new profile with explicit vertices/faces, recalculates normals, bevels, unwraps, builds a procedural stripe material, bakes it, and derives lower LODs. It contains no original-game import, `images.load`, FBX import or `open_mainfile` call. The `.blend`, FBX and all four newly generated texture files were hashed; none matches the original 374-file manifest. **Different hashes alone are not proof of new authorship**; the observed generation recipe and retained `.blend` provide the additional evidence.

Visual review used the generated [Blender render](../blender/barrier-render.png). The barrier has a readable silhouette, grounded proportions, coherent stripe placement and visible beveled edges. A static studio render cannot replace gameplay-distance or WebGL verification.

![Newly authored barrier under studio lighting](../blender/barrier-render.png)

Remaining Unity checks belong to the main P02 round trip: Y-up conversion and dimensions; URP material/map assignment; texture/mesh compression; LODGroup thresholds; primitive colliders; prefab missing references/scripts; Console asset warnings; baked-lightmap UV2 if used; and WebGL load/FPS/memory. Blender has UV0 only. No rig/animation is required for this static barrier.

The MCP server prints an addon-discovery warning while starting, then successfully handshakes with the live addon and returns Blender 5.2.1/protocol 7. This is a server discovery message, not a missing-material or mesh warning. The asset inspection itself reported zero failed checks.
