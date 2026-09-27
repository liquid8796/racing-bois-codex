# Ash V2 — complete inspection candidate, not accepted production art

The current asset has a coherent anatomical body/head foundation, fitted garments and gloves, protective panels, helmet/goggles/straps, boots, three skinned LODs, facial expression geometry, and twelve matching animation clips. **It does not yet meet the locked concept's 100% visual requirement.** Neither this source audit nor the diagnostic Unity descriptor grants visual, contact, performance or roster acceptance.

## Exact references and provenance

- Locked concept: `ArtSource/Concepts/P08/Golden/ash-v2.png`, SHA256 `6fa1090e13547df14e578f0ac77504ae5722d99a031a09e5f575c2775f9ce7e6`.
- Anatomical topology, morph/weight/joint data, eye/brow/hair foundation and selected garment/shoe foundations derive from MakeHuman/MPFB core **CC0 asset data**. They are not claimed as topology created entirely from scratch. Source checkout commit: `3edf9df0551765be43563d047888cf7877eb89b4`.
- No MPFB addon was installed or executed. The rejected addon-registration attempt remains recorded separately. Only plain OBJ/numeric asset data and the direct pinned Blender MCP were used; safe mode was not disabled.
- `ArtSource/P08/Golden/Ash/V2/provenance.json` binds original data hashes and targets. Adjacent license copies preserve the [upstream asset license](https://github.com/makehumancommunity/mpfb2/blob/3edf9df0551765be43563d047888cf7877eb89b4/LICENSE.md). System-pack source and license are listed by the [MakeHuman project](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html).
- No original-game production asset, Jarvis MCP, paid external generation service or API credit was used.
- The user's `RB_Club.blend` remains at protected SHA256 `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`.

## Current artifact contract

- Source: `ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend`.
- Runtime FBX: `Assets/RacingBois/Art/P08/Golden/Ash/V2/RB_Golden_Ash_V2.fbx`.
- Authoring-path descriptor: `descriptor.json`; its failed Unity path attempt is preserved. **Current Unity descriptor: `descriptor-unity.json`**, corrected from actual Generic import: three skins are direct model children, while markers and armature live below `RB_Golden_Ash_V2/`. Its rig root is the actual Hip bone. Both bind source/FBX/maps by SHA256.
- Original fifteen semantic bone paths are preserved. Thirty anatomical finger bones under the two hand bones bring the rig to **45 bones**, with at most four normalized skin influences per vertex.
- All twelve matching clips were authored for this anatomical rest rig. Actual Unity subasset names are `RB_P06_Rider_Rig|RB_Ride`, `...|RB_LeanLeft`, `...|RB_LeanRight`, `...|RB_AttackLeft`, `...|RB_AttackRight`, `...|RB_KickLeft`, `...|RB_KickRight`, `...|RB_Hit`, `...|RB_Fall`, `...|RB_Run`, `...|RB_Remount`, `...|RB_Idle`. `__preview__` editor subassets are excluded. Old P06 translation curves must not be applied to this different rest anatomy.
- Descriptor model yaw is **180 degrees**. Real Hand_L/Hand_R bone paths provide semantic side checks; a synthetic forward marker alone is insufficient. Unity must independently confirm +Z forward and -X/+X left/right.
- Final curved-optics LODs contain approximately **99,339 / 42,124 / 12,706 triangles**. These are measured inventories, not an FPS claim. Dense and editable authoring parts are retained in hidden source collections and excluded from FBX export.
- Thirteen material bindings use fifty-two final Base Color, tangent Normal, Metallic/Smoothness and Occlusion maps. The exported files total **19,940,142 bytes**. Sizes range from 512 to 2048. Hair/brow sheets require explicit alpha and double-sided treatment. `rig-data-provenance.json` also binds the pinned anatomical base, joint metadata and detailed skin-weight dataset.

## Verification performed and its limits

`runtime-audit.json` measures geometry, UV and skinning, plus five actual deformation samples for every clip. The current audited runtime meshes have zero degenerate geometry/UV triangles, zero edges shared by more than two faces, zero invalid weight sums, finite UVs, and at most four influences. Remaining open borders are intentional hair/brow alpha sheets, not garment openings. The stricter Unity cross-product-squared threshold `1e-16` was independently checked in `unity-threshold-probe-mcp.json`; none of the frozen Ash triangles fell at or below it.

The audit caught and repaired real defects rather than weakening gates: sliced trouser hems, welding of touching closed cuff seams, collapsed brass-rivet bevel triangles, and collapsed optical rim UVs. UV layers were normalized to `UV0` **before joining** because Blender joins layers by name; otherwise the helmet's `UV0` and imported `UVMap` data occupied different channels. The original image lookup coordinates are retained in `UVSource` during baking.

The texture files are actual Blender property/AO bakes. `pack_pbr_maps.py` performs only engine channel packing and numeric validation; it does not paint, warp or invent albedo artwork. `texture-bindings.json` records fresh FILE loads, explicit reload, forced lazy decoding and packing. `packed-texture-verification.json` verifies all fifty-two final PNGs by SHA256 against complete CRC-valid PNG byte streams in the saved `.blend`, paired with those live bindings. The binary verifier recognizes Blender 5.2's newer header and does not invent SDNA ownership from an obsolete block parser.

The `runtime-*` and `portrait-*` images are **Blender renders of the runtime meshes and baked maps**, not Unity player screenshots. The long first review batch exceeded the MCP response window, but all fifteen outputs and its final neutral/saved state were checked afterward. `runtime-face-curved-optics.png` is the later lens correction; earlier full-body/portrait screenshots retain the preceding flat panes and must not be represented as final curved-optics proof.

## Remaining visual and contact differences

The candidate remains substantially simpler than the reference in face likeness, hair shape, garment construction and wear. The head is a coherent human mesh but still has different brow/eye/cheek/jaw proportions and facial character. The hair does not reproduce the reference's tousled curl structure. Jacket panel cuts, belt/hem construction, stitched detail, wrinkles and wear do not yet match the reference; current albedo remains too uniform. Boot silhouette and finish require further work. Helmet/goggle details and material response also differ. Curved optical geometry corrected the large flat mirror-like reflections, but is not a fidelity pass.

Hand curves demonstrably animate, but images suggest the curl axis should follow each anatomical palm rather than the former global-axis approximation. Exact palm/seat/foot contacts against an accepted bike are still pending. Animation finiteness does not certify convincing grip, self-intersection freedom or grounded motion. Native Unity appearance, LOD transitions, all input/display modes, FPS/memory, and user visual acceptance remain unverified here.

The separate ImageGen leather-atlas candidate is **unaccepted**. Read-only comparison found UV foreground drift (not an artistic similarity score), colored boundary fringes, broad marbling and lighting-like fold shading. `texture-candidate-comparison.json` records the method and measurements. Two private mapped renders compare full strength and a 25% in-memory material mix: full strength is visibly over-marbled; the lower-strength experiment adds wear but does not resolve reference or UV discrepancies. No image was edited by the analysis script, and the original material was restored without saving source. The candidate has not replaced any frozen descriptor input.

## Authoring and resumption

Recipes are under `tools/p08/golden/ash_v2/`; offline preparation is `tools/p08/golden/prepare_ash_complete_inputs.py`. Numeric data preparation is separate from Blender modeling. Do not execute arbitrary addon code or disable the pinned MCP safe mode. Inspect the current task-owned scene before any rebuild and preserve saved candidates.

The task-owned Blender on port 9876 was resumed as PID 33780 after its prior process/listener disappeared. No crash cause was established; no matching crash log was found. The other Blender instance on port 9877 belongs to Canyon authoring and must not be touched. Do not stop a process based on a stale PID without rechecking ownership.

The descriptor inputs are frozen while the root performs Unity technical import. Any later accepted mesh/material change requires fresh exports, hashes, descriptor, baked/runtime render evidence and appropriate checks. No production-content mask, canonical portrait slot or roster acceptance was promoted from this candidate.
