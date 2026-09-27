# Native editor workshop fixture — still visually unaccepted

The fixture now uses the real generated baked garage scene additively, retaining Unity's lightmaps, reflection cube and probe data. It leaves production masks, profiles and gameplay authority unchanged. The notice in captures is editor-only; these are not released game screenshots.

Verified in the running Unity6000.5.7f1 Editor:

- The loaded V5 scene supplies60lightmapped renderers,1Custom reflection and27actual baked probe positions.
- The first additive probe set did not emit the expected needsRetetrahedralization notification. The fixture now checks that actual loaded positions and spherical-harmonic data cover its authored probes before explicitly tetrahedralizing. It still listens for later native data updates. It never substitutes a lightmap/probe array or clears readiness on a timer.
- Rapid Garage→Main→Garage→Main cancellation settled to the original Race scene with0garage probes. Re-entry reached Garage with no error and ready=true.
- Closing the fixture preserved a separately created unrelated witness scene with its exact64-bit handle, restored Race as active, restored the bootstrap and prior runtime-quality pipeline, and removed the owned garage/probes only. The witness was then explicitly unloaded. Evidence: `workshop-after-rapid-switch.json`, `workshop-native-restore.txt`.
- ForceLOD calls now occur only after the object/group is active. The earlier disabled-group warnings are retained as an actual failed attempt. Later capture logs contained only external MCP duplicate-command warnings, not fixture asset errors.
- The camera fit uses actual posed LOD0 vertices. An independent engine WorldToViewportPoint measurement on77337Apex vertices agrees with the managed fit rectangle to1.192093e-7 normalized units. This measures framing correctness, not concept similarity: `r3-mesh-framing-check.json`.

Actual full1920x1080 captures: `garage-v2-real-workshop-1920.png`, `r3-garage-v5-frontal-1920.png`, `r3-mesh-framed-garage-1920.png`. Earlier1095x496camera captures have a different aspect and must not be treated as16:9 comparisons.

Still open: hero shape/material fidelity, workshop lighting/detail matching, rendered Spark/Apex thumbnails, menu-specific Ash pose, final camera/depth treatment, scene-preexistence rejection and managed-reload lifecycle checks, and actual shipping-player UI/frame/memory verification. The screen still differs visibly from the locked garage-v2 concept. No global fidelity percentage is assigned.

Latest V7 lighting06 capture: r3-v7-focus-1920.png. Optional owned Gaussian depth-of-field keeps the bike and overlay sharp while softening the workshop. Native lifetime control verified effect enabled in Garage, disabled in Main, and zero temporary focus objects/profiles after Close. The camera data and project profiles are restored. Visual differences remain: broad flat fairing, tall round tank, thin tail, weak mechanism highlights, excessive floor normal relief, logo weight/spacing, missing rendered thumbnails. No acceptance is implied.
