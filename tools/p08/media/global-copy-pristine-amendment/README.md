# Explicit ENU pristine-state amendment

The active revision is `current-overlay.json`. Regenerate its exact reviewed
module with `python tools/p08/media/global-copy-pristine-amendment/effective_generate.py`;
use `--check` for read-only verification and `--check-live` to include the installed
module. This entry consumes only repository files and checks all source/data hashes,
all 906 Career cells and the 5,550-cell native union. It writes only this staging
module, never Assets. The older Career `generate.py` now stops with this command
instead of silently restoring its frozen older ENU label.

Revision 2 adds only a source comment pointing to the active overlay. `revision1/`
preserves the exact first amendment module, handoff, installer and README; its
separately recorded native 5,743-check proof continues to identify that revision.
The authored locale and union remain byte-for-byte unchanged. This revision needs
its own source/assembly attestation; it does not relabel the earlier proof.

`career.garage.pristine` describes condition 100, which includes a new undamaged
bike as well as a repaired one. The ENU label changes from **BIKE FULLY REPAIRED**
to **BIKE UNDAMAGED**. This is one explicit authored translation-cell amendment.
The canonical VI template, key, named arguments, all other ENU copy, the other
five locale values, intents, conditions and layout remain unchanged.

`before/` preserves the exact old ENU locale, generated module, Career and combined
handoffs, and authored union. Original union/receipts were not overwritten. The
new `ENU.json` and `authored-text-union.json` are this revision's authoritative
inputs; do not silently reapply the older frozen generation/handoff over it.

`install.py` validates one target and its unchanged script metadata. Only root
uses `--install`, then recompiles/source-attests and reruns the existing native
UI-tree harness with **this directory's fresh union path** and the new proof.
Managed checks compare all 5,550 union cells and all 2,364 global native-provider
equivalents, allowing exactly this one ENU difference. Those checks are not native
execution, language-review completion or UI/rendering acceptance.
