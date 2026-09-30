# Ash HQ01 normalization appendix — 2026-09-30

This appendix adds one derived asset. The frozen four-asset `handoff.json`, its
audits, README, normalizer implementation and 22 synthetic tests remain unchanged.

Raw input: `ArtSource/P08/Tripo/Ash/20260930-hq01/model.glb`, SHA256
`a6b3cd89e0d6521f519145c0e649535fdb8a81f8ca73be5295f692d1b65c1172`,
77,496,048 bytes. Its hash matches the completed generation receipt.

Derived output:
`ArtSource/P08/Tripo/Ash/20260930-hq01/derived/RB_Ash_HQ01_Normalized.glb`,
SHA256 `44dfe1fda54b5a708f6d6afa383c899f76ae7a40972aecd4921966a66d09eea5`,
77,496,044 bytes. Local technical asset ID: `RB_ASH_HQ01_20260930`.

`RB_ASH_HQ01_20260930.json` binds the source/output, full BIN bytes, semantic
JSON and all four accessors. All 13,586,201 decoded components are identical.
Geometry, transforms, topology, UVs, normals, material channels and embedded
images are preserved. Neutral technical names and local export-tool metadata
replace the supported provider metadata; no provider/task identifier remains in
JSON. The original model and its server task receipt were not rewritten.

The original 8192×8192 JPEG, 4096×4096 JPEG and 4096×4096 PNG retain exact bytes.
The JPEGs contain ordinary FFE0/JFIF metadata. No copyright/license notice was
found in the JSON or inspected conventional image metadata. This pass does not
establish rights, assign authorship, inspect/remove pixel steganography or change
texture pixels. Runtime resizing/LOD preparation and rendered concept review
remain separate steps. The asset is still visually and production unaccepted.

`ash-hq01-append-handoff.json` binds only the three new outputs. Stage those and
the append handoff; its protected raw input and the base handoff are evidence
inputs, not modifications.
