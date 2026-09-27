# Ash V7 UV import diagnosis and triangulated export control

This is an isolated diagnostic continuation, not a new accepted character.
The locked Ash concept, frozen V7 source, original FBX, all textures and the
protected Club source remain unchanged. Root owns Unity operations. This work
uses only the pinned direct Blender MCP with safe mode enabled and local data.

## Observed failure

Unity reports 279 collapsed primary-UV triangles, 93 per LOD, in the new inner
collar facing. Its first failed LOD0 triangle is 51116, in material slot 5.
All 279 native triangles were mapped back to source polygons by actual vertex
positions (including the observed local-Z sign inversion), with a one-micrometre
matching bound. See `unity-collapsed-uv-triangles.json` and
`native-source-mapping.json`.

The first mapped source quad is polygon 110977, vertices
72886/72887/72896/72895. Its four source UV corners are distinct. Source vertex
72886 has UV `(0.631733239, 0.536803663)`, while Unity reports
`(0.631333232, 0.537203670)`, identical to the adjacent corner. Thus the native
failure is an actual UV-coordinate substitution, not a stricter threshold
merely rejecting an unchanged source triplet.

Read-only scans of both original V6 and V7 FBXs found no collapsed UV triplets,
including every three-corner combination within their nontriangle polygons.
The frozen V7 Blender mesh also passes the exact double-edge calculation used
by the Unity validator; its minimum LOD0 cross is approximately `7.694112e-11`,
above the unchanged `1e-14` gate. Mesh compression and secondary UV generation
are disabled. Root's exact-file welding control returns 279 failures with
`weldVertices=true`, 279 with `false`, and 279 after restoration. Welding is
therefore a rejected hypothesis. Root also disabled both mesh optimizations:
the result stayed 279; additionally disabling tangent generation produced 384,
and restoring CalculateMikk returned to 279. See
`unity-mesh-options-causal-control.json`. All importer flags were restored.
These controls do not identify the precise internal conversion algorithm.

## Separate triangulated export control — native failure retained

The installed Blender 5.2 FBX operator exposes `use_triangles`. A separate
export uses the frozen scene and identical export options with that option
enabled. No source geometry, UV, material, animation or texture was edited;
the frozen `.blend` was not saved. The diagnostic FBX is:

`_local/p08-ash-v7r1-staging/triangulated-diagnostic.fbx`

SHA256: `da8a56822b5c02d4512d060e954edab5a2e8d2710298b7b85c6fd5a74053c95b`.

`descriptor-control-staged.json` is outside Assets and must be rebound after
root copies the FBX into a fresh review location. Both the 12 gameplay clip
references and the separate MenuHero preview reference bind this export.
It does not promote availability masks or replace the original V7 descriptor.
Root's subsequent native import still failed on the collar UV, first at triangle
51117. Explicit triangulation alone therefore did not resolve the problem.
The triangulated control remains an unaccepted failed alternative.

The independent binary audits establish:

- 234,140 triangles, zero remaining nontriangle polygons and zero primary-UV
  failures; unchanged vertex coordinates.
- Every exported triangle belongs to one original polygon with identical
  vertex/UV-corner/material tuples. Each original polygon supplies exactly
  `n - 2` triangles.
- Exact connection-bound equality of 5,538 animation channels, 135 skin
  clusters with weights/bind transforms, six shape deltas and three ordered
  material-binding lists.

Blender assigns new numerical FBX object IDs between processes and gives its
temporary triangulation meshes a `.001` suffix. Absolute STRIP texture paths
also name the new export directory. The audit explicitly normalizes those
expected serialization differences. An initial raw-ID/order comparison was
unsuitable; its failed diagnostic report is retained. Semantic connection
checks close that comparison gap. Maps are still bound by their existing
descriptor hashes, not copied or rebaked by this operation.

The first export request was rejected before execution because the safe-mode
script imported `os`. The script was rewritten to use allowed Blender APIs,
with destination-existence preflight in the shell; safe mode was not disabled.
The successful request and the rejection are both retained.

## Fresh radius-only candidate — native technical import passed

After the failed controls, root authorized one bounded UV revision: expand
only the 70 inner-collar quads per LOD around their original patch centres,
from authored radius 0.0004 to 0.002. Exactly 280 loop UVs per LOD change by
the fivefold scale. `uv-radius-repair.json` checks exact source equality of
all geometry, shape coordinates, weights, materials, rest bones and all
13 actions before and after the edit; all non-collar UVs remain exact.

Fresh source: `ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend`,
SHA256 `2fc56084ea261c46109e49ad6d76f515665d7b22d3e11daa9785c51179d74d6b`.
Blender's native lossless compression produces 87,355,702 bytes. The first
uncompressed R1 save is preserved in ignored private staging. Original V7
source SHA256 remains `3981a210d2e79ca9d5a2aa4cb511e174b81cf49c1f50280b4e8322be1e601578`.
The first compression request used a reserved safe-mode variable name and was
rejected before execution; the corrected allowed request is retained alongside it.

Fresh FBX: `_local/p08-ash-v7r1-staging/RB_Golden_Ash_V7R1.fbx`,
SHA256 `61c66f057897fb58d0b89a402386e2b0581ea11c8b597bfe6442a6de18b694c9`.
It retains the original nontriangulated export policy to isolate the UV change.
`radius-candidate-audit.json` independently proves exact vertex/polygon data,
connection-bound equality of all 5,538 animation channels, 135 skin clusters,
six shape deltas and material ordering, plus the exact authorised UV changes.
All original material maps still match their pinned hashes.

`descriptor-radius-staged.json` binds the new source/FBX and all 13 clips.
Root published its exact FBX bytes into the fresh V7R1 Assets path and imported
`descriptor-radius.json`. The actual Unity receipt
[`import-6564375159dc4cda9d727e69a2951f27`](../../unity/import-6564375159dc4cda9d727e69a2951f27.json)
passes structural/UV/material/LOD/rig validation and all 13 clips, with source
binding stable, 47,556,769 sampled vertices and source fingerprint
`ac2cb2be00b5d3033421f62c2ec96c63811b7fea24d7d2f4960c039b943cef17`.
Triangle counts remain 142,973 / 70,234 / 20,933. That descriptor and prefab
retain the legacy `fallenRootOffset=-0.55` baseline.

This controlled result establishes that enlarging the specific collar UV patch
survives the current native importer and resolves its reported collapse. It
does not identify a precise internal Unity/FBX SDK algorithm. Welding, mesh
optimization and triangulation-only alternatives remain disproven remedies;
no mathematical threshold was relaxed.

The separate final `descriptor-ground-origin.json` selects
`fallenRootOffset=0` and a distinct ID `RB_Golden_Ash_V7R1_GroundOrigin`, preserving
the imported legacy-placement control prefab. Its source/FBX/maps/clips are the
same radius-only candidate. `handoff.json` binds both descriptors and the real
UV-control receipt. This explicit placement choice is not part of the UV-only
FBX proof; fresh compilation attestation and native import are still required
for the final descriptor. The inherited Fall clip's approximately -0.153 m
ground penetration at root zero remains unresolved.

The same patch is not spatially constant in every texture channel. The sampled
full-resolution bilinear comparison in `uv-sampling-options.json` records zero
stored BaseColor change, at most approximately 0.003/255 mask/AO change and
7.740054/255 normal-channel change for radius 0.002. Native compression, mip
selection and lighting are separate; no zero-visual-change claim is made.
Larger radii cross unrelated texture regions and were not authored.

## Ownership and acceptance

Spark's PID 17856 owns both ports 9879 and 9876; its saved scene auto-started the
extra listener. No mutation was sent to either port. Ash diagnosis uses its own
factory-started PID 16944 on port 9878, verified before loading the source.
The post-export scene and viewport were inspected; the viewport is a solid-mode
diagnostic view, not a concept-fidelity comparison.

The radius-only native technical gate passes, while the final ground-origin
descriptor awaits its own import. The V7 visual,
animation/ground-contact and performance gaps remain those recorded in
`../v7/README.md` and `../v7/fullbody-visual-review.md`. No threshold was weakened,
no source defect or engine cause was invented, and no visual acceptance is made.
