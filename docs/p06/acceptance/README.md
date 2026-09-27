# P06 Editor acceptance harness

`Assets/RacingBois/Editor/P06AcceptanceHarness.cs` contains explicit Unity Editor operations for the P06 integration owner. Adding/importing the file does **not** run a test or create a passing receipt. The harness does not start Play Mode, build the player, operate Blender, change simulation code, or alter the original club source. Run it through Unity MCP after compilation and inspection of Editor state and console.

Use an actual runtime/source-manifest identity for `SOURCE_REVISION` in the snippets below. The helper additionally hashes the current scene dependency files, its own source, the view, weapon view and projection adapter. A revision label alone is not proof that a build came from those bytes.

## Create dedicated scenes

Stop Play Mode and explicitly save the configured Race scene first. Scene creation refuses any dirty loaded scene and refuses to overwrite an existing destination unless it contains the harness's ownership marker. It creates `Assets/RacingBois/Scenes/ArtBenchmark.unity` and `StressBenchmark.unity` as saved copies of Race, then returns to Race. The saved Race bytes must remain unchanged. Other unrelated open scenes are not preserved as an Editor layout; all must be saved before invoking this operation.

Unity MCP `execute_code`:

```csharp
return RacingBois.Authoring.Editor.P06AcceptanceHarness.CreateBenchmarkScenes("SOURCE_REVISION");
```

The copies retain the production route, prefabs, camera, lights, post-process volume and quality controller. `RaceBootstrap` and every copied `UIDocument` are disabled. The actual `P06BenchmarkRunner` receives the same Stage, audio bank and effects materials as gameplay. It builds the stage at runtime, uses the external P06 effects, and does not enable the obsolete Stage impact emitters. Each scene has a harmless root marker named `P06_ACCEPTANCE_GENERATED_BENCHMARK_V1`.

The copies assign the existing `RaceVisualQuality` to the runner and set `QualityIndex=1` (Medium). `P06BenchmarkRunner.Begin()` applies this tier to the runtime pipeline clone and the road's scenery settings before building the workload or starting warmup. It verifies and records the actual tier/render scale; a changed tier, pipeline or scale during sampling invalidates measurement coverage. It never changes a saved pipeline asset, and there is no Editor lifecycle callback. `QualityIndex=0/1/2` selects Low/Medium/High and determines the effects' `LowQuality` value. No saved player preference changes benchmark quality.

## Validate imported references

With Race active and Play Mode stopped:

```csharp
return RacingBois.Authoring.Editor.P06AcceptanceHarness.ValidateSceneReferences("SOURCE_REVISION");
```

Assertions cover Stage/road/camera references, all 17 nonempty audio-bank clips, the exact twelve nonempty rider actions, the eight actor prefab references, missing scripts in those prefabs, usable Editor material/shader references and consistent skin/bone/bindpose references. A successful invocation writes a uniquely named `scene-references-*.json` here. This is a reference check; it is not pixel review, web shader validation, topology/UV validation, frame-rate proof or complete animation acceptance. The dedicated Blender/Unity asset receipts retain those scopes.

## Run a real pool functional smoke

Open StressBenchmark in Edit Mode and disable benchmark autostart for this Play lifecycle:

```csharp
UnityEditor.SceneManagement.EditorSceneManager.OpenScene(RacingBois.Authoring.Editor.P06AcceptanceHarness.StressScene);
var runner = UnityEngine.Object.FindAnyObjectByType<RacingBois.Client.Bootstrap.P06BenchmarkRunner>();
runner.AutoStart = false;
return "Pool smoke configured; enter Play Mode next. Do not save this temporary AutoStart override.";
```

Enter Play Mode through MCP. Wait for the Editor to report ready, then invoke:

```csharp
return RacingBois.Authoring.Editor.P06AcceptanceHarness.PlayModePoolSmoke("SOURCE_REVISION");
```

The method requires an untouched Stage and a stopped/uncompleted benchmark runner. It applies the configured Medium quality explicitly inside the Play Mode smoke, then fills all **16 rider, 12 traffic and 6 pedestrian** view slots from a deterministic authoring `GameplayWorld` fixture through `BenchmarkReadModelProjection`, the same production projection facade. Only immutable read models reach Stage. It uses 24 identity generations with unchanged actor-kind distribution, checks active counts and fixed pool sizes, retires all views to the menu and reacquires them, and verifies that creation stabilizes after the initial 34 pool entries while real reuse increases. The menu display rider is separate from those 34 entries.

Every rider exercises a visible club attack with the left hand, authoritative Fist equipment hiding the club, then retirement/reacquisition with a Club resetting to the right hand. The check reads the weapon view's private hand field via reflection solely for this Editor assertion; it does not set it. The helper also checks finite view transforms and rejects warning/error/assert/exception logs emitted during its synchronous invocation.

Only after all assertions complete does it write a unique `pool-smoke-*.json` here. Exceptions leave no success receipt. This is an **actual Play Mode functional test of object reuse**, not a real-time gameplay/network simulation test, memory-leak soak, full-console-history check or FPS benchmark. Its mutable world fixture deliberately changes IDs/equipment and does not execute `RaceSimulation.Step`; core gameplay remains unchanged. Use separate regression programs for simulation behavior and the measured benchmark for sustained rendering cost.

Stop Play Mode after the smoke. Reopen the saved benchmark scene and discard the temporary AutoStart override before running a benchmark; do not reuse the smoke's filled pools for a cold-start performance measurement.

## Run sustained benchmarks

For each of ArtBenchmark and StressBenchmark, use a new Play lifecycle from the saved scene with `AutoStart=true`, fixed Game View resolution, Medium, audio on, and a bound `RuntimeSourceRevision`. The runner performs 8 seconds warmup and at least 60 seconds sampling and writes its own unique receipt under `docs/p06/performance`. Read `Running`, `Progress`, `Completed`, `Error` and `LastReceiptPath` through MCP. Do not resize or mutate the scene while measuring.

See [benchmark semantics](../performance/README.md) for actual frame counters, workload coverage, dropped ticks and the distinction between Editor/global counters and browser performance. Complete Release Web/browser, original asset, native regression and local multiplayer checks separately. No passing receipt here closes the P05 physical-LAN, real Internet or remote-contact presentation limitations.

## Evidence policy

Receipt files use `FileMode.CreateNew`; previous evidence is not overwritten. Source/build drift invalidates conclusions about another build, not the historical measurement itself. Preserve failures and unavailable counters and record any later successful rerun separately. Console messages outside the invocation must be checked through MCP independently. The helper must actually execute before a result is described as passed.
