# Explicit ENU pristine-state amendment

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
