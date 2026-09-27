# Desktop builder preservation checkpoint

The builder now composes owned scene/UI/font/pipeline assets, scopes effective
settings, preserves original state and validates actual consumed source identities.
It no longer calls project-wide SaveAssets or writes project StreamingAssets while
preparing a player. The schema-3 auditor checks these owned inputs and restoration
receipts; historical schema-2 audit behavior remains covered.

Full Authoring.Editor compilation and 69 managed audit contracts pass. Unity's
actual ten-assembly PE/PDB/source attestation passes in
`compiled-sources-safe-20260928-02.json`. New scripts required a full AssetDatabase
refresh; the initial script-only request compiled the changed builder before its
new helper files were imported. The full refresh resolved those missing-type
errors without changing the implementation.

Two actual BuildTo calls rejected prerequisites before creating player output:

1. `build-87f9466b12774b4386dddf342e69c70b.json` rejected an unsaved atlas in an
   owned UI-review copy. Root verified its GUID and local subasset ID and saved
   only that copied atlas. No original font or unrelated asset was saved.
2. `build-800d8fd1cbab496687195190ed672127.json` then reached content validation
   and rejected the absent `Assets/RacingBois/Content/P08/Actors.asset`.

Both native receipts report unchanged loaded scenes and existing dirty objects,
with no restoration errors. The independent
`prerequisite-rejection-20260928-01-verification.json` verifies that no output
folder exists and all ten bound original source/settings files remain exact.
The authoritative [content prerequisite audit](../content/DESKTOP_PREREQUISITES_20260928.md)
lists the missing assets and existing source/hash mismatches.

**No Windows game player was built by these calls.** The successful BuildPlayer
path, generated-font preservation during that path, installed distribution and
native full-game launch remain unverified. No content masks, art acceptance or
pack-completeness requirement was relaxed. The startup-smoke draft remains paused
outside Assets until actual content prerequisites can be satisfied.
