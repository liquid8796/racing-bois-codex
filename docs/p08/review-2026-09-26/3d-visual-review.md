# 3D visual review — 2026-09-26

**Verdict: the inspected hero models do not meet the requested Windows desktop presentation quality.** The concepts generally supply useful direction, but the models lose their proportions, construction, surface detail and identity. Rebuild hero geometry; rework most scenery selectively. Preserve existing sources and working IDs, sockets, colliders and pipeline while replacement candidates are evaluated. This review made no production changes or deletions.

## Evidence limits

The images below were opened directly with `view_image`. P08 contact sheets and bike renders are Blender authoring views, not Unity gameplay. The P06/P04 Unity images are historical saved screenshots. This is an image-based judgement of those exact artifacts, not proof that they match the latest FBX bytes. Source/receipt freshness belongs to the separate technical audit. Images cannot verify UV overlap, scale, rig mapping, LOD transitions, topology, missing references or performance. A missing render is **unreviewed**, not a failed model.

## Motorcycles

**Rebuild all twelve inspected P08 hero bike meshes for final presentation.** Retain their concept direction and stable semantic IDs. They could remain temporary gameplay proxies during replacement.

Common failures: nearly identical tall, narrow chassis, fork spacing, engine fins, exhaust, wheels and upright controls; crude tank curvature; shallow undetailed lamp faces; little separation between rubber, painted metal and upholstery. Sport fairings sit around the same exposed upright mechanical core. This is not a minor texture-only gap. Shared manufacturing parts are reasonable, but distinct vehicle classes must retain different proportions and riding posture.

| ID/name | Specific observed gap against its concept |
|---|---|
| 01 Kestrel | Teardrop tank, compact engine construction, curved fender and headlamp detail reduced to coarse blocks; blue roadster identity survives. |
| 02 Rift 250 | Concept red/cream panel arrangement largely lost; same blunt nose and tall controls as 05/07/09/12. |
| 03 Jackal | Grille and twin high exhausts identify it, but knobby tyres, protective skid plate and scrambler stance are missing visually. |
| 04 Ember | Reads primarily as recoloured Kestrel; concept twin-cylinder character, swept exhaust and separate saddle shape are weak. |
| 05 Apex | Concept angular nose, under-seat exhaust and integrated aerodynamic shell become upright common chassis and generic twin lamps. |
| 06 Corvus | Twin projectors/purple accent survive; tank, shrouds and mechanical density lack the concept's distinctive angular construction. |
| 07 Viper | Three vents survive; narrow eye lamps and aggressive wedge silhouette are replaced by the common sport nose. |
| 08 Rift 750 N | Blue colour survives; sculpted vertical headlight cluster becomes a broad flattened snout with white strips. |
| 09 Specter | Flowing silver/navy integrated fairing becomes broad uneven panels and an applied dark patch. |
| 10 Nightjar | Rack/tall screen survive; touring saddle, front enclosure and tank-to-fairing transition need rebuilding. |
| 11 Cinder 10 | Round twin lamps distinguish it, but endurance fairing/vent construction and proportions remain generic. |
| 12 Rift 750 | Red colour/angular vent survive; sharp lamps, tail and compact sporting posture do not. |

Coverage: every `docs/p08/art/RB_P08_Bike_01-render.png` through `12-render.png`, paired with every corresponding `ArtSource/Concepts/P08/Bikes/01-kestrel-v1.png` through `12-rift-750-v1.png`. Bikes 13/14 were not inspected as models.

## Four P08 environment kits

All four concept/contact pairs were inspected: `ArtSource/Concepts/P08/Environments/{neon-district,ridge-pass,coastal-line,orchard-road}-v1.png` and `docs/p08/art/{neon,ridge,coast,orchard}-contact.png`.

| Kit | Decision |
|---|---|
| Neon | Rework warehouse/shop facades: flat glowing windows, blank surfaces, missing depth and construction wear. Keep gantry, tank, lamp and shelter base geometry as candidates; enrich joins, materials and functional detail. |
| Ridge | Rework gallery roof/pillars, uniform masonry and cabin. Rebuild nearby rock silhouettes; fir needs denser irregular branching and foliage. Current pole may be retained after gameplay-distance testing. |
| Coast | Rework bridge/beacon/shack. Palm canopy is sparse and mechanically radial; rebuild crown and leaf mass. Rock is a rounded lump; rebuild near-road geology. Shrub is too small in this contact to approve detail. |
| Orchard | Rebuild apple foliage: faceted solid blobs contradict leafy concept. Rework barn/silo surfaces and proportions; fence, hay bale and kiosk foundations are usable with material/edge-detail work. |

These kits do not establish complete route composition, atmosphere or road-surface quality.

## Reused P06/P04 content

Inspected P06 `motorcycle-v1`, `rider-v1`, `patrol-v1`, `canyon-v1` concepts; corresponding hero/environment renders; both TrafficCoupe/TrafficVan renders; Ride, AttackRight, KickLeft, Fall and Run pose images; `docs/p06/unity/race-refined.png`.

- **Rebuild motorcycle/police and rider hero visuals.** Rider cylindrical limbs, detached-looking shoulder construction, mitten-like palms and egg-shaped helmet visibly depart from tailored clothing/anatomy. Static poses do not prove convincing motion or grip contact.
- **Rework coupe/van:** recognisable silhouettes, but oversized flat glazing, slab panels and generic wheels need detail and proportion refinement.
- **Rebuild nearby canyon rock/foliage appearance; rework composition/materials.** Historical Unity frame shows repetitive horizontal rock bands, sparse ground and broad flat terrain, far from the concept. Roadside pole/sign/guardrail base shapes are reusable candidates.
- **Keep club geometry candidate; rework finish if used close-up.** Inspected `ArtSource/Concepts/P03P04/club-concept-v1.png`, `docs/p04/club/club-render.png`, `unity-right-attack.png`: readable silhouette/grip in gameplay, but wood grain and wrap are simplified. Preserve the user-modified `.blend` untouched.

P08 rider00 has no reviewed beauty render; remaining riders, portraits, new traffic/pedestrians and full P08 route gameplay are outside verified coverage. Acceptance requires fresh Unity close-ups, rear gameplay framing, turntables, animation contact and measured performance after replacements.
