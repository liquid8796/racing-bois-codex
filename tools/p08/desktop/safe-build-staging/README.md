# Desktop build preservation candidate (staged, not installed)

This candidate keeps the existing audited content-pack contract and builds a new
technical Windows player from an owned Race scene, UI/font tree and URP pipeline.
It does not accept P08 art, change catalog masks, alter protocol/authority or claim
release readiness. No Unity execution or production installation has occurred.

The old builder source is preserved in `before/`. Its former `Prepare` rebuilt the
shared DesktopPipeline, changed global settings, wrote project StreamingAssets and
called project-wide SaveAssets. Staged `Prepare` is read-only readiness validation;
BuildTo changes only its owned assets/output and scoped ProjectSettings.

The copied scene is never opened while it references original fonts. Its two
unique panel/UXML GUIDs are remapped in the copied serialized bytes, followed by
synchronous import and an actual dependency closure check. All other scene bytes
remain identical. P08OwnedUiAssets is extracted from the R2 fixture whose actual native preparation
passed for both fonts and all248 authored codepoints. No font clone/cleanup or
broad subasset allowlist is introduced. Production binds the actual checkout
font bytes rather than diagnostic-only user hashes.

Build entry verifies actual loaded assemblies against independent PE/PDB/source
attestation, rejects unrelated authoring drafts and dirty consumed dependencies,
clones the explicit reviewed desktop pipeline and selects it at every quality,
then persists effective settings via NativeBuildProjectSettingsScope. Exact DX11
readback, global font preservation, source/dependency fingerprints and restoration
checks remain mandatory. Only the new player directory receives the audited pack
and selected public runtime config after BuildPlayer. Existing StreamingAssets is
source-bound and is not authored or cleared.

The build receipt records dependency schema 3 with the unique owned roots,
original UI provenance, actual effective build-settings hashes and exact restored
settings evidence. Existing schema-2 receipts remain historical. The staged Python
auditor must validate this new contract before any build is publishable. Private
font byte/memory backups stay under `_local`; only hash/summary evidence can enter
the technical player. Build output must be fresh; owned font copies are retained.

Loaded scenes must be clean; their exact setup/order/active selection and saved
source/meta bytes must match afterward. No implicit scene restoration overwrites
a concurrent edit. Preparation failures verify already-captured original fonts
and retain private failure evidence even before the caller receives the utility.
Owned generated font members/pixels are also captured and checked across BuildPlayer.
Two strict dirty snapshots preserve entry state and then include newly imported
read-only artifacts without relaxing authored-object rejection.

Managed validation: full Authoring.Editor compilation with zero warnings/errors;
50 existing schema2 contracts plus19 schema3 file/failure controls. Independent
preservation/source/owned-UI reviews have no remaining must-fix. These are not
native build, launch or restoration proof. Only root installs using install.py,
then refreshes Unity and runs a fresh compiled-source attestation:

```powershell
dotnet run --project tools/p08/desktop/safe-build-staging/CompileAudit/CompileAudit.csproj -- desktop D:/Project/Unity/racing-bois docs/p08/desktop/compiled-sources-<fresh-id>.json
```

Root invokes P08DesktopBuilder.BuildTo with a fresh Build child and that exact
proof path from an idle, clean, quiet editor. Owned asset copies and private
backups remain for diagnosis; the helper never deletes FontAssets. The actual
Windows player, original-state checks and schema3 distribution audit must pass
before a technical candidate is archived. Masks/promotion/release gates remain open.
