# Ash V3 — contact and material candidate, unaccepted

V3 continues the licensed anatomical V2 candidate. It is **not accepted for
production** and does not match the locked Ash 2D concept 100%. Technical
checks and contact distances do not establish that visual requirement.

The locked reference remains `ArtSource/Concepts/P08/Golden/ash-v2.png`, SHA256
`6fa1090e13547df14e578f0ac77504ae5722d99a031a09e5f575c2775f9ce7e6`.
V2 provenance and CC0 static data licenses remain applicable; V3 does not
claim that the anatomical topology was made from scratch. No addon was
registered or executed. All DCC operations used the direct pinned Blender
MCP server with safe mode enabled. No Jarvis MCP or paid service was used.

## Actual changes

- The source is a separate V3 `.blend`; frozen V2 source, FBX and texture files
  were preserved. The protected user Club file was also preserved.
- A read-only import of the actual Apex V8/R2 FBX supplies seat, grip and peg
  markers. The reference bike is excluded from the exported rider FBX. Bike
  material appearances in these DCC contact views are not a fidelity review
  of the native Unity bike materials.
- Anatomical palm orientation replaces the arbitrary global hand axis.
  Four fingers wrap a finite grip cylinder using their actual phalanx lengths;
  the thumb uses a bounded opposition solve. These transforms are baked into
  the 45-bone actor's own 12 clips, retaining semantic bone and clip names.
- Hip/ankle targets account for actual posed garment and rubber sole surfaces.
  Lean moves the torso while retaining grip and peg targets.
- BootLeather and Rubber UV islands were repacked on LOD0 and transferred to
  their matching loops on LOD1/2. The operation asserts that unrelated LOD0
  material UVs remain unchanged. Eight PBR maps were rebaked for these two
  roles, including a continuous boot-to-sole color transition. Other materials
  reuse the exact frozen V2 maps. File images are explicitly decoded after
  reload and packed before the final source save.

## Evidence and limits

`descriptor-bind.json` identifies exact source, FBX, concept and map hashes.
It requests explicit bind rest restoration, following the actual Unity
Generic import behavior discovered in V2. Source standing dimensions must
not be widened to accept a default seated animation pose.

`runtime-audit.json` checks all three LOD meshes, normalized skin weights,
finite UVs and five deformation samples for each of the twelve real clips.
`actual-contact-rays.json` and `contact-summary.json` measure the evaluated
LOD0 skin against actual imported contact markers and physical seat geometry.
They are sparse surface diagnostics, not a complete collision test. The
historical `contact-*.png`, `private-*` and `boot-flat-bake.png` images show
intermediate investigations; the `authored-*` images are sampled from the
actual keyed clips.

Remaining visual differences are substantial: facial likeness and skin tone,
hair volume/strand treatment, helmet hardware/weathering, continuous tailored
ochre panels, seam placement, leather grain/wear, garment fit, boot shape and
stitched construction. Some glove pad deformation and tiny boot seam artifacts
still need review. No fabricated similarity percentage is assigned, no full
roster is derived from this candidate, and no gameplay asset is silently
promoted by these technical diagnostics.
