# Fresh FBX material remaps: actual Unity controls

The public-only optimization is installed after independent review. Fresh imported FBX renderer materials must be unambiguous embedded subassets owned by that exact file, with an empty entire external-object map and an exact descriptor-name set. The importer then applies settings and final remaps in one reimport. The strict existing fallback and final material/geometry/UV/source/output validation remain.

Two owned FBX copies contain the exact Apex R5 bytes (SHA9fc3f8e0580b96c6cb20f44e2c6be2746a08731c98a773f98acd4da718738130). Before the first operation, direct Unity inspection found zero remaps and nine uniquely named embedded materials in each. One descriptor intentionally substitutes an unknown material name.

| Actual Unity control | Model reimports during the operation | Result |
|---|---:|---|
| Fresh embedded sources, final settings/remaps together | 1 | Import `be8a5fbc04ff498194ac5e4cc29a9e90` PASS, source binding PASS |
| Unknown declared material | 0 | Import `69d87819d16b4f44aea33c0ed761d0de` correctly FAIL; importer memory and metadata bytes unchanged, remaps still0 |
| One intentionally wrong existing external remap | 2 | Strict fallback clears/reimports, validates original names, then remaps; `e6bf0df0a19042299413d06277e06fe7` PASS |
| Already-correct repeat | 0 | `edd65ec1d3f547188efd54b428ce25c2` PASS, source binding PASS |

Counts come from the actual engine log deltas for the exact owned FBX path, starting after initial ordinary source import and after deliberate wrong-remap setup. Corresponding `.txt` log excerpts and named receipts are retained. The unknown-material failure is not relabelled as asset acceptance. Only test-owned generated materials were persisted after that expected failure.

These small actor controls demonstrate import-count behavior and preserve final structural checks; they do not measure a Canyon time saving or accept art. The earlier real Canyon operation required two expensive generated-secondary-UV imports. The new path removes the second settings/remap reimport when the fresh-material preconditions hold; ambiguous, missing, external or pre-remapped material identities keep the original strict path. No internal `ModelImporter.sourceMaterials` API or inverse-name guess is used.
