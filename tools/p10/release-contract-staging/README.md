# Desktop dependency receipt repair — preserved staging history

Current resumption check on 2026-09-27: all three live targets now match the
`candidateSha256` values in `candidate-manifest.json`. The repair is integrated;
the staging files, baseline and original before hashes remain historical proof.
The live verifier's 50 tests passed again in
`docs/p10/candidate-packaging/20260927T160259Z/receipt.json` alongside 20 native
candidate archive tests. This does not establish a completed P08 player build.
Do not rerun the old generator against the integrated source. The text below
describes the original staged proposal and its original verification.

The live builder includes Unity scene/render-pipeline dependencies in its source
snapshot. The live Python verifier allows only code plus seven fixed paths,
so a legitimate material/prefab/render-pipeline asset fails verification. The
real existing WebURP asset reproduces this mismatch without launching Unity.

`candidate-manifest.json` binds three proposed replacement files to exact live
before hashes. Root must check those hashes before integrating; no apply script
or live Editor mutation is performed here. The baseline verifier is retained
for the before/after control. Rerunning `stage_fix.py` after integration is not
appropriate: it is a generator against the recorded prior source shape.

The proposed builder records schema-2 dependency metadata from actual
`AssetDatabase.GetDependencies` for the Race scene and DesktopPipeline. Virtual
`Packages/...` paths resolve via installed
`UnityEditor.PackageManager.PackageInfo.FindForAssetPath().resolvedPath`.
Every logical asset path maps to a hashed physical project file. Each resolved
package has an exact embedded or PackageCache directory and a hashed
`package.json`. The verifier also requires its name/version and the package-lock
entry. It does not admit arbitrary Library files or drop unresolved files.

Only `Resources/unity_builtin_extra` and `Library/unity default resources` are
explicit built-in exceptions; their names are included in the dependency digest
with the actual Unity version. These built-ins are version-bound engine inputs,
not claimed as individual copied/file-hashed project assets.

Python requires sourceFiles to be typed, canonical, case-unique, sorted and equal
to the authored code/UI + fixed settings + exact resolved dependency/manifest
union. It rejects symlinks/junctions, path aliases/traversal/ADS, size/hash drift,
missing package files, unlisted Assets and other Library directories. The build
compares both source and dependency fingerprints before/after BuildPlayer.

The actual engine receipt must be selected by the caller; arbitrary fabricated
JSON is not authenticated merely because its self-declared hashes are internally
consistent. This contract still does not certify visual fidelity, semantic
content mapping, full importer `.meta`/assembly-definition reproducibility or
native runtime performance.

Validation: 51 actual generated-fixture tests pass, including a real filesystem
symlink control and the old-verifier rejection of a real project asset. The
staged C# compiles against installed Unity 6000.5.7f1 assemblies with zero errors
and warnings. See `docs/p08/release-readiness-20260927/staged-verification.json`.
No native engine capture or player build is inferred from these results.

```powershell
python tools/p10/release-contract-staging/verify.py
python tools/p10/release-contract-staging/readiness_snapshot.py
```

After root integrates, execute the real builder through direct Unity MCP and
use its new receipt with the updated verifier. Existing historical receipts
without schema-2 dependency metadata cannot establish this stronger binding.
