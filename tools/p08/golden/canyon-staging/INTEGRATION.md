# Isolated module LOD implementation for root integration

`GoldenSampleBuilder.Modules.cs` is intentionally staged outside Assets to avoid triggering a Unity domain reload during the current imports. It compiles against the installed Unity6000.5.7f1 assemblies. Twenty-two executable schema/hash/coverage tests pass, including the real217-module Canyon map. **Native hierarchy/bounds validation is not yet claimed**; root must copy the file into the Editor assembly and run the provided probe.

## Additive contract

Add `public InputFile moduleLodMap;` to `AssetSpec`. It is optional for existing assets. In `ReadDescriptor`, call `ReadModuleLodMap(asset.moduleLodMap, asset)` when `HasInput(asset.moduleLodMap)` is true. In `AssetInputs`, yield its path when present so the existing before/after input fingerprint and saved receipt bind the map itself.

Schema1 is exact: top-level fields are required `schema`, `assetId`, `source`, `modules`, and optional descriptive `scope`. `source` contains exactly `path` and `sha256`, matching the asset's exact FBX input. A module contains exactly `id` and `lods`. Each of its three LODs contains exactly a finite decreasing `height` and nonempty `rendererPaths`. Every source renderer occurs once across all modules and at the same logical level as `AssetSpec.lods`. Unknown/duplicate keys, JSON type metadata, path traversal, wrong asset/hash, cross-level assignments and incomplete coverage are rejected. The parser uses the standard BCL JSON-to-XML reader; no Newtonsoft or new package dependency is required.

Module maps are permitted only for static environment assets. Renderer transforms must be leaf `MeshRenderer` objects. Skins, animator hierarchies and arbitrary child renderers are rejected instead of being silently reparented.

## Call sites

1. In `CreatePrefab`, replace the single-root-LOD block with a branch. With a map, call `CreateModuleLodGroups(root, model.transform, spec, map)`; otherwise retain the existing root LODGroup. Call the helper after material setup and after removing imported LODGroups, before saving the prefab.
2. `CreateModuleLodGroups` unpacks only the generated model instance. It leaves raw FBX meshes/material assets untouched. Renderers move under `root/Module LODs/<module id>/L<n>_R<index>`, with world transforms preserved. Ground/forward/left/right markers stay in Model. Each group has one conservative union centre and size calculated from **all three LOD levels**, not a changing pivot per level.
3. In `ValidateAsset`, with a map first call `ValidateModuleLodGroups(root, model, spec, map, spec.moduleLodMap)`. Then obtain logical renderer levels with `ModuleInspectionLods(root, spec, map)` for the existing material, mesh, bounds and triangle-count checks. This aggregate is a reporting list; no dummy whole-asset LODGroup is created. Actual module thresholds/references/bounds are checked against the stored child groups by the module validator. Keep the existing root-group validation branch for assets without a map.
4. In `CreateReviewScene`, use `ModuleInspectionLods(root, spec, map)[0].renderers` when a map exists; keep the old root-group lookup otherwise. `GoldenReviewController.SetLod` already traverses child groups, so no change is needed there.
5. Add the returned `ModuleLodReport` to a receipt if desired. It reports actual module bounds, per-level triangles, exact renderer coverage and preserved source mesh/transform references. It does not grant visual or frame-time acceptance.

The validator requires each module LOD to have nonempty geometry and decreasing triangle counts, checks that all prefab renderers belong to exactly one module, rejects a competing root LODGroup, and independently recomputes bounds from current vertices. It compares each relocated renderer with the raw imported FBX mesh/material and its expected transform after the asset's model rotation. A large coarse basin may legitimately have a large bound; foreground foliage, paint, shoulders and rails now have separate10m sections. The map does not hide this distinction.

## Native probe

After a normal golden import creates the review prefab, root can call:

```csharp
GoldenSampleBuilder.ProbeModuleLods(
    "docs/p08/golden/canyon/v13/descriptor-lighting.json",
    "RB_Golden_Canyon_v13",
    "docs/p08/golden/canyon/v13/module-lod-mapping.json");
```

It loads a prefab-content copy, replaces the legacy LODGroup in that copy, validates all module groups and unloads the copy without saving. It checks that the persisted prefab and raw FBX hashes did not change. If the prefab already uses module groups it validates them directly. This probe is useful during integration, but full asset acceptance must still run the existing geometry/material checks. The V13 geometry currently has known microscopic triangles and is **not a production candidate** until the V14 repair passes the unchanged native threshold.

## Contact and streaming boundaries

The new code adds no collider and infers none from module bounds. The current Canyon has explicit zero colliders and an analytical authored curve; its geometry is not yet bound to the authoritative gameplay course sampler. Adding one box or MeshCollider around the whole environment would create incorrect ground/side contacts and is not permitted by this implementation.

Per-module LOD and culling are implemented by this partial. Independent bundle residency/unloading is a separate runtime concern and is not claimed by the LOD map. Runtime streaming must retain the authoritative course collision/surface data for the active race independently of visual module residency. Future primitive obstacle colliders need explicit authoring samples tied to the same course curve and exact render module transforms; a render bounds box is not a collision shape.

## Checks

```powershell
dotnet build tools/p08/golden/canyon-staging/modules-preflight.csproj --nologo -v:minimal
dotnet run --project tools/p08/golden/canyon-staging/tests/modules-contract-tests.csproj --nologo
```

The executable tests are parser/contract tests and do not substitute for the native Unity probe or an actual player frame-time/memory run.
