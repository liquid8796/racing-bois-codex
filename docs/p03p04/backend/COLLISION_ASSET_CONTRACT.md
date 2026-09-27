# Collision shape / authored asset alignment

The initial gameplay proxy used one 1.90 × 4.40 m traffic body and a fixed 1.50 m vertical threshold. Comparing it with the newly authored concept revision exposed 20.5–28 cm of possible lateral visual overlap and an airborne path through the van above 1.50 m. The shared simulation now uses measured authored dimensions.

Blender LOD0 root-local bounds, converted to Unity axes, are recorded in `docs/p03/assets/independent-mesh-audit.json`. Final Unity import validation additionally checks coordinate conversion and prefab scale.

| Asset | Width | Height | Length | Center from root |
| --- | ---: | ---: | ---: | --- |
| Motorcycle | 0.950 m | 1.196 m | 2.120 m | (0, 0.598, -0.010) m |
| Traffic coupe | 2.160 m | 1.360 m | 4.540 m | (0, 0.680, 0) m |
| Traffic van | 2.310 m | 2.290 m | 4.640 m | (0, 1.145, 0) m |

`VehicleDimensions` is the shared authority definition. The motorcycle uses symmetric half-length 1.070 m to include the rearward 1 cm center offset; this leaves 2 cm of conservative space at the front. Its collision height is 1.200 m, 4 mm above the measured top. The coupe and van use the listed full dimensions, including mirrors and roof markers. These are conservative simple boxes; they intentionally do not follow every curved panel or mirror gap.

`VehicleDimensions.IsVan(id)` selects the same body as presentation. Spawned traffic receives that body's width, length and height. Traffic snapshots include all three dimensions; the immutable readmodel exposes `HalfWidthMeters`, `HalfLengthMeters`, `HeightMeters`, and `IsVan`. The protocol also preserves travel direction independently via `Oncoming` and signed speed.

The swept collision check expands traffic width/length by motorcycle half-extents. Its vertical interval for motorcycle bottom height is `[-motorcycleHeight, trafficHeight]`, adjusted for the road elevation at each participant's old/new route position. This allows a motorcycle above the coupe roof to clear the coupe while still contacting the taller van, and includes slope elevation in the sweep. No Unity/PhysX collision decides damage.

The shared simulation regression suite checks van-only side contact, van-versus-coupe airborne clearance, dimensions at spawn, swept high-speed crossings and recovery. Client integration validates every published snapshot across 20,000 ticks and the maximum transport payload. Runtime visual inspection and final camera/animation polish remain separate acceptance checks.
