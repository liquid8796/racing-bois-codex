# Apex R6 checkpoint26 — unaccepted source study

This is a bounded Blender source study against the unchanged locked `ArtSource/Concepts/P08/Golden/apex-v2.png` (SHA256 `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`). It is not a production handoff or a claim of matching the concept. Root requested a freeze after the current render for fresh independent review.

## Exact resume state

Open `ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_checkpoint26_review.blend`. It preserves checkpoint26 geometry, materials, current quarter review camera and studio state after the completed render. The owned Blender5.2.1LTS instance remains on port9878 / PID32112, root `RB_Golden_Apex_r6`, with source clean and script auto-execution disabled. No render is still running. Parent task owns the decision to resume or replace this scene; port9877 belongs to the Canyon task.

Final comparison renders are `26-front.png` and `26-quarter.png` in this directory. Both are actual Cycles CPU renders at1280x900,24samples,4threads. The quarter camera matches the R5 review camera; front is an additional diagnostic view without a matched R5 Blender camera. No fresh checkpoint26 side/rear render was made. Earlier side views describe earlier geometry only. The right-side quarter exposes the vehicle-right mechanical side; the concept's large chain-side view is vehicle-left and needs a corresponding left-side comparison before accepting mechanical detail.

## Changes and actual observations

- Fairing05 added a held shoulder/lower planes and a recessed front return while preserving the R5 repaired belly clearance. It is frozen independently in `fairing-study05-handoff.json`. It remains a broad, relatively flat white shell compared with the wrapped, multi-plane concept.
- Infill10 added four small seat/tank side panels. Their fit and silhouette remain tentative: a pointed panel edge and an existing protruding fastener are still visible. These are not validated seat/body improvements.
- Cowl20 lowered the optical assembly and increased the screen's visible height. Front improved, but quarter revealed an excessively upright screen. Cowl22's added cheeks produced pointed lamp-corner wings and are retained as a rejected intermediate.
- Cowl24 reduced the lamp surround and fitted lower cheeks to actual fairing points. It revealed old collar/centre-blade discontinuities. The read-only ray diagnosis in `cowl24-rays.json` identifies the old collar and real holes beside the blade; it is not an image-only explanation.
- Cowl25 replaces that centre/collar with closed surfaces matched to actual optical edges and sweeps the existing screen rearward. Front no longer has the previous floating white shards/holes. Quarter exposed detached mirror feet after the rake change.
- Cowl26 connects the upper optical shoulder to the screen support and reattaches the mirror feet. Actual quarter now shows continuous white upper shell and attached feet. The mirror stems have become steeper; this new placement still requires concept review. The screen remains very dark, the lamp unit still reads as a distinct goggle-like assembly, and the broad exposed radiator/fork opening and heavy fairing/belly silhouette remain visibly different from the concept. These limitations prevent visual acceptance.

All01/02/03/04/05/10/20/22/24/25/26 source checkpoints, renders and receipts are retained. Some prepared render scripts were never executed; only existing PNGs with corresponding completed MCP receipts are rendered evidence. Geometry and material changes were authored locally through the direct pinned Blender MCP server in safe mode. No paid service, Jarvis, Unity call, Assets export, LOD rebuild or promotion was used.

## Limited technical observations

`audit26.json` inspected101 edited-system meshes and compared542 other mesh signatures to the saved R5 source. Those542 signatures and both wheel transforms were unchanged. The ten scoped belly pair checks report zero overlapping triangle pairs. This does not establish whole-bike clearance, smooth seams, steering/rider contacts or FBX/native validity.

The audit deliberately remains failed: the two tentative seat-to-tank bridge meshes contain3 triangles at or below the existing Unity degeneracy threshold (2left,1right). All101 observed meshes are manifold and have no zero-area UV triangles under this check. No repair was attempted after the requested freeze. LODs, FBX roundtrip, Unity materials, animations and native reference review are pending.

`preservation-after26.json` rechecks all162 files bound by `preserved-inputs-before.json`: locked reference, all prior R5 artifacts, R4 texture inputs, protected Club, unowned AshV7R2 and original font files are unchanged. The final source/state/render/input inventory is bound in `checkpoint26-handoff.json`.
