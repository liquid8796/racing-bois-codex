# Read-only accounting of the local Ash V7R2 save

The protected local `.blend` is **87,342,023 bytes**, SHA256
`6d689a5df0ddf9de97d249bd4f56fd8a4e7bba844af80fc44a11c54fd428dcd8`.
The adjacent `.blend1` is **87,335,715 bytes**, SHA256
`472b1c44108999a4fd634795885db3ccc7afbdc230e4fa7885b8e9bb97426bb0`.
That backup exactly matches the frozen V7R2 handoff, Git LFS HEAD pointer and
locally available LFS object. Neither file was overwritten, restored, opened in
Blender or exported by this audit. The author and intent of the local save are
unknown and are not inferred from its timestamp or differences.

Both streams use Blender 5.2's format-1 header and identical SDNA definitions.
The audit uses the installed official pure-Python header reader and bundled
zstandard module from standalone Python; it does not import `bpy` or start a
Blender process. All serialized field sizes sum exactly to their SDNA TLEN.

| Authored data checked | Result |
| --- | --- |
| 530 meshes | All owner-scoped attribute names, types, domains, storage/count/order, payload bytes and polygon offsets match; zero unresolved mesh pointers. This includes geometry, topology and UV/material-index data. |
| 218 authored ID groups | 13 actions, 62 materials, 135 images, armature, five Key groups, camera and world match full group bytes/address bindings after excluding only ID session/update counters. |
| Rig and animation records | 45 rest bones, 45 pose channels, 5,850 FCurves and 124,866 Bézier keys match. Only the explicitly identified pose-channel runtime session UID is excluded. |
| Skinning and modifiers | 374,426 deform vertices, 605,729 weights, 1,169 deform-group records and all checked modifier records match exactly. |

The initial raw-address comparison overstates content differences because
temporary attribute-storage addresses are reused in different owning IDs. The
owner-resolved attribute comparison handles that ambiguity explicitly; it does
not simply erase pointer bytes or infer geometry equality from block counts.
Implicit-sharing handles are excluded from the geometry payload comparison, so
storage-alias ownership itself is not claimed equivalent.

Observed non-content changes include session IDs and recalculation counters;
object `base_flag` low-bit changes for the floor versus rig/markers/root/skin;
the rig's `actcol` changing from 0 to 1; and saved workspace, screen, region,
properties-panel and view-layer data. Raw addresses of some editor graph nodes
were reused or reallocated, so complete name-resolved editor/view-layer pairing
remains outside this audit. Those nodes must not be described as fully identical
or their changed flags silently treated as harmless authoring intent.

The checked authored model data shows no mesh/UV, rig/weight, material/image or
action-content change. This supports making a **fresh owned copy of the current
save** for a new candidate while preserving both exact baselines. It does not
authorize overwriting the local save or assigning its new hash to old import,
floor, export or visual receipts. New candidates need their own source binding
and actual renders/native review. Existing visual differences from locked
`ash-v2.png` remain unaccepted.

Evidence: [raw blocks](block-comparison.json), [SDNA fields](field-differences.json),
[owner-resolved mesh attributes](mesh-attributes.json), and
[rig/weight/curve invariants](rig-weight-invariants.json). Scripts live under
`tools/p08/golden/ash_readonly_audit/` and refuse existing report outputs.
