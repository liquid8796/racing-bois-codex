# Golden UI stage fixture — staged, not integrated

The four C# files in this directory are an Editor-only candidate for the
existing `RacingBois.Authoring.Editor` assembly. They have **not** been copied
into Assets or executed in the live Unity Editor by this subtask.

Offline compilation against installed Unity **6000.5.7f1** modules and the
project's current script assemblies passes with warnings treated as errors.
This is API/type validation, not a claim that native lifecycle, input isolation,
camera framing or visual matching has been verified.

## Actual context and scope

`RaceBuilder` creates separate `Race Presentation`, `Canyon Run Ribbon` and
`Main Camera` objects and stores them on `RaceBootstrap.Stage`, `Stage.Road`
and `Stage.ViewCamera`. The fixture uses those public references. It never
hardcodes a scene instance ID or searches for a guessed hierarchy name.

`RaceBootstrap.Update` directly calls `Stage.RenderFrame`; merely disabling
the Stage component would therefore not isolate camera/actor updates. The
fixture saves and disables the supplied bootstrap's `enabled` state, the
actual Stage/Road roots' `activeSelf` states, and that camera's `enabled` state.
It leaves original camera transforms/projection, stage fields, content loaders,
render settings, pipeline assets and account/session data unchanged.

Owned prefab clones, a camera, a toolbar and UI callbacks are destroyed or
removed on Close. Original menu label text, presentation states and focus are
restored, including on Play-mode exit and assembly reload. Cleanup steps run
independently so one failure cannot prevent later restoration attempts.

Open requires an initialized, disconnected idle menu: no race, room, settings,
practice overlay, content load, career view or cutscene. Unrelated enabled
Game cameras and a presentation subtree which also owns the app/UI are rejected
instead of being silently disabled. The new owner belongs to the supplied
bootstrap's actual loaded scene.

## Inputs and visible limitations

Default prefab paths refer to the actual Golden Apex V8/R2, Ash V3 and Canyon
V14 candidates. Missing prefabs fail before the live presentation changes;
there is no silent fallback to rejected older versions. Prefab behaviors are
limited to the audited `RiderAnimationSet` and `GoldenSkinBounds` components.
Physics is disabled only on cloned objects.

The main menu uses real Canyon geometry and a real posed Ash/Apex pair. Main
menu labels temporarily display the explicit Canyon/level 1/Apex visual
sample. Practice selectors, content masks and registry entries are untouched.
Original launch/network/utility intents are intercepted while the fixture is
open; its toolbar switches views and closes the fixture.

Garage uses the existing `GaragePrototypeFixture` and its read-only in-memory
transport. `WorkshopPrefab` is null by default: the garage then shows a neutral
empty background and an explicit **THIẾU XƯỞNG 3D** notice. No concept image is
used as a scene background and no workshop is fabricated. Only real rendered
sprites may be supplied through `RenderedBikeThumbnails`; missing captures
remain blank/pending and are reported. Selecting Spark hides Apex and reports
the missing candidate instead of showing the wrong model as Spark.

The main concept's hand-on-bike standing pose is not authored yet; the actual
Ash Idle clip is sampled and this mismatch is reported. All actor/environment
candidates remain visually unaccepted.

## Composition

Both locked references were viewed directly before authoring:

- `main-v2.png`: SHA256 `9b7ad175234636c591846552178f2d25a279434763ce5d0f252af738c6c8e95e`.
- `garage-v2.png`: SHA256 `65b237da2f4a13b554de13d5a70ec2c3aed995e9cba5c95af6601ca7d0201ef5`.

The camera fits measured posed LOD0 geometry into target rectangles measured
in the 1672×941 concepts. It does not frame the oversized animation culling
envelope. An off-centre projection preserves the full-screen UI while placing
the subject on the right. Configuration exposes pose, direction, FOV and target
rectangles for actual capture-based iteration; fitting a bounding rectangle is
not evidence of silhouette, background or material fidelity.

## Integration and native verification for the root task

After reviewing/copying the four `.cs` files into the Editor assembly and
verifying the current compiled source hashes, use the actual idle Race context:

```csharp
GoldenUiStageFixture.OpenMain(); // Resolves exactly one initialized RaceBootstrap.
GoldenUiStageFixture.OpenGarage();
GoldenUiStageFixture.Describe(); // JSON: camera, measured bounds, hashes and failures.
GoldenUiStageFixture.Close();
```

For ambiguous/additive scene contexts, pass the exact `RaceBootstrap` reference
to `OpenMain(context, configuration)`. No new scene or asset is saved.

Before acceptance, inspect actual 16:9 Game-view captures of both modes; test
toolbar/garage close, null-workshop/non-Apex selection, aspect changes, original
menu input blocking, exception rollback, Play exit and assembly reload. Verify
the original stage/road/camera/bootstrap flags, original labels/focus and the
absence of owned fixture objects after close. Account, content mask/registry
and persistent preferences must remain unchanged. Missing workshop/thumbnails,
pose differences and candidate-model differences stay explicit failures.

Build command:

```powershell
dotnet build tools/p08/golden/ui-stage-staging/preflight.csproj --nologo -v:minimal `
  -p:BaseOutputPath=D:/Project/Unity/racing-bois/_local/golden-ui-stage-preflight/bin/ `
  -p:BaseIntermediateOutputPath=D:/Project/Unity/racing-bois/_local/golden-ui-stage-preflight/obj/
```
