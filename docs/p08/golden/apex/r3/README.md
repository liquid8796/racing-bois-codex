# Apex R3 — staged structural candidate, visual acceptance still failed

The locked `apex-v2.png` concept and actual R2 native front/side/quarter views were inspected before this revision. R3 retains useful R2 mechanical parts while replacing the tank, tail skins, fairing/duct surfaces, optical housings, screen and mirrors. It preserves the canonical 1.43m wheelbase, approximately 0.63m tyres, 0.82m saddle and existing measured grip/foot contacts. It does not use a rejected mesh as the visual master.

## Concrete changes

- One main projector per recessed dark housing, with a compound cover and physically separate enclosure. The lens-off diagnostic proved the pale region was cover reflection rather than a white cavity. Actual cover highlights still differ from the concept.
- A tank with held shoulder creases and deliberate front sections; an enclosed rear subframe region and repositioned visible rear LED; a screen seated on the cowl with forward-convex curvature.
- White/black lower fairing boundaries share actual control points. The panel has two real openings. Its final constrained triangulation explicitly verifies one outer boundary and two separate hole loops before adding wall thickness. Interior skins use the shared graphite finish with explicit outward orientation.
- Active UV names are normalized before joining, preserving authored values. Blender otherwise joins different names as separate partially empty channels. Small cap charts are repaired locally; repeating finish UV overlap is intentional and is not a claim of unique decal UVs.
- Three LODs, with only collapsed tiny disconnected LOD2 fragments removed. The cleanup refuses broken main panels or removal exceeding 10% of a group's faces. The real drilled-rotor experiment was not retained; current mechanical parts use the R2 foundation.

## Verified artifact scope

`handoff-manifest.json` binds the saved editable/assembled sources, staged FBX, unchanged R2 PBR maps, locked concept/review and authoring recipes. No R3 asset was written into Assets by this task. Root can run `python tools/p08/golden/apex_r3_manifest.py --publish` when Unity is ready; it refuses to overwrite a different published candidate and then creates `descriptor.json`.

| Check | Actual result |
|---|---|
| LOD0 / LOD1 / LOD2 triangles | 83,380 / 41,690 / 16,278 |
| Renderers | 9: body/front wheel/rear wheel at each LOD |
| Material roles | 9, exact original names |
| Physical triangles with cross squared <= 1e-16 | 0 across all LODs |
| Non-manifold edges | 0 across all LODs |
| Degenerate UV triangles | 0 across all LODs |
| Actual FBX roundtrip | All 9 renderer names and per-mesh triangle counts exactly preserved |
| Minimum roundtrip world cross squared | 5.399415810376833e-15 |
| Size in metres | 0.76632 × 1.12970 × 2.06339 |

FBX SHA256: `44452d79168f486edb1d8f0db10879deda0a4a8be7b36e8f24d4bc936e67e335`.

Authoritative structural evidence: `assemble-final-clean-3-mcp.json`, `audit-final-clean-mcp.json`, `export-staged-final-mcp.json`, `roundtrip-final-mcp.json`. Earlier Boolean/LOD failures remain as rejected diagnostic evidence, including `_local/p08-apex-r3-staging/rejected-initial-topology.fbx`; do not use them as current outputs.

## Visual review and remaining gaps

The final assembly was rendered from quarter, front, side and rear views and at all three LODs. Actual outputs are `beauty-final.png`, `front-final.png`, `side-final.png`, `rear-final.png`, `lod1-final.png`, and `lod2-final.png`. The long six-image MCP call lost its completion response (`No data received`) after writing the images. A fresh `render-postcheck-mcp.json` confirmed the final path and restored LOD0 visibility. A separate bounded LOD2 render is recorded in `render-lod2-confirm-mcp.json`; transport failure is not relabelled a passed batch call.

**This candidate does not match the concept 100%.** The tank/tail proportions and skin transitions still differ, the head cover reflection can obscure a projector in quarter view, side-light rim shading is uneven, and the retained mechanical parts/material wear remain simplified. LOD2 visibly loses small rotor/fin details; native transitions and gameplay distance need checking. Mesh/UV/roundtrip results do not waive these differences. Native Unity material/axis verification, actual frame/memory measurement, final prefab acceptance and production promotion remain root-owned work.

Source iteration snapshots and failed approaches are preserved. The protected user `RB_Club.blend` hash remains `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`. Only direct task-owned Blender9878 was used, safe mode enabled, CPU renders capped at four threads. No Jarvis, paid service, new local-model trial, OCI mutation or production mask change occurred.

Constrained triangulation follows the installed Blender geometry API and its [official reference](https://docs.blender.org/api/5.1/mathutils.geometry.html#mathutils.geometry.delaunay_2d_cdt); the saved source and executable manifold checks, rather than that documentation alone, establish the reported topology.
