# Garage V7 — explicit triangle export; native verification pending

V5 source and its exported/reimported Blender FBX passed the triangle UV audit,
but root's actual Unity import found 24 collapsed UV0 triangles. Merely enabling
FBX `use_triangles` in V6 still produced 22, and disabling Unity vertex welding
did not resolve them. Blender roundtrip proof therefore cannot substitute for
the native Unity gate.

V7 creates each mesh from V5's already-audited `mesh.loop_triangles` stream.
It copies the exact original vertex coordinates, triangle ordering, per-corner
UV0 and LightmapUV values, material assignments, smooth flags and object
transforms. Exporter triangulation and modifiers are disabled; all source
polygons are already triangles. There are still 180 meshes and 165,812 triangles
(132,592 / 28,712 / 4,508 across the three LODs). Geometry, materials, textures,
lighting and concept versions were not redesigned.

The source preservation receipt confirms exact positions, UV float32 values,
triangle indices, materials and transforms. Corner normals were supplied to
Blender's custom-normal encoder; they are **not bit exact**. On 142 meshes the
encoding differs from V5, with maximum component deviation 0.000554904342 and
maximum angular deviation 0.0346907223 degrees. This deviation is explicitly
retained in the report, not described as perfect normal preservation.

The explicit FBX roundtrip preserves every mesh's triangle order (allowing only
cyclic corner order), material assignments and per-corner UV float32 values.
It reports zero physical or UV-area failures. Maximum world-position deviation
is 0.000001192093 metres; maximum normal angular deviation from the V7 source
is 0.0390054506 degrees. Native Unity verification remains required.

`delivery.json` binds the staged FBX, new editable source, scripts and receipts
to hashes. V5 remains untouched, and the protected Club hash still matches.
Only the assigned direct Blender MCP on port 9877 was used; no Assets files or
Unity state were changed by this task. The first safe-mode rejection for an
unused `struct` import is preserved as `exact-source-mcp.json`; the corrected
script uses exact finite float representations without weakening safe mode.

This is a structural export repair, **not visual acceptance or a claim of
100% concept fidelity**. Root owns the native probe and subsequent rendered
comparison. V5 materials are unchanged, including the baseline rough floor;
the separate coated-floor comparison is not substituted.
