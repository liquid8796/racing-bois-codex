# Canyon overhang: causal geometry audit

The oversized profile is inherited from the scan/formation authoring and amplified
by V17 scaling. V15 closure adds a thin shell; it does not create the large new
vertex extension. It does, however, make backing/rim surfaces visible on the first
large cliff. Both mechanisms matter. A palette change alone cannot fix this gap.

This audit inspected the locked concept and actual native
`../native-20260928-01/subject-0-lod-0-view-4.png`, then read the frozen V13, V14,
V15, V16 and V17 candidate05 Blender sources plus the original local CC0 FBXs.
Only the owned direct pinned Blender MCP session on port 9877 was used, with
safe mode enabled. It returned to frozen05 at the end. No source was saved,
no geometry was edited/exported, no Assets file was written and no Unity call
was made. All candidates remain visually unaccepted.

## What the actual meshes show

Across all twelve Far LOD0 modules:

| Transition | Maximum measured vertex-set difference |
| --- | ---: |
| V13 → V14 | 0.0000683 m |
| V14 open skin → V15 closed shell | 0.175058 m |
| V15 → V16 face normalization | 0 m |
| V16 → V17-05 fitted diagonal affine transform | 0.0002461 m residual |

Applying the measured V16→05 affine transform to the preclosure V14 skin puts
every current closed-shell vertex within at most 1.276802 m of that transformed
skin. The twelve per-module maxima range from about 0.79 to 1.28 m. This is an
actual point-set measurement, not a similarity/fidelity score. It does not mean
that an open skin and a closed surface render identically: new faces can become
visible inside an almost unchanged outer vertex envelope.

V15's code uses Solidify thickness 0.03–0.35, offset zero and no even-offset
expansion, and checks new vertices against the original skin. The actual measured
0.175058 m displacement agrees with that bounded half-thickness. V16 only removes
redundant faces; the Far vertex positions remain exact.

The earlier V13 formation code is the main proportion change: it applies
anisotropic scale, compresses height above its cap to 22% of the previous height
excess, adds a horizontal sine warp, then heavily decimates the distance mesh.
The cap operation flattens upper slopes by about 4.55× before later transforms.
V17 subsequently stretches the existing shape again instead of authoring new
fractured terrain.

Representative actual dimensions, in Blender world X/Y/Z metres:

| Geometry | Width X | Depth Y | Height Z |
| --- | ---: | ---: | ---: |
| Original cliff02 scan | 20.2275 | 6.5934 | 7.1838 |
| V13 Far33 open skin | 102.8136 | 37.6992 | 66.6003 |
| V15/V16 Far33 closed | 103.0131 | 37.8904 | 66.7776 |
| V17-05 Far33 | 95 | 185 | 180 |
| Original cliff01 scan | 8.2790 | 4.3901 | 4.9611 |
| V13 Far34 open skin | 42.6392 | 28.1030 | 47.5834 |
| V15/V16 Far34 closed | 42.8384 | 28.2976 | 47.7393 |
| V17-05 Far34 | 98 | 185 | 188 |

The source and formation yaw differ, so these world-axis extents describe the
saved geometry rather than a pure isolated scale factor. The V16→05 measured
diagonal scales are direct: Far33 is `[0.9222, 4.8825, 2.6955]`; Far34 is
`[2.2877, 6.5377, 3.9381]`. Other Far depth scales reach about 7.30.

The point plots preserve physical metres and equal axis scale within each panel;
only origins are translated. They show the pre-existing upper shelves, the nearly
overlapping open/closed profiles and their later expansion. They are geometry
diagnostics, not a new reference concept or edited native render.

![Actual source side profiles](side-profile-provenance.png)

## Why closure is still visible

Read-only camera rays use the unchanged candidate05 gameplay camera and step past
the atmospheric volume boundary. Far33 hits at normalized image positions such as
`(0.32,0.04)`, `(0.32,0.10)` and `(0.36,0.10)` use **Canyon_Sandstone**, the added
backing/rim material. Nearby Far34 and Far35 hits use **Canyon_Cliff01** and
**Canyon_Cliff02**, their original scan materials. The first broad visible face
therefore exposes the closure surface, while the neighboring stretched profiles
also exist on original scan surfaces.

Far33 has 1,746 original scan triangles in V13/V14. V15 adds 2,082 Sandstone
backing/rim triangles, closes 168 open boundary edges, and keeps the same final
3,828 triangles through V16 and V17-05. The closed module is still a thin offset
of a scanned skin, not a deliberately modeled solid canyon mass. Closure can
expose the underside/rim along the already long boundary; the measurements do
not support blaming the large shelf extent on extrusion thickness alone.

The same UVs also survive the large V17 affine changes. Material grain/tiling is
therefore stretched with the geometry. This explains why material review remains
necessary, but it does not replace fixing the visible shape and backing.

## Bounded next correction

Start with one separate Far33 test module, preserving all frozen versions. Hold
the candidate05 gameplay camera, lighting, road, rail, foliage and other modules
fixed. Use the locked concept's corresponding left-to-center escarpment view to
author a fractured, stepped, closed landform profile instead of stretching the
whole open scan into a thin curtain. Remove the long artificial cut-shelf edge;
place real back/side volume behind the visible cliff rather than exposing an
offset skin as the principal face. Orient any retained scan detail toward the
actual camera; use it at a suitable detail scale, not as the full oversized mass.

Render that one-module geometry experiment with existing material inputs first,
so its silhouette, block placement and ledges can be assessed independently of
palette changes. Only after the actual corresponding-view render is inspected
should the approach extend to the neighboring visible Far modules. Generate
coherent LODs from the corrected LOD0 and validate their real physical geometry,
primary UVs, closure and exact FBX roundtrip without relaxing thresholds. No new
model or production acceptance has been authorized or created by this audit.

## Evidence and reproduction

`summary.json` contains compact measured bounds, profiles, material counts,
camera hits and all twelve transition comparisons. The exact MCP receipt is
preserved losslessly as `frozen-mesh-comparison.json.gz` (8.27 MB; uncompressed
19,983,379 bytes), including the actual point clouds. Its uncompressed SHA256 is
`5fa55d0efc5cdf620e4fd711d15842f6c3062513475681b37c35c49c031c2ab5`.
The original plain receipt is retained under `_local/canyon-v17` to avoid storing
the same large evidence twice in Git. `inputs.json` binds sources, reference,
native image, scripts and public evidence.

`tools/p08/golden/canyon_overhang_audit/compare_versions.py` performs the guarded
read-only Blender comparison. `report.py` reads the exact archived receipt and
uses Matplotlib for the standalone diagnostic PNG/SVG. Plot dependencies were
installed only into `_local/canyon-profile-plot-packages`; no project dependency
or global Python package was replaced. The plotting versions are recorded in
`requirements-plot.txt`. Reproducing plots requires a fresh `--output` directory;
existing diagnostic outputs are not overwritten.
