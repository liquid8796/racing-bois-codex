# Imported shader / unchanged dirty-flag correction

Native baseline01 did not build. Its initial dirty-object snapshot already held
Lit.shader and HDRDebugView.shader as dirty imported Shader objects. The real
[before/after gather probe](../../../../docs/p10/native-baseline/diagnosis-baseline01/gather-probe.json)
shows identical shader JSON, clean ShaderImporter JSON, dependency identity, name,
hide flags (8), per-shader maximum LOD (-1) and global maximum LOD (Int32.MaxValue)
for both objects. The probe does **not** establish that GatherShaderFeatures made
them dirty.

The [exact object comparison](../../../../docs/p10/native-baseline/diagnosis-baseline01/changed-dirty-objects.json)
found only StudioReviewPipeline's dirty flag changed true to false. Its serialized
memory and every recorded source/meta byte remained unchanged. That observation
motivates restoring only the original dirty flag after an exact identity check;
the guard never overwrites an object's values or its source bytes.

The narrow imported-shader policy applies only to `Shader` objects produced from
`.shader` source by a `ShaderImporter`. A dirty dependency may proceed only when
it existed at guard capture, the importer is clean, exact source/meta/importer and
dependency hashes still match, writable shader properties retain the inspected
read-only/default state, and the Shader name matches its source declaration.
Compiler JSON hashes remain recorded for diagnosis; they are not used as the
authoring identity for these imported artifacts. ShaderGraph and other imported
types receive no new build exemption. Dirty materials, ScriptableObjects, fonts
and importers still fail dependency validation. Source, metadata, importer,
dependency or writable shader-property changes still fail preservation.

Only when the original object data (including its full serialized memory hash),
type/local ID and source/meta identity are exact may the guard restore a cleared
original dirty flag with `SetDirty`. It never clears flags, saves/reimports assets
or restores stale object values. Changed data still fails without replacement.

The separately frozen candidate preserves the earlier scoped-build handoff.
Compile with `dotnet build tools/p08/golden/dirty-guard-staging/Preflight.csproj`.
`install.py --install` replaces only this reviewed guard and preserves its meta.
Root must run native positive/negative controls and a fresh build after source
rebinding; this staged compile is not a successful native build.
