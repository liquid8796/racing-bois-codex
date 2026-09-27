using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Xml;
using System.Xml.Linq;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        private const string ModuleContainerName = "Module LODs";
        private const float ModuleBoundsPadding = .02f;

        [Serializable] public sealed class ModuleLodMap
        {
            public int schema;
            public string assetId, scope;
            public InputFile source;
            public ModuleLodSpec[] modules;
        }

        [Serializable] public sealed class ModuleLodSpec
        {
            public string id;
            public LodSpec[] lods;
        }

        [Serializable] public sealed class ModuleLodMeasurement
        {
            public string id;
            public Vector3 center, size;
            public float lodSize;
            public int rendererCount;
            public long[] triangles;
        }

        [Serializable] public sealed class ModuleLodReport
        {
            public string assetId, mapSha256;
            public bool passed, exactRendererCoverage, sharedBounds, rawMeshesPreserved;
            public int moduleCount, rendererCount;
            public ModuleLodMeasurement[] modules;
            public string scope = "Native prefab module structure, source meshes/transforms and LOD bounds only; not visual or performance acceptance.";
        }

        /// <summary>Read a bounded strict JSON map; no unknown or duplicate fields are ignored.</summary>
        public static ModuleLodMap ReadModuleLodMap(InputFile input, AssetSpec asset)
        {
            Require(asset != null && asset.kind == "environment" && asset.isStatic,
                "Module LOD maps are supported only for static environment assets.");
            VerifyInput(input);
            var bytes = File.ReadAllBytes(ProjectPath(input.path, false));
            Require(bytes.Length > 0 && bytes.Length <= 4 * 1024 * 1024, "Module LOD map exceeds the 4 MiB authoring limit.");
            using (var hash = SHA256.Create())
                Require(BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").Equals(input.sha256, StringComparison.OrdinalIgnoreCase),
                    "Module LOD map changed while reading.");

            var quotas = new XmlDictionaryReaderQuotas
            {
                MaxDepth = 16, MaxStringContentLength = 1024 * 1024,
                MaxArrayLength = 65536, MaxBytesPerRead = 4096, MaxNameTableCharCount = 65536
            };
            XElement document;
            using (var reader = JsonReaderWriterFactory.CreateJsonReader(bytes, quotas))
                document = XDocument.Load(reader, LoadOptions.None).Root;
            var fields = ModuleObject(document, "map", "schema", "assetId", "source", "scope", "modules");
            int schema = 0;
            Require(ModuleType(ModuleRequired(fields, "schema")) == "number" && int.TryParse(fields["schema"].Value,
                NumberStyles.None, CultureInfo.InvariantCulture, out schema) && schema == 1, "Module LOD schema must be integer 1.");
            var sourceFields = ModuleObject(ModuleRequired(fields, "source"), "source", "path", "sha256");
            var map = new ModuleLodMap
            {
                schema = 1, assetId = ModuleString(ModuleRequired(fields, "assetId")),
                scope = fields.ContainsKey("scope") ? ModuleString(fields["scope"]) : "",
                source = new InputFile
                {
                    path = ModuleString(ModuleRequired(sourceFields, "path")),
                    sha256 = ModuleString(ModuleRequired(sourceFields, "sha256"))
                },
                modules = ModuleArray(ModuleRequired(fields, "modules")).Select(ReadModuleSpec).ToArray()
            };
            Require(map.assetId == asset.id && map.source.path == asset.fbx.path &&
                string.Equals(map.source.sha256, asset.fbx.sha256, StringComparison.OrdinalIgnoreCase),
                "Module map is not bound to this exact asset and FBX.");
            VerifyInput(map.source);
            ValidateModuleMapCoverage(map, asset);
            return map;
        }

        private static ModuleLodSpec ReadModuleSpec(XElement element)
        {
            var fields = ModuleObject(element, "module", "id", "lods");
            return new ModuleLodSpec
            {
                id = ModuleString(ModuleRequired(fields, "id")),
                lods = ModuleArray(ModuleRequired(fields, "lods")).Select(item =>
                {
                    var lod = ModuleObject(item, "module LOD", "height", "rendererPaths");
                    float height = 0;
                    Require(ModuleType(ModuleRequired(lod, "height")) == "number" && float.TryParse(lod["height"].Value,
                        NumberStyles.Float, CultureInfo.InvariantCulture, out height) && !float.IsNaN(height) && !float.IsInfinity(height),
                        "Module LOD height must be a finite number.");
                    return new LodSpec { height = height, rendererPaths = ModuleArray(ModuleRequired(lod, "rendererPaths")).Select(ModuleString).ToArray() };
                }).ToArray()
            };
        }

        private static Dictionary<string, XElement> ModuleObject(XElement element, string context, params string[] allowed)
        {
            Require(ModuleType(element) == "object", "Expected JSON object: " + context);
            Require(element.Attributes().All(attribute => attribute.Name.NamespaceName.Length == 0 && attribute.Name.LocalName == "type"),
                "Unsupported JSON metadata in module-map object: " + context);
            var result = new Dictionary<string, XElement>(StringComparer.Ordinal);
            foreach (var child in element.Elements())
            {
                string key = child.Name.LocalName;
                Require(child.Name.NamespaceName.Length == 0 && allowed.Contains(key, StringComparer.Ordinal), "Unknown module-map field: " + context + "." + key);
                Require(!result.ContainsKey(key), "Duplicate module-map field: " + context + "." + key);
                result.Add(key, child);
            }
            return result;
        }

        private static XElement ModuleRequired(Dictionary<string, XElement> fields, string key)
        { Require(fields.ContainsKey(key), "Missing module-map field: " + key); return fields[key]; }

        private static string ModuleType(XElement element) => element?.Attribute("type")?.Value ?? "string";
        private static string ModuleString(XElement element)
        { Require(element != null && ModuleType(element) == "string" && !element.HasElements, "Expected JSON string in module map."); return element.Value; }
        private static XElement[] ModuleArray(XElement element)
        { Require(ModuleType(element) == "array", "Expected JSON array in module map."); return element.Elements().ToArray(); }

        private static void ValidateModuleMapCoverage(ModuleLodMap map, AssetSpec asset)
        {
            Require(map.modules != null && map.modules.Length > 0 && map.modules.Length <= 4096, "Module count must be 1..4096.");
            Require(asset.lods != null && asset.lods.Length == 3, "Asset needs three logical LOD sets before module mapping.");
            var declared = asset.lods.Select(lod => new HashSet<string>(lod.rendererPaths, StringComparer.Ordinal)).ToArray();
            var covered = new[] { new HashSet<string>(StringComparer.Ordinal), new HashSet<string>(StringComparer.Ordinal), new HashSet<string>(StringComparer.Ordinal) };
            var ids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var allPaths = new HashSet<string>(StringComparer.Ordinal);
            foreach (var module in map.modules)
            {
                Require(module != null && SafeId(module.id) && module.id != "." && module.id != ".." && ids.Add(module.id), "Unsafe or duplicate module id.");
                Require(module.lods != null && module.lods.Length == 3, "Each module needs exactly three LODs: " + module.id);
                float previous = 1.01f;
                for (int level = 0; level < 3; level++)
                {
                    var lod = module.lods[level];
                    Require(lod != null && lod.height > 0 && lod.height < previous && !float.IsNaN(lod.height) && !float.IsInfinity(lod.height), "Module LOD heights must strictly decrease: " + module.id);
                    Require(lod.rendererPaths != null && lod.rendererPaths.Length > 0, "Module LOD has no renderers: " + module.id);
                    previous = lod.height;
                    foreach (string path in lod.rendererPaths)
                    {
                        Require(!string.IsNullOrEmpty(path) && path.Length <= 512 && !path.Contains("\\") &&
                            path.Split('/').All(segment => SafeId(segment) && segment != "." && segment != ".."), "Unsafe renderer hierarchy path: " + path);
                        Require(declared[level].Contains(path) && covered[level].Add(path) && allPaths.Add(path),
                            "Module renderer is unknown, duplicated or assigned to the wrong logical LOD: " + path);
                    }
                }
            }
            for (int level = 0; level < 3; level++)
                Require(covered[level].SetEquals(declared[level]), "Module mapping does not cover the complete asset LOD " + level + ".");
        }

        /// <summary>Create groups in a generated prefab instance; the raw FBX is never edited.</summary>
        public static void CreateModuleLodGroups(GameObject root, Transform model, AssetSpec asset, ModuleLodMap map)
        {
            ValidateModuleMapCoverage(map, asset);
            Require(root != null && model != null && model.parent == root.transform, "Expected generated prefab root/Model hierarchy.");
            Require(root.GetComponentsInChildren<LODGroup>(true).Length == 0 && root.transform.Find(ModuleContainerName) == null,
                "Create module LODs before adding any legacy whole-asset LODGroup.");
            var paths = map.modules.SelectMany(module => module.lods).SelectMany(lod => lod.rendererPaths).ToArray();
            var renderers = paths.ToDictionary(path => path, path => FindRenderer(model, path), StringComparer.Ordinal);
            Require(renderers.Values.All(renderer => renderer is MeshRenderer && renderer.transform.childCount == 0),
                "Module relocation requires static leaf MeshRenderers; actors and nested renderer hierarchies need a separate contract.");
            Require(new HashSet<Renderer>(renderers.Values).SetEquals(model.GetComponentsInChildren<Renderer>(true)), "An imported renderer is outside the module map.");
            // Unpack this temporary/generated instance only. Mesh assets and the FBX file remain shared and immutable.
            if (PrefabUtility.IsPartOfPrefabInstance(model.gameObject))
                PrefabUtility.UnpackPrefabInstance(model.gameObject, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            var container = new GameObject(ModuleContainerName).transform;
            container.SetParent(root.transform, false);
            foreach (var module in map.modules)
            {
                var members = module.lods.SelectMany(lod => lod.rendererPaths).Select(path => renderers[path]).ToArray();
                Bounds union = ModuleWorldBounds(members);
                var node = new GameObject(module.id).transform;
                node.SetParent(container, false);
                node.position = union.center;
                var group = node.gameObject.AddComponent<LODGroup>();
                var levels = new LOD[3];
                for (int level = 0; level < 3; level++)
                {
                    var selection = module.lods[level].rendererPaths.Select(path => renderers[path]).ToArray();
                    for (int index = 0; index < selection.Length; index++)
                    {
                        selection[index].transform.SetParent(node, true);
                        selection[index].name = ModuleRendererName(level, index);
                    }
                    levels[level] = new LOD(module.lods[level].height, selection) { fadeTransitionWidth = .15f };
                }
                group.fadeMode = LODFadeMode.CrossFade; group.animateCrossFading = true;
                group.SetLODs(levels);
                // One conservative reference centre/size is shared by all LODs, including any LOD silhouette drift.
                group.localReferencePoint = Vector3.zero;
                group.size = Mathf.Max(union.size.x, Mathf.Max(union.size.y, union.size.z)) + ModuleBoundsPadding;
            }
        }

        public static ModuleLodReport ValidateModuleLodGroups(GameObject root, Transform model, AssetSpec asset, ModuleLodMap map, InputFile mapInput)
        {
            ValidateModuleMapCoverage(map, asset);
            VerifyInput(mapInput);
            Require(root.GetComponent<LODGroup>() == null, "A whole-asset LODGroup would override independent module distances.");
            var container = root.transform.Find(ModuleContainerName);
            Require(container != null && container.childCount == map.modules.Length && root.GetComponentsInChildren<LODGroup>(true).Length == map.modules.Length,
                "Module LODGroup count differs from the exact map.");
            var raw = AssetDatabase.LoadAssetAtPath<GameObject>(asset.fbx.path);
            Require(raw != null, "Raw FBX asset unavailable during module validation.");
            var visited = new HashSet<Renderer>();
            var measurements = new List<ModuleLodMeasurement>();
            foreach (var module in map.modules)
            {
                var node = container.Find(module.id);
                Require(node != null && node.localRotation == Quaternion.identity && node.localScale == Vector3.one, "Missing or transformed module holder: " + module.id);
                var group = node.GetComponent<LODGroup>();
                Require(group != null && group.enabled && group.fadeMode == LODFadeMode.CrossFade && group.animateCrossFading, "Invalid module LOD policy: " + module.id);
                var levels = group.GetLODs();
                Require(levels.Length == 3, "Module lost an LOD: " + module.id);
                var members = new List<Renderer>();
                var triangles = new long[3];
                for (int level = 0; level < 3; level++)
                {
                    var expected = module.lods[level];
                    Require(Mathf.Abs(levels[level].screenRelativeTransitionHeight - expected.height) < .0001f && levels[level].renderers.Length == expected.rendererPaths.Length,
                        "Module LOD renderer count or threshold changed: " + module.id);
                    for (int index = 0; index < expected.rendererPaths.Length; index++)
                    {
                        var renderer = node.Find(ModuleRendererName(level, index))?.GetComponent<Renderer>();
                        Require(renderer != null && renderer == levels[level].renderers[index] && visited.Add(renderer), "Missing, duplicated or reordered module renderer.");
                        var source = FindRenderer(raw.transform, expected.rendererPaths[index]);
                        Require(MeshOf(renderer) == MeshOf(source) && renderer.sharedMaterials.SequenceEqual(source.sharedMaterials), "Module replaced a source mesh/material binding: " + expected.rendererPaths[index]);
                        Matrix4x4 expectedMatrix = model.localToWorldMatrix * raw.transform.worldToLocalMatrix * source.transform.localToWorldMatrix;
                        Require(ModuleMatrixEqual(renderer.transform.localToWorldMatrix, expectedMatrix), "Module relocation changed the original mesh transform: " + expected.rendererPaths[index]);
                        members.Add(renderer); triangles[level] += MeshOf(renderer).triangles.LongLength / 3;
                    }
                    Require(triangles[level] > 0, "A module LOD has empty geometry: " + module.id);
                    if (level > 0) Require(triangles[level] < triangles[level - 1], "Module LOD triangles do not decrease: " + module.id);
                }
                Require(node.GetComponentsInChildren<Renderer>(true).Length == members.Count, "Unexpected renderer in module holder: " + module.id);
                Bounds union = ModuleWorldBounds(members);
                float expectedSize = Mathf.Max(union.size.x, Mathf.Max(union.size.y, union.size.z)) + ModuleBoundsPadding;
                Require(Finite(group.localReferencePoint) && Vector3.Distance(node.TransformPoint(group.localReferencePoint), union.center) < .003f &&
                    !float.IsNaN(group.size) && !float.IsInfinity(group.size) && Mathf.Abs(group.size - expectedSize) < Mathf.Max(.003f, expectedSize * .00001f),
                    "Module culling centre/size does not contain all three LODs with a shared bound: " + module.id);
                measurements.Add(new ModuleLodMeasurement { id = module.id, center = root.transform.InverseTransformPoint(union.center), size = union.size,
                    lodSize = group.size, rendererCount = members.Count, triangles = triangles });
            }
            Require(visited.SetEquals(root.GetComponentsInChildren<Renderer>(true)), "A prefab renderer is controlled by no module or by multiple modules.");
            return new ModuleLodReport { passed = true, assetId = asset.id, mapSha256 = mapInput.sha256, moduleCount = map.modules.Length,
                rendererCount = visited.Count, exactRendererCoverage = true, sharedBounds = true, rawMeshesPreserved = true, modules = measurements.ToArray() };
        }

        /// <summary>Aggregate logical levels for existing mesh/skin-independent validators and review framing.</summary>
        public static LOD[] ModuleInspectionLods(GameObject root, AssetSpec asset, ModuleLodMap map)
        {
            var container = root.transform.Find(ModuleContainerName);
            Require(container != null, "Module LOD container missing.");
            return Enumerable.Range(0, 3).Select(level => new LOD(asset.lods[level].height,
                map.modules.SelectMany(module => container.Find(module.id).GetComponent<LODGroup>().GetLODs()[level].renderers).ToArray())).ToArray();
        }

        /// <summary>Read-only native probe against a loaded prefab-content copy; never saves the modified copy.</summary>
        public static string ProbeModuleLods(string descriptorPath, string assetId, string mapPath)
        {
            Require(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling, "Module probe requires idle Edit mode.");
            var descriptor = ReadDescriptor(descriptorPath);
            var asset = descriptor.assets.Single(item => item.id == assetId);
            var input = new InputFile { path = mapPath, sha256 = Digest(ProjectPath(mapPath, false)) };
            var map = ReadModuleLodMap(input, asset);
            string beforeFbx = Digest(asset.fbx.path), beforePrefab = Digest(PrefabPath(asset));
            var root = PrefabUtility.LoadPrefabContents(PrefabPath(asset));
            try
            {
                var model = root.transform.Find("Model");
                if (root.transform.Find(ModuleContainerName) == null)
                {
                    foreach (var group in root.GetComponentsInChildren<LODGroup>(true)) UnityEngine.Object.DestroyImmediate(group);
                    CreateModuleLodGroups(root, model, asset, map);
                }
                var report = ValidateModuleLodGroups(root, model, asset, map, input);
                Require(Digest(asset.fbx.path) == beforeFbx && Digest(PrefabPath(asset)) == beforePrefab, "Module probe changed persisted source/prefab data.");
                return JsonUtility.ToJson(report, true);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        private static string ModuleRendererName(int level, int index) => "L" + level + "_R" + index.ToString("D3", CultureInfo.InvariantCulture);
        private static Bounds ModuleWorldBounds(IEnumerable<Renderer> renderers)
        {
            bool initialized = false; Bounds bounds = default;
            foreach (var renderer in renderers)
            {
                var value = CurrentGeometryBounds(renderer);
                Require(Finite(value.center) && Finite(value.size), "Nonfinite module geometry bounds.");
                if (initialized) bounds.Encapsulate(value); else { bounds = value; initialized = true; }
            }
            Require(initialized && bounds.size.sqrMagnitude > 0, "Empty module bounds.");
            return bounds;
        }
        private static bool ModuleMatrixEqual(Matrix4x4 first, Matrix4x4 second)
        {
            for (int index = 0; index < 16; index++)
                if (float.IsNaN(first[index]) || float.IsInfinity(first[index]) || Mathf.Abs(first[index] - second[index]) > .0005f + Mathf.Abs(second[index]) * .000001f) return false;
            return true;
        }
    }
}
