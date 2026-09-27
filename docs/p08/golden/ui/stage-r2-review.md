# Actual candidate UI staging

The Editor-only fixture under `Assets/RacingBois/Editor/GoldenUiStage` is integrated and has run on the actual Race scene. It uses the real Apex R2, Ash V3 and Canyon V14 prefabs, samples the authored Idle clip, and shows explicit fixture notices. It does not open production masks or alter accounts/content registry.

`golden-main-v2-stage-1920.png` and `golden-garage-v2-stage-1920.png` exposed an incorrect camera side and toolbar overlap. The r2 captures reverse the camera to the concept's side, hide the debug controls while retaining the notice, and use temporary comparison lighting. The fixture's Close restored the bootstrap, stage and camera, and the prior runtime quality pipeline; no Console errors were observed.

These images still fail visual acceptance. The main backdrop is the wrong composition, the hero pose lacks the hand resting on the motorcycle, surface/shadow artifacts remain, and both hero models differ substantially from the concept. The garage lacks the real workshop and genuine thumbnails. Fitting measured bounds to a screen rectangle is not visual parity.

State reports `main-stage-r2-state.json` and `garage-stage-r2-state.json` bind the actual candidate paths, concept hashes, camera pose and projected bounds. Native GUI/input acceptance is separate from this Editor fixture.
