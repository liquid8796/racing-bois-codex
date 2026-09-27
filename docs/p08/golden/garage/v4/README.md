# Garage V4 — authored lightmap UVs, visual review pending

The room retains the locked garage-environment-v1 concept and garage-v2 UI reference. V2 geometry, material assignment, normals, primary UV coordinates and PBR files remain unchanged. V4 changes the lightmap channel and its export order; it is not a new visual design and is not accepted for production.

Unity's generated secondary UVs collapsed 2,472 valid bevel triangles in V2. Changing unwrap angles, tolerances and coordinate scale did not repair them. The isolated xatlas0.0.9 trial also collapsed triangles and produced conflicting polygon corners, so it was rejected. The Python bindings and their remapping contract were inspected in the [upstream project](https://github.com/mworchel/xatlas-python). No external inference service was used.

Blender Smart UV Project produced the dedicated LightmapUV layer on 60 LOD0 modules. Before/after comparisons assert exact preservation of vertices, triangle indices, corner normals and primary UVs. The independent Shapely2.0.7 triangle-intersection audit covers 132,592 UV triangles: no degenerate triangle and no positive-area overlap above1e-14; the minimum UV cross product is6.591900358898783e-10. These are geometric UV checks, not lightmap appearance or texel-density acceptance.

The first V3 native import correctly failed: DisplayHelmet and ToolboardAndWrenches retained an unused UV_MetricTile layer between UV0 and LightmapUV. V4 removes only that unused intermediate layer after confirming materials have no named UV-map node. Exact primary/lightmap values are preserved and the lightmap becomes channel1. Source/export and failed native receipts remain available in V2/V3; nothing was rewritten to hide a failed attempt.

Actual Unity V4 import passed with source binding at attempt fcc8d0cd5d504decb8997bea2a52b8d0. The importer now accepts an explicit authored lightmap policy and verifies finite, bounded, nondegenerate LOD0 UV1 data. Legacy descriptors still default to generated UVs, verified in the running engine. Lower LODs receive light probes in the isolated indoor review scene.

The explicit Progressive CPU bake began at23:07UTC on2026-09-26. A scene-creation receipt is deliberately not a passed bake. Completion, real renderer/lightmap bindings, reflection data, native pixels and console diagnostics must still be verified. The room's composition, surface response and prop detail remain below the locked concept; no production content masks changed.

Evidence: ../v3/uv-validation.json, uv-channels-mcp.json, export-mcp.json, roundtrip-mcp.json, descriptor.json, unity-lighting-initial.json and the timestamped Unity import receipts.
