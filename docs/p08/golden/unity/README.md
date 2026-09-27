# Isolated Unity golden-sample inspection

This pipeline exists because the old importer collapses material slots and its historical PASS receipts do not establish visual quality. It never replaces existing production prefabs or promotes `ProductionContent` masks. The Unity scene and Windows player are review specimens, not a P08 release.

## Current verification

The importer, validator, review controller and native build source compile against the installed Unity 6000.5.7f1 assemblies with warnings treated as errors. Actual Unity import has additionally passed for Apex V8/R2 and Ash V2 with explicit bind-rest restoration. Their scoped receipts remain distinct from visual approval: both candidates still have concept differences. Editor captures have exposed real shadow and export-pose issues. Native player and environment-module checks are in progress; inspect each receipt rather than inferring completion from compilation.

Root owns Unity Editor operation. Other agents may author isolated export inputs and run the managed preflight, but must not call live Unity tools concurrently.

## Calls in Unity

Before these calls, force-refresh **all** assets/scripts, wait for actual compilation/domain reload, then run `dotnet run --project tools/p08/golden/CompileAudit -c Release -- . docs/p08/golden/unity/compiled-sources.json`. The audit binds PE/PDB identity and physical source checksums for Authoring.Editor, Client.Presentation and Golden. The builder also checks the executing module MVID, so matching current source-file hashes cannot disguise stale loaded code. The known virtual Unity MonoScript generator document is identified explicitly; no physical-source comparison is claimed for it.

All methods belong to `RacingBois.Authoring.Editor.GoldenSampleBuilder`:

1. `ReadDescriptor(descriptorPath)` verifies the current files and contract; it does not create assets.
2. `Import(descriptorPath)` imports textures and FBX, remaps each source material by its exact FBX name, creates new prefabs under `Assets/RacingBois/Golden/Generated/`, validates them and records input/output hashes.
3. `Validate(descriptorPath)` requires a successful import with matching current descriptor/code/source hashes and unchanged recorded outputs. It then checks the actual prefabs again.
4. `CreateReviewScene(descriptorPath)` creates `Assets/RacingBois/Golden/Generated/GoldenReview.unity`. It refuses unsaved existing scenes, creates its scene additively, saves and closes it, and restores the previous active scene. It does not replace the production build scene list.
5. Root can open that saved scene and enter Play mode. **Tab** changes subject; **1–6** selects three-quarter/front/side/rear/gameplay/detail views; **Space** turns the asset; **L** selects automatic/LOD0/LOD1/LOD2; **H** hides the inspection controls. Capture with controls hidden as well as a clearly labelled diagnostic view.
6. `BuildReviewPlayer(descriptorPath, "Build/Golden/<new-version>")` requires current import and scene receipts, builds one scene for Windows x64, release Mono, DX11, then restores the previous player settings. Existing output folders are never overwritten. Every packaged file and exact source snapshot is hashed.

The default project `StreamingAssets` are still subject to Unity's normal build inclusion rules; this review builder does not delete, relocate or rewrite them. They are included in the packaged-file receipt if present. The inspection scene contains no account, network or gameplay bootstrap.

## Descriptor contract (schema 1)

The JSON path is passed explicitly; the builder does not assume an Apex/Ash export directory. Repository-relative paths only, no traversal or linked paths. `InputFile` means `{ "path": "actual/path", "sha256": "actual 64-character SHA-256" }`. Every named input must exist and match its hash. There is no placeholder final descriptor.

The root object contains `schema: 1` and nonempty `assets`. Every asset has:

| Field | Contract |
|---|---|
| `id` | Unique safe identifier. Letters, digits, underscore, hyphen and dot only. |
| `kind` | `bike`, `rider` or `environment`. |
| `concept` | InputFile for the inspected generated 2D sheet. |
| `conceptReview` | InputFile for the actual review/clearance record. Hash binding records provenance; it is not automatic visual approval. |
| `source` | InputFile for the saved authoring source, normally `.blend`. |
| `fbx` | InputFile inside `Assets/`, with `.fbx` extension. |
| `modelRotationEuler` | Explicit `{x,y,z}` correction in degrees. No hidden 180-degree yaw is applied. |
| `restPose` | Default `file`. Riders may explicitly request `bind`: derive world bone transforms from imported mesh bind matrices, require all skins to agree, reject shear/reflection, and restore parents before children in the generated prefab. This does not rewrite the FBX or widen its physical envelope. |
| `moduleLodMap` | Optional exact InputFile for static environments. Strict map schema binds the same FBX, covers every renderer at its declared logical level, and creates independent LODGroups with shared per-module bounds. No whole-environment dummy group or inferred collision geometry is added. |
| `minimumSize`, `maximumSize` | `{x,y,z}` bounds of the acceptable rest-geometry dimensions in metres. Do not copy guessed dimensions from generated image text. |
| `maximumBelowGround` | Default0.04m; actors cannot increase it. Terrain environments may declare a larger explicit depth below their road/ground anchor (for a canyon valley), independently of the required y=0 anchor markers and size envelope. |
| `materials` | Nonempty exact source material bindings, described below. |
| `lods` | Exactly three `{height, rendererPaths}` records, with strictly decreasing positive screen heights and no renderer duplicated across levels. Paths are relative to the imported FBX root, before the builder names that root `Model`. Every exported renderer must be assigned. |
| `forwardMarker` | Transform path of a marker at Unity root-space +Z, `z > 0.1`, `abs(x) < 0.02`. |
| `leftMarker`, `rightMarker` | Required for bikes/riders; optional as a pair for environment. Transform paths must measure negative/positive root-space X respectively after the explicit model rotation. This catches a yaw fix that silently swaps semantic hands, grips or road sides. |
| `groundMarkers` | Nonempty transform paths of ground contacts with root-space `abs(y) < 0.025`. |
| `wheelPivots` | Bikes only: `[frontPath, rearPath]`, axle-centred parents owning all three wheel LOD renderers. Front lies ahead on +Z; wheelbase is 0.8–2.0 m. |
| `rigRoot` | Riders only: exact transform path for the generic skeleton root. |
| `requiredBones` | Riders only: at least 15 bone paths. They must exist and be bound by the skin set. A separate head mesh is not required to use leg bones. |
| `clips` | Riders only: nonempty records `{path, sha256, name}` pointing at actual imported AnimationClip subassets. Twelve P06 clip names can be retained only if they animate the new hierarchy. |
| `colliders` | Explicit `box` entries with `center,size`, or `capsule` entries with `center,radius,height,direction`. No collider is inferred from visual bounds. No MeshCollider is accepted. |
| `isStatic` | `false` for a motorcycle/rider. Static environment can use secondary lightmap UV generation. |
| `lightmapUv` | `generated` by default. Static specimens can explicitly select `authored` to preserve the FBX channel1 and validate finite unit-square, nondegenerate LOD0 UV triangles. Independent overlap/texel checks and the real bake remain separate gates. |

Each material specifies:

- `sourceName`: **exact FBX material name**, using the same safe identifier characters as `id`. The entire FBX source material set must match the descriptor; missing/extra/default material slots fail.
- `baseColor`, `normal`, `metallicSmoothness`: required InputFiles. Metallic occupies **R**, smoothness occupies **A**. The shader does not directly consume a roughness source map.
- `occlusion`, `emission`: optional InputFiles. Occlusion follows URP's **G** channel convention. Tangent-space normals must use the intended Unity convention; handedness still requires visual inspection.
- `maxSize`: power-of-two limit from 512 to 4096, default 2048. Resolution must be justified by the view and UV coverage, not by this limit alone.
- `transparent`: default `false`; `opacity` defaults to `1`; `normalScale` defaults to `1`; `emissionIntensity` defaults to `1`.
- `doubleSided`: default `false`; enables explicit URP cull-off for thin opaque leaf/grass surfaces when true. This is not transparent rendering or a substitute for appropriate normals and shadow review.

Base/emission maps are sRGB. Normal/mask/AO maps are linear. Standalone normal maps use BC5 and all other maps use BC7; mipmaps, trilinear filtering and texture streaming are enabled. Models preserve imported normals, calculate Mikk tangents, keep material/submesh separation and allow at most four skin influences. Mesh CPU access is retained for this diagnostic pipeline, not prescribed as a shipping optimization.

## What the validator establishes

- Identity prefab root, measured rest geometry, explicit forward/ground/axle placement.
- Explicit left/right handedness for actors; a forward-only rotation correction is insufficient.
- Every renderer in one of three LODs, decreasing triangle counts, submesh/material parity, populated normals/tangents/UV, valid indices and finite nondegenerate geometry.
- No missing scripts/object references/materials, explicit primitive colliders only.
- Rider bone references, normalized weights, bind-pose counts, actual clip bindings, seventeen sample times per clip, finite bounded deformations and an envelope covering sampled vertices.
- Exact input/code and generated output hashes from the operation that ran. Build additionally snapshots scene dependencies and active project build settings before and after compilation.

Rest dimensions are measured from actual current mesh vertices, not animation-expanded culling bounds. The sampled skin envelope is stored by `GoldenSkinBounds` and restored on instantiation. Unity documents `Renderer.localBounds` as a renderer-local culling volume and cautions that a custom override may need restoration at runtime: [Unity Renderer.localBounds](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Renderer-localBounds.html).

UV overlap/texel distribution, plausible anatomy and machine construction, transparent-surface sorting, lighting artifacts, all-angle silhouettes, animation contacts and deformation appearance still require authoring audit and real Unity/player inspection. Frame time and memory are unmeasured until the review player runs.

## Environment and native review captures

`CreateEnvironmentReviewScene(descriptorPath, recipePath)` creates a road-level inspection view from a measured camera, sun direction and hash-bound HDR panorama. The recipe requires an explicit `unitySkyRotationDegrees`; Blender's world rotation is not silently assumed equivalent. Light intensity and sky orientation still need actual Unity comparison. Its recipe/HDR inputs are bound to scene and player-build receipts.

Review scenes own a separate pipeline override through `GoldenReviewPipelineScope` and restore the previous quality override when disabled. Studio shadows use a 25m range, two cascades and 4096 resolution, following real controlled captures which isolated diagonal fairing artifacts to self-shadowing. The gameplay/Web pipeline asset is unchanged. This inspection profile is not a gameplay performance claim.

The standalone review player accepts `--rb-review-output <new-absolute-directory>`. `GoldenCaptureRunner`, attached only to review controls, submits actual URP camera render requests for each subject/view/LOD, records their hashes and exits. It refuses an existing output path and rejects effectively uniform frames. It is disabled in Editor. These are engine camera renders, not window-framebuffer/UI captures, and do not replace a ten-minute gameplay benchmark or concept acceptance.

The first hidden-window framebuffer attempt produced 36 black images and is explicitly rejected under `native-actors-20260927-0424`. After replacing it with the installed URP render-request API, `native-actors-20260927-0502` contains 36 verified nonuniform PNGs from the real Windows DX11 executable, including all three forced LODs for Apex R2 and Ash V3. Sample views were inspected; the models still fail concept fidelity. The corresponding native build passed with zero errors/warnings and unchanged source/file hashes.

## Managed preflight

Run `dotnet build tools/p08/golden/importer-preflight.csproj --nologo -v:minimal`. This compiles only the new review infrastructure against the installed engine and Input System references. It does not launch Unity, execute Unity APIs, generate fake assets or substitute for Editor compilation.

## Physical-unit correction

The first mesh validator applied its cross-product-squared threshold to raw mesh-local coordinates. Actual Canyon FBX inspection exposed a compensating scale of100 on renderers, so that test was not expressed in metres and could report false positives. The validator now transforms edge vectors into identity-prefab metre space before applying the same1e-16 threshold, avoiding translation-induced precision loss. Historical V13/V14 raw-local failures are retained but are not valid claims of physically degenerate source geometry. Source cleanup and local-coordinate recentering may still improve robustness and efficiency; they do not justify the old unit mistake. Native scale-invariance controls and fresh imports are required after this correction.
