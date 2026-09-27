# Native baseline diagnostics — current result

The Windows x64 Mono/DX11 build and ten-minute run `20260928-baseline05` completed
with verified source/player bytes and working Win32 memory instrumentation.
**Foreground performance acceptance failed:** the player was focused for
108.924 of600.154seconds (18.15%), below the declared99% requirement.
`VERIFIED_BASELINE` means the recorded evidence is internally verified;
`measurementPassed=false`, `p08Accepted=false` and `releaseAccepted=false` remain
the recorded results.

This is the existing P06 standard benchmark: one scripted rider, six AI and a
police rider on the baseline Canyon route, with its real camera, actors, audio
and effects. It is uncapped Medium1920x1080 (`targetFrameRate=-1`, `vSyncCount=0`).
It excludes normal game UI/network/input/campaign flow and accepted P08 content.
Entity counts do not establish eight independently accepted character assets.
The measured rate is Unity-loop throughput, not physical display refresh.

| Native05 observation | Recorded result |
| --- | --- |
| Platform | Windows11, NVIDIA GeForce RTX3070 Laptop GPU, actual Direct3D11 |
| Observation | 562,640 chronological raw frames over600.154seconds |
| Unity-loop timing | 937.49FPS mean; p50 0.9799ms; p95 1.7294ms; maximum154.3898ms |
| Simulation | 36,000 fixed ticks, zero dropped ticks, ten workload restarts |
| Focus | 18.15% of measured time; foreground gate failed |
| Process memory | 600 positive native samples; maximum sampled working set447.63MiB; private committed bytes834.13MiB |
| Native timing | 562,640 distinct timestamps; 475,849 available GPU timing samples; maximum22.32832ms; no value exceeded the entire observation window |
| Runtime diagnostics | Zero warnings/errors; owned process exited0 and stopped |

Process memory is sampled once per second; those maxima are observed sample
maxima, not continuous memory high-water measurements. Private committed bytes
are separate from resident working set. Dedicated GPU residency remains
unmeasured. Draw-call, batch, GC and graphics-driver allocation counters were
unavailable. Set-pass, triangle and vertex counters produced562,639 samples
(means35.1 passes,267,055 triangles and326,019 vertices); their minima include
zero. Together with the distinct native timing samples and actual camera PNGs,
these support sustained rendering activity without proving a displayed frame
for every loop iteration.

The first raw row is a partial BeginMeasurement-to-LateUpdate interval. The last
row includes the existing workload's completion/sort/summary cost. Both remain
in the data. The background-dominant window is retained in full; it has not been
trimmed or relabelled as a foreground result.

## Evidence

- [Original launch and source/player checks](20260928-baseline05/launch.json)
- [Raw-derived verification](20260928-baseline05/verification.json)
- [Original native receipt](20260928-baseline05/runtime/receipt.json),
  [frames](20260928-baseline05/runtime/frames.csv),
  [memory](20260928-baseline05/runtime/memory.csv),
  [workload/render counters](20260928-baseline05/runtime/workload.json)
- [Separate independent review](diagnosis-baseline05/REVIEW.md) and
  [stdlib recomputation](diagnosis-baseline05/independent-review.json)
- [Exact build receipt copy](20260928-baseline05/build-evidence/NativeBaseline.build.json),
  [binding](20260928-baseline05/build-evidence/NativeBaseline.binding.json),
  [font-preservation summary](20260928-baseline05/build-evidence/font-preservation.json),
  [copy manifest](20260928-baseline05/build-evidence/copy-manifest.json)

The build-copy SHA256 is
`514713296f26cfe55535f60a6b2bf4c91916d402bc70bd00d1c523400f1ec65a`.
Its original paths remain unchanged inside the copied receipt. Binaries stay in
ignored `Build/NativeBaseline/20260928-baseline05`; tracked receipt copies keep
their actual build evidence available without publishing player binaries or
private font backups.

## Preserved failures and repairs

| Attempt | Result and disposition |
| --- | --- |
| baseline01 | Stopped before BuildPlayer on preexisting imported shader dirty state. The unrelated-asset guard also detected a cleared dirty flag; settings bytes were restored. Narrow native controls subsequently distinguished imported caches from authored drafts. |
| baseline02 | Build failed with five UIDocument live-reload errors after the component was destroyed. Unity's global font cleanup also changed the two SDF files. The owned scene now retains disabled documents with detached UI assets; its dependency closure follows only actual build roots. |
| baseline03 | Native compilation succeeded but the post-build guard failed: Unity auto-saved the owned dirty material witness and changed font atlas state. Future unsaved authoring drafts are rejected before building. |
| baseline04 | Ten-minute run used unexpected Direct3D12 and managed Process memory returned zeros. The original launch FAIL is preserved. [Independent review](diagnosis-baseline04/independent-review.json) also retains two impossible GPU durations. |
| baseline05 | Build, restoration, actualDX11 and native memory checks succeeded. The full recorded window failed foreground coverage; no performance/release acceptance was granted. |

The initial user font changes were recovered byte for byte from a Codex Git
snapshot and remain excluded from commits. [Recovery and native protection](FONT_PRESERVATION.md)
records the investigation. The later baseline05 build verifies the integrated
font-preservation scope: original source/meta/owner/material/atlas pixels and
clear flags survived unchanged. Raw backups remain under `_local`; only summary
hashes are copied into build evidence. Native helper tests reject referenced
dynamic fonts and dirty owners. Windows graphics API setup now selects the
explicit API list before disabling automatic selection, with native readback.

## Current commands

Root operates Unity through direct Unity MCP. After source changes, refresh
Unity, finish compilation and attest the current nine assemblies:

```powershell
dotnet run --project tools/p10/native-baseline-staging/CompileAudit -- . docs/p10/native-baseline/compiled-sources.json
```

Create a new native build through Unity:

```csharp
RacingBois.Diagnostics.NativeBaseline.Editor.NativeBaselineBuilder.Build(
    "Build/NativeBaseline/NEW-BUILD", false);
```

Then launch into a fresh evidence directory:

```powershell
python tools/p10/native-baseline-staging/run.py --build Build/NativeBaseline/NEW-BUILD --output docs/p10/native-baseline/NEW-RUN
```

An unchanged audited build may be reused for a new run; existing evidence is
never overwritten. Keep the player focused throughout the ten-minute window and
avoid simultaneous heavy workloads. The launcher forcesDX11; startup rejects
the wrong API or unavailable/zero native process counters before measurement.
The source/player/font hashes are checked before and after execution.

For a separate verification receipt, retaining the original run:

```powershell
python tools/p10/native-baseline-staging/verify.py --build Build/NativeBaseline/NEW-BUILD --run docs/p10/native-baseline/NEW-RUN/runtime --receipt docs/p10/native-baseline/NEW-RUN/review-NEW.json
```

The [staging guide](../../../tools/p10/native-baseline-staging/README.md) describes
installation and measurement details. P08 visuals/content, a full native game
run, real input/hardware coverage, physical offline LAN and geographic clients
remain separate required gates.
