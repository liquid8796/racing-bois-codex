# Single-asset conditioning studies — 2026-09-30

All source images were visually inspected before this work. The three new images use the built-in ImageGen tool with explicit local references and requested transparent backgrounds. They are separate **unaccepted input studies**; the locked masters and their complete view sheets remain unchanged. No Tripo job, key access, Blender operation or Unity promotion was performed by this preparation task.

| Asset | Conditioning image | Dimensions | Review disposition |
| --- | --- | --- | --- |
| Ash | `ArtSource/Concepts/P08/TripoInputs/20260930/ash-front-v1.png` | 1024 × 1536 | Single full-body neutral front; root review pending |
| Odyssey | `ArtSource/Concepts/P08/TripoInputs/20260930/odyssey-quarter-v1.png` | 1536 × 1024 | Single front-quarter; tyre margins and reference details need review |
| Havoc | `ArtSource/Concepts/P08/TripoInputs/20260930/havoc-quarter-v1.png` | 1536 × 1024 | Single front-quarter; tight tyre margins and mirror conflict need review |
| Spark | Existing `ArtSource/Concepts/P08/Golden/spark-v1-side.png` | 1536 × 1024 | Clean, large single bike; reuse original bytes for an input candidate |

## Bounded visual comparison

**Ash:** The study retains the helmeted adult man's front view, warm tan skin, dark fringe, ivory open-face helmet with goggles above the eyes, charcoal jacket and trousers, ochre shoulder/arm stripes, articulated black gloves and brown riding boots. Both hands and complete boot soles are visible. Extraction reframes the figure at higher image occupancy. The face is reinterpreted rather than copied pixel-for-pixel; nose/jaw/eye expression, helmet wear and goggles differ locally. Leather wear is more strongly cracked, folds and seam paths are redrawn, and hand/boot details need direct reference comparison. Root must review these differences before using this image for generation. It does not replace the approved face studies, side view or back view.

**Odyssey:** The study retains the bronze/ivory tank and dark knee pad, brown two-level seat and luggage roll, rear rack and pannier, short smoked screen, circular projector headlamp with a horizontal bar, mirrors, amber signals, alloy road wheels, ribbed engine, silver cases, side silencer and perforated lower plate. The selected hero view is re-rendered: perspective/relative wheel presentation, rack/luggage stitching, engine-case detail and panel/wear details differ. The visible pannier does not prove the hidden side was preserved. The front tyre reaches the lower edge of the conditioning canvas. The sheet's side/front/rear views remain the independent construction specification.

**Havoc:** The study retains the faceted sandy tan tank/cowl/tail, black knee pad and seat, rectangular horizontal headlamp, exposed finned V-twin, black trellis frame, paired stacked short steel cans, wide tyres and black fork. Relative proportions, engine/header details, tank wear and small mechanical fittings are re-rendered. The front tyre reaches the lower edge; the rear tyre is close to the left edge. The source itself shows mirrors in the rear view while its large hero and front view omit them. This study follows the selected hero's mirror-free handlebar; it does not resolve that source conflict or certify a consistent all-view design.

**Spark:** The existing side image already shows a single complete large motorcycle with copper/cream tank, brown stitched seat, round lamp, black frame/engine, twin rear suspension, road wheels and metal side silencer. Its quarter-view master was also inspected and the visible identity is consistent. The floor and warm backdrop remain in the original RGB image; it is not a transparent cutout. One side cannot specify the hidden opposite side or establish 3D part fidelity. No generation, copy or alteration of this original was needed.

## Alpha and provenance

The three generated PNGs are RGBA with zero-alpha corners. All have alpha extrema 0–254; no pixel has alpha 255. `image-metadata.json` records decoded dimensions, hashes, byte counts, alpha bounds and counts without changing raster data. Odyssey and Havoc alpha bounds reach the lower image edge, so real tyre contour/framing must be inspected before dispatch. Alpha presence and mesh generation success cannot establish clean semantic cutouts or concept fidelity.

`provenance.json` records exact master, study, prompt and metadata hashes, original built-in output paths, source view selection, visual differences and pending status. Each full prompt is retained beside this README. New images were copied byte-for-byte from the tool's output directory; the originals were retained. The exact underlying ImageGen model identity is not exposed by the tool.

Root owns final input review and any API dispatch. A resulting Tripo model still requires Blender correction, source-bound corresponding-view render review, geometry/rig/LOD checks and the unchanged production promotion gate.
