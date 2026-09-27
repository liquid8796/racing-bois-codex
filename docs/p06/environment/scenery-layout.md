# P06 canyon scenery layout

The layout revision follows the inspected `ArtSource/Concepts/P06/canyon-v1.png`. The earlier `docs/p06/unity/race-first.png` showed narrow, isolated rock pillars and foliage too far from the road to read at gameplay distance. This revision changes placement of the already authored P06 prefab kit; it does not introduce another model or bypass the concept-before-3D workflow.

## Composition and budget

- Each 160 m chunk has three staggered groups on each side: six broad upper banks using RockA, each paired with a lower RockB ledge. Two small low outcrops break the gaps. Upper-bank scale is approximately 5.2-6.5 on X, 1.9-2.45 on Y, and 10.5-13 on Z. This yields wide, comparatively low forms instead of highly variable spires. The existing mesh detail and material remain intact.
- Banks follow the local road direction with small deterministic yaw changes. Paired ledges sit toward the road and slightly forward of their bank. A 5-by-5 grid samples the actual rotated footprint, inverts its curved route coordinates, and buries the imported lower bound under the lowest sampled terrain height to remove floating roadward undersides.
- The previous six upper-rock placements per chunk remain six. Lower-rock placements increase from six to eight. At the current imported LOD triangle counts, these two extra RockB placements add at most 3,512 resident triangles per chunk across all three LODs, before clearance rejection. The 16-chunk route therefore adds at most 56,192 triangles (about 2.7% of the earlier 2.06 million baseline), rather than multiplying the environment population.
- Sage and grass retain their previous instance counts. Sage is concentrated at 10.8-18.8 m from the centerline; dry grass at 9.8-16.3 m. Broader clusters improve shoulder density without adding foliage meshes. Roadside furniture remains unchanged.
- Distant mesas reuse RockB LOD2, with reduced height variation and a broader depth. No new horizon mesh asset is authored.

The existing one-time mesh combination, three-LOD batches, five-Hz chunk visibility checks, shared materials, and uploaded unreadable combined meshes remain in place. Layout clearance runs only during `Build`, never during the frame update.

## Road clearance and surface invariants

The physical route definition, asphalt, shoulder, edge paint and center markings are unchanged. The terrain ribbon remains within 110 m of the road centerline, below the existing route's minimum inner bend radius. This layout does not add physics colliders.

Every RockA, RockB and horizon-mesa candidate is checked against the complete route, including other arms of bends. The check:

1. Combines imported source bounds across all LODs in prefab-root coordinates.
2. Transforms the four corners of that XZ footprint by the candidate's real placement matrix.
3. Computes minimum distance from the footprint to every segment of the centerline sampled at 4 m spacing, with segment intersection and contained-point checks.
4. Reserves the 9 m visual road/shoulder half-width, a further 0.25 m chord allowance, and at least 1 m of free space before the conservative rock bounds. A near candidate can move outward by 8 m twice; otherwise it is omitted. The 4 m chord allowance exceeds the maximum approximately 0.015 m circular-arc deviation at the existing 0.0072 rad/m peak curvature.

This uses a conservative transformed bounds footprint, not a mesh-triangle intersection test. The public `AcceptedLargePropCount`, `RejectedLargePropCount`, and `MinimumLargePropRoadClearance` expose actual build measurements for Unity validation. The final value subtracts both the 9 m half-width and 0.25 m allowance from the minimum footprint-to-polyline distance; accepted candidates require at least 1 m.

## Validation status

The pre-edit screenshot and concept were inspected. Source whitespace validation passed after the layout edit. The runtime placement counts, resulting triangle count, measured clearance and visual acceptance must be recorded after the root agent rebuilds the actual Unity scene. No precomputed placement PASS or new screenshot acceptance is asserted by this document.

## Directional sign correction

The source arrow points along prefab semantic -X. Positive track curvature turns right, so right-curve boards now rotate 168 degrees (the original -12 plus180); left-curve boards retain12 degrees. Both authored board faces have valid matching UVs. This fixes the initial right-turn arrow mistake without negative scale, changed assets, collider changes or modified authority. The first Web candidate was superseded before delivery.
