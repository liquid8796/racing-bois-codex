# NativeProbe and PosePreview preservation integration — reviewed v2 candidate

Prepared outside `Assets`, then refined after baseline05 finished. The diagnostic and compile-audit managed builds both pass with **zero warnings/errors**. No live installation, Unity call or player run has been performed for this stage. Earlier stages, receipts, source scenes and live source bytes remain unchanged.

Both builders add the existing global dirty-authoring preflight and proven `NativeBuildFontPreservationScope`. They pass the generated diagnostic scene's exact dependencies (and PosePreview's owned pipeline) to the scope. A referenced dynamic font is rejected by that scope; clean unreferenced project TextCore fonts are backed up privately and protected from the global prebuild cleanup. The original project fonts are never cloned, regenerated or saved. Private backup bytes stay under `_local/p10/<diagnostic>/<attempt-id>/font-preservation`; only the preservation summary enters build evidence and the output file manifest.

Rollback order is deliberate: the existing settings/scene callbacks run first, then exact project settings restoration, then font restoration, then the original dirty-asset postcheck. The preflight is repeated immediately before `BuildPlayer`, and protected font identity is checked immediately before and after it. Constructor/partial-apply failures retain journaled restoration. Source binding, existing scene construction, output paths, runtime workload, protocol and build options retain their behavior.

NativeProbe includes the earlier staged full serialized-settings repair. It also clones the current selected project URP profile into an owned resource folder, assigns that clone at every quality level and prepares shader features only against that owned profile. Its source manifest now binds the actual scene/pipeline dependencies, package metadata/locks, script metadata, original profile bytes and effective ProjectSettings. Before/effective/after/restored setting files are preserved as build evidence; both serialized-memory drift and file drift fail the build. Output must be a new directory with no reparse-point parents.

Its new optional `compileProofPath` adds PE/PDB/MVID/source attestation before any mutations and after the build. PosePreview extends its existing attestation with the executing `RacingBois.Authoring.Editor` assembly. Both source inventories bind all consumed shared helper files/metas, the Authoring Editor asmdef, proof file and required assembly DLL/PDB bytes. Both Editor asmdefs reference Authoring.Editor; no reverse dependency is introduced.

Files prepared for later installation:

| Staged file | Target under `Assets/RacingBois/Diagnostics` |
|---|---|
| `NativeProbe/NativeProbeBuilder.cs` | `NativeProbe/Editor/NativeProbeBuilder.cs` |
| `NativeProbe/NativeProbeCompiledSources.cs` | `NativeProbe/Editor/NativeProbeCompiledSources.cs` (new) |
| `NativeProbe/RacingBois.Diagnostics.NativeProbe.Editor.asmdef` | Same name under `NativeProbe/Editor` |
| `PosePreview/PosePreviewBuilder.cs` | `PoseEnvelopePreview/Editor/PosePreviewBuilder.cs` |
| `PosePreview/PreviewBuildInputs.cs` | `PoseEnvelopePreview/Editor/PreviewBuildInputs.cs` |
| `PosePreview/RacingBois.Diagnostics.PoseEnvelopePreview.Editor.asmdef` | Same name under `PoseEnvelopePreview/Editor` |

The new `CompileAudit` source supports separate `native-probe` and `pose-preview` modes, includes the required Authoring.Editor proof and refuses an existing proof destination. It preserves the earlier compile-audit programs and receipts.

After independent review clears this candidate, root can verify/install its exact files without replacing existing metadata, refresh Unity compilation, and generate **new** proofs. `install.py` defaults to verification and requires an exact-handoff validation receipt before `--install`:

```powershell
dotnet build tools/p10/diagnostic-preservation-v2-staging/Preflight.csproj -c Release
python tools/p10/diagnostic-preservation-v2-staging/install.py
python tools/p10/diagnostic-preservation-v2-staging/install.py --install
dotnet run --project tools/p10/diagnostic-preservation-v2-staging/CompileAudit/CompileAudit.csproj -c Release -- native-probe . docs/p10/diagnostic-preservation/native-probe-compiled-sources.json
dotnet run --project tools/p10/diagnostic-preservation-v2-staging/CompileAudit/CompileAudit.csproj -c Release -- pose-preview . docs/p10/diagnostic-preservation/pose-preview-compiled-sources.json
```

The two proof paths above are the staged builders' defaults. For later attempts, choose fresh filenames and pass them explicitly. Native preservation and build validation are still pending. The initial stage remains at `tools/p10/diagnostic-preservation-staging` for review history; its NativeProbe source/configuration gap is superseded by this v2 candidate. No historical PASS or frozen receipt is rewritten by this stage.
