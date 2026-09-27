# Spark V1 export candidate — visual acceptance remains open

The pinned hero and side images, the existing `04-quarter.png` / `04-side.png`, and fresh `05-export-lod0-quarter.png` / `05-export-lod2-quarter.png` were opened and inspected. The hero remains the design master. The side image is an uncalibrated supporting reference; neither its perspective nor a different studio background is used as evidence of a geometric measurement.

Hero SHA256: `e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6`. Side SHA256: `ad5478c942350462a34d12b1ba9f9714cb00a595ff9465bc1d000cf6b5e7ad0b`.

## Actual corresponding-view observations

| Component | Reference versus actual LOD0 quarter/side render | Gate |
| --- | --- | --- |
| Overall family | Copper classic naked bike, finned engine, twin shocks, round lamp/dials and same-flank chain plus stacked silencers are present. Presence alone does not establish matching proportions or details. | Not accepted |
| Tank | The reference has a flatter lower profile, more tapered teardrop shoulders and a carefully bounded cream inset. The candidate is rounder and taller at the rear shoulder; the cream mask and fine boundary differ visibly. | Not accepted |
| Saddle | The reference has distinct dark brown padded sections, fine stitching, piping and a passenger strap. The candidate has a broad light-brown ribbed surface; strap/stitching and rear transition differ or are not resolved in the inspected quarter view. | Not accepted |
| Engine | The candidate's flat stacked fins and large rectangular blocks lack the reference's rounded twin-cylinder castings, local covers, connectors and varied metal response. The round crankcase caps are much simpler. | Not accepted |
| Exhaust | Twin silencers and the forward collector exist. Curvature, connections, clamps, shield openings and satin/heat variation still differ. | Not accepted |
| Wheels/brakes | Cast spokes and perforated discs exist, but the spoke profiles, hub depth, caliper structure and rotor thickness/detail differ. Tire sidewall lettering and subtle surface detail are absent. | Not accepted |
| Cockpit/lamp | Twin instruments, mirrors and lamp exist. Brackets, controls, cable routing and lamp/reflector depth remain simplified. | Not accepted |
| Finish | Copper, cream, leather, black structure and metal families are present. Their gloss, grain, shade and local material separation do not yet match the concept. Studio illumination also differs, so this is an observed appearance gap rather than a measured BRDF diagnosis. | Not accepted |

The LOD2 render is intentionally shown at the same close camera as LOD0 to expose reduction artifacts. It shows faceting on mirrors/headlamp, lost tread, and strong shading artifacts around perforated discs and exhaust shields. This close stress view does not establish whether the configured screen-height transitions are acceptable. Unity distance/transition captures and native performance remain required.

## Verified export work

The pinned direct Blender MCP server at commit `6f992ffbca3cb715d111fc640b737b808632273c`, addon protocol 7 and Blender 5.2.1 LTS were used with safe mode enabled. Only task-owned Blender PID 17856 / custom port 9879 was edited. Loading the old saved source also started the addon's stored default listener on 9876 in that same process; no other Blender scene was used. The first audit script was rejected for a lambda, with no execution; it was rewritten using an ordinary named function while safe mode stayed enabled. The rejected receipt is retained.

The initial real FBX roundtrip caught 36 lost triangles in `Spark_L2_Body`. These were 36 isolated dial ticks/needles reduced to two coincident opposite triangles with the same three vertices. Edge-manifold checks alone had missed this zero-thickness condition. The initial failure, detailed diagnosis and original assembled source are retained.

`spark_v1_repair_lod2_gauges.py` restores each of those measured components as a closed 0.4 mm triangular prism. It checks their exact count, material and gauge-region bounds before editing. It saves a separate `RB_Golden_Spark_v1_export.blend`; the original assembled source, editable source, LOD0 and LOD1 remain preserved. Final source checks now explicitly reject duplicate-index faces as well as non-manifold edges, loose vertices, non-finite values, physically collapsed triangles and degenerate UV triangles.

Final LOD triangle totals are **124,828 / 70,574 / 27,252**. All nine FBX renderers preserve exact triangle counts, material-slot lists and parents. The maximum bidirectional world-vertex difference after Blender reimport is **0.000000240274 m**; all 13 empty/root/axle/contact markers remain within the 0.00001 m check tolerance. No physical or UV triangle failures were observed. These are geometric export checks, not a concept-fidelity score or Unity acceptance.

## Explicit Unity prerequisites

The descriptor and `staged-delivery.json` bind 37 files in `_local/p08-spark-v1-staging` to their intended `Assets/RacingBois/Art/P08/Golden/Spark/V1` destinations. This export task has not copied files into Unity Assets or invoked Unity MCP. The descriptor therefore becomes resolvable only after the root-owned exact-hash copy.

Twenty-two runtime maps are intentionally constant 4×4 fields. `constant-map-declarations.json` records their exact hashes, modes and decoded constant channel values. Their source/staged bytes are identical. The existing importer rejects dimensions below 256; no maps were enlarged and no importer check was weakened here. An explicit constant-map contract is a prerequisite.

The current descriptor cannot reproduce Blender's Copper/Cream clearcoat or Lens transmission/IOR exactly. Its Lens alpha 0.18 is an unverified URP preview trial, clearly recorded in `staged-delivery.json`. Actual Unity shading and transparency must be compared with the reference; this candidate remains unaccepted even after structural import passes.

The protected Club, locked concept/prompt files, Apex sources and `VehicleDimensions.cs` all match the original `before-manifest.json` hashes. No Jarvis MCP, paid service, downloaded geometry, canonical physics change, production mask change, commit or push was performed by this delegated export task.

## Reproduction and receipts

Run only in an isolated task-owned Blender session. `spark_v1_export_preflight.py` loads the original assembled Spark. Run the bounded gauge repair, then `spark_v1_audit_export.py` and `spark_v1_roundtrip.py` through `tools/blender/mcp_client.py --port <owned-port>`. The roundtrip reports `passed` inside its JSON because the addon discards captured stdout when Python raises; `spark_v1_prepare_descriptor.py` explicitly requires the final source and roundtrip receipts to pass before staging.

The checked-in preflight/generator is bound to the numbered final receipts in this directory. A later revision must create fresh receipts and intentionally update those bindings, rather than silently overwrite earlier failed evidence. `source-audit-final.json`, `fbx-roundtrip-final.json`, `staged-delivery.json` and the actual MCP receipts contain the machine-readable evidence. The two `05-export-*` images are fresh CPU Cycles renders of the final source, not the imported Unity asset.
