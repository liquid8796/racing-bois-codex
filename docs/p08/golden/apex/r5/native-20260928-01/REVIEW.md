# Apex R5 actual Windows review

The Windows64 Mono player built successfully with zero errors/warnings, explicit Direct3D11, unchanged bound sources, restored project settings, and preserved original fonts/dirty assets. Build receipt: `../../../unity/build-d33dd349e5b44d238c5dce13c6d4908c.json`. `launch-check.json` binds the exact receipt and all player files before/after the owned process. The player exited 0 and produced 18 hash-verified, independently decoded 1920x1080 PNGs (six views at each of three LODs).

The locked reference remains `ArtSource/Concepts/P08/Golden/apex-v2.png`, SHA256 `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`. Root inspected the actual LOD0 three-quarter, front and side views against corresponding reference views. These studio camera views are useful for silhouette comparison, but their lighting, camera angle and framing are not an exact reference reconstruction.

The corrected lower-shell seam is no longer visibly overlapping in the inspected views. That is a bounded geometric repair, not acceptance. Major differences remain:

- The model's white side panel reads as a thin, nearly vertical hanging wedge. The reference has a full sculpted, faceted fairing with a defined shoulder and angular dark belly enclosure.
- The tank/seat/tail transition lacks the reference's filled side panels; exposed long frame rods create large empty areas. The tail and under-seat exhaust housing have different proportions.
- The headlamp assembly projects as two large outlined boxes. The reference lenses sit recessed inside a narrower, integrated front cowl with different tilt and brow geometry.
- Wheel hubs, perforated rotors, calipers, swingarm, engine fasteners and cables remain visibly simplified and differently arranged.
- The native pearl finish is largely uniform and loses the reference's facet changes, surface detail and controlled material separation. The hard studio light also introduces shadows across the upper fairing; changing light alone cannot repair the geometry differences.

Visual acceptance remains false. No roster mapping, content mask or release gate is promoted. The images are actual engine renders, not window/UI captures or performance evidence.
