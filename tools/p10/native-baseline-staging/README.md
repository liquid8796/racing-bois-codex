# Native baseline throughput and pacing diagnostic

This stage observes the actual Windows x64 Mono/DX11 renderer running the existing
P06 scripted simulation, chase camera, baseline actors, audio and effects. It
does not open P08 content masks, substitute accepted Golden art, enable campaign
routes or claim full-game/user-input/physical-LAN/visual acceptance.

The workload is uncapped Medium at1920x1080: only the new explicit
`BeginNativeDiagnostic()` bridge selects600seconds, targetFrameRate=-1 and
vSyncCount=0. Ordinary benchmark Begin retains its60fps and60–120second behavior.
The diagnostic restores prior timing settings after its last sampled LateUpdate,
and also on failure/disable. Raw rows and binding record both effective controls.
Budgets stay mean>=60FPS, p95<=20ms and peak working set<=2GiB; results are not
rounded upward or relabelled to pass.

`prepare.py` generated a hash-guarded candidate of P06BenchmarkRunner containing
the explicit entry point and read-only measurement/cycle/tick properties. It also
preserves provenance for the existing restoration journal and compile auditor.
Do not rerun that generator after installing the bridge. No live source is
modified until root explicitly invokes the installer with `--apply`.

## Root installation and real run

The shared `NativeBuildProjectSettingsScope`, `NativeBuildDirtyAssetGuard` and
`NativeBuildFontPreservationScope` must first be reviewed/installed from their
explicit current stages: `tools/p08/golden/build-staging`,
`tools/p08/golden/imported-font-guard-staging`, and
`tools/p08/golden/font-scope-staging`, respectively.

```powershell
python tools/p10/native-baseline-staging/install.py
python tools/p10/native-baseline-staging/install.py --apply
```

Root then refreshes Unity through direct Unity MCP and waits for its actual
compilation to finish, checking the Console. Attest the loaded assemblies:

```powershell
dotnet run --project tools/p10/native-baseline-staging/CompileAudit -- . docs/p10/native-baseline/compiled-sources.json
```

Through direct Unity MCP, invoke:

```csharp
RacingBois.Diagnostics.NativeBaseline.Editor.NativeBaselineBuilder.Build(
    "Build/NativeBaseline/NEW-ID", false);
```

`false` selects the standard baseline workload (one scripted rider + six AI +
police); `true` selects its existing16-rider stress fixture. These are entity
counts, not independently accepted bike/rider roster counts. The builder copies
the saved ArtBenchmark/StressBenchmark scene into its own new folder, keeps
RaceBootstrap/UIDocument disabled and detaches their UI assets, and reuses actual baseline prefab
references. It clones the explicit DesktopPipeline asset. Original scenes/assets
are preserved; dirty consumed dependencies fail rather than being silently saved.

The builder binds authored source, metadata, actual scene/pipeline dependencies,
resolved package files, native PE/PDB/loaded assembly identity and baseline prefab
paths. Built-in engine dependencies are identified with the Unity version. The
shared settings helper records original, effective, before, after and restored
bytes; unrelated dirty assets remain guarded. No global SaveAssets is used.
Genuinely unsaved authoring drafts are rejected globally before building. The
font scope journals restoration before temporarily suppressing TextCore's global
cleanup for clean unreferenced fonts, with native before/after verification.
Original font source/meta/memory backups stay under `_local`; only hash/identity
summary receipts enter BuildEvidence. Referenced or dirty fonts fail closed.

After successful/restored build receipt, keep bound sources stable for the run:

```powershell
python tools/p10/native-baseline-staging/run.py --build Build/NativeBaseline/NEW-ID --output docs/p10/native-baseline/RUN-ID
```

This launches one owned graphics-enabled player with explicit `-force-d3d11`,
with neither batchmode nor nographics. The runtime refuses to start measurement
unless it observes actual Direct3D11 and positive current-process Win32 memory
counters from the correctly sized80-byte PROCESS_MEMORY_COUNTERS_EX structure.
It needs approximately10seconds warmup +600seconds measurement and
brief post-window capture/export. The750second watchdog stops only that exact
process handle. Keep the player foreground and avoid simultaneous heavy builds/
bakes for an interpretable result; all samples are retained if contention occurs.
The independent verifier requires at least99% of measured time focused.

## Evidence and limits

Runtime writes every chronological LateUpdate interval to `frames.csv`, including
world tick/cycle, monotonic measured simulation ticks, actor counts, resolution,
quality, timing controls, focus, native CPU/GPU timing timestamp and available
GC counter. Native timing values may lag or repeat; the verifier reports unique
and repeated timestamps. Missing counters remain blank. A fixed million-frame
buffer avoids silent truncation for an uncapped run; its memory overhead and
the underlying workload's finite diagnostic buffer are included in measurements.

The first row is the partial interval from P06 BeginMeasurement in Update to
the same frame's LateUpdate. Therefore raw rows equal workload frames+1. The
last row includes the existing P06 completion/sort/summary cost in Update; it is
not discarded. The wrapper's subsequent camera capture/export is outside the
window. Actual measurement-start/end UTC is retained separately from process
launch/exit timestamps.

Memory is sampled on actual observed frames at least one second apart, with
start/end coverage verified. Working set/private process memory, Unity allocation,
managed heap and graphics-driver allocation are separate; driver allocation is
not dedicated GPU residency. Current-process Win32 counters replace Mono's managed
Process properties, which returned zero during the retained04failure. Failed
Win32 reads retain blanks plus their error codes; zero is not accepted as process
memory availability. All raw GPU counter values remain preserved, including
impossible outliers; anomaly counts are reported separately without filtering
them to manufacture a GPU performance result. Actual URP camera PNGs are captured in warmup and
after measurement, then independently decoded. They prove rendered diagnostic
views, not exact concept fidelity or window/UI/input behavior.

The launcher verifies every player/source byte before and after the run. Effective
ProjectSettings are checked against bound build-evidence copies, since the live
Editor settings are deliberately restored. The raw verifier recomputes quantiles,
FPS, memory and coverage; matching summary booleans alone are insufficient.
World tick resets need a matching observed cycle; measured ticks start at zero
and cannot grow by more than the real six-step Update cap per frame.

`verification.json` may verify a correctly recorded performance failure. Its
`measurementPassed` is distinct from integrity verification, and both P08 and
release acceptance remain false. Source/image/shape checks and fixture tests are
never presented as the actual ten-minute native result.
