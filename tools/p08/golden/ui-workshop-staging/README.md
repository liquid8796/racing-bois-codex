# Baked workshop scope — staged Editor-only candidate

The four C# sources in this directory compile against installed Unity
6000.5.7f1. They have not been copied into Assets or executed in the live
Editor by this subtask. Native scene lifecycle and visual matching remain
unverified; compilation is not visual acceptance.

## Integration boundary

`GoldenUiWorkshopScope` accepts a saved generated Garage scene path, its
actual room-root identity, the live fixture owner, and an explicit list of
fixture Light/ReflectionProbe/Volume components to suspend. It does not
hardcode a recipe hash. Root currently uses recipe03:

`Assets/RacingBois/Golden/Generated/Garage/RB_Golden_Garage_v4_1294deae38a9/GarageReview.unity`

Example caller flow (using real existing references):

```csharp
workshop = new GoldenUiWorkshopScope(settings.WorkshopScenePath,
    settings.WorkshopRoomIdentity, owner, fixtureLighting);
workshop.Changed += RefreshWorkshopStatus;
workshop.SetGarageVisible(true);  // enter asynchronously
// Keep the capture pending until IsReady and ErrorCode is empty.
workshop.SetGarageVisible(false); // restores Main immediately, unloads its scene
workshop.Dispose();              // call before destroying owner / studio lighting
```

Do not hide the entire fixture owner to suspend its lights: it also owns the
actors and camera. The caller still positions its real actors/camera in the
authored room and selects the compatible review pipeline. The scope never
moves room geometry, clones the room, rebakes lighting, replaces a material,
changes scene asset data or uses a concept image as a background.

`State`, `ErrorCode`, `IsReady`, `IsTransitioning`, `OwnedSceneHandle`,
`LoadedSceneSha256`, `RoomRoot`, and the baked-resource counts are diagnostics.
The counts prove resource presence only. They do not prove illumination,
reflection quality, camera composition or fidelity to the locked concept.

## Ownership and cleanup

- Refuses to adopt a matching scene that already existed before entry.
- Owns only the newly returned scene handle plus exact path. SceneHandle is
  serialized as its Unity-provided 64-bit raw identity.
- On its own sceneLoaded callback disables that scene's cameras, listeners,
  review controller, capture runner and pipeline scope before Start. Awake
  and OnEnable have already run; the known pipeline scope's OnDisable
  restores the pipeline it displaced.
- Captures the currently active scene/environment immediately before garage
  activation. Enter/leave verify final active-scene identity rather than
  trusting the setter's return value on an idempotent request.
- Restores only explicitly suspended fixture components. An environment
  restoration error does not prevent an owned-scene unload attempt.
- Cancel during load waits for the load callback, suppresses review controls,
  and unloads the owned scene before gameplay frame updates. Rapid re-entry
  waits for unloading and the probe-data refresh.
- On managed reload, restores environment synchronously and records only the
  owned handle/path for the new domain to finish unloading. Play exit clears
  transient bookkeeping without writing runtime values into an Edit scene.

Unity retains and merges the actual LightmapSettings data. Custom reflection
probes with a baked texture count as baked content, as required by recipe03.
Probe tetrahedralization follows Unity's needsRetetrahedralization signal;
the handler remains subscribed until Play mode ends so late external probe
data can be processed after an unload/reload callback. There is no replacement
of LightmapSettings.lightmaps or LightmapSettings.lightProbes.

Unity documents that [LoadSceneInPlayMode returns the loading scene](https://docs.unity3d.com/ScriptReference/SceneManagement.EditorSceneManager.LoadSceneInPlayMode.html),
and that [probe data may arrive after the scene-loaded event](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/LightProbes-needsRetetrahedralization.html).
The data-ready event carries no scene identity. The native review must confirm
readiness during rapid transitions; simultaneous unrelated scene streaming
is outside this isolated idle-menu fixture.

## Required native review

1. Start in the actual idle Race menu; snapshot active/loaded scenes, original
   pipeline, RenderSettings and fixture light/probe/volume flags.
2. Enter recipe03, wait for IsReady, verify actual lightmap textures/indices,
   reflection texture and probe count, and that no review camera/controller
   renders or consumes input. Capture the real garage composition.
3. Switch Garage to Main to Garage quickly, including cancellation before the
   first load finishes; verify only one owned workshop at a time and no stale
   probe readiness. Repeat after all async callbacks complete.
4. Close during Garage/loading/unloading; test Play exit and a managed reload.
   Ensure the original scene and flags are restored and only the owned
   additive scene is removed. Preserve unrelated additive scenes.
5. Verify a pre-existing copy of the same scene is rejected without unloading
   it. Verify a missing root or baked-resource failure restores Main and
   unloads only the newly owned scene.
6. Confirm scene/pipeline/material/lightmap asset hashes remain unchanged.
   Compare the actual Game-view capture against garage-v2; all mismatches
   remain unaccepted.

Offline compile:

```powershell
dotnet build tools/p08/golden/ui-workshop-staging/preflight.csproj --nologo -v:minimal `
  -p:BaseOutputPath=D:/Project/Unity/racing-bois/_local/golden-workshop-preflight/bin/ `
  -p:BaseIntermediateOutputPath=D:/Project/Unity/racing-bois/_local/golden-workshop-preflight/obj/
```
