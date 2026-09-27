# Owned Editor UI rendering fixture — R2

R2 preserves the copied font's original name. The first native run reported an
ImportLog subasset caused by renaming the main font object away from its filename;
the strict font/material/atlas membership gate rejected it. Root verified all
original font files, serialized member hashes, pixel hashes and dirty flags stayed
exact. R1 and its failed receipt are preserved. No ownership allowlist is broadened.
The new helper assembly is `RacingBois.Tools.OwnedUiRenderR2.dll`; the public
fixture type and API are unchanged.

This helper prepares isolated copies for actual UI rendering. It does not build
a player, install production C#, run itself, accept fonts/art or establish P08
release readiness. Root owns all native execution and preservation checks.

## Exact preservation contract

The two original SDF files are pinned to their existing user-owned bytes:

- Regular: `758d967293e80b4ff61c92e83419513176a6a6564490c2fb5ffdc51f1cf72fa3`.
- ExtraBold: `e17386894e80dffe8afffc5f94f60dc1008419e7847c48f01a5ae225a847843a`.

Before copying, the helper records each original font/material/atlas object's
GUID/local ID, identity, dirty state, serialized-memory hash and readable atlas
pixel hash, plus asset/meta hashes. Exact bytes, member JSON and atlas bytes are
backed up under a fresh ignored `_local/ui-owned-render-font-backups/<runId>`.
Snapshot checks repeat during preparation, before attachment, around captures
and after release. No source font flag, cache, atlas, importer or file is changed
or restored by this helper. Unreadable or unsupported source members fail closed.

`AssetDatabase.CopyAsset` copies the exact UXML/USS/TSS/TTF/SDF dependency tree
under `Assets/RacingBois/Diagnostics/OwnedUiReview/<runId>/Mirror/Assets/...`.
The mirrored layout retains relative stylesheet/font URLs. Only copied asset
references/source-font GUIDs are remapped. All font/material/atlas ownership is
checked before glyph warming, including exact atlas subasset membership. Font
assets are never instantiated, destroyed or deleted by this helper.

The copied fonts alone receive the frozen 248-codepoint corpus from
`docs/p08/media/global-copy-character-corpus-20260928.json` (925 keys × six
locales, uppercase variants and printable ASCII; no live player/profile data).
Missing glyphs reject preparation. New copied atlas textures become subassets of
their copied font. The copy's clear-on-build flag is disabled, but this is an
Editor review fixture, not a verified player-build font migration.

The copied panel retains the source panel's scale/theme settings, with owned
PanelTextSettings/default/fallback fonts and an owned target texture. Unity
6000.5 exposes defaultFontAsset as obsolete; this fixture validates and assigns
the current serialized m_DefaultFontAsset field on its own new settings object,
and explicitly sets the document root's owned FontDefinition. Original settings
are untouched. A complete AssetDatabase dependency closure must contain the
copied fonts and no original copied UI/font/TTF asset before UIDocument attach.

## Root lifecycle

Use an idle editor with a preserved quiet scene and no enabled existing
UIDocument. Root must keep the generated cache ignored/uncommitted; copied font
assets include the existing source font data. Suggested ignore entry:
`/Assets/RacingBois/Diagnostics/OwnedUiReview/`.

1. Build/load the helper DLL after the root-owned source compilation settles.
2. Call `OwnedUiRenderFixture.Prepare(freshRunId, 1920, 1080)` once and keep the
   returned fixture in an AppDomain slot or another root-owned holder. Return
   `Snapshot()` from tool wrappers, not the Unity-object-bearing fixture itself.
3. Call `Attach()`. Initialize the actual current presentation views on
   `Document` with synthetic session data. No RaceBootstrap, real network or
   live credentials are needed. Current views accept locale in Initialize and
   expose SetLocale.
4. After each state/locale change call `MarkChanged()`, then wait at least two
   editor updates. `CapturePng("menu-enu.png")` records actual offscreen pixels,
   focus target, text bounds/elision and the font/source preservation report.
   The target starts explicitly clear; a still-clear image or unattached/zero
   layout rejects capture. Actual visual inspection remains required.
5. `FocusControl(name)` and `SubmitFocused()` use the attached panel's public
   focus controller and NavigationSubmit event route. These are synthetic
   native UI events, not physical keyboard/gamepad/foreground acceptance.
6. Call `Detach()`, wait two editor updates, then `Dispose()`. The UIDocument is
   disabled and detached from VTA/panel first. Only owned transient document,
   target texture and preview scene are released. Font/UI asset copies and
   private backups remain for review; no generic cleanup is attempted.

Preparation failure retains incomplete copied assets. Never delete a possibly
misbound FontAsset as ad-hoc cleanup: its OnDestroy can destroy atlas objects.
The fixture reports failed preservation/closure checks; it does not repair or
clear unowned font state. Root must inspect failures before any follow-up.

The existing NativeBuildFontPreservationScope protects unreferenced original
dynamic fonts only. A future player build would need a reviewed owned scene/UI
dependency replacement plus the existing settings/font/source guards. This
fixture does not establish that full build path or arbitrary username glyph
coverage. The six-locale authored corpus and actual rendered layout are separate
checks; original-font and visual acceptance flags remain false.
