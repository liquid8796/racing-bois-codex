# Scoped TextCore font preservation — staged

This candidate is not a visual acceptance or a completed native build. Root owns
native probes and installation. Its managed compile passes against Unity
6000.5.7f1; it makes no assumption that a successful compile proves restoration.

Root subsequently completed the copied-font Apply/Verify/Restore control,
dirty-owner and referenced-font negative controls, then the global scope with the
actual installed TextCore hook. The
[native restoration receipt](../../../../docs/p10/native-baseline/diagnosis-baseline03/font-scope-global-hook-restored.json)
records exact original source/meta, owner/material and atlas-pixel preservation.
Private exact-byte backups remain under
`_local/rb4-font-recovery/global-scope-hook-01`. Both original source hashes remain
`e17386894e80dffe8afffc5f94f60dc1008419e7847c48f01a5ae225a847843a`
and `758d967293e80b4ff61c92e83419513176a6a6564490c2fb5ffdc51f1cf72fa3`.
This establishes the controlled hook/protection path; a successful complete
player build still needs its own final source/font-preservation receipt.

The actual TextCore prebuild hook scans all project FontAssets, even those absent
from the selected build scene. A previous build reset the two Noto assets. Their
exact pre-turn bytes have been recovered by root from Git's Codex snapshot tree
`757babe93e4ba64ea38f18144e8a748b41e5544f`, with independent backups retained under
`_local/rb4-font-recovery/start-of-turn`. The current protection must preserve those
bytes, not reconstruct or approve an equivalent regenerated font.

Root's [native mechanism probe](../../../../docs/p10/native-baseline/diagnosis-baseline03/font-clear-policy-native-probe.json)
verified that temporarily disabling the installed serialized
`m_ClearDynamicDataOnBuild` field prevents the actual TextCore preprocessor from
clearing both fonts. The probe restored original flags, owner JSON and exact
source hashes at that observation point. A later cleanup diagnosis identified a
separate unsafe shallow-clone destruction path, so that early receipt is not proof
of complete lifecycle preservation. This scope adds source/meta backups, complete
subasset identity, dirty-state checks and readable atlas pixel hashes around the
policy and must be checked after all cleanup.

Do not use `Object.Instantiate(FontAsset)` followed by normal destruction as a
probe. In the installed TextCore runtime module (SHA256
`acfd25b7c88c07587729f91233ecae963af3a45c1a114ddf9b442b2e1f9880a6`),
`FontAsset.OnDestroy` calls `DestroyAtlasTextures` when `m_IsClone` is false. That
method destroys referenced atlases with `allowDestroyingAssets:true` and does not
check their owner/path or sharing. The engine's special clone factory sets
`m_IsClone=true`; plain Instantiate does not provide that protection. Use only an
owned `AssetDatabase.CopyAsset` probe whose atlas/material references are proven
to belong to the copied asset. This scope itself never clones or destroys a
FontAsset, material or texture.

The public constructor takes the actual build dependency paths and a **new**
repository-contained evidence directory. Callers must select `_local/` or `Build/`
so source backups never become imported project assets. It captures/backs up only; it does
not change fonts. The scope selects exact TextCore FontAsset objects with dynamic
population mode and clear-on-build enabled. Referenced dynamic fonts are rejected
because altering their effective policy could affect shipped content; an isolated
build strategy or separately reviewed owned-font pipeline is required for them.
Dirty owners/materials/atlases, non-owned or unreadable atlases, missing fields,
unexpected subassets and invalid material/atlas links also fail before mutation.

Register `Restore` in the build's cleanup journal **before** calling `Apply`.
`Apply` sets only the verified clear-on-build field to false, verifies that this
is the only serialized owner change and that every other member/pixel is unchanged,
then clears only the new dirty flag caused by its own transient change to an
initially clean owner. It never invokes SaveAssets, SaveAssetIfDirty, reimport,
atlas resets or a write to the original font/metadata file.

Call `VerifyProtected` immediately before and after the native BuildPlayer call.
`Restore` returns only the owned flag, verifies exact original source/meta, owner
JSON, material/subasset identities, dirty states and atlas CPU pixels, and writes
a separate result. It does not restore entire JSON or texture pixels over unknown
changes. A mismatch fails; it attempts only flag cleanup on the same owner and
preserves other changed values/dirty state for inspection. Immutable source/meta
backups exist before any mutation so a failure is recoverable.

The root-owned first probe should use an actual copied font asset beneath
`Assets/RacingBois/Golden/Generated/FontPreservationProbe/`, keeping its own copied
material and atlas subassets. `ForOwnedCopyProbe(path, newEvidenceDirectory)`
limits selection to that owned copy. Use `Apply`, `VerifyProtected`, and `Restore`,
with `Restore` in a finally block. **Do not invoke the global TextCore hook while
only the copy is protected:** it would still process the original fonts. The
copy scope is labelled as a probe and cannot establish global protection. Only
after those copy checks succeed should root apply a global scope over every real
clean, unreferenced font, invoke the actual hook, verify/restore all of them and
independently rehash the pre-turn bytes. Root's earlier mechanism probe already
provides scoped evidence that the installed hook honors the temporary policy.

The current candidate deliberately permits only FontAsset, Material and Texture2D
members. If the copied native asset includes metadata subassets such as
AssetVersion, inspect and bind the actual type/role before changing this rule.
No speculative metadata or texture exception is included.

The separate imported-font dirty guard covers only the measured empty, readonly
legacy `.ttf` cache. It does not waive this TextCore/SDF atlas contract. Neither
scope accepts art, changes production masks or closes P08/P10.

The active staged helper exactly matches the native-proven live SHA256
`22e0b950258ecfb553c1927d47c82267585cb409ffe04bd777bd13e528042363`.
A later path-restriction-only proposal is retained under `private-path-candidate`
and is not the installed/tested class. The current Golden caller explicitly uses
private `_local/native-font-preservation` storage.
