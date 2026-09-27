# Apex mechanical base feasibility — 27 September 2026

**No downloaded motorcycle is accepted as Apex, and none is a production-ready drop-in.** The best candidates are useful mechanical references or selectively repairable components. Apex's locked silhouette, body panels, lights, tank, saddle, tail, two under-seat exhaust outlets and materials still require substantial original authoring. Imported components must retain their provenance; this work cannot be described as an entirely scratch-built motorcycle.

The specification remains [apex-v2.png](../../../ArtSource/Concepts/P08/Golden/apex-v2.png), SHA256 `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`. Nothing here changes its 100% matching or production gates.

## Sources and access

The [official Objaverse API documentation](https://objaverse.allenai.org/docs/objaverse-1.0/) exposes per-object annotations. Its database license is not a substitute for a mesh's own license. We checked all 81 IDs in the published LVIS `motorcycle` category: 77 current object metadata responses and four errors; 61 CC-BY, 13 NC variants, three BY-SA, no CC0. This is a bounded search, not an exhaustive search of all motorcycle models. Records and errors remain in [the metadata snapshot](sketchfab-lvis-motorcycles.json).

| Candidate and creator | Verified permission and delivery | Decision |
|---|---|---|
| [SZH2I2 Procedural Reshade](https://sketchfab.com/3d-models/motorcycle-szh2i2-procedural-reshade-ver-95a107fee2ab41bdb6e21bac72741781), **ChamberSu** | Current per-object CC-BY 4.0, downloadable; original Objaverse annotation also `by/true`. Official public GLB returned HTTP200 and was downloaded, 48,839,024 bytes. Creator describes designing the machine and its Blender workflow. | Strongest original-design provenance and useful exposed mechanical detail. Material-batched geometry makes semantic component reuse laborious. Entire ornate exterior and exhaust routing differ from Apex. |
| [Ducati Panigale V4](https://sketchfab.com/3d-models/ducati-panigale-v4-47f87e3d70f644289e34cbff91255d0c), **ROY** | Current per-object CC-BY 4.0, downloadable; original Objaverse annotation also `by/true`. Official public GLB returned HTTP200 and was downloaded, 18,313,296 bytes. Creator's [profile](https://sketchfab.com/roy.3dartist) calls the distributed works his models. | Better separated mechanisms and sportbike layout. Branded exterior, low exhaust and single-sided rear assembly are not Apex. No game-rip statement was found, but there is no independent authoring-history proof; retain that provenance limit. |
| [Sports Bike](https://sketchfab.com/3d-models/sports-bike-a80259b859c842d5824c25c61e0fc421), **appsnation** | Current per-object CC-BY 4.0 and downloadable. Creator says made in Blender. 641,501 listed triangles. Not in the original Objaverse object-path index. Anonymous source delivery was not established. | Public preview shows detailed sportbike mechanisms. Not downloaded, and not a cleared no-account acquisition path. No restricted viewer extraction was attempted. |
| [GYO](https://blenderfantasycg.seesaa.net/article/503528383.html), **サラダたまご / Salad Tamago** | Creator explicitly publishes `motorcycle-gyo.zip` under CC0, permits modification/redistribution, and provides editable texture sources. Declared ZIP7.9MB. | Legitimate direct-author fallback. ZIP endpoint and actual geometry were not inspected; raw page retrieval returned403, although the public article was readable through web search. Do not equate a published link with a successful download. |
| [fancy motorcycle](https://opengameart.org/content/fancy-motorcycle), **Teh_Bucket** | CC0. Public `.blend` and `.obj` HEAD requests returned200, 1,862,904/637,347 bytes. Author states no textures, approximately10k triangles. | Actual public preview is a stylized enclosed cruiser. Rejected for Apex fit before downloading. |

CC-BY 4.0 permits commercial adaptation with attribution, a license link and identification of changes; it does not establish that every uploader owns every underlying right. CC0 likewise does not waive third-party trademark/patent rights. Preserve exact creator, object URL, license snapshot and changes in any eventual component attribution. The imported branded bodywork should not become Racing Bois artwork merely by changing its color. [CC-BY terms](https://creativecommons.org/licenses/by/4.0/), [CC0 terms](https://creativecommons.org/publicdomain/zero/1.0/).

No PolyHaven motorcycle was verified; catalog/API access limitations are not evidence that none exists. The public [sportbike-sim repository](https://github.com/strong-ery/sportbike-sim) has an MIT license, but includes Asset Store dependencies and no specific ZX6R mesh origin/license statement in the inspected README/license/tree. Its bike is **not cleared** by the repository-level license. NC/ND, unknown-license objects, commercial-game derivatives such as the HCR2 models, and gated downloads requiring signup were excluded.

## Actual local inspection

Root authorized two official public GLB downloads, below1GB total. Actual total: **67,152,320 bytes**. [download-manifest.json](download-manifest.json) binds the source URLs, creators, exact licenses, sizes and hashes:

- ChamberSu: `208419b0aa252eb2029b6cf065a755748801fe77c1d12b388cd51167de9c8ed8`.
- ROY: `83f555ed9ac013feb319c582e0fb2bb09e8094e0f9835f7a616c4796afb92370`.

The official distribution paths are recorded in [objaverse-availability.json](objaverse-availability.json), with matching historical annotations in [objaverse-original-annotations.json](objaverse-original-annotations.json). No account, payment, cloud upload, viewer-data extraction or addon installation occurred.

Both were imported through direct pinned Blender MCP9878 into separate inspection scenes. Script auto-execution was asserted disabled. The first three scripts were rejected by safe-mode validation before execution; the fourth used supported imports/operators and succeeded. Safe mode was never disabled. Saved inspection file: [`licensed-base-inspection.blend`](../../../_local/p08-apex-base-inspection-20260927/licensed-base-inspection.blend). Original GLBs remain unchanged; no imported material or mesh was copied into game `Assets`.

| Measured property | ChamberSu SZH2I2 | ROY Panigale V4 |
|---|---:|---:|
| Imported triangles | 469,654 | 372,664 |
| Mesh objects / material roles | 14 / 9 | 107 / 27 |
| Images used by materials | 12 packed1024² | Four packed:1024²,512²,512×256,64×32 |
| Meshes without UV layer | 0 | 1 (`Object_46`,1,444triangles) |
| Raw seam-split boundary edges | 315,802 | 373,506 |
| Aggregate diagnostic weld boundary / non-manifold edges | 10,525 / 12,046 | 4,351 / 5,466 |
| Aggregate connected / closed components after diagnostic weld | 1,169 / 692 | 842 / 756 |
| Zero-area faces after diagnostic weld, area≤1e-20m² | 1 | 2 |

Evidence: [raw import](geometry-inspection.json), [per-object weld](weld-inspection.json), [aggregate weld](aggregate-inspection.json), and corresponding `*-mcp.json` receipts. The very large raw boundary counts include GLTF UV/normal seam splits. Diagnostic welding was performed on disposable BMesh copies at1µm after display normalization to2.05m footprint length; it did **not** repair the source. Aggregating material partitions removes additional false boundaries but leaves substantial real/open or non-manifold geometry. Closed-component counts include tiny fasteners and are not semantic part counts. No unique-UV, proper collision, LOD, rig, native Unity, memory or frame-time acceptance is claimed.

ChamberSu splits meshes chiefly by cover/sharp/smooth/tube material groups, including65,532-vertex batching. A wheel, engine or fork cannot be assumed to be one ready object. ROY exposes many separately addressable mesh nodes, but most names are generic and the hierarchy mixes parts/material partitions. Both need semantic identification and selective topology checks before reuse. GLB is locally editable but does not preserve an original procedural Blender modifier stack.

## Render evidence and remaining work

Neutral views use Cycles CPU, four threads,24samples,1100×850, fixed gray environment and identical lighting. Display length normalization and a measured vertical ground adjustment are for comparison only, not a claim of correct real-world source scale. Source materials are retained, exposing their actual imported appearance.

- ChamberSu: [quarter](renders/95a107fe-quarter-grounded.png), [side](renders/95a107fe-side-grounded.png), [front / -Y](renders/95a107fe-negative-y-grounded.png), [rear / +Y](renders/95a107fe-positive-y-grounded.png).
- ROY: [rear quarter](renders/47f87e3d-quarter-grounded.png), [side](renders/47f87e3d-side-grounded.png), [front / +Y](renders/47f87e3d-positive-y-grounded.png), [rear / -Y](renders/47f87e3d-negative-y-grounded.png).
- Material-independent clay: [ROY](renders/47f87e3d-clay-front-quarter.png), [ChamberSu](renders/95a107fe-clay-front-quarter.png). These confirm the incompatible body shapes also exist in geometry.

The actual renders show mechanical assemblies materially more detailed than the current authored R3, but do not prove engineering correctness. ChamberSu has an excessively tall ornamental nose and saddle, distressed shell layers and low side exhausts. ROY has more conventional sportbike wheel/brake/fork mechanisms, a tank and tail unrelated to Apex, brand markings, broad reflective shell surfaces and a low exhaust. **Neither supplies Apex's exact two under-seat outlets.**

Recommended next work, subject to root's integration decision: inspect a small chosen wheel/brake/fork subset from ROY and an engine/chain/frame subset from ChamberSu in isolation; identify source nodes and license obligations before any transfer. Repair or re-author only mechanically useful parts, then retopologize/bake to the production budget. Author Apex's silhouette-defining pieces directly from its locked views and measured dimensions. Recheck actual front/side/rear/quarter renders, source/export/native orientation, topology, UV/PBR, LOD transitions, collider/prefab integrity and gameplay performance. No candidate promotion or reduced fidelity criterion follows from this feasibility result.

**Root's subsequent decision: geometry references only; no borrowed meshes.** The next Apex R4 will remain original authored geometry. The inspection does not authorize a licensed base integration. [Postcheck](inspection-postcheck.json) confirms both GLBs, saved Apex R3 and protected Club source hashes unchanged; the operational soak remained running with stable source at the recorded time.

The actual Unity [garage screenshot](../golden/ui/r3-v7-focus-1920.png), locked [garage UI concept](../../../ArtSource/Concepts/P08/Golden/UI/garage-v2.png) and bike concept were inspected together. R4's ordered shape correction is: angular tank shoulder and knee transition; curved fairing with intentional planar breaks and edge returns; swept integrated lamp/screen cowl; continuous saddle, substantial tail side return and exactly two under-seat exhaust outlets. The dark mechanisms and rim/screen reflections require a separate native neutral-fill/material/probe comparison by root. Increasing mesh detail does not by itself correct that lighting issue.
