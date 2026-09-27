# NativeProbe and PosePreview preservation integration — staged only

**Follow-up:** after the performance freeze ended, both managed builds passed with zero warnings/errors. Independent review found missing NativeProbe effective-settings/dependency binding and a shared URP profile risk. This initial stage was not installed; use the separate `tools/p10/diagnostic-preservation-v2-staging` candidate for the completed repair. The frozen handoff below remains its original pre-compilation snapshot.

Prepared outside `Assets` during the native baseline05 measurement window. **No compilation, tests, installation, Unity call or player run has been performed for this stage.** Existing stages, receipts, source scenes and live source bytes remain unchanged.

Both builders add the existing global dirty-authoring preflight and proven `NativeBuildFontPreservationScope`. They pass the generated diagnostic scene's exact dependencies (and PosePreview's owned pipeline) to the scope. A referenced dynamic font is rejected by that scope; clean unreferenced project TextCore fonts are backed up privately and protected from the global prebuild cleanup. The original project fonts are never cloned, regenerated or saved. Private backup bytes stay under `_local/p10/<diagnostic>/<attempt-id>/font-preservation`; only the preservation summary enters build evidence and the output file manifest.

Rollback order is deliberate: the existing settings/scene callbacks run first, then exact project settings restoration, then font restoration, then the original dirty-asset postcheck. The preflight is repeated immediately before `BuildPlayer`, and protected font identity is checked immediately before and after it. Constructor/partial-apply failures retain journaled restoration. Source binding, existing scene construction, output paths, runtime workload, protocol and build options retain their behavior.

NativeProbe includes the earlier staged full serialized-settings repair. Its new optional `compileProofPath` adds PE/PDB/MVID/source attestation before any mutations and after the build. PosePreview extends its existing attestation with the executing `RacingBois.Authoring.Editor` assembly. Both source inventories bind all consumed shared helper files/metas, the Authoring Editor asmdef, proof file and required assembly DLL/PDB bytes. Both Editor asmdefs reference Authoring.Editor; no reverse dependency is introduced.

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

Only after the timed run and after-source checks finish, root can review/compile this stage, install exact reviewed files without replacing existing metadata, refresh Unity compilation, and generate **new** proofs:

```powershell
dotnet build tools/p10/diagnostic-preservation-staging/Preflight.csproj -c Release
dotnet run --project tools/p10/diagnostic-preservation-staging/CompileAudit/CompileAudit.csproj -c Release -- native-probe . docs/p10/diagnostic-preservation/native-probe-compiled-sources.json
dotnet run --project tools/p10/diagnostic-preservation-staging/CompileAudit/CompileAudit.csproj -c Release -- pose-preview . docs/p10/diagnostic-preservation/pose-preview-compiled-sources.json
```

The two proof paths above are the staged builders' defaults. For later attempts, choose fresh filenames and pass them explicitly. Native preservation and build validation are still pending. No historical PASS or frozen receipt is rewritten by this stage.
