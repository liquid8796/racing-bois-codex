# Apex v2 — isolated authoring candidate

New geometry was authored after inspecting `ArtSource/Concepts/P08/Golden/apex-v2.png` and its root-approved production decisions. The existing P08 bike geometry, material atlas and user-owned Club source were not used as visual masters or overwritten. This is a candidate for independent Unity review, **not a production acceptance receipt**.

## Current files

- Authoring source: `ArtSource/P08/Golden/Apex/RB_Golden_Apex.blend`.
- Export: `Assets/RacingBois/Art/P08/Golden/Apex/RB_Golden_Apex.fbx`.
- Exact-input Unity descriptor: `docs/p08/golden/apex/descriptor.json`.
- Fresh authoring observations and hashes: `geometry-observations.json`.
- Reproducible recipes: `tools/p08/golden/apex_model.py`, `apex_textures.py`, `apex_audit.py`, `apex_descriptor.py`.

The source was executed through the repository's pinned Blender MCP server, with safe mode enabled, in the task-owned Blender 5.2.1 LTS instance on port9876. Scene inspection confirmed a fresh Cube/Light/Camera scene before the initial snapshot/reset. No external asset service, original-game extraction or headless export was substituted for MCP.

## Design and measured geometry

The sporting chassis uses a new shaped tank/split saddle/tail, fitted multi-piece fairing with an actual intake opening, windscreen attached to its fairing, two fairing-mounted mirrors, low clip-ons, inclined engine, four headers, central riser and exactly two hollow under-seat exhaust outlets. Wheels, suspension, chassis, chain and brake assemblies use their actual placement. LOD wheels rotate about axle-centered parents.

- Wheelbase: **1.43m**; nominal tyre diameter: **0.63m**.
- Seat contact target: `(0, .824, -.370)`. The uncompressed saddle crown is about`.844m` at that longitudinal position; the20mm difference remains an explicit padding/pose fit check when Ash is seated, not a solved contact claim.
- Grip contacts: `(±.294, .927, .389)`; foot contacts: `(±.286, .342, -.249)`.
- Measured visual bounds: approximately **.8883 × 1.2017 × 2.0654m**, including mirrors. Ground tyres extend about2.7mm below the nominal contact plane because of their shallow channels; Unity's ground markers remain exactly at0.
- Current LOD triangle counts: **68,948 / 31,024 / 10,340**. Three mesh renderers per level; eight distinct material slots across the asset. This is a measured inventory, not an FPS/memory verdict.
- All nine current meshes are manifold; the source audit found zero degenerate geometric triangles and zero zero-area UV triangles.

The initial76k-triangle candidate was reduced by lowering subpixel bevel segmentation. Subsequent longitudinal profile samples improved tank/tail curvature. Close-up cost and LOD transitions still need native Unity inspection; no automatic quality approval follows from triangle reduction. The `.blend` also retains named editable manufactured parts in the hidden `Apex_Source_Components` collection. This collection is excluded from the FBX and render; the assembled runtime root is separate.

## Surface and UV policy

Eight physically distinct materials: pearl fairing paint, graphite chassis/trim, machined metal, rubber/upholstery, titanium, tinted glass, front optics and red optics. These are full-field physical finishes, not4×4 colour swatches. Pearl maps are2048px, structural finishes1024px, small optics/glass512px. Metallic/smoothness uses R/A; roughness sources are kept. Colour maps are sRGB and data maps linear.

Analytic longitudinal/radial UVs follow shaped surfaces and round manufacturing parts; panels use projected charts. Manufactured components intentionally reuse seamless surface finishes. Thin bevel faces, cap faces and solidify rims receive planar charts at metric scale when an inherited UV triangle collapses. No triangle is packed into a microscopic repair strip. This policy allows intentional component overlap/tiling; the audit does not claim a unique non-overlapping body decal bake or measured texel stretch.

Rotor drilling is represented by dark recessed markers to limit geometry; it is not a boolean-cut manufacturing simulation. This detail needs gameplay/garage visual assessment. Materials and glass response in Unity must be checked independently from Cycles.

## Visual iteration and remaining gates

`iteration-01-rejected-beauty.png` and `iteration-01-side.png` exposed a solid nose hiding lamps, an oversized shoulder rail and flat side panels. `iteration-02-rejected-beauty.png` exposed lamp/cowl interference and faceted side shading. The current third revision replaces the nose with a fitted shell, removes the rail spike, smooths shell shading, separates optics and makes the twin exhaust openings physically hollow.

The fourth visual revision removes weighted normals from curved lathed surfaces, preserves flat annular end faces and samples tank/tail profiles smoothly; this fixes the foil-like exhaust highlights exposed by the third rear view.

Current renders: `apex-beauty.png`, `apex-side.png`, `apex-rear.png`, `apex-rear-direct.png`. These are Blender authoring views, not game screenshots. Root review must judge whether the new silhouette, fairing surfaces, lighting/material finish and mechanical detail are good enough to become the project's art standard. The author's assessment remains conservative: stance and assembly are improved, but fairing surfacing and finish detail are simpler than the photographic concept. **Do not mass-produce the roster from this candidate yet.**

An attempted render reuse check after adding the editable source collection did not produce an identical exported-data signature. The final revision was therefore rendered again; no old PASS or image was promoted through that mismatch.

Outstanding: Unity import/axis and material inspection, prefab/LOD validation, native player views, steering/wheel clearance, rider grip/seat/foot contacts, movement/weapon interactions, shader/UV mip behavior and measured performance. The explicit collider is a review proxy; it does not change server collision authority. Production gameplay IDs, prefab references and content masks remain unchanged.
