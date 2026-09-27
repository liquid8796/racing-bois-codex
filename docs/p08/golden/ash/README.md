# Ash v2 authoring attempt — rejected

The actual current character **does not meet the inspected concept or the requested quality**. It must not become a golden sample or be multiplied across the roster. The candidate is isolated; no production prefab, gameplay ID, production-content mask or original asset was replaced.

## Actual execution and visual result

The recipe was executed through the pinned Blender MCP server in the task-owned Blender 5.2.1 LTS instance, after an explicit writer lease. Initial scene inspection confirmed the saved Apex model; a separate `scene-before-ash.blend` preserves that state. Existing P06 source was opened with scripts disabled only to retain the generic 15-bone rig. Its old character geometry was removed from the working scene and not used as the new visual mesh.

The first rendered candidate failed: protruding eyes and facial pieces, spiky hair, angular straps, floating amber panels, cylindrical sleeves, simple boots, overly smooth face. Its LOD0 cost was 207,602 triangles. The second correction recessed the eyes, adjusted face pieces and straps, narrowed the sleeves, projected garment panels and reduced the mesh to 114,676 triangles. **The second render still fails.** It remains a mannequin-like procedural character, with thin detached-looking facial features and penetrating garment patches. Lower triangle count and normalized weights do not fix those visual failures.

- First rejection evidence: `iteration-01-rejected-body.png` and `iteration-01-rejected-face.png`.
- Current second rejection evidence: `ash-preview-body.png` and `ash-preview-face.png`.
- Actual saved candidate: `ArtSource/P08/Golden/Ash/RB_Golden_Ash.blend`.
- Actual candidate export: `Assets/RacingBois/Art/P08/Golden/Ash/RB_Golden_Ash.fbx`.

The first execution failed at Edit-mode context immediately after opening another `.blend` in the same MCP operation. Loading the trusted rig and authoring in separate operations resolved that execution issue. This is not a visual-quality fix.

## Technical observations, not acceptance

Current three LODs contain **114,676 / 52,749 / 20,641 triangles** and twelve material slots. Source audit found zero degenerate geometric triangles and zero vertices with invalid weight sums, with at most three active influences. The meshes contain **68 / 55 / 27 nonmanifold edges**, including thin strip details; these require classification or correction before any production use. UV channels are finite but useful texel distribution and nonoverlap have not been accepted.

The 15 old bone paths are preserved. Existing twelve clip files are available, but no claim is made that the new model's deformation or grip/seat/foot contacts are correct. Actual expression shapes exist; final portraits are intentionally not promoted from a rejected face. The portrait recipe is prepared but has not run.

Original procedural texture maps were authored locally; no concept pixels or original-game assets were pasted into them. This proves provenance, not quality. Surface resolution or compressed file size does not make the character production-ready.

## Required change of approach

Use a coherent anatomical sculpt or generated anatomical base followed by deliberate topology/garment construction, face/hand sculpting, material work, rig deformation and actual contact checks. The current primitive-driven recipe should not be reused as the roster foundation. Any external generator must first be checked for availability and the selected inputs/outputs documented; no external generation or upload was performed during this attempt.

The isolated Unity descriptor, if present, binds exact failed-candidate inputs for diagnostic inspection only; it does not overturn this rejection. Unity import, native performance, all twelve clip contacts and final portrait acceptance remain unperformed.
