# Derived GLB metadata normalization — 2026-09-30

Four frozen Tripo outputs now have separate derived GLBs with local asset IDs,
neutral technical object/image/material names and a local export-tool generator.
The original GLBs and their task receipts remain unchanged. The local asset ID
does not replace a Tripo server task or assert authorship/copyright ownership.

| Frozen source | Derived file | Local asset ID |
| --- | --- | --- |
| `ArtSource/Trials/Tripo/Apex/20260930-01/model.glb` | `ArtSource/Trials/Tripo/Apex/20260930-01/derived/RB_Apex_Trial01_Normalized.glb` | `RB_APEX_TRIAL01_20260930` |
| `ArtSource/P08/Tripo/Apex/20260930-hq02/model.glb` | `ArtSource/P08/Tripo/Apex/20260930-hq02/derived/RB_Apex_HQ02_Normalized.glb` | `RB_APEX_HQ02_20260930` |
| `ArtSource/P08/Tripo/Spark/20260930-hq01/model.glb` | `ArtSource/P08/Tripo/Spark/20260930-hq01/derived/RB_Spark_HQ01_Normalized.glb` | `RB_SPARK_HQ01_20260930` |
| `ArtSource/P08/Tripo/Apex/20260930-parts01/model.glb` | `ArtSource/P08/Tripo/Apex/20260930-parts01/derived/RB_Apex_Parts01_Normalized.glb` | `RB_APEX_PARTS01_20260930` |

Each same-named JSON audit in this directory binds the source and derived file
hashes, changes by JSON path and original-value hash, complete BIN hash, semantic
JSON hash and each decoded accessor hash. All four passed the frozen input hash,
round-trip, final on-disk metadata and raw-source preservation checks. Across
them, all 156 accessors and 53,266,675 decoded components are identical. Geometry,
transforms, topology, UVs, normals, material channels and texture references are
preserved. No provider/task identifier remains in their JSON metadata.

The nine embedded images also retain exact bytes. The trial maps are 2048×2048;
Apex HQ02 and Spark HQ01 each contain an 8192×8192 JPEG, a 4096×4096 JPEG and a
4096×4096 PNG. The six JPEGs contain conventional FFE0/JFIF metadata; the PNGs
have no text metadata. No copyright/license notice was found in the JSON or
inspected conventional image metadata. This observation does not establish an
asset license or prove that hidden pixel steganography/watermarks are absent.

The normalizer does not alter pixels, strip image segments/chunks, remove hidden
watermarks, assign a creator or transfer rights. Any copyright/license/attribution
notice it encounters is retained and flags the derived result for review.
Unsupported provider/task strings outside known technical metadata, compressed
accessors without a decoder, malformed embedded metadata and late mismatches
reject normalization. Twenty-two synthetic preservation/negative controls passed
on Windows, including normalized integers, interleaving, sparse accessors, matrix
padding, notice retention, PNG/JPEG metadata and concurrent source changes.

These GLBs remain **unaccepted for production and visual fidelity**. Runtime LOD
generation and 1K/2K texture preparation are separate Blender steps; this metadata
pass preserves the high-resolution source images. It does not close those gates.

Implementation: `tools/p08/tripo/normalize_glb.py` and
`tools/p08/tripo/test_normalize_glb.py`. The CLI requires a frozen expected input
SHA256, an explicit local asset ID, a fresh `.glb` output and a fresh `.json` audit
inside this workspace. It never overwrites its source or an existing output.

Format references:
[Khronos glTF 2.0 specification](https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc),
[W3C PNG specification](https://www.w3.org/TR/png-3/).
