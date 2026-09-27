# Apex golden sample authoring contract

Original preflight plan, retained for comparison. Apex v2 concept clearance was subsequently received; current candidate results and remaining gates are in [README.md](README.md).

The September 26 review rejected the existing Apex hero shape. Its identity is preserved as gameplay bike 05, but this candidate uses a separate source/export directory and does not overwrite the current prefab or GUIDs. The user-owned Club source is outside this task.

## Shape and construction

Use the reviewed concept as the visual specification. Compact sport proportions, fitted multi-piece fairing, a tank with knee recesses, tapered seat/tail, connected windscreen, recessed intake and lamp assemblies, clip-ons, substantial brake assemblies, routed headers and paired under-seat exhausts must read together in side, front three-quarter and rear gameplay views. Final dimensions depend on that concept; initial engineering envelope is approximately 2.05 m long, 1.43 m wheelbase, 0.82 m saddle height. No old motorcycle template or unchanged common stance is accepted as the new design.

Primary visible surfaces use purpose-built rings, sweeps and panel boundaries. Manufacturing primitives are appropriate for real cylindrical components such as fork stanchions, fasteners and hubs; they are not a substitute for authored main bodywork. Panels need thickness and assembly gaps. Mechanical details are positioned from the actual axle, engine, chassis and steering layout.

## Unity contract

- Meters, positive forward axis verified in Unity, identity root and ground-level origin.
- Three separate LOD levels; body plus rotating front/rear wheels with axle-centered `*_Wheel_Front` and `*_Wheel_Rear` parents.
- Export hand grip, seat and foot contact markers in semantic Unity coordinates for the rider golden sample.
- Three or four materially distinct surface groups with useful UV coverage. Paint/fairing 2048 px, mechanical and rubber/upholstery 1024 px are proposed limits, not evidence that detail is sufficient.
- BaseColor, tangent-space Normal and MetallicSmoothness maps; roughness source saved. Metallic occupies R and smoothness is 1 minus roughness in A. Colour is sRGB; data maps are linear. An emissive lamp material is allowed if the actual concept requires it.
- Proposed triangle envelope: 45–65k close-up, about 24k middle and 8k far. Counts can change only with documented visual and native-player cost evidence. LOD silhouette and material preservation must be inspected.
- Dynamic motorcycle: static flags off; no MeshCollider. Collision proxy remains an explicit gameplay integration check.

## Evidence gates

1. Concept is generated, viewed and recorded before new geometry.
2. Real Blender MCP scene inspection before reset; save the old task scene within this candidate's source folder.
3. Save new `.blend`, FBX and maps; render beauty, orthographic side and rear views. Inspect the images and fix visible failures before handoff.
4. Capture current mesh/UV/material/LOD counts and contact dimensions. Hash the exact input and output files rather than reusing the old PASS receipts.
5. Root imports with a dedicated golden importer. The old P08 importer would collapse all materials into one atlas and must not be used unchanged.
6. Candidate acceptance remains pending until Unity close-up/gameplay views, wheel rotations, rider contacts and performance are checked. A Blender render or structural report alone never earns production-ready status.
