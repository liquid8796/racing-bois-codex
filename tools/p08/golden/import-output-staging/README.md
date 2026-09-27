# Selected Golden import outputs

This stage fixes two importer bookkeeping defects. It does not edit live Assets until root runs the explicit install command.

`GoldenSampleBuilder.Import.cs` previously hashed every prefab, material and metadata file under `Golden/Generated`. An unrelated inspection floor, review pipeline or later candidate therefore invalidated a selected asset's import receipt. The new `GoldenSampleBuilder.Outputs.cs` inventories only the descriptor's generated prefab/material files and their metadata, plus metadata for explicit descriptor inputs beneath `Assets/` (including FBX, maps, clips and any imported module map). Shared paths are sorted/deduplicated. Missing selected metadata fails instead of being silently omitted. Actual input bytes, descriptor hashes, compiled-source binding and full native asset validation stay in their existing validators.

The second change captures each texture/model importer's original dirty flag before assigning settings. If the serialized settings are exactly unchanged, `ReimportChangedSettings` restores only that flag. A genuinely pre-existing dirty importer stays dirty; changed settings retain the existing reimport behavior. The change does not globally clear importers, force unchanged reimports or relax the native build dirty-dependency gate. Root still needs the native clean/dirty importer control because managed tests cannot execute Editor dirty-state APIs.

Validation performed against the staged production selector and existing hash verifier:

```powershell
dotnet build tools/p08/golden/import-output-staging/Preflight.csproj -c Release
dotnet run --project tools/p08/golden/import-output-staging/Tests/Tests.csproj -c Release -- tools/p08/golden/import-output-staging/tests.json
```

Managed compile: zero warnings/errors. Twenty isolated-file controls passed, including unrelated mutations staying outside the receipt and selected prefab/material/FBX/map/clip/module metadata changes or missing metadata failing. These fixtures are not native Unity evidence.

Root-owned installation, after the active native build/run window is clear:

```powershell
python tools/p08/golden/import-output-staging/handoff.py
python tools/p08/golden/import-output-staging/handoff.py --install
```

The helper verifies frozen candidate/original hashes and existing script metadata before writing either file. It preserves the Import source's original line endings and installs the new partial helper before its call site. Root must compile, refresh compiled-source proof, import into a **new receipt**, generate the review scene and validate/build against the new source-bound import. Historical broad receipts and captures remain unchanged; they are not retroactively repaired. This patch does not expand the public Validate/CreateReviewScene/Build APIs or solve selection through `import-latest.json`.
