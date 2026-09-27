# Fresh embedded-material import optimization — staged only

The installed Unity 6000.5.7f1 assembly exposes `ModelImporter.sourceMaterials`
as an **internal** getter, not a public API. Offline Cecil metadata in
`installed-api.json` also shows that public `SourceAssetIdentifier(Object)`
only copies the object's runtime type and current name. It cannot reconstruct
original source identities after a renderer has been remapped to generated
materials. This staging uses no internal/reflection-based Unity API.

The live `Import` method already performs a synchronous AssetDatabase refresh.
For a newly imported FBX with no remaps, its existing rendered material slots
can therefore provide the original names before changing importer settings.
The staged `HasFreshEmbeddedMaterialSources` accepts this path only when:

- The entire external-object map is empty, including non-material overrides.
- A model and rendered slots exist; no slot is null.
- Every used material is a real subasset owned by the exact FBX path.
- Distinct embedded materials have nonempty, unique names.
- The used source-name set equals the descriptor's material-name set exactly.

All eligibility checks run before importer setters. An exact embedded source
set that disagrees with the descriptor fails immediately. Missing, external,
already remapped or ambiguous identities retain the existing strict fallback;
the code never derives source names from generated material names or guesses
through inverse remaps.

For the eligible fresh case, final importer settings and every known material
remap are applied together before one `SaveAndReimport`. This removes the
second generated-lightmap-UV pass previously caused by setting up geometry first
and applying material remaps afterward. It does not remove the initial ordinary
source import during the synchronous refresh. No runtime speedup is claimed yet.

The final exact generated-material set check remains, as do `CreatePrefab` and
`ValidateAsset`: renderer coverage, submesh/material-slot count, physical/primary
UV validation, secondary-UV policy, LODs, bindings and source/output fingerprints
are unchanged. The already-correct-remap path keeps its existing changed-settings
optimization. Stale remaps keep the original clear/reimport/validate/add/reimport
sequence. No UV threshold or visual gate changes.

`Preflight.csproj` compiles the complete Golden importer source set against the
installed Unity assemblies, replacing only the live Import.cs with this staged
file. `preflight-build.txt` records PASS with zero warnings and errors. This is
managed compilation, not actual Unity behavior or timing evidence.

The live importer and frozen Canyon V17 files are untouched. Do not install this
candidate while the root-owned native V17 import is running. The expected live
base is `Assets/RacingBois/Editor/GoldenSampleBuilder.Import.cs`, SHA256
`3b903432e935cdda251cf87f20878954853957d6115dbc9a86754076c9300483`.

Before adopting the optimization, root should run native controls using small,
fresh, owned FBX copies after the current import completes:

1. Fresh embedded material model: prove eligibility, one settings/remap reimport,
   exact final material/geometry validation and stable source bytes.
2. Unknown descriptor material: fail the exact embedded source-name check before
   any importer setter/reimport; retain a failed receipt, not an accepted fixture.
3. Existing wrong/remapped material: prove the old strict fallback remains active
   and restores correct bindings rather than trusting generated material names.
4. Already-correct repeat import: prove no unnecessary unwrap when settings and
   remaps are unchanged. Verify material slots and complete output binding again.

Any importer setting or postprocessor that changes source material naming must
fail final validation. If a fresh native control cannot establish stable source
identities, leave the strict fallback in place; do not replace it with internal
serialized field names or an assumed material list.
