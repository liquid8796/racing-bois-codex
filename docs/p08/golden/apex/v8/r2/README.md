# Apex V8 / R2 — structural repair and another visual candidate

**Visual acceptance remains failed.** This revision is an isolated replacement candidate for inspection, not the finished Apex, and is not claimed to match the concept100%. The previous V8 source, export, descriptor and Unity failure evidence remain unchanged.

Reference remains `ArtSource/Concepts/P08/Golden/apex-v2.png`, SHA256 `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`.

## Native-threshold geometry repair

Root's actual Unity import rejected the previous LOD0 body:312 triangles had squared cross-product magnitude at or below1e-16. The earlier Blender audit's1e-12 area threshold was too loose; that old report did not prove Unity readiness.

R2 removes redundant micro-bevels from already thickened, curved fairing/optical skins, instead of weakening the gate or welding distinct mechanical components. The remaining collinear triangulation on the tank underside's closed cap was replaced by centered fans. The final Blender audit uses the same `crossSq <= 1e-16` rejection condition as Unity.

Fresh final observations across all nine runtime meshes:

- Zero triangles at or below the Unity threshold; minimum LOD0-body crossSq is7.012498e-14.
- Zero non-manifold edges, zero zero-area geometry triangles and zero zero-area UV triangles.
- LOD triangles: **79,492 / 34,974 / 11,126**; three mesh renderers per level, nine material groups.
- Lower triangle count came from removing redundant edge microgeometry, not a claim that silhouette or fidelity was accepted.

Source observations are not substituted for native validation. Performance is unmeasured and the LOD0 count remains above the earlier45–65k proposal.

Actual Unity import subsequently passed in `docs/p08/golden/unity/import-1a07d725bd2e4529ac6b59a7daba45f7.json`; that receipt is the authority for structural/native import results, not this authoring description. The first native review render showed diagonal fairing artifacts. A temporary runtime normal-map-scale-zero control left them, while the settled no-shadows control removed them. This points to review shadow acne rather than proving a bad normal map or FBX normal export. R2 source was kept frozen; no speculative normal recalculation or shader-noise workaround was applied. Root is correcting the isolated review lighting/pipeline and retaining shadows before visual comparison continues.

## Visual changes and remaining differences

The nose now has a wider graphite wedge tapering toward the lower center, more swept lamp boundaries and distinct clear lens material. Tank cross sections have more deliberate shoulder changes and a higher crown. A real dark intake plenum blocks the incorrect view through the opposite fairing. The main chassis uses tapered rectangular cast spars, and lower forks have shaped axle supports instead of simple cylinders. Bright exposed support strips were reduced, and an inner frame panel fills an inappropriate opening.

The actual final beauty render still differs substantially from the reference. The painted nose/tank/fairing curvatures and panel boundaries are not exact; the tail remains too schematic; mirrors and material/texture detail are simplified; and the overall manufactured appearance is below the concept. Keep this revision unaccepted and do not replicate it across the bike roster. The unchanged reference must remain the visual target.

## Inspection entry points

- `descriptor.json`: id `RB_Golden_Apex_v8_r2`, current exact-source/FBX/texture hashes and explicit forward/left/right/contact markers.
- `geometry-observations.json`: exact inputs and strict geometric measurements.
- `apex-beauty-final.png`, `apex-side-final.png`, `apex-side-right-final.png`, `apex-front-final.png`, `apex-rear-final.png`: actual CPU Cycles views of the final assembly.
- `ArtSource/P08/Golden/Apex/V8/R2/RB_Golden_Apex_v8_r2.blend`: assembled candidate; the sibling `_editable.blend` preserves named parts before joining.
- `Assets/RacingBois/Art/P08/Golden/Apex/V8/R2/RB_Golden_Apex_v8_r2.fbx`: separate export, never a replacement for the production prefab.

Direct pinned Blender MCP only, dedicated port9878, safe mode on, CPU rendering capped at four threads. No Jarvis MCP or paid asset service. Maps were fully written before reload/packing. Intentional shared finish UVs and the nine material roles follow the first V8 report. No original-game production asset, production content mask, Club source or OCI state was changed by this work.
