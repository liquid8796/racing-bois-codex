# Content preparation prerequisite and save boundary

`P08ContentPackBuilder.Setup()` previously created routes and materials before
discovering missing actors. Its two global `SaveAssets` calls could also save
unrelated editor drafts. All public preparation entry points now inspect the
complete shared pack before creating an asset or changing an importer.

The read-only inspection resolves the existing promotion/fallback bindings,
prefabs, materials, shaders, twelve unique rider clips, utility audio bank,
24 portrait importers, 97 distinct audio deliveries and their SHA256 values,
functional sound roles, route music, output types and dirty dependency/importer
state. It collects failures so a missing first bike does not hide the remaining
inputs. This prerequisite check does not grant art acceptance or reconcile the
separate Ridge provenance mismatch. Existing promotion rules and masks remain.

Composition saves only its 30 route/material outputs or three actor/library/bank
outputs. Existing output drafts and dirty dependencies are rejected first; the
existing dirty-asset guard verifies unrelated drafts even on a failed call.
Portrait and sound import settings remain explicit preparation operations after
the full check succeeds. The change is not an atomic filesystem transaction:
an unexpected failure during a future successful-input composition still needs
inspection, and no full successful composition is claimed here.

## Actual verification

- [Native receipt](preparation-native-20260928-01.json): **25 checks passed**.
  All three entry points rejected the current nine missing bike prefabs, eight
  rider prefabs and 24 portraits, with no content/material output creation.
- [Read-only inventory](preparation-inputs-20260928-01.json): 226 checks,
  41 missing inputs. This inventory is deliberately **not ready**.
- Six in-memory audio mutations rejected duplicate IDs/paths, missing functional
  cues/route music, unknown categories and extra entries; the real 97-entry
  inventory passed. No production manifest was changed for these tests.
- An isolated native fixture proved a scoped save persisted the requested asset
  while leaving another asset's edited memory, dirty flag and old disk bytes
  intact. A dirty destination was rejected; the clean destination was allowed.
  The two owned fixtures were then saved clean under the ignored diagnostics root.
- All actual audio source/importer bytes, loaded scene setup and preexisting
  dirty assets remained unchanged. Club, unowned Ash, both original SDF fonts
  and the Race scene retained their exact starting SHA256 values.
- [Loaded compilation proof](compiled-preparation-20260928-01.json) binds all ten
  executing game/editor assemblies, including 55 editor source documents.
  Separate managed authoring compilation passed with zero warnings/errors.

The native script is at
`tools/p08/content-pack/preparation-20260928/native-check.cs.txt`. It requires a
fresh owned fixture directory and a fresh matching compilation proof for a rerun;
the published report must not be overwritten. No bundle, full player build,
complete production composition or P08/P10 acceptance follows from these checks.
