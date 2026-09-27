# NativeProbe exact project-settings restoration

The current NativeProbe setter rollback preserves the public API getter result, but that is insufficient while Windows automatic graphics selection is enabled: `GetGraphicsAPIs` can return the platform default list instead of the hidden serialized explicit list. Restoring that getter result can change `m_APIs` without changing the final getter result. The earlier claim of complete restoration from API readback was therefore too broad.

This staged repair reuses the existing `NativeBuildProjectSettingsScope`. It captures original Player/Graphics/Quality settings memory JSON, disk bytes and dirty flags before any probe settings mutation. Its restore is registered first, so the rollback journal invokes it **last**, after existing settings/scene callbacks. Exact original-state verification inside the shared scope contributes to the existing `editorStateRestored` result; a mismatch fails restoration. The graphics setter/readback fix stays intact.

Only the NativeProbe builder and its Editor assembly reference change. The consumed shared helper source and metadata are added to the probe source manifest. `RacingBois.Authoring.Editor` does not reference NativeProbe.Editor, so the added Editor-only reference creates no direct assembly cycle. Historical probes/stages/receipts are preserved. This fix addresses project settings; it does not claim that historical builds preserved every unrelated asset or that the modified builder has passed a native run.

Managed compile command:

```powershell
dotnet build tools/p10/native-probe-settings-staging/Preflight.csproj -c Release
```

Root must install the staged builder/asmdef when appropriate, preserve their existing metadata, refresh compilation and run the native automatic=true/hidden-explicit-list restoration control. No Unity invocation, settings mutation or player run occurs while staging/compiling this patch.
