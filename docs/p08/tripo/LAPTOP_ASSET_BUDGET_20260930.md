# Laptop asset budget — proposed, 2026-09-30

Target hardware class supplied by the user: **discrete GPU with 4 GB VRAM, 16 GB RAM**. No CPU minimum or successful hardware measurement is established. Windows 10/11 DX11 at **1920×1080 Medium, mean ≥60 FPS and frame p95 ≤20 ms over 600 seconds**, with **peak process working set ≤2 GiB**, remains a target. The frame/process goals already exist in `docs/p08/desktop/README.md` and `DesktopAcceptanceRecorder.cs`; the foreground run remains deferred.

This audit edits only policy documents outside Assets. `laptop-asset-budget-20260930.json` binds the inspected source/configuration files, distinguishes current behavior from proposals, and stores exact memory arithmetic. Root separately installed the runtime streaming scope described below; this reviewer changed no runtime or importer.

## Current verified policy

- `RaceVisualQuality` clones a runtime URP asset. Low/Medium/High use render scales 0.78/1/1, MSAA 2/2/4, shadow distances 35/70/100 m, shadow maps 1024/2048/2048, and LOD biases 0.65/1/1.3. Its new `RaceTextureStreamingScope` enables runtime streaming with budgets **256/512/768** and maximum mip reductions **3/2/2**. Disposal restores only settings still equal to the scope's applied values; the actual original quality-pipeline override is restored too. It adds no global mip-limit or P08 texture-group assignment. `RaceBootstrap.ApplyQuality` also adjusts effects and scenery density.
- `DesktopPipeline.asset` serializes Medium-like scale 1, MSAA 2, a 2048 main-light shadow map, 70 m shadows and one cascade. Serialized Standalone quality defaults to index 5 (`Ultra`); the three game quality indices are a separate runtime abstraction.
- All six serialized Unity quality levels still have **streaming disabled**, a stored budget of 512, and no mip-limit groups; the runtime scope enables streaming after game quality is applied. `Very Low` already has global mip limit 1; the others have 0. The runtime patch and this proposal add no global mip-limit change.
- Current `P08ArtBuilder` code requests 1024 BaseColor, 512 other maps, BC7 color/masks and BC5 normals; it creates three LODs at 0.22/0.075/0.009 screen heights and one material per asset. Its validator checks reduction, not an absolute triangle ceiling. Sample legacy BikesA BaseColor metadata still has Standalone override disabled/Automatic and streaming off, so code intent is not proof every current asset was reimported.
- The Golden diagnostic importer preserves material slots, requests BC7/BC5, mipmaps and streaming, disables texture CPU readability, and uses a material-wide `maxSize` default 2048 with allowed range 512–4096. The sampled Apex Pearl metadata has the Standalone override and streaming flag enabled. Diagnostic meshes retain CPU readability. Golden validation enforces three decreasing LODs and declared materials, without an absolute triangle/material ceiling.

Root's actual Unity Play-mode receipt `runtime-quality-native-20260930-01.json` passes **22 configuration/ownership/restoration checks**; `compiled-runtime-quality-20260930-01.json` passes the ten loaded-assembly source proof. This establishes native configuration behavior and saved-file preservation. Texture residency, GPU memory, frame budgets and full P08 release remain unmeasured by those receipts.

## Source and native derivatives

Retain raw Tripo GLB, high-resolution maps and Blender masters in **ArtSource**, with immutable hashes. The inspected HQ02 report records **1,944,606 source triangles, 8192² color and 4096² normal/ORM**; those are authoring inputs. A shipping derivative requires retopology/LOD construction, baked maps, rig/contacts and native review. The shipping dependency allowlist must exclude raw meshes, masters and 8K maps.

The existing architecture proposes **20k–40k triangles for a near bike+rider pair**, middle ≈50%, far ≈20%, hero textures 1K–2K, and ordinary props 200–5k with 256–1K textures. The later Apex authoring plan proposes **45k–65k for the bike alone**, ≈24k/8k lower LODs, and 3–4 surface groups. Neither is measured acceptance; they conflict as near-actor budgets. The following stricter Medium starting allocation stays within the earlier **40k combined** envelope. Raising it requires documented visual and native cost evidence.

| Native Medium category | Base / normal / packed mask | LOD0 / LOD1 / LOD2 triangle targets | Material targets |
| --- | --- | --- | --- |
| Hero bike | 2048 / 1024 / 1024; secondary surfaces 1024 or 512 | ≤28k / 14k / 5.6k | ≤4 distinct slots |
| Hero rider | 2048 / 1024 / 1024 for face/clothing sets | ≤12k / 6k / 2.4k | ≤4 distinct slots |
| Secondary bike + rider | 1024 / 1024 / 512 | Bike ≤14k/7k/2.8k; rider ≤6k/3k/1.2k | ≤2 slots each |
| Ordinary modular scenery/prop | 1024 / 512 / 512, tiled/shared where appropriate | ≤5k / 2.5k / 1k | ≤2 per module |
| Small repeated roadside prop | 512 / 512 / 512 | ≤1k / 500 / 200 | 1 shared slot |

These are aggregate counts across all renderers in each active asset LOD. Wheels, visible face/hand forms, fairing/cowl silhouettes and required garment folds remain real geometry. Complex landmarks/cliff modules require their own explicit reviewed budget; a complete Canyon scene must not use one giant LODGroup. Reuse shared surface sets without merging away required transparency, material response or semantic articulation. Existing Golden `maxSize` is material-wide: per-map sizes can be supplied as separately baked derivative images; it is not already a per-map policy.

Medium content-residency planning ceiling: **512 MiB of P08 textures**, provisionally split 256 MiB shared actors, 128 MiB the current route, and 128 MiB auxiliary/VFX/portrait content. This partition is a proposal, not current loader enforcement. Count unique textures once, include optional AO/emission maps, and measure route-swap overlap. Selective **4K High** derivatives are optional only after native visual/cost proof; 8K remains source-only.

## Expected compressed texture memory

BC7 uses 16-byte 4×4 blocks; BC5 uses 8 bits per pixel too. Full-chain calculation is `Σ 16 × ceil(width/4) × ceil(height/4)` down to 1×1. [Microsoft BC7](https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format), [Unity BC5](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/TextureFormat.BC5.html).

| Square map | One BC7 or BC5 map, full mips |
| --- | --- |
| 512 | 349,552 bytes ≈0.33336 MiB |
| 1024 | 1,398,128 bytes ≈1.33336 MiB |
| 2048 | 5,592,432 bytes ≈5.33336 MiB |
| 4096 | 22,369,648 bytes ≈21.33336 MiB |
| 8192 | 89,478,512 bytes ≈85.33336 MiB |

Thus one 2K/1K/1K three-map set is **8,388,688 bytes ≈8.00008 MiB**; 1K/512/512 is **2,097,232 bytes ≈2.00008 MiB**. Hypothetical BC import of HQ02's 8K/4K/4K maps would be **134,217,808 bytes ≈128.00008 MiB**, before meshes, render targets, driver overhead, copies or other content. These are calculated payloads, not measured GPU/process memory. PNG/download size does not establish runtime residency.

Propose P08-only importer membership and mip-limit groups; protect fonts/UI and unrelated existing 512 maps from new limits. Unity's streaming budget is **global and soft**, includes non-streaming textures, and cannot force non-streaming textures under the budget. It is not a P08-only or VRAM hard cap. The runtime Medium value 512 is now configuration-tested; P08 membership, camera participation and actual residency measurements are still required. [Unity streaming budget](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/QualitySettings-streamingMipmapsMemoryBudget.html), [mip-limit groups](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/TextureMipmapLimitGroups.html).

## Isolated validation before shipping

1. Root imports fresh derivative copies with new owned paths/GUIDs; snapshot source/reference/settings and dirty state first. Keep raw sources and protected assets outside the mutation set.
2. Verify actual imported dimensions, BC7/BC5 and sRGB/data channels; triangle totals per LOD, material slots, skin weights, contact markers, bounds and original file preservation. Retain diagnostic CPU mesh access for these checks; evaluate disabling it only on separate shipping copies after verification.
3. Compare actual native corresponding views and gameplay-camera distances against locked concepts, including forced LODs, transitions, transparency, face/hands and UI thumbnails. Budget compliance cannot waive the **100% finalized-concept requirement**. A mismatch stays unaccepted.
4. Audit native build dependencies and runtime texture/mip/format readbacks; reject raw 2M-triangle reconstructions or 8K source textures in the shipping bundle. Stress actual actor density, route changes and unload/reload, recording managed/native/GPU/texture residency and draw/submitted-triangle counters separately.
5. On a real 4 GB / 16 GB target laptop, measure the unchanged 600-second 1080p Medium gate once foreground coordination is available. Record device/driver and available CPU/GPU timings; unavailable counters stay unavailable. No FPS, hardware pass or phase completion is claimed here.
