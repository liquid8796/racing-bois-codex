# Isolated native pose-envelope comparison — staged only

This harness does not install a duplicate Client DLL, change the live game
bootstrap, connect to any server, load player profiles or alter the ongoing
source-frozen soak. Only its isolated diagnostic assembly/scene is new. Root
owns installation, Unity MCP operations and the real player run.

Three frozen candidate classes are copied into
`RacingBois.Diagnostics.PoseEnvelopePreview` by one literal namespace change.
`prepared-inputs.json` binds original and transformed bytes. The40m/s path uses
the copied Unity wrapper and pure envelope. A separate explicitly named20m/s
comparison fork changes translation speed40→20, maximum duration.375→.75s and
burst lifetime.6→1.2s; spatial bound10m and angular policy16rad/s stay unchanged.
The original candidate remains frozen. Neither version is accepted by this tool.

Four source-bound f WAN pairs are selected deterministically: indices0 (largest
Riding→Falling),2 (reverse),11 (same-Falling bike step),1 (forecast Wrecked).
The last case keeps its recorded rendered **Falling** mode and authoritative
Riding metadata; it does not invent an authoritative or rendered wreck.

The root-selected assets are ApexR4 and AshV6 generated prefabs. There is no
fallback if AshV6 has not yet been imported. Actual `RiderAnimationView` consumes
the prefab's authored `RiderAnimationSet` clips. All physical colliders are
disabled on diagnostic instances. LOD0 is forced for a consistent comparison,
so this is not a gameplay performance benchmark or production content build.

## Reconstruction and capture

The scene uses actual Unity Vector3/Quaternion projection and envelope evaluation,
a source-bound TrackDefinition ribbon, a follow camera and colored reference
markers. Ground/obstacle/contact markers are **diagnostic primitives**, not new
production assets, and are not evidence of a recorded collision. They are not
counted toward P08 content parity.

The displayed-pose trace lacks every render frame, camera history and some bike
height/lean/attack values. Center checkpoint values fill the explicitly listed
missing fields. Before pose is held for warm-up; after the recorded correction,
captured speeds/height/lean are held and mode age advances. It does not simulate
the rest of the match or claim full WAN replay. Wheel spin, actual contact events,
sound and gameplay VFX are not reconstructed.

Each case runs sequentially as unfiltered,40m/s and optionally20m/s, on the same
real prefabs. The latter two use separate rider/bike envelopes and camera rebase.
“Unfiltered target” means input to the new visual envelope after the historical
Application presentation, not the server's authoritative position.

The player targets60Hz, records actual frame/timestamps, missed slots, unfiltered
and shown poses, camera, display errors, remaining duration and reset reasons.
It never backfills invented frame observations. It saves explicit URP engine
camera PNGs at before/correction/common.15s/common.8s, using asynchronous GPU
readback. Encoding is deferred until motion trials finish to reduce capture
stalls. Actual timing deviations remain in the report; no FPS or comfort success
is inferred from capture completion. Graphics API/device and UV orientation are
recorded; root must inspect actual images, including orientation and actor visibility.

The runtime has a100s limit. The optional root-invoked Editor launcher uses the
exact owned Process handle, a hidden window and a130s watchdog. It never searches
or kills processes by name. Avoid Editor domain reload while that watchdog is
active. The runtime's own limit remains independent; a separate external owner
would be needed to supervise an Editor shutdown plus a GPU hang.

## Root execution order

1. Review `prepared-inputs.json` and the source. Run
   `python tools/p10/pose-envelope-native-staging/verify_staging.py`.
2. Root invokes `install.py --apply`; it refuses different existing files and
   copies only Runtime/Editor/Data into the new Diagnostics folder. Refresh via
   direct Unity MCP, wait for compilation/domain reload, inspect Console.
3. Once the actual ApexR4/AshV6 prefabs exist, run `freeze_selection.py` with a
   fresh `--output docs/p10/pose-envelope-native-staging/selection-<id>.json`.
   This binds descriptors, prefabs, maps, source clips, fixture and algorithms.
4. Attest actual loaded-source candidates after Unity compilation:

   ```powershell
   dotnet run --project tools/p10/pose-envelope-native-staging/CompileAudit -- . docs/p10/pose-envelope-native-staging/compiled-sources.json
   ```

5. Through direct Unity MCP call
   `RacingBois.Diagnostics.PoseEnvelopePreview.Editor.PosePreviewBuilder.Build(selectionPath, "Build/PoseEnvelopePreview/<fresh-id>")`.
   The builder verifies PE/PDB/source identity, source/meta/dependency hashes and
   ordinary virtual package paths. It creates only an owned additive scene and
   diagnostic materials. It never globally calls SaveAssets or replaces game
   build-scene settings. A reverse restoration journal restores only its own
   settings and closes only its own scene, including partial-failure paths.
   The three project-settings files are bound after the diagnostic overrides.
   Persistent native settings cannot be written with the untracked serializer:
   the builder serializes owned transient copies to `BuildEvidence/effective`,
   verifies full JSON identity and nonempty output, then copies those exact bytes
   to the scoped settings files before taking the source snapshot. It checks
   both full in-memory settings and disk hashes after the build. Restoration
   attempts every original memory state, disk image and dirty flag independently.
6. Through direct Unity MCP call
   `PosePreviewLaunch.Start(buildDirectory, "docs/p10/pose-envelope-native-staging/captures-<fresh-id>", true)`.
   The launcher verifies all build files before/after execution and returns
   immediately with an owned PID/receipt. No OS input/window automation is used.
   Alternatively root's own supervised launcher can use the opt-in arguments:
   `--rb-pose-preview --rb-pose-output <absolute-new-folder> --rb-pose-fingerprint <build-hash> --rb-pose-include20`.
7. Verify actual bytes and chronology, then inspect the actual camera PNGs:

   ```powershell
   python tools/p10/pose-envelope-native-staging/verify_run.py --build-root Build/PoseEnvelopePreview/<id> --output docs/p10/pose-envelope-native-staging/captures-<id> --receipt docs/p10/pose-envelope-native-staging/native-check-<id>.json
   ```

The verifier checks the real x64 build receipt/player files, bound fixture,
complete32/48 image matrix, hashes, independently decoded PNG pixels/CRC,
finite values and unique chronological frame observations. It separately flags
capture timing gaps; successful byte verification does not accept images or
hide raw prediction uncertainty. Native runs/images do not exist merely because
the staged compiler or synthetic fixture controls pass.
The independent verifier also recomputes the source fingerprint, requires exact
before/after source snapshots and no recorded memory mutations, and matches all
three effective/before/after settings copies to their source hashes. It does not
trust `sourceBindingPassed` alone.
