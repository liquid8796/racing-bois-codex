# P06 original hero art

The 2D references were opened and visually inspected **before** their 3D recipes were authored. Production geometry and textures are newly authored; no original game meshes, sprites, textures or animations are loaded or projected into these assets.

| Asset | Concept | LOD triangles | Renderers per LOD |
|---|---|---:|---:|
| Amber cafe racer | `ArtSource/Concepts/P06/motorcycle-v1.png` | 14,668 / 6,442 / 2,396 | 3 |
| Helmeted rider | `ArtSource/Concepts/P06/rider-v1.png` | 11,442 / 5,488 / 2,282 | 1 |
| Traffic coupe | `ArtSource/Concepts/P03P04/coupe-concept-v1.png` | 5,600 / 2,396 / 898 | 1 |
| Traffic van | `ArtSource/Concepts/P03P04/van-concept-v1.png` | 5,588 / 2,382 / 886 | 1 |
| Patrol motorcycle | `ArtSource/Concepts/P06/patrol-v1.png` | 16,210 / 7,118 / 2,682 | 3 |
| Patrol rider palette variant | `ArtSource/Concepts/P06/patrol-v1.png` | 11,442 / 5,488 / 2,282 (shared rider mesh) | 1 |

This is five FBX exports and six prefab variants. The patrol motorcycle adds panniers, fairing and beacon to the new motorcycle design; the patrol rider shares the original P06 rider geometry/rig/clips. These variants are not presented as six independent base designs. Both traffic vehicles share one atlas/material; the patrol rider has a distinct Base Color but shares the byte-identical rider normal, metallic-smoothness and roughness maps.

## Source and workflow

Authoring sources: `ArtSource/P06/Hero/*.blend`. Reproducible recipes: `tools/p06/hero/common.py` plus the asset-specific `create_*.py`. They are composed into a literal script on the host using `compose.py`, then executed through the pinned **real Blender MCP** stdio server and the task-owned Blender add-on at port 9876. Blender safe mode stays enabled. No dynamic `exec`, file reads, shell/network access, or headless-export substitution is used inside Blender.

The initial composition using `exec()` was rejected by the MCP safe-mode guard. It was rewritten into literal allowed Python, and subsequent authoring receipts show successful Blender operators. Another guard rejected an indirect callable; the recipe was rewritten as explicit named-function dispatch. Neither rejection was bypassed by disabling the guard.

Example (only after obtaining the shared Blender slot):

```powershell
python tools/p06/hero/compose.py motorcycle
& .\_local\blender-env\Scripts\python.exe tools/blender/mcp_client.py execute_blender_code --code-file _local/p06-motorcycle-recipe.py --receipt docs/p06/hero/motorcycle-mcp.json
```

Every authoring scene reset first saves the live task scene to `_local/p06-before-<asset>.blend`. The pre-existing user-modified `ArtSource/Weapons/RB_Club.blend` is untouched. The final read-only audit opens each saved hero `.blend` with script execution disabled and never saves or exports it. After the earlier task-owned Blender process had exited, `tools/blender/start-blender.ps1` restored the loopback bridge; the final source audit and postcheck then passed with safe mode enabled.

## Geometry, surface and import contract

- Meters, identity prefab root; preserved FBX model conversion plus Y 180 degrees makes gameplay forward **+Z**. Motorcycle wheel centers are `(0, .32, .80)` and `(0, .32, -.73)`; wheel radius `.322m`. Body and each wheel are consolidated to one mesh per LOD.
- One PBR atlas per hero: 1024 Base Color, 512 tangent normal / metallic-smoothness / roughness. Atlas texels are procedural material microdetail, not image projections. Distinct tiles separate paint, rubber, leather, metal and glass. Repeated surface components and LODs intentionally reuse material tiles.
- Final topology is triangulated before smart unwrapping. Rare folded thin bevel triangles are isolated in a reserved strip of their material tile. Independent positive-area triangle intersection checks verify no unintended overlap within each connected surface. Thin collapsed details are removed from distant LODs.
- Blender QA checks closed/manifold components, consistent outward winding, positive component volume, zero degenerate faces/loose vertices, UV bounds and positive UV triangle area. All **27 meshes across five saved exports** pass the final independent audit, including traffic wheel arches and patrol equipment. Material tile reuse between disconnected parts is intentional and explicitly excluded from the within-component overlap gate.
- `P06HeroAssetBuilder.Setup()` creates URP/Lit materials, WebGL DXT5 compressed mipmapped textures, Mikk tangents, non-readable low-compression meshes, dynamic probe lighting and one primitive collider per prefab. Dynamic vehicles/characters intentionally have no baked lightmap UV2 or Static flags.
- Prefabs are written only under `Assets/RacingBois/Prefabs/P06/`; previous phase sources and prefabs remain separate.

## Skinned rider and clips

One armature, 15 deform bones, one skinned renderer per LOD, normalized weights with at most **two influences per vertex**. The continuous sleeve/leg meshes blend across elbows and knees. Helmet, glove and armor details share the same consolidated skin. The Generic rig exposes the hand transforms for runtime weapon attachments; it does not claim Humanoid retargeting.

Bone prefix: `RB_P06_Rider_L0_`, with `Hip`, `Torso`, `Head`, `UpperArm_L/R`, `Forearm_L/R`, `Hand_L/R`, `Thigh_L/R`, `Shin_L/R`, `Foot_L/R`. The armature object is `RB_P06_Rider_Rig`.

| Clip | Frames at 30Hz | Loop |
|---|---|---|
| RB_Idle, RB_Ride, RB_LeanLeft, RB_LeanRight | 1–31 | Yes |
| RB_AttackLeft, RB_AttackRight | 1–16 | No |
| RB_KickLeft, RB_KickRight | 1–17 | No |
| RB_Hit | 1–11 | No |
| RB_Fall | 1–19 | No |
| RB_Run | 1–25 | Yes |
| RB_Remount | 1–25 | No |

All clips are newly keyframed in Blender. Root motion is disabled; gameplay authority owns position. The Unity presentation samples clips using authoritative mode age. The importer preserves exposed transforms, builds a Generic avatar, and verifies exactly 12 named clips. Actual imported duration follows the 30Hz frame range (for example Kick is 16/30 seconds); runtime scales the clip to the authoritative attack duration.

The ride pose places wrist joints at approximately `(±.3395, 1.1465, .7085)` before the stage offset. With the existing `(0, -.08, -.32)` seated offset this is near the authored handle grips. Final attachment clearance is reviewed in Unity at gameplay distance.

## Evidence and remaining acceptance

- `motorcycle-mcp.json`, `rider-mcp.json`: real MCP export/save/render receipts.
- `motorcycle-audit-mcp.json`, `rider-audit-mcp.json`: independent topology/UV/skin audit.
- `saved-sources-audit-mcp.json`: final real-MCP read-only re-audit of all five saved `.blend` sources; `source-audit-summary.json` binds their hashes to the receipt. `traffic-audit-before-arch-fix.json` is a retained failing historical receipt; the final traffic and saved-source audits supersede it.
- `traffic-marker-fix-mcp.json`: fixes Blender's automatic `.001` marker suffix on the second traffic export by assigning exact asset-prefixed marker names; checks full vertex, polygon and UV arrays remained unchanged. The saved-source audit was repeated after this metadata-only re-export. `traffic-marker-fix-context-failed.json` retains the first export's stale selection-context error; the final call supplies an explicit Blender export context.
- `RB_P06_Motorcycle-render.png`, `RB_P06_Rider-render.png`: actual Cycles model renders.
- `RB_P06_TrafficCoupe-render.png`, `RB_P06_TrafficVan-render.png`, `RB_P06_PoliceMotorcycle-render.png`: actual Cycles traffic/patrol renders, visually reviewed against the preceding concepts. These web-budget meshes retain the concept silhouette and palette; the renders do not establish photographic equivalence to the generated concept.
- `RB_Ride-pose.png`, `RB_AttackRight-pose.png`, `RB_KickLeft-pose.png`, `RB_Run-pose.png`, `RB_Fall-pose.png`: actual evaluated armature/skin renders; joint measurements are in `pose-review-mcp.json`.
- `unity-validation.json`: generated only after the root agent invokes the Unity importer/validator.
- `source-manifest.json`: final source/import/receipt hashes, generated only when all six Unity variants and all five saved-source audits pass. Run `python tools/p06/hero/write_manifest.py --check` after later changes to reject stale evidence.

Three byte-identical patrol-rider surface PNGs and their unreferenced metadata were archived under `_local/p06-hero-unused` after SHA-256 equality and zero GUID-reference checks. Two obsolete composed recipe copies were archived there too; `compose.py` plus `common.py` and `create_*.py` are the authoring entry points. The original Blender backup files remain local and are excluded from distribution by `.gitignore`.

These source/asset checks do not establish browser FPS, memory, visual approval of the complete route, or multiplayer network quality. Those gates belong to the P06 scene/browser benchmark and remain separate from this asset report.
