# Ash golden-sample character

Status: two actual MCP authoring/render iterations completed on 2026-09-27. Both are visually rejected; see `README.md`. This plan remains the intended acceptance scope, not completed acceptance.

The actual v2 image was inspected after the root clearance: `ArtSource/Concepts/P08/Golden/ash-v2.png`, SHA-256 `6fa1090e13547df14e578f0ac77504ae5722d99a031a09e5f575c2775f9ce7e6`. Accepted features are recorded in `ash-v2-review.md`: tan adult man, natural face/profile, charcoal and amber sewn leather, riding trousers, articulated gloves/brown boots, ivory open-face shell/lining/strap and goggles raised above the eyes.

`tools/p08/golden/ash_model.py` constructs an isolated candidate. Original surface maps are prepared by `ash_textures.py`; concept pixels are never copied into them. `ash_render.py`, `ash_portraits.py`, `ash_audit.py` and `ash_descriptor.py` provide actual-render and exact-input handoff operations. Python syntax and the pinned MCP safe-mode validator pass. Actual source and export now exist, with a diagnostic descriptor binding their hashes. Neither the descriptor nor structural observations establish quality. Final portraits and animation contacts were not accepted after the actual visual rejection.

## Scope and evidence

Replace the visual construction of the rejected segmented rider with one reviewable original character. Preserve existing production files, semantic character ID `rb-ash`, and the user's Club source. Candidate outputs live under `ArtSource/P08/Golden/Ash/` and `Assets/RacingBois/Art/P08/Golden/Ash/`; they do not automatically replace the shipping prefab.

The 2026-09-26 review found cylindrical limbs, disconnected-looking shoulders, mitten-like hands, an egg-shaped helmet and inadequate garment/anatomy detail. Those are silhouette and construction failures; higher texture resolution or more polygons alone does not solve them.

## Construction and surface plan

- Anatomical proportions come from the inspected v2 construction sheet and a measured metre-scale specification. A coherent connected jacket surface must include the shoulder-to-sleeve junction and elbow loops. Trousers must connect at the pelvis/crotch with knee loops. Separate actual clothing layers, armor and fasteners remain separate where physically appropriate.
- The adult head needs continuous facial planes: jaw, chin, cheek, brow, nose, lips and eyelids. Eyes sit inside sockets; ears have a visible helix and inner fold. Hair follows scalp volume. Helmet shell thickness, cheek/neck lining, straps and raised goggles are constructed parts rather than an opaque egg over a face.
- Gloves need palm volume and distinct thumb/finger anatomy. Boots need heel, instep, toe box, upper and sole construction. Cloth seams, leather panels and folds must describe construction and bending, rather than evenly spaced decorative pipes.
- Allocate useful unique UV space to face, garment and hands. Original authored base color, normal and roughness/metallic maps distinguish skin, woven cloth, leather, painted shell, rubber and metal. Keep skin and cloth nonmetallic. Avoid sixteen tiny atlas tiles stretched over an entire close-up character.
- Produce three LODs after the base character is visually acceptable. Preserve face silhouette, hands and deformation loops at near distance; remove small hardware before destroying the main forms.

## Existing animation contract to verify

The P06 rig has 15 deform bones under `RB_P06_Rider_Rig` with prefix `RB_P06_Rider_L0_`: Hip, Torso, Head, and bilateral UpperArm, Forearm, Hand, Thigh, Shin and Foot. Existing clips bind to these paths. Their names are `RB_Ride`, `RB_LeanLeft`, `RB_LeanRight`, `RB_AttackLeft`, `RB_AttackRight`, `RB_KickLeft`, `RB_KickRight`, `RB_Hit`, `RB_Fall`, `RB_Run`, `RB_Remount`, `RB_Idle`.

Rest joints use the existing metric locations to allow comparison, not as a claim that the old poses are correct. The rig has no finger or jaw bones. Facial expression shapes can be authored on the mesh; grip fingers require an authored closed hand shape or an explicit later rig extension. Do not silently promise finger articulation from this skeleton.

## Acceptance sequence

1. Root supplies the generated v2 construction sheet. Inspect it, record file hash and resolve ambiguous construction before writing geometry.
2. Build a candidate using Blender MCP only during the granted exclusive writer lease. Save isolated source, export and exact recipe. No old assets deleted or overwritten.
3. Inspect neutral front/side/rear and close-up head/hands, plus full body under neutral lighting. If it still reads as primitive/toy, mark failed and correct it before promotion.
4. Verify scale/root, normals, topology, triangle budgets, nonoverlapping UVs, normalized weights, material maps and three LODs on the exact saved revision.
5. Sample all twelve existing clips; inspect shoulders, hips and elbows and actual grip/seat/peg contacts with the new Apex. A structurally valid rig is not animation acceptance.
6. Render actual Neutral/Happy/Focused portrait images from the same model, restore neutral state and hash source/export/portraits.
7. Root imports the candidate and runs Unity visual, material, deformation, collider/prefab, camera-distance and runtime checks. Blender renders and static file audits do not establish production readiness.

No visual, rig, UV, performance or production PASS is claimed by this plan.
