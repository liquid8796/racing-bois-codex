# Prevent native Unity build autosaves before entering BuildPlayer

This proposal was kept outside Assets during baseline04. After that run ended,
root authorized applying the guard and both builder call sites. The active Golden
importer/promotion managed preflights now compile with zero warnings/errors;
native early-rejection controls remain root-owned. No Unity/player was launched
by this patch author.

Baseline03's actual BuildPlayer returned success with zero warnings/errors and
stable selected build inputs, but the final preservation guard correctly failed.
The [native comparison](../../../../docs/p10/native-baseline/diagnosis-baseline03/dirty-state-diff.json)
records three effects:

- The deliberately unsaved `DirtyGuardWitness-20260928.mat` was saved by Unity.
  Its source changed, its memory did not, and its dirty flag cleared. It must
  remain a preservation failure; neither a successful build nor identical
  in-memory values makes this source write acceptable.
- Two Noto SDF atlas `Texture2D` subassets changed in memory and became clean,
  while their containing font asset source/meta files remained unchanged.
  This is not proof that every font/texture change is disposable cache data.
- Project settings restored exactly, independently of those asset effects.

The proposed guard adds `RejectUnsavedAuthoringAssets()` and calls it immediately
after constructing the dirty-state guard, before scene copying, URP gathering,
any owned asset save, or BuildPlayer. Call it again just before BuildPlayer to
catch authoring data made dirty during preparation. It rejects dirty persistent
project/package authoring objects globally, including Material, ScriptableObject,
FontAsset and Texture subassets, not only objects reachable from the build scene.
It never saves, clears or restores their values. The existing post-build checks
remain required for mutations that still occur.

Imported Shader artifacts retain their existing narrow source/importer/property
contract. AssetImporter objects retain the existing dirty-dependency rejection
and before/after identity checks; this proposal does not broaden or weaken those
rules. It does not claim that arbitrary unsaved importer metadata can safely be
used in a build. A later measured global importer write would require its own
preflight protection.

This is deliberately conservative: a dirty ScriptableObject whose bytes happen
to equal disk is still blocked. The guard does not deserialize another copy,
silently save it or infer that the user's dirty state is disposable. Root can
prepare a clean, owned derived asset through its explicit authoring workflow;
the build itself must not decide to save a user draft.

For the Noto atlas investigation, preserve owner FontAsset source/meta hashes,
owner serialized settings, atlas membership/local IDs, population mode,
clear-on-build policy, owner/material/atlas dirty states, atlas dimensions and
memory/pixel identity before/after. A cache-specific policy would require that
evidence and a positive/negative native control distinguishing a generated dynamic
atlas from authored texture edits. Until then dirty font atlas textures are
blocked by the proposed preflight and any observed texture mutation remains a
failure. No blanket texture exception is proposed.

## Targeted installed TextCore evidence

Read-only inspection of Unity 6000.5.7f1 establishes the actual TextCore path,
not merely the analogous TMP implementation. The installed file
`Editor/Data/Managed/UnityEngine/UnityEditor.TextCoreTextEngineModule.dll`
is 211,456 bytes, SHA256
`4a1d3e9cac7b1406f744e93b4425b910d01970af6eb82573c86889ebce4d3656`.
`UnityEditor.TextCore.Text.TextCorePreBuildProcessor.OnPreprocessBuild(BuildReport)`
searches globally for `t:FontAsset` under Assets. Dynamic/DynamicOS owners with
`clearDynamicDataOnBuild` and a nonzero atlas width trigger
`ClearCharacterAndGlyphTablesInternal`, independently of the selected build scene.

The sibling `UnityEngine.TextCoreTextEngineModule.dll` is 323,584 bytes, SHA256
`acfd25b7c88c07587729f91233ecae963af3a45c1a114ddf9b442b2e1f9880a6`.
Its `UnityEngine.TextCore.Text.FontAsset.ClearCharacterAndGlyphTablesInternal()`
clears glyph/character tables and invokes `ClearAtlasTextures(true)`. That path
keeps atlas zero, removes extra atlases, reinitializes the remaining atlas to 1×1,
resets it through FontEngine, and applies the texture. This explains a mechanism
for changes to an otherwise unused dynamic atlas; it does not identify the exact
dirty-flag-clearing instruction or prove every observed texture edit disposable.

The saved owners are TextCore FontAssets (owner local ID 11400000), with exact
membership:

| Owner | Asset GUID | Atlas zero local ID |
| --- | --- | --- |
| NotoSans-ExtraBold SDF | `39152ce5ab92a0340bbdff2e17611e1b` | `2580687842620488958` |
| NotoSans-Regular SDF | `8e3b65e6723dcc34593746de4a20f835` | `1100642487506886696` |

Both owners serialize population mode Dynamic (1), clear-on-build true,
multi-atlas enabled and atlas index zero. Each owner's `m_AtlasTextures[0]` and
material `_MainTex` point to the listed texture. Saved atlas dimensions are 1×1
and TextureFormat is Alpha8 (1). Owner/type/membership/flags are stronger evidence
than a filename or Texture2D type alone, but confer no permission to discard an
unsaved texture edit. The conservative staged preflight therefore remains intact.

After the current native window ends, root can review/apply the adjacent patch,
compile and run native controls: a dirty unrelated material must be rejected
before any BuildPlayer entry/source write; dirty ScriptableObject/FontAsset/atlas
must also reject; a clean baseline can proceed; shader-artifact and exact dirty-
flag controls must retain their prior behavior. The patch is not yet native
validated and does not retroactively accept baseline03.
