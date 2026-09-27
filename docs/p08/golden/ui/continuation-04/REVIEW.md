# Garage candidate selection and actual thumbnails

The locked main-v2 and garage-v2 concepts were opened before this patch. Their
reference bytes remain unchanged. This patch addresses two concrete missing
behaviors in the editor review stage: empty inventory thumbnails and selecting
Spark hiding the Apex without showing any replacement.

The stage now renders the actual imported Apex R4 and Spark V1 prefabs into
temporary RGBA sprites using an isolated Unity preview scene. It keeps every
material and mesh binding, measures LOD0 vertices to frame the camera, and owns
the sprite/texture lifetime. Supplied caller sprites remain caller-owned. The
garage's existing real CareerView inventory controls select the corresponding
candidate and reframe it. Production content and profile authority are unchanged.

Actual Unity 6000.5.7f1 Play-mode observations:

- At 1920x1080, both inventory images show the appropriate candidate. A
  NavigationSubmitEvent sent through the Spark inventory button switches the
  title and actual stage to Spark (catalog index0); Apex is index5. Both reports
  show selectedBikeMissing=false and renderedThumbnailsMissing=false.
- Fresh 1366x768 screenshots show each selected bike with unclipped inventory,
  title, condition and bottom actions. These are editor UI-event checks, not
  physical gamepad or shipping-player input acceptance.
- Three Main/Garage switches followed by Close restored the enabled bootstrap,
  the Race scene alone, and the prior 1920x1080 Game view. Zero owned thumbnail
  sprites or textures remained. The final console had no errors; its single
  warning was external MCP duplicate-command suppression.
- A compilation while the first 1366 capture was being prepared closed the
  fixture by its reload guard. That screenshot is retained as
  invalidated-by-reload-main-1366.png; it is a baseline main menu, not garage
  evidence. The subsequent fresh captures have the suffix -valid.
- The first standalone thumbnail probe was black because the preview utility
  reset the camera FOV. The retained probe02 uses the correct FOV; probe03 proves
  RGBA readback. The implementation preserves its measured camera projection
  with Render(true,false), and the final inventory textures were inspected.

The implementation is still visually unaccepted. Apex R4 has visible jagged
fairing/belly overlap; Spark silhouette/mechanics/materials differ substantially;
the workshop, typography, spacing, colors and wordmark still differ from the
reference. The garage concept's Spark thumbnail also predates the later locked
Spark-v1 hero: those visual references must be reconciled before final acceptance.
No 100% fidelity or whole P08/P10 completion follows from this patch.
