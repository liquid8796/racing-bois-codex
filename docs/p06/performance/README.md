# P06 Editor gameplay benchmark

`P06BenchmarkRunner` measures the real shared simulation, the production read-model projection, the same `RaceStageView` and gameplay chase camera, P06 effects, and original audio. This artifact is **Editor measurement**, separate from browser acceptance and the 8-player network tests. It does not include lobby/HUD layout, transports, browser/Wasm overhead or worldwide network conditions, and does not establish 16 online players.

## Scene setup owned by root integration

Copy the current Race scene for standard and stress scenes. Disable `RaceBootstrap` and the UI document, and assign the runner on the application object. Keep the actual Stage, route, prefabs, current lighting/post-processing and gameplay camera. Configure both scenes to the same Medium quality. Disable the obsolete Stage impact system so only `RaceEffectsView` emits impact particles.

Runner fields:

| Field | Configuration |
|---|---|
| `Stage` | The copied scene's `RaceStageView` with a road and chase camera |
| `AudioBank` | Complete `RB_P06_AudioBank.asset` |
| `DustMaterial`, `SparkMaterial`, `SkidMaterial` | The same three P06 materials used in the game |
| `Stress` | False for normal workload; true for maximum actor fixture |
| `AutoStart` / `BuildStageOnStart` | True for a fresh copied scene; avoid pre-building the road twice |
| `EnableAudio` | True to measure the complete mix; Editor auto-unlocks, player/browser needs a real activation |
| `VisualQuality` / `QualityIndex` | Scene quality controller; index 1 applies Medium before warmup and records actual URP render scale |
| `ReducedMotion` / `LowQuality` | Reduced motion false; LowQuality is derived from QualityIndex for effects |
| `WarmupSeconds` | Default 8; clamped to 5-30 |
| `SampleSeconds` | Default 60; clamped to 60-120, so a short smoke cannot produce a 60-second receipt |
| `Seed` | Default 6061996; stored in receipt |
| `RuntimeSourceRevision` | Root-supplied commit plus source-manifest identity for this exact run |
| `OutputPath` | Project-relative path, default `docs/p06/performance/editor-{profile}-{run}.json` |

Start Play Mode once the fields and Game View resolution are correct. `AutoStart` invokes `Begin()`. Alternatively set `AutoStart=false` before Play Mode and call `Begin()` once. Read `Running`, `Progress`, `Completed`, `CurrentTick`, `LastReceiptJson`, `LastReceiptPath`, and `Error` to track the run. Do not resize Game View or issue scene/build mutations during sampling. Use a new Play Mode lifecycle for each profile and after an interrupted run.

## Workloads

Standard creates one scripted player, six native AI opponents and a native police rider: eight riders. Traffic and pedestrians use ordinary core spawn behavior. Tick-based integer input steers through actual route curvature, weaves within a bounded central corridor, controls speed, and attacks. The simulation - not presentation - resolves contact, damage, knockdowns, jumps and gear changes.

Stress creates eight scripted players, seven AI opponents and police: **sixteen simulated riders**, with twelve traffic and six pedestrian slots maintained around the camera route. The extra seventh AI is an explicit authoring fixture beyond `CreateDefault`'s six-bot lobby configuration. Real `RaceSimulation.Step` still executes movement, AI, collision and combat. Out-of-range/terminal fixture riders and out-of-range traffic/pedestrians are recycled; those operations and their actual allocation/render effects are included. The receipt counts fixture recycles. This is a maximum-actor rendering/simulation load test, not ordinary lobby or network behavior.

Both workloads restart their benchmark world after the local rider remains terminal for two seconds or approaches the route end. Subsequent worlds begin at successive route sections. Restarts keep the camera workload moving and are counted; world ticks may reset, so use `measuredSimulationTicks`, rather than subtracting the final tick from the first. The workload uses a fixed 60 Hz accumulator with at most six catch-up steps per frame. Excess time is recorded as dropped simulation ticks; a stalled Editor cannot silently receive full simulation-coverage credit.

The `BenchmarkReadModelProjection` facade delegates to the same internal production mapper. It does not expose mutable world objects to views. Projection runs at 20 Hz and the local rider is projected at render cadence, matching the existing local presentation path. Event retention is bounded to 128 events/two seconds.

## Receipt semantics

A receipt is written **only after the full requested sample duration completes with actual frame samples**. Stopping Play Mode, disabling the runner or otherwise interrupting the run writes no successful-looking partial file. File writing is Editor-only, must remain inside the project, and uses `CreateNew` so previous evidence is not overwritten. In a Player, completion is available through `LastReceiptJson`, without a file-write claim. No run has been performed merely by adding this runner.

The receipt contains actual frame p50/p95/max, mean FPS, total measured duration/frame count, simulation tick coverage/drops, measured attack/hit/crash counts, actual rider/traffic/pedestrian min/mean/max, and independent flags for required workload density and measurement coverage. `measurementCoverageValid` requires at least 60 seconds, 600 frames, 95% simulated time coverage, no sample-buffer overflow, and stable camera dimensions. It is not a visual-quality or gameplay acceptance flag. `frameP95WithinBudget` is a direct comparison with the 16.667 ms target; no tolerance is silently added. There is no unconditional `passed` field.

GC allocation, draw calls, batches, SetPass calls, triangles, vertices, Unity allocation totals, managed memory, FrameTiming CPU/GPU and benchmark update CPU cost are reported with `available`, `samples`, minimum/mean/maximum. Unavailable values are `-1`, with `available=false`. A missing allocation counter therefore never becomes a zero-allocation claim. GC collection deltas are included separately. These counters can include Editor and Scene View work; the receipt names that scope. Missing GPU timing is retained as unavailable instead of inferred from CPU.

Scene inventory records actual Stage/road mesh-renderer counts, unique shared meshes and their vertex totals, legacy Stage particle systems/currently playing legacy systems, P06 particle/trail pool counts, particle hard cap and audio source count. Inventory totals include LOD components and are **not** GPU-drawn triangle counts; use the available render counters for submitted geometry. Hardware, Unity/product versions, actual camera resolution, quality/vSync/target frame rate, motion/audio settings and source binding are recorded.

## Interpretation

Compare standard and stress only with matching source, settings, Game View resolution and machine conditions. Keep the original receipts, including failures, unavailable counters, frame outliers and simulation drops. A 60-second Editor p95 under budget is useful evidence for the slice but cannot replace the Release Web build's 1080p performance, browser memory/loading/audio, Internet multiplayer, or human visual/usability acceptance.
