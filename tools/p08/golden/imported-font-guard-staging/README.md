# Empty imported TTF texture guard

The [actual native ownership proof](../../../../docs/p10/native-baseline/diagnosis-baseline03/imported-font-textures-full.json) identifies two dirty `Texture2D` subassets produced by clean `TrueTypeFontImporter` objects. These are empty legacy `UnityEngine.Font` caches belonging to `.ttf` inputs. They are separate from the authored TextCore SDF `.asset` atlases and their preservation problem.

This follow-up preserves the global unsaved-authoring rejection and existing imported-shader policy. Its only added exception must have been present in the guard's initial capture and must satisfy every observed condition:

- An `Assets/*.ttf` source with a clean `TrueTypeFontImporter`, clean dynamic main `Font`, clean imported material, and exact `font.material.mainTexture` identity.
- Font/material/texture GUIDs and asset paths agree; native local IDs are exactly 12800000 / 2100000 / 2800000. Material and texture are actual subassets.
- Font and texture flags are exactly `NotEditable`; texture name is `Font Texture`.
- Texture is 0×0, Alpha8, one mip, unreadable, Bilinear, Repeat on U/V/W, anisotropy 1 and mip bias 0.

Preflight and postcheck require identical source/meta bytes, dependency hash, importer JSON/dirty state, Font and Material serialized hashes, GUID/local IDs and every recorded sampler/owner field. **The complete texture memory hash must also remain unchanged.** There is no general allowance for volatile texture memory. Changed or newly dirty objects, populated TTF caches, SDF atlases, dirty owner/material/importer objects and authored textures still reject. Existing exact-data dirty-flag restoration remains; this patch never saves, reimports, clears, regenerates or overwrites font/cache contents.

Managed compile passed with zero warnings/errors:

```powershell
dotnet build tools/p08/golden/imported-font-guard-staging/Preflight.csproj -c Release
```

`install.py` freezes and verifies this new candidate against the current guard, original script metadata and exact native diagnosis before `--install`. Earlier build/dirty/authoring-preflight stages remain unchanged. Root owns native positive/negative controls and the subsequent actual build; managed compilation is not native behavioral evidence. Recommended controls include the observed empty-cache positive case and independent rejection of nonzero dimensions, readability, filter/wrap/mip-bias changes, mismatched ownership and dirty importer/material/Font/SDF changes.
