# Global UI copy — native verification, 2026-09-28

The desktop client now shares language selection across its main menu, settings,
race HUD/results, career, multiplayer and content-status presentation. The 394
new semantic keys join 531 cinematic keys: 925 keys, with 5,550 authored values
across ENU, DEU, ESP, FRA, ITA and VI. No argument keeps Vietnamese. For example,
`--language=FRA` selects French; `--cinematic-language=ENU` can still override
cinematics separately. Malformed or unsupported explicit options fall back to
English. This change does not introduce a new language-selector layout.

Player names, room names, catalog names, invite codes and transport discriminators
remain opaque data. Only recognized client-facing status/error messages are
translated at their presentation boundary. Locale changes retain selections,
account drafts and the exact pending career command. They do not issue gameplay,
commerce, quality, preference or network commands. The UXML changes add 27 semantic
names to the existing 160-node tree; default text, hierarchy and values are retained.

## Evidence and its limits

- Main/composed managed controls: 3,142; client-message controls: 905. The complete
  Windows, Editor and Web presentation/bootstrap preflights compile without
  warnings or errors. Career additionally verifies its Vietnamese expression
  equivalence and lookup/opaque-value contracts in its own source-bound receipts.
- [Final compiled identity](global-copy-pristine-r2-compiled-sources-20260928.json)
  binds the installed DLL/PDB identities to physical source checksums.
- [Final native contracts](global-copy-pristine-r2-native-contracts-20260928.json)
  pass 5,743 checks in Unity against those installed assemblies. This covers all
  six locales, real view bindings, draft/confirmation preservation and the old
  tick-600/event-200 to new tick-0/event-1 race rollover without replaying events
  merely because the locale changed. Owned objects are released and observed
  global settings remain unchanged.
- These native contracts deliberately use an unattached UI tree. They do not
  establish rendering, physical input, readability or full-game acceptance.
  The separate owned-font render fixture records those narrower observations.
- [Authored character corpus](global-copy-character-corpus-20260928.json) contains
  248 codepoints including uppercase variants and printable ASCII. Both source
  TTFs contain them according to [the source coverage check](global-copy-source-font-coverage-20260928.json).
  This is not a glyph-layout, arbitrary-player-name or font acceptance result.

## Reproducible authored inputs

The main, multiplayer, career and client staging directories under
`tools/p08/media/global-copy-*-staging` retain their canonical inventories,
translations, generators, metadata and original reviewed handoffs. Their
historical reports identify those exact revisions.

The current Career output retains the explicit ENU amendment:
`career.garage.pristine` is **BIKE UNDAMAGED**, covering condition 100 for both a
new bike and a repaired bike. Rendered fit review additionally shortens three
Career labels and one German Multiplayer invite heading. Current inputs are
identified in `global-copy-effective/current.json`. Use:

```powershell
python tools/p08/media/global-copy-effective/generate.py --check-live
```

The older Career generator refuses to overwrite this chain. Revision 1 and its
native proof remain preserved; revision 2 only adds the active-input source
comment and has the separate final source/native proofs linked above. Neither
older handoff should be reapplied over the active amendment. The latest
[native fit/viewport checkpoint](../ui-owned-render/FIT_VIEWPORT_20260928.md)
records 1,976 attached checks, the 108 actual images, the separate 5,743-contract
pass and the remaining explicit-scroll coverage work.

No content masks, online/LAN authority, locked art concepts or phase acceptance
flags change. Language review and corresponding rendered UI review remain
necessary before full localization acceptance.
