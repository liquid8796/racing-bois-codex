# Scoped Golden native build repair

This is a staged source patch. It has not run Unity or built a player. The managed
preflight compiles the candidates against the installed Unity 6000.5.7f1 libraries
with zero warnings/errors. Root owns installation and actual native validation.

The old `GoldenSampleBuilder.Build` called `AssetDatabase.SaveAssets` before and
after building. That could persist unrelated dirty assets, including the fonts
being deliberately preserved outside the current patches. It also captured
settings from disk without explicitly persisting the effective native settings,
restored only selected fields, and wrote a success receipt before restoration.

The candidate uses the previously native-verified ProjectSettings clone/serialize
mechanism from `PreviewProjectSettingsScope`, exposed once as the public
`RacingBois.Authoring.Editor.NativeBuildProjectSettingsScope`. The baseline builder
can reference the same helper through the Authoring.Editor assembly rather than
carry a separate implementation. Its API is constructor,
`UsePipelineAtEveryQuality`, `PersistOriginalSettings`, `PersistEffectiveSettings`,
`ChangedDuringBuild`, and `Restore`.

`NativeBuildDirtyAssetGuard` independently snapshots the serialized memory,
saved-file/meta hashes and dirty flags of pre-existing dirty persistent Assets or
Packages objects. It rejects dirty build dependencies and verifies those original
objects after the operation. It never saves, clears, reimports or overwrites user
assets. A detected concurrent/unrelated change fails the receipt rather than being
silently overwritten. This observation is limited to dirty persistent objects
loaded at guard construction; it is not a claim about all external filesystem
activity.

The rewritten Golden builder requires a fresh output directory, uses an owned
pipeline/renderer clone, explicitly persists effective settings, binds complete
resolved package dependencies and captures before/after source snapshots. It
preserves original/effective/before/after/restored settings in `BuildEvidence` and
returns PASS only after successful native build, exact source binding, restoration
and dirty-asset preservation. Failed attempts replace the latest status while
retaining their own attempt receipt. Existing outputs are never overwritten.

Focused scene-authoring changes remove the other global saves on the same review
workflow: studio floor, environment sky, review pipeline, garage emissive copies
and owned bake outputs are saved by explicit object ownership. The original model
sources, concepts, prefab identities and production availability masks are not
changed by this source patch.

```powershell
dotnet build tools/p08/golden/build-staging/Preflight.csproj --nologo -v:minimal
python tools/p08/golden/build-staging/handoff.py
```

`handoff.json` freezes the seven candidate files and expected live source/meta
hashes. When root's active Unity review is complete, install with:

```powershell
python tools/p08/golden/build-staging/handoff.py --install
```

The installer checks every file before any copy, refuses independent live edits,
preserves existing script GUIDs and is idempotent for identical installed bytes.
It does not invoke Unity, accept models, change masks or save project assets.

After installation root must let Unity finish compiling, refresh the compiled
source proof and current import/scene receipts, then build into a fresh
`Build/Golden/<name>`. Check the actual final receipt and all settings evidence,
verify the preserved dirty assets (including the fonts), inspect the real Windows
render output, and keep visual acceptance false for any model/reference mismatch.
Compilation, staging and helper reuse do not establish those native outcomes.
