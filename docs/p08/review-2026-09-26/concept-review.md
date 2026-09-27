# Independent concept review — 2026-09-26

Scope: visually inspected the actual PNG for every concept under `ArtSource/Concepts/P08` (14 motorcycles, 8 riders, 4 environments and 5 UI screens), plus all 11 earlier P03/P04/P06 concepts. This is a review of the 2D images, not certification of the corresponding mesh, textures, Unity prefab or runtime UI. No concept or production file was edited, generated or deleted during this review. `concept-coverage.json` binds the 42 reviewed paths to their file hashes.

## Decision

Do not delete the entire concept set. Most motorcycle and rider images provide useful visual direction. Their photoreal surface detail does **not** make them reliable engineering turnarounds or prove that current 3D assets reach the same quality. Several sheets contain incompatible views, and every generated dimension needs replacement by an explicit project specification before it can drive scale.

The UI needs a corrected v2 specification before it can be called approved: its composition is useful, but its screens invent routes, catalog artwork, controls, prices, copy and dates. The gallery hero explicitly contains `YAMAHA`; replace that hero. The environment sheets are mood and prop-selection references, not complete modular construction plans. There is no basis in the images alone for marking the whole collection production-ready.

### Classification meanings

- **Keep direction**: retain the design and reference; production constraints and 3D verification still apply. This does not mean the image should be imported as game UI/texture.
- **Revise**: preserve the core idea but correct an identified ambiguity or mismatch before treating it as the canonical reference.
- **Reference only**: useful for mood or history, insufficient as the final modeling/layout specification.
- **Regenerate section**: replace the named visual section because local cleanup would leave a misleading reference. Preserve the old image as review evidence until a replacement is accepted.

## Motorcycle concepts

All P08 bike paths below are relative to `ArtSource/Concepts/P08/Bikes/`.

| Image | Decision | Observed strengths and required correction |
|---|---|---|
| `01-kestrel-v1.png` | Keep direction | Round lamp, narrow tank, flat saddle and spoked wheels establish a readable simple roadster. The `750 mm` width annotation spans much less than the visible handlebar span; do not trace it as a measured drawing. Tiny engine lettering and decorative emblem need a deliberate original decal decision. |
| `02-rift-250-v1.png` | Keep direction | Rectangular twin lamps, white/red slab fairing and upright tail provide a distinguishable older sport-bike silhouette. Canonical side/axle positions, rear light and fairing thickness must be specified outside the sheet. Do not reuse image dimensions as authoritative handling/scale data. |
| `03-jackal-v1.png` | **Revise** | Raised fender, knobby tires and olive/brown scheme read as a scrambler. Hero/side/detail show two high exhaust cans on one side; rear view shows a can on each side. Choose one routing and redraw the conflicting rear view. Check leg/boot clearance around the high heat shields in the actual riding pose. |
| `04-ember-v1.png` | **Revise** | Burgundy tank, rounded fenders and stepped saddle give the retro bike a clear identity. Hero/side show two stacked cans on the visible side; rear view shows four outlets, two per side. Lock cylinder/header/muffler count and correct the rear. Remove malformed tiny exploded-view text. |
| `05-apex-v1.png` | Keep direction | White/black angular fairing, tall intake and under-seat exhaust define a usable shape language. Windshield/fairing joins, vent depth and exhaust support are actual geometry requirements; flat color blocks will not reproduce this concept. Lamp close-up is more elaborate than the front overview, so select one final lamp construction. |
| `06-corvus-v1.png` | Keep direction | Twin exposed projectors, faceted charcoal tank and purple accents distinguish it from the retro round-lamp bikes. The many tiny engine/radiator parts are visual suggestion, not a validated assembly. Preserve the large negative spaces; do not model every painted line as a tube. |
| `07-viper-v1.png` | Keep direction | Green full fairing, three side slots, low exhaust and slit lights form a clear family. The `850 mm seat height` line is drawn beside the front view and reaches a front-body landmark, not the saddle. Correct dimensions in the production sheet and validate the three vent openings with real thickness. |
| `08-rift-750-n-v1.png` | Keep direction | Blue naked bike with a compact angular headlamp, exposed engine and stepped seat is distinguishable from faired Rift 750. Verify actual steering clearance between bars, tank and headlamp shroud. Do not inherit generated embossed case text. |
| `09-specter-v1.png` | **Revise** | Flowing silver/navy bodywork provides a useful contrast to the angular sports. Hero, side and exhaust detail show stacked outlets on one side; rear view splits them left/right. Correct exhaust routing and its relationship to the swingarm before modeling. |
| `10-nightjar-v1.png` | Keep direction | Tall screen, broad seat and rear rack make the touring role legible. Screen, mirror and rack mounts need explicit connections. The front `0.78 m` width dimension does not cover the full bars; replace with canonical measurements. |
| `11-cinder-10-v1.png` | Keep direction | Orange endurance fairing, twin circular lamps and large perforated muffler have a distinct period flavor. `~205 kg`, class and dimensions are generated annotations, not game design authority. Use one lamp housing outline consistently and clarify lower fairing/engine separation. |
| `12-rift-750-v1.png` | Keep direction | Red angular full fairing, side intake and tapered tail distinguish it from the naked variant. Its design family is close to Apex/Viper, so preserve the particular tank/vent/tail profile rather than using one common fairing with recolors. |
| `13-odyssey-v1.png` | Keep direction | Copper/cream roadster with panniers and a small screen contributes a visibly different touring silhouette. Pannier, rack and exhaust clearance need a riding/rear-wheel sweep check in 3D. Small side-cover/case markings are not approved branding. |
| `14-havoc-v1.png` | **Revise** | Sand-colored muscular tank, short rectangular nose and high stacked cans give a useful chunky silhouette. Mirrors are absent from the hero/side but appear in front/rear views; choose a canonical configuration. Resolve high-exhaust leg clearance and the thin rear subframe support explicitly. |

The set has meaningful role variety: retro roadsters, scrambler, naked bikes, faired sports and touring bikes. There is still substantial visual clustering among the faired sports and among dark naked bikes. A colorless side/rear silhouette comparison at actual gameplay distance is needed before approving the roster; this review did not infer diversity merely from 14 different paint colors.

### Cross-cutting bike fixes

1. Generate/author a **canonical** left, right, front and rear orthographic sheet with the same wheelbase, wheel radii, axle alignment and part counts. A perspective hero and detail panels may accompany it, but cannot contradict it.
2. Use project-owned measured dimensions in a separate table. Numerous current annotations use a plausible number with the wrong arrow endpoints. They should not override gameplay envelopes.
3. Specify steering pivot, swingarm pivot, rider contact points, wheel/fender clearance, exhaust routing, and connected brackets. Images alone cannot certify that an apparently plausible suspension/chain arrangement works.
4. Keep branding original. Visible small gibberish/case stamps are not asset detail to trace. No clearly readable real manufacturer name was found on these 14 bike sheets at the inspected resolution; that is narrower than a legal originality guarantee.
5. Do not attempt to rescue a blocky 3D implementation by replacing a good concept. Compare model silhouette, part connections, material response and gameplay shot to the existing usable direction first.

## Rider concepts

All paths are relative to `ArtSource/Concepts/P08/Riders/`. All eight images were viewed individually, including their face studies.

| Image | Decision | Finding |
|---|---|---|
| `00-ash-v1.png` | Keep direction | Coherent charcoal/amber outfit, ivory goggles helmet, boots and adult facial identity across the views. Useful primary reference. Discard invented mottos and specify the helmet strap/raised-goggle state for play versus portrait. |
| `01-juno-v1.png` | Keep direction | Teal/cream jacket, tied curls and cream visor helmet are coherent and distinguishable. Hair and transparent raised visor require a bounded production treatment; the image is not proof that individual flyaway hairs are necessary or affordable. |
| `02-mako-v1.png` | Keep direction | Navy suit and orange shoulder/knee armor are readable. Helmet, panels and body proportions are consistent enough for design direction. Differentiate his back silhouette from Ash and Kai in the gameplay view; face ethnicity alone is not a distant gameplay cue. |
| `03-rook-v1.png` | Keep direction | Oxblood jacket, cropped auburn hair, high collar and dark half helmet are coherent. Her core jacket/trouser construction is still close to Vale/Kai; preserve shoulder silhouette and stance rather than relying only on color. |
| `04-sol-v1.png` | **Revise** | Stockier body, ochre vest and olive sleeves give the strongest body-shape contrast. Front/back are bare-headed while side/head study are helmeted, with no explicit alternate-state labeling. Add the missing helmeted front/back and define whether the bare-headed state is portrait/menu-only. |
| `05-vale-v1.png` | Keep direction | Plum/slate jacket, pale trousers and bob haircut provide clear value contrast. The three small face studies are useful variation but do not constitute the exact neutral/happy/focused production expression set. Lock those states and keep facial proportions consistent. |
| `06-echo-v1.png` | Keep direction | Pearl/navy suit, teal hair and helmet form a readable light silhouette. Add defined facial expressions and verify elbow/knee protection during seated, strike and crash poses. |
| `07-kai-v1.png` | Keep direction | Navy/brown jacket, orange neck scarf and white hair streak are specific identifying details. Scarf is shown tucked rather than long trailing cloth; preserve that intentional limit. Back view is otherwise close to the darker jacket riders. |

The figures are mostly consistent adult anatomy and coherent clothing. No obvious extra limb or gross missing limb was observed in these sheets. That does **not** establish clean fingers, deforming topology, skin weights, facial rig or safe visor transparency in the actual mesh.

The repeated motivational copy (`Same Roads`, `Brighter Tomorrow`, `People`, etc.) is irrelevant generated filler and should not become game dialogue, signage or UI copy. The faces/clothes establish a grounded realistic art direction. A low-detail mannequin with a helmet and recolored jacket will not meet it. Add matching front/side head construction, the three required expression states, a riding pose and strike pose before final character art acceptance. Actual shared-rig constraints must be imposed deliberately, not guessed from the common `~1.75 m` captions.

## Environment concepts

All paths are relative to `ArtSource/Concepts/P08/Environments/`.

| Image | Decision | Finding and next requirement |
|---|---|---|
| `neon-district-v1.png` | Reference only | Strong dusk industrial-waterfront mood and a recognizable six-prop selection. It is dominated by invented slogans on warehouses, lamp banner, bus shelter and tank, and has less actual neon identity than its title suggests. Retain lighting/palette/industrial hierarchy, replace the writing with intentional environmental storytelling, and add scale/backs/modular joints for buildings, gantry, shelter and tank. |
| `ridge-pass-v1.png` | Reference only | Clear alpine silhouette, road sight line, fir/granite/wall/hut/snow-pole/gallery vocabulary. Useful target for natural tree silhouettes and rocky layering. Six small isolated views do not define gallery tunnel depth, connected modules, collision passage or foliage LOD construction. Add a modular engineering sheet and gameplay camera blockout. |
| `coastal-line-v1.png` | Reference only | Clear coastal palette, broad road visibility, palm/shack/beacon/bridge/boulder/shrub selection. Several irrelevant slogans clutter the scene. The bridge pier cutout is not a full bridge kit. Define deck/abutment/rail/pier continuity and road clearance before calling the environment buildable. |
| `orchard-road-v1.png` | Reference only | Readable rural variation: apple rows, barn/silo landmark, fence, hay and produce stand. The sheet still says `PC-WEB` and uses first-person handlebars while the main gameplay HUD reference is third-person. Keep biome direction, establish the actual gameplay camera and repeated-row/terrain modules, and remove filler copy. |

These four images are much closer to photographic environment mood boards than low-cost procedural kit specifications. They do not prove that six isolated objects per biome reproduce the depth, terrain, distant landmarks, ground cover and material detail shown in the hero images. Nor do they prove performance. A successful six-object export is not an equivalent visual result.

## UI concept review

All paths are relative to `ArtSource/Concepts/P08/UI/`. Review is of the generated concepts; the root review separately evaluates actual Unity UI and source behavior.

| Image | Decision | Finding |
|---|---|---|
| `ui-main-v1.png` | **Revise** | Useful large primary action, open scene and flat route rail. Generated `EST.1996`, trademark glyph, mottos, jacket/sign copy and route names are not authoritative. The rail says Coast Ride/Industrial/Highland/Night City rather than the actual five-course naming used elsewhere. Make a corrected reference with real routes, clear practice/career/online/LAN ownership and keyboard focus. |
| `ui-garage-v1.png` | **Revise** | List, large vehicle stage and pinned actions are an appropriate PC-game composition. List thumbnails do not honor the canonical bike designs (Kestrel is represented as a sport bike), the featured Specter differs from its bike master, and prices/stats/condition are invented. It also combines an unowned price selection with `CHỌN XE`/repair actions without defining their enabled states. Correct the actual item/state flow and remove marketing filler. |
| `ui-lobby-v1.png` | **Revise** | Eight seats, invite block, readiness and a fixed footer are useful. `SINCE 1994` contradicts the other invented `1996` branding. Portraits and motorcycles do not match the defined roster. Large background/hero banners spend height that the eight rows need at smaller desktop sizes. Add exact host/guest/loading/disconnected/full/error variants, actionable invite/server address distinctions for LAN and Internet, and real focus/disabled states. |
| `ui-hud-v1.png` | **Revise** | Peripheral placement protects the main road and gives speed/rank strong hierarchy. Generated `Q SỬ DỤNG / E ĐỔI VŨ KHÍ` conflicts with the actual left/right attack controls described in project provenance. The permanent top/bottom branding and decorative slogans add noise to a combat HUD. Define rider/bike/weapon/stamina/police/connection feedback from real game rules and separate online menu behavior from offline pause. Readability over bright road/sky needs actual runtime testing. |
| `ui-gallery-v1.png` | **Regenerate section** | Replace the hero/reference artwork: `YAMAHA` is clearly readable on the orange bike, characters and bikes are unrelated to the roster, and the plate/year/slogans are invented. The left list also presents invented categories/titles/counts/durations and simultaneously shows browse/play/skip/subtitle states. Retain the general list-plus-stage composition, but create a new reference with original approved actors and the real cinematic taxonomy, with browse and playback as separate states. |

The charcoal/ivory/amber system, flat rows and vehicle-led framing are worth retaining. However, all five screens rely heavily on attractive generated scenic imagery; there is no assurance the current Unity scene reaches it. Implemented UI should be compared to **actual** rendered models and environments, not accepted because the concept looks polished.

All five use substantial small, condensed uppercase text. At 1080p this may work for headings, but secondary Vietnamese text, glyph accents, 1366×768 layout, UI scale, keyboard/controller focus, long player names, empty/error/loading states and readable contrast remain unproven. The PNGs cannot demonstrate smooth animation or accessible interaction. No replacement should simply paste the generated screen as a background.

## Earlier reused concepts

| Image under `ArtSource/Concepts/` | Decision | Finding |
|---|---|---|
| `P03P04/motorcycle-concept-v1.png` | Reference only | Useful angular orange naked-bike origin; later P06 changes tank, saddle and front cowl to a retro design. These are different canonical shapes, not two exact views of one bike. Pick the intended Spark 450 master and record supersession. |
| `P03P04/rider-concept-v1.png` | Reference only | Coherent helmeted orange/ivory/charcoal rider, but historical dimensions and generic identity are not the P08 eight-person roster. Preserve as predecessor, not face/character acceptance. |
| `P03P04/canyon-concept-v1.png` | Reference only | Useful road/canyon and boulder/shrub direction; browser wording is obsolete. Later P06 is the more detailed scenic reference. Neither defines complete terrain geometry or visibility budgets. |
| `P03P04/club-concept-v1.png` | Keep direction | Simple silhouette, wrapped grip and wood/grain direction are legible without gratuitous details. Painterly glossy wood needs grounding against the realistic P06/P08 materials. Add intended dimensions/contact grip in the asset specification. This review does not authorize overwriting the pre-existing user-edited `.blend`. |
| `P03P04/coupe-concept-v1.png` | Keep direction | Side/front/rear/hero consistently identify a simple two-door traffic coupe. The `3.8k triangles`/clean topology text is only a generated claim. Headlamp/trim/tire details and materials need to match the later realistic style in actual production. |
| `P03P04/van-concept-v1.png` | Keep direction | Side/front/rear/top are useful and retain the cream/orange van identity. Confirm dimensions, sliding-door side, marker lamps and mirrors against the canonical model. A box with colored windows would not meet even this restrained concept. |
| `P03P04/pedestrian-concept-v1.png` | **Revise** | Vest/jeans/t-shirt role is usable, but the face/hair and illustrated finish are noticeably more cartoon-like than the P08 rider portraits. Rebase its head/material treatment onto the same character art direction before visible cutscene/gameplay acceptance. Generated `2000–3500 triangles` is not a topology audit. |
| `P06/motorcycle-v1.png` | Keep direction | Coherent orange retro roadster, twin round lamps, stepped brown saddle and stacked exhaust. Visually valuable master if this is the intended Spark 450; do not silently mix its curving tank/saddle with the P03 angular version. Need exact scale/steering/rider-pose specification. |
| `P06/rider-v1.png` | Keep direction | Clean full-face helmet/jacket/glove/boot direction. Useful generic rider construction, but a closed helmet cannot supply the eight visible P08 faces and expressions. |
| `P06/canyon-v1.png` | Reference only | Useful sunlit layered canyon and coherent road-furniture palette; no distracting text. Requires world/terrain blockout, near/far rock treatment, ground cover, horizon and actual gameplay comparison. |
| `P06/patrol-v1.png` | **Revise** | Police color blocks, panniers, tall screen and blue beacon are legible. Hero shows two stacked exhausts on the visible side, rear mini-view shows one outlet on each side. Resolve routing and give the patrol rider a back/side construction reference. |

## Repair order before resuming content expansion

1. Freeze these originals as evidence; mark superseded references in a manifest. Do not erase useful masters or user work before replacement acceptance.
2. Fix the four P08 conflicting bike sheets (Jackal, Ember, Specter, Havoc), the patrol routing, and Sol's unlabeled helmet variants. Supply canonical dimensions and assembly decisions separately for all bikes.
3. Regenerate gallery hero with approved original actors. Revise all five UI specs with actual catalog/course/control/state data and no slogans, invented dates or real manufacturer marks.
4. Establish one grounded character/vehicle/environment style target and compare actual gameplay-distance renders to it. Correct any 3D gap in the model/material, rather than hiding it behind a different concept.
5. Create the missing technical environment-kit and character head/pose sheets where required for the next modeling pass. Then resume production and independently test mesh, UV, material, collision, rig, LOD and runtime quality.

No overall percentage or quality score is assigned. This is a complete **image coverage** review of 42 files, not completion of production QA.
