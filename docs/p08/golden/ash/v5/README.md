# V5 head-equipment geometry trial — unaccepted, not exported

V4's verified publisher, published FBX/maps and frozen source are unchanged.
This separate V5 source addresses the highest-impact geometry findings in
geometry-audit.md. No new ImageGen, cloud or installation service was used;
only direct Blender MCP9876 with safe mode enabled. No Unity call or
Client/server/shared/probe edit occurred in this work.

The old head equipment was removed on the V5 copy while retaining the face,
expression coordinates and skin weights. The new geometry has taller rounded
optical apertures, a2.6mm stamped rim, closed curved lenses, shell-conforming
dark backing, a continuous projected18mm goggle band, side attachments/rivets,
a curved brow opening, a raised rear/nape contour and shaped padding. The
existing hair was fitted behind the new shell instead of leaving its old cap
intersecting the helmet. The face itself was not randomly resculpted in this
pass; its jaw/cheek, nose, eyelid and mouth priorities remain documented.

The first goggles were too canted/large and exposed the old hair cap; those
images are retained. The first closest-surface chinstrap jumped to inappropriate
cheek/neck points and was rejected. The current band uses smooth helmet-anchored
guides and still needs finer fit/closure work. Final actual source images:

- equipment-front-final.png
- equipment-quarter-final.png
- equipment-side-final.png

The current goggles/rim/strap construction is a useful structural comparison,
but it is not100% concept fidelity. The face remains generic; the hair,
weathering, lens appearance, strap closure, collar and clothing remain below
the locked reference. Rear strap visibility is ambiguous across the reference
views and is not silently treated as resolved. Several V5 materials are
constant authoring materials and still need the actual runtime PBR workflow.

The new equipment contains66 objects across three detail levels, with
16,644/8,740/5,028 triangles respectively. These are not yet merged into the
three rider skins and are not a production draw-call budget. The source audit
checks normalized Head weighting and zero degenerate new-equipment geometry/
UV triangles. It found thin pole-cap triangulation in the first shell: real
pole fans replaced the n-gons rather than lowering the geometric threshold.
Planar UV returns repair collapsed edge/cap faces; this is not a packed,
exclusive-atlas certification.

The goggle band has measured signed clearance from the shell:
LOD0 approximately2.17–4.00mm, LOD1 approximately2.15–4.00mm and LOD2
approximately2.05–4.00mm. This is specific geometry evidence, not a claim that
all equipment contacts or all views match the concept. The existing45-bone rig
and13 action names remain; no new animation was authored in V5.

`native-policy-baseline.json` records the parent-verified V4 native descriptor
policy: six explicit loops and the separate MenuHero preview clip. Use that
policy when preparing a future V5 handoff; do not fall back to implicit FBX
loop inference or replace gameplay Idle.

Source: ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend

SHA256: `20ed1963ccf7f7f537a2899a89b59d84a62924b98e7bf94bfeb339e61d9cd5c9`

There is no V5 FBX, Assets publication, native import or visual/performance
acceptance in this trial.
