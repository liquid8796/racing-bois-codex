# Spark V2 refined06 — continuous tank candidate

This is a bounded replacement of the visible Boolean tank scallops in refined05.
Refined05 and all pinned hero/side references are preserved. The approved hero and
side images and the actual refined05 quarter/side captures were opened again
before authoring. No engine, chain, exhaust, canonical physics or contact edits
were added to this revision.

The new tank uses monotone longitudinal profiles and smooth cross-sections, with
a deliberately raised continuous underside arch and a setback front wall.
Concave end sections are triangulated as closed caps. It uses the original
material and image bytes, retaining the full side paint chart and avoiding
collapsed UVs. No Boolean cutter or modifier is used for the new tank.

The first attempt failed because this Blender version returns triangle indices
from `tessellate_polygon`, while the initial mapper expected vectors. It did not
save a candidate. The second attempt produced valid topology/UVs and cleared the
head, clamps and saddle, but correctly remained unsaved after finding 28 contacts
with each frame rail. Its measured contact region was Y 0.346–0.349 m, where the
neck narrowed over the rail. The final attempt raises the entire lower neck
profile there, preserving a smooth broad clearance surface instead of lifting
only the centerline. All earlier receipts remain available.

## Verified final scope

- 4,544 tank vertices and 9,084 triangles.
- Zero physical triangle failures, degenerate UV triangles or non-manifold edges.
- Zero named surface intersections with the steering head, upper/lower clamps,
  both frame rails and the saddle.
- 951 other meshes retain exact vertex/face data, transforms and material bindings.
  Only the replacement tank and vertical seating of its existing fuel cap/gasket
  are in scope.
- Canonical markers remain unchanged and the actual seat center remains at
  Z 0.800 m within the existing 0.00001 m check.
- New native compressed source: `RB_Golden_Spark_v2_refined06.blend`.

The checks are static and named. They do not establish swept steering clearance,
export/LOD readiness, full material fidelity or an exact concept match. The final
quarter/side images use the same camera parameters as refined05 for direct
comparison. This candidate remains visually unaccepted and is not exported or
promoted to Unity.

## Actual final render review — visually rejected

Both `06-quarter.png` and `06-side.png` were opened after rendering and compared
with the corresponding refined05 and pinned concept views. The exposed Boolean
scallops are gone and the new neck is a closed smooth surface. However, the
underside clearance solution leaves the tank visibly too high and separated
from the frame/engine, especially in the side image. The front silhouette is
shorter and more pointed than the concept, and the cream inset becomes an arrow
shape at the neck rather than the reference's rounded panel. A preserved upper
ignition lead is now conspicuously exposed beneath the raised tank. The tank's
mounting relationship and the concept's lower silhouette are therefore not
resolved by passing intersection tests.

Disposition: preserve refined06 as an explicitly unaccepted/rejected visual
candidate and comparison record. Do not promote it over refined05 or export it
as a finished asset. The batch stops here as instructed by root; no additional
geometry refinement is started. This record does not claim completion of Spark
or of overall P08 visual fidelity.
