# Spark 450 V1 finish maps — staged candidate

These original procedural finishes cover ten existing Spark materials. They do not add a new asset family. No concept pixels, downloaded texture, model or baked lighting were used. The Copper tank atlas, geometry, Blender scene, Unity Assets and frozen runtime sources were not changed by this task.

The inspected hero reference is `ArtSource/Concepts/P08/Golden/spark-v1.png`, SHA256 `e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6`. The separately inspected side reference is uncalibrated, SHA256 `ad5478c942350462a34d12b1ba9f9714cb00a595ff9465bc1d000cf6b5e7ad0b`. The generator verifies both identities before writing.

**No visual acceptance is claimed.** The maps must be seen on the actual mesh, under the review lighting and gameplay camera, before accepting their material response or concept fidelity.

| Finish | Surface response | Largest map | UV multiplier |
| --- | --- | --- | --- |
| Cream | Uniform warm ivory paint; existing clearcoat preserved | 4×4 | 1 |
| Graphite | Fine isotropic cast/powder-coat grain | 512×512 | 2 |
| Machined | Fine directional steel tool marks | 512×512 | 8 |
| SatinSteel | Satin exhaust steel with restrained directional roughness | 1024×1024 | 4 |
| Rubber | Matte isotropic mould finish | 512×512 | 2 |
| Leather | Dark brown pigment, small rounded grain and shallow creases | 1024×1024 | 1 |
| Lens | Clear glass tint, flat normal; transmission stays shader-owned | 4×4 | 1 |
| Lamp / Amber / RedLamp | Constant pigment and separately stored emission color | 4×4 | 1 |

The original `UV0_SurfaceMetres` repeats twice per metre. The multipliers above produce 0.25 m Graphite/Rubber tiles, 0.0625 m Machined, 0.125 m SatinSteel and 0.5 m Leather. The two directional metal patterns run along UV U. UV projection orientation must be reviewed on each part; generic maps cannot correct incorrect UV direction.

Most base colors use 4×4 constant textures, because material response belongs in the roughness and normal channels. Only Leather needs a 512×512 base map, with up to 2.2% pigment modulation before linear-light downsampling. Normal relief spans about 15.4 µm for Graphite, 4 µm for SatinSteel and 53.2 µm for Leather. These are author-selected candidate values, not measured BRDF data.

## Data contract

- Base Color and Emission RGB: explicitly sRGB-encoded from the linear reflectance values in the original Spark build. Import as sRGB. No lighting highlights or shading are painted into those colors.
- Normal RGB: linear data, tangent-space +Y. The top PNG row corresponds to UV V=1. Use normal-aware mip generation and renormalization after filtering.
- MetallicSmoothness RGBA: **R = metallic, G/B = zero, A = smoothness**. Alpha is data, never opacity or premultiplication. Disable sRGB and alpha-as-transparency.
- Roughness L: linear data for Blender. Every stored roughness byte plus its packed smoothness byte equals exactly 255.
- Lamp, Amber and RedLamp emission strength remains the existing 0.15 / 0.25 / 0.25. Signal behavior and physical illumination are not implemented by these maps.

`finish-surface-intent.json` records every PNG's hash, dimensions, channel mode, decoded minima/means/maxima and three decoded pixel samples. It also records nominal reflectance, UV scale, material intent and limitations.

## Apply through Blender MCP — parent-owned action, before assembly

The new `finish-material-binding-mcp.py` is staged, syntax-checked and **not executed**. It imports only `bpy`, embeds all finalized bindings as literals and uses Blender image APIs for loading/reloading/packing. It does not read files with Python filesystem helpers or dynamically import/execute other scripts.

First run this separate read-only preflight in ordinary Python, outside Blender MCP:

```powershell
python tools/p08/golden/spark_v1_finish_preflight.py
```

The preflight checks the locked manifest and concept hashes, all 43 PNGs, the original manifest dependencies, exact literal binding equivalence and the new snippet's allowed imports/calls. It prints the new snippet SHA256. The parent then sends the **file's literal source directly** to Blender MCP. Do not wrap it in `exec`, `open`, `pathlib`, custom imports or a file-loading bridge.

**Executing the new snippet explicitly changes source UV loop data.** It must run in Object mode on the editable `RB_Golden_Spark_v1` root before assembly/LOD generation. For each polygon it resolves the object's actual material slot, then applies that material's 2/4/8 multiplier to the named first UV channel exactly once. Factor-1 materials and all Copper faces remain unchanged. Shared unbaked mesh datablocks are copied before mutation so other users cannot be scaled accidentally.

Object and mesh custom properties record the material/face layout and completed UV coordinates. Matching guards skip UV multiplication on reruns. Changed layouts, edited UVs, mismatched guards or an interrupted pending bake stop explicitly; **do not clear those guards blindly**. A pending marker is set before mutation so a partial interruption cannot quietly produce another multiplication.

The shader reads the baked UV directly with effective scale 1; it contains no Mapping/VectorMath scaling node. This puts the repeat scale in the FBX mesh data used by Unity. Existing tagged helper nodes are replaced. Images are loaded fresh using `check_existing=False`, assigned their color space and packed-alpha mode, reloaded and packed before UV/material mutation. Existing clearcoat/transmission shader values are preserved. Camera, lights, geometry positions and Copper material/texture data are outside scope.

The original `finish-material-binding.py` is retained only because its hash is recorded in the frozen manifest. **Do not use that old shader-scale helper after the new UV bake.** The new MCP helper supersedes it; both files and this distinction are explicit rather than silently changing the manifest or PNG bytes.

## Verification and observed limits

`finish-validation.json` records exact PNG readback, channel checks and repeat generation: all 43 PNGs plus the manifest and binding helper were byte-identical across a second run. Total PNG size is **2,669,004 bytes**, without padding. The maximum decoded normal length deviation after RGB8 quantization is 0.002596; normal import/filtering must renormalize it.

The actual Leather base/normal, Graphite normal and SatinSteel normal/roughness PNGs were opened and inspected. The leather base is dark brown with barely visible pigment grain; the normal contains fine cellular response. Graphite is deliberately shallow and isotropic. SatinSteel contains narrow parallel variation and no broad stains. These observations concern the 2D maps only.

Remaining physical/art limitations:

- One Graphite response currently serves cases, frame and fenders; these may require separate gloss if their reference appearances differ.
- One Machined response cannot represent circular brake machining, longitudinal fork polishing and a true mirror equally. Those surfaces need suitable object-specific UVs or further material separation if visibly different.
- Lens flutes, reflector prisms, tire tread, grip ribs, saddle ribs, strap, piping, stitching and exhaust heat treatment are not invented by generic tiling finishes.
- Blender/Unity rendered response, compressed textures, LOD appearance, draw calls and final matching to the reference remain unverified by this task.

Regenerate with `python tools/p08/golden/spark_v1_finish_textures.py`. Only the ten named finish maps and their original generated manifest/helper are rewritten; Copper is not enumerated or touched. The new MCP snippet and preflight are separate staged files and are not executed by regeneration.
