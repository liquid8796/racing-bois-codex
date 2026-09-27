# Spark V1 — actual Unity import and render review

The [native publication record](native-publication.json) binds the exact 37 copied files, descriptor and successful Unity import `fb4faf8fbf1a4c8985c562a895640fa1`. Input and output hashes were independently checked again after capture. No production content mask changed.

Twenty-two explicitly declared constant maps remain their original 4×4 size. Unity decoded all 16 pixels of every source and matched the recorded channel values. Real negative PNG controls rejected a single changed alpha pixel and an 8×4 image. Undeclared textures retain the 256×256 minimum. No image was scaled or rebaked to pass a size check.

Four actual Editor URP/Direct3D12 camera renders are in [the capture directory](unity-studio-20260927-02/capture.json). The helper creates a temporary neutral studio, restores pre-existing lights and closes only its scene. These are Editor renders, not native player or performance evidence. The initial uniform-frame attempt was rejected; the final helper frames explicit mesh vertices rather than depending on newly instantiated renderer bounds.

Inspected the quarter and side LOD0 images and the same quarter LOD2 image against the locked hero and side concepts. The corresponding silhouettes make the remaining differences clear:

- The engine reads as a tall rectangular stack with empty surrounding frame space, instead of the reference's closely joined rounded twin-cylinder castings and varied covers.
- The tank's shoulder/cream inset, thin long seat, passenger strap and rear seat transition differ.
- Exhaust bends and heat shields, fork and wheel profiles, brake/caliper detail, cable/control placement and the lamp reflector remain simplified.
- The native surface response is much brighter and more uniform across metal parts. Studio lighting is not calibrated to the concept, so this is an observed appearance difference rather than an isolated material diagnosis. Clearcoat and transmission remain unresolved.
- LOD2 visibly loses tire tread and produces faceting/shading artifacts on discs, shields and the lamp. Its current transition distances are not accepted.

The asset passes structural import; it fails the requested visual specification. `visualAccepted=false` remains explicit. The [earlier export review](EXPORT_REVIEW.md) remains applicable, with its importer-size blocker now resolved by the explicit constant-map contract.
