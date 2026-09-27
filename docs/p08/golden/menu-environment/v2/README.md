# Menu V2 — targeted material partition; native verification pending

**Subsequent causal control:** root reimported the same frozen V1 FBX with
`generateSecondaryUV=false`; both original stones then resolved their correct
Canyon_Cliff03/Canyon_Sandstone slots. See
`../v1/native-no-secondary-uv-control.txt` and the preserved failed importer
metadata. This identifies Unity's failed automatic lightmap unwrap as the
material-fallback cause. V2 remains a preserved compatibility variant and is
not required to correct that cause. Realtime-menu import policy can explicitly
disable baked-GI contribution/secondary generation while retaining strict UV0.

V1 native Unity import reported default URP Lit on slot0 of exactly
`Menu_L0_EdgeStone_12` and`Menu_L0_EdgeStone_13`. The failed V1 source/export and
native receipt are preserved. Blender inspection found no missing assignment:
both had DATA slots Canyon_Cliff03/Canyon_Sandstone with1468/1600 polygons at
indices0/1. Independent binary FBX inspection confirms the same two material
connections and valid ByPolygon indices, identical to successful stone11.
Therefore this is **not established as a bad Blender assignment**.

Root additionally observed two Unity secondary-UV packing warnings during V1
import. A separate no-secondary-UV control is appropriate for this realtime
menu, which does not request baked GI. That native causal test belongs to root;
this source variant does not prove its outcome.

V2 splits only the two affected LOD0 meshes by their existing material into two
single-material renderers each. It preserves every triangle, coordinate, UV and
material identity, with measured custom-normal re-encoding deviation recorded.
Unused vertices are removed from each partition. No fallback material is added.
Other geometry, materials, LODs and composition remain unchanged.

There are now139 module groups,419 renderers and the same1,938,935 triangles.
The module maps explicitly list both new LOD0 renderers for the two stone
modules; their lower LOD paths remain unchanged. Source physical/UV/frontface
gates pass. Strengthened FBX roundtrip checks every slot in order, each polygon
index, valid ranges, exact renderer/triangle coverage and physical/UV areas:
zero failures. The old roundtrip checked used per-polygon material identities
but omitted explicit whole-slot-table equality; V2 closes that evidence gap.

`delivery.json` binds the published files and proofs. `menu_publish_v2.py`
refuses different existing destination bytes and preserves V1. Actual Unity
material/UV import and rendered concept fidelity remain unaccepted until root
records them. The dedicated menu geometry still has the visual differences
documented under V1; a material-partition change does not close those differences.
