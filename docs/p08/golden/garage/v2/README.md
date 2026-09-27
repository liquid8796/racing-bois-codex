# Garage V2 — candidate for native indoor calibration

The original 3D workshop was revised against the inspected `garage-environment-v1.png` and unchanged `UI/garage-v2.png`. V2 narrows the toolboard, separates three larger loose wrenches, adds a closed helmet and visor prop, darkens the near concrete finish, lowers the overhead beams, reduces warm spill and balances the doorway fill. Powder coat and helmet paint now use dielectric metallic values; bare tool steel remains metallic. Drawer pulls have rounded physical profiles for highlights.

`descriptor.json` binds 48 inputs, 60 independently culled modules, 180 renderers, 13 PBR materials and 20 explicit box colliders. Source LOD triangle counts are 132,592 / 28,712 / 4,508. The actual FBX reimport has exactly 165,812 triangles, with identical per-mesh coverage/counts and zero physical area failures (`minimumWorldCrossSquared = 2.968436263230732e-16`, gate `>1e-16`). The final source audit found no open or non-manifold edges, invalid UV values or non-finite vertices. The floor intentionally extends 0.18m below its y=0 anchor; room bounds are 12 × 3.48 × 11.998m. V1 is preserved.

The frozen source is `ArtSource/P08/Golden/Garage/V2/RB_Golden_Garage.blend`; the real CPU render is `gameplay.png`. `source-audit-final-mcp.json`, `roundtrip-mcp.json`, `export-mcp.json` and `render-final-mcp.json` bind actual operations. Downloaded CC0 inputs and the protected user club remain unchanged.

**Visual acceptance remains false.** Compared with the locked reference, concrete has excessive horizontal grain, cabinet/shelf layouts and smaller prop details differ, the room perspective is too frontal, fixtures/glow differ, and the floor highlight shapes and distribution are still mismatched. The helmet is a background approximation and does not establish an approved rider helmet. No fabricated similarity percentage is reported. Native Unity lighting, UV chart overlap, gameplay-distance appearance and frame/memory measurements remain unverified.

`lighting.json` records the actual Blender source. `unity-lighting-initial.json` adds explicit **unmeasured initial Unity intensities** for the root-owned native bake; those values are not a conversion from Blender watts. The staged indoor builder and compile proof live outside Assets in `tools/p08/golden/garage-staging/`. A real bake must produce valid lightmap bindings and a saved local reflection before its scene receipt can pass. That pass still does not grant visual fidelity or production acceptance.

FBX SHA256: `76b960292653165f6a101657a59fe032dd767d2da92d6ec37f3c002a6da3997c`.
Source SHA256: `b57f26d6e03ae2b9f15e41fd613c2e03a75fcaf88a615e77fa5e3d00fdcee77c`.
