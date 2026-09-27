> Historical candidates: V12 has confirmed road/left-shoulder winding errors. The initial V13/V14 triangle failures were partly caused by testing unscaled mesh-local coordinates; root corrected the validator to physical metres. V14 passed native geometry/module checks but failed visual inspection because the scan skins have open backs. V15 is being repaired and must not be treated as accepted.

# Canyon candidate V12 — visual acceptance remains open

This is an isolated 80m review segment authored against the inspected and locked `ArtSource/Concepts/P08/Golden/canyon-v2.png`. It is **not accepted for production** and does not establish 100% concept fidelity. The production route, prefabs and content masks were not changed.

## Actual evidence and remaining differences

`gameplay-v1.png` through `gameplay-v12.png` are actual Blender CPU renders, not generated concepts or pasted backgrounds. The first five candidates were rejected during iteration: block-like synthetic geology, discontinuous heightfield walls, poor distant massing and incorrect lighting. V6–V8 replaced those walls with locally modified natural geometry and corrected the road-side orientation, framing, atmospheric depth, foreground boulders and road-line edges.

V12 still differs visibly from the target:

- The distant formation silhouettes and gaps do not reproduce the concept's continuous canyon mesas and layered valley.
- The near cliff uses modified Karoo scan geometry; its specific fractures, plates, face angles and bedding do not reproduce the generated sandstone reference exactly.
- V8 close-ups exposed excessively thick stems and geometric leaves. V9�V12 replace them with millimetre-scale branching, smaller curved leaf outlines, denser secondary shoots and explicit upper-face normals. Foliage placement, density and leaf response still require matched reference review.
- Road lines are too clean, shoulder wear is too regular, and the asphalt does not yet have the same dust/gravel distribution as the concept.
- The reference's low sun, bright warm haze, clouds, contrast and reflected light are not matched by the current authoring lighting.
- Technical source checks, renderer counts and successful FBX export do not clear any of these visual differences. There is no invented similarity percentage.

A live texture-cache defect was also found and repaired: Blender reused old pixels after source PNG regeneration. The recipe now explicitly reloads every referenced image before packing. `images-refresh-v11-mcp.json` records the actual before/after image values; the V11 onward packed source and render use current disk textures. Earlier dark foliage previews are not current texture evidence.

V12 also fixes 16-bit grayscale normalization: four scanned rock roughness inputs are I;16 PNGs, which must be normalized by 257 before packing 8-bit maps. The old conversion saturated them to 255. `tools/p08/golden/canyon_verify_textures.py` now checks every source roughness/AO pixel, mask channel, resolution and exact input hashes; `scalar-packing-check.json` records the successful current-data check.

Current source geometry: **991,985 / 495,936 / 204,607 triangles** across the three LOD sets, with 13 material bindings. Source geometry checks report zero nonfinite vertices, zero degenerate polygons and populated finite UVs. These are scoped source checks, not a universal asset pass.

Root owns actual Unity import, rendering and player validation. No native frame-time, memory or game-route contact acceptance has been performed for this candidate.

## Source, export and coordinates

- Authoring source: `ArtSource/P08/Golden/Canyon/RB_Golden_Canyon.blend`.
- Candidate FBX: `Assets/RacingBois/Art/P08/Golden/Canyon/RB_Golden_Canyon.fbx`.
- Recipe: `tools/p08/golden/canyon_model.py`, executed by the direct pinned Blender MCP server on the dedicated port **9877**. The task-owned Blender process was restarted only after the former process and listener had ended; the replacement PID was 20164. Port 9876 was never accessed.
- Design coordinates are X lateral, Y up, Z along the road, in metres. Blender conversion is `(x,z,y)`, FBX `axis_forward=-Z`, `axis_up=Y`, explicit Unity model rotation zero. Actual Unity marker validation remains required.
- Markers: Forward `(0,0,5)`, Ground_Origin `(0,0,0)`, LeftRoadMarker `(-3.7,0,0)`, RightRoadMarker `(3.7,0,0)` in design coordinates.
- Root is identity. Eight independent 10 m road modules share analytical curve boundaries; cliff, boulder and rail meshes are separately named; three explicit renderer LOD sets are exported. Because the review descriptor spans distant scenery, its whole-asset LOD group is not a production streaming policy. A playable route must use per-module LOD/culling groups; otherwise the large bounds keep LOD0 active from the road camera.
- The segment includes distant scenery hundreds of metres away. Do not use total bounds to frame a gameplay screenshot: use Unity camera `(1.7,1.55,3)` looking toward `(-2,-2.6,32)`, equivalent 28 mm focal length/36 mm sensor, aspect 2:1. The Blender camera has these same semantic coordinates.

## Material and geometry treatment

Thirteen exact named material bindings preserve source UVs and material separation. Six scanned/tiled surface sets use2048² maps and seven small foliage/metal/paint sets use512². These are candidate budgets, not a proof that every close view has sufficient texel density. The descriptor drives URP Base Color, tangent Normal, MetallicR/SmoothnessA and optional OcclusionG maps. The original OpenGL normals require the actual Unity lighting check. Opaque sage/grass explicitly request double-sided rendering; correct backlighting still needs visual inspection.

Road UVs intentionally tile a 3 m scanned surface; shoulder/gravel UVs intentionally tile every 2 m. Scan UVs are retained through local transformation and decimation. Tiled UV overlap is intentional; a unique lightmap unwrap is left to the isolated Unity static-asset importer. There are no duplicate material slots created to pad asset counts.

W-beam guardrail geometry includes the corrugated face, posts, bases, bolts and amber reflectors. Vegetation uses actual branches, lanceolate leaf polygons and grass blades. CPU rendering is explicitly capped at four threads; no GPU render was used.

The review descriptor declares **zero colliders**: this specimen is presentation-only and is not connected to the existing authoritative road/obstacle simulation. It must not be substituted into a playable route as if collision/grounding were validated. Actual course integration requires mapping the analytical road and guardrail to the simulation and adding only the necessary primitive obstacle colliders. There are no hidden MeshColliders.

## Licensed local dependencies

All generation and processing used local/free tools. There were no paid image-to-3D jobs or Jarvis MCP calls. Geometry is not extracted from Road Rash or another game.

The original road/rail/foliage/composition uses CC0 Poly Haven surface inputs `rock_face`, `asphalt_02`, and `brown_mud_rocks_01`. Exact upstream URLs, sizes, MD5 and SHA256 are in `ArtSource/P08/Golden/Canyon/Materials/PROVENANCE.json`.

Natural geometry dependencies are [Namaqualand Cliff01](https://polyhaven.com/a/namaqualand_cliff_01), [Namaqualand Cliff02](https://polyhaven.com/a/namaqualand_cliff_02), and [Namaqualand Boulder02](https://polyhaven.com/a/namaqualand_boulder_02), under the [Poly Haven CC0 asset license](https://polyhaven.com/license). Their exact 15 downloaded files, original URLs, upstream MD5 and local SHA256 are recorded in `ArtSource/P08/Golden/Canyon/SourceModels/PROVENANCE.json`. Local changes include tinting, rock-face placement, nonuniform shape changes, top erosion, multi-scale arrangement and independent decimation. These are disclosed scan dependencies, not falsely claimed as wholly self-authored scan geometry.

## Reproduction and inspection

1. Run `python tools/p08/golden/canyon_textures.py` to derive the PBR maps from existing licensed local inputs.
2. In the dedicated task-owned Blender instance only, execute `canyon_model.py` through `tools/blender/mcp_client.py execute_blender_code --port 9877`.
3. Run `canyon_render.py` and `canyon_detail_render.py` through that same MCP instance. Inspect actual renders before changing any visual-acceptance status.
4. Run `canyon_audit.py` through MCP to `source-audit-mcp.json`; run local `canyon_descriptor.py`. The descriptor is generated only when current geometry has no nonfinite vertices, degenerate polygons or invalid/missing UV values. These checks do not validate closed volumes, every-angle appearance or full UV overlap.
5. Root can pass the fresh `docs/p08/golden/canyon/descriptor.json` to `GoldenSampleBuilder.Import`, then inspect actual Unity views and LOD transitions. Preserve the unaccepted status until remaining visual and runtime gates are resolved.
