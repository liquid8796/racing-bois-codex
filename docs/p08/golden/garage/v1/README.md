# Garage V1 — unaccepted inspection candidate

An actual 3D workshop, authored through direct Blender MCP port9877 after inspection of `garage-environment-v1.png` and the unchanged `UI/garage-v2.png`. The room is not a raster backdrop. Geometry, lighting and camera are separately inspectable.

The saved source, FBX, 10 material bindings and 59 module LOD map are bound by `descriptor.json` (38 exact inputs verified). The source has 177 closed mesh renderers and 121,336 / 26,464 / 3,936 triangles across its three LODs. The actual exported FBX roundtrip preserves each mesh's triangle count and passes the physical metre-space area gate. Root transforms and forward/left/right/ground markers are explicit. Bounds are 12 × 3.8 × 11.998m; the floor extends 0.18m below the ground anchor.

Twenty explicit box colliders represent the slab, walls, pier, ceiling, major cabinets, countertop and rack. There is no whole-room solid box or MeshCollider. Material UV tiling intentionally overlaps between repeating surfaces and is measured in metres (floor 2m, concrete 2.2m per tile). Lightmap UVs and native lighting remain to be generated and inspected in Unity.

## Evidence and limitations

`source-audit-final-mcp.json`, `roundtrip-mcp.json`, `export-mcp.json`, `render-refined-mcp.json` and `gameplay-refined.png` describe actual source/export/render operations. The earlier first render showed displaced furniture due to stale transform evaluation while moving mesh origins. That error was fixed with an explicit new matrix, and the final measured bounds and renders use the corrected source.

V1 is **not accepted against the concept**. Visible differences remain in wall grain (too horizontal), furniture detailing and steel highlights, missing helmet, practical-light glow and floor reflection, and perspective/composition. An import or mesh PASS does not waive those differences. The final UI target remains the unchanged garage-v2 concept, not this candidate render.

`lighting.json` records source camera and six physical strip fixtures plus the doorway fill. Blender watts are explicitly not asserted to equal Unity light intensity. Native indoor review needs appropriate baked area-light GI, emission and local reflection capture; a Canyon sun/HDRI recipe is not equivalent. No performance claim is made before native measurement.

CC0 surface sources and exact download hashes are in `ArtSource/P08/Golden/Garage/Materials/PROVENANCE.json`. The floor coating transformation and all packed textures are recorded in `textures.json`; scalar 16-bit maps are normalized rather than saturated. All geometry is authored for this room from the generated reference, not recovered from the original game.

FBX SHA256: `cbf9594c02d6f668401338950bc4e0320d012a8a0460ff07ef40870541b1fd38`.
