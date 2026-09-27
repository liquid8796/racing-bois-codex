using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Manifest-driven import and validation of concept-led original P08 production art.</summary>
    public static class P08ArtBuilder
    {
        public const string Source = "Assets/RacingBois/Art/P08/";
        public const string Prefabs = "Assets/RacingBois/Prefabs/P08/";
        public const string Materials = "Assets/RacingBois/Materials/P08/";
        private const string SharedRiderSource = "Assets/RacingBois/Art/P06/Hero/RB_P06_Rider.fbx";
        private static readonly string[] Maps = { "BaseColor", "Normal", "MetallicSmoothness", "Roughness" };

        [Serializable] public sealed class Manifest { public int schema; public AssetEntry[] assets; }
        [Serializable] public sealed class AssetEntry
        {
            public string name, concept, source, fbx, surface, kind;
            public bool primitiveCollider, conceptInspectedBeforeGeometry;
        }
        [Serializable] private sealed class Receipt { public bool passed; public string unityVersion; public AssetReceipt[] assets; }
        [Serializable] private sealed class AssetReceipt
        {
            public string name, prefab, kind; public bool passed, rootIdentity, channelsValid, sharedRigClips;
            public int renderers, colliders, materials, facialExpressionsChecked; public long[] lodTriangles; public Vector3 bounds;
            public long posedVerticesChecked; public int sampledClips;
        }

        public static AssetEntry[] Entries()
        {
            if (!File.Exists(Source + "ArtManifest.json")) throw new InvalidOperationException("P08 export manifest is missing.");
            var result = JsonUtility.FromJson<Manifest>(File.ReadAllText(Source + "ArtManifest.json"));
            if (result?.assets == null || result.assets.Length == 0) throw new InvalidOperationException("Empty P08 art manifest.");
            if (result.assets.Select(a => a.name).Distinct().Count() != result.assets.Length) throw new InvalidOperationException("Duplicate P08 semantic asset ID.");
            return result.assets;
        }

        [MenuItem("Racing Bois/P08/Import Production Art")]
        public static void Setup()
        {
            Directory.CreateDirectory(Prefabs); Directory.CreateDirectory(Materials); AssetDatabase.Refresh();
            var entries = Entries();
            foreach (var surface in entries.Select(a => a.surface).Distinct())
            {
                foreach (var map in Maps) ImportTexture(surface, map);
                CreateMaterial(surface);
            }
            foreach (var entry in entries) CreatePrefab(entry);
            CreateSparkAlias();
            AssetDatabase.SaveAssets(); Validate();
            Debug.Log("RB_P08_ART_IMPORT_READY");
        }

        private static void ImportTexture(string surface, string map)
        {
            string path = Source + surface + "_" + map + ".png";
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null) throw new InvalidOperationException("P08 surface missing: " + path);
            int size = map == "BaseColor" ? 1024 : 512;
            importer.textureType = map == "Normal" ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = map == "BaseColor"; importer.mipmapEnabled = true; importer.isReadable = false;
            importer.alphaSource = map == "MetallicSmoothness" ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
            importer.wrapMode = TextureWrapMode.Clamp; importer.filterMode = FilterMode.Trilinear; importer.anisoLevel = 2;
            importer.maxTextureSize = size; importer.textureCompression = TextureImporterCompression.Compressed;
            importer.SetPlatformTextureSettings(new TextureImporterPlatformSettings { name = "WebGL", overridden = true,
                maxTextureSize = size, compressionQuality = 85, format = map == "Normal" || map == "MetallicSmoothness" ? TextureImporterFormat.DXT5 : TextureImporterFormat.DXT1 });
            importer.SetPlatformTextureSettings(new TextureImporterPlatformSettings { name = "Standalone", overridden = true,
                maxTextureSize = size, compressionQuality = 90, format = map == "Normal" ? TextureImporterFormat.BC5 : TextureImporterFormat.BC7 });
            importer.SaveAndReimport();
        }

        private static void CreateMaterial(string surface)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) throw new InvalidOperationException("URP Lit shader missing.");
            string path = Materials + surface + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null) { material = new Material(shader); AssetDatabase.CreateAsset(material, path); }
            material.shader = shader; material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Source + surface + "_BaseColor.png"));
            material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Source + surface + "_Normal.png"));
            material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Source + surface + "_MetallicSmoothness.png"));
            material.SetFloat("_Smoothness", 1); material.SetFloat("_SmoothnessTextureChannel", 0); material.SetFloat("_BumpScale", .55f);
            material.SetFloat("_Surface", 0); material.SetFloat("_Cull", (float)CullMode.Back);
            material.EnableKeyword("_NORMALMAP"); material.EnableKeyword("_METALLICSPECGLOSSMAP");
            material.DisableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A"); material.enableInstancing = true; EditorUtility.SetDirty(material);
        }

        private static void CreatePrefab(AssetEntry entry)
        {
            if (!entry.conceptInspectedBeforeGeometry || !File.Exists(entry.concept) || !File.Exists(entry.source))
                throw new InvalidOperationException("Incomplete concept/source provenance: " + entry.name);
            bool rider = entry.kind == "rider" || entry.kind == "pedestrian", bike = entry.kind == "bike";
            var importer = AssetImporter.GetAtPath(entry.fbx) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("Missing P08 FBX: " + entry.fbx);
            importer.globalScale = 1; importer.bakeAxisConversion = true; importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.importCameras = false; importer.importLights = false; importer.importVisibility = false;
            importer.meshCompression = ModelImporterMeshCompression.Low; importer.isReadable = true;
            importer.importNormals = ModelImporterNormals.Import; importer.importTangents = ModelImporterTangents.CalculateMikk;
            importer.generateSecondaryUV = false; importer.importAnimation = false; importer.importBlendShapes = rider;
            importer.animationType = rider ? ModelImporterAnimationType.Generic : ModelImporterAnimationType.None;
            if (rider) { importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel; importer.optimizeGameObjects = false; }
            importer.SaveAndReimport();
            var root = new GameObject(entry.name);
            try
            {
                var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(entry.fbx));
                model.name = "Model"; model.transform.SetParent(root.transform, false);
                model.transform.localRotation = Quaternion.Euler(0, 180, 0) * model.transform.localRotation;
                foreach (var group in root.GetComponentsInChildren<LODGroup>(true)) UnityEngine.Object.DestroyImmediate(group);
                var renderers = root.GetComponentsInChildren<Renderer>(true);
                var material = AssetDatabase.LoadAssetAtPath<Material>(Materials + entry.surface + ".mat");
                foreach (var renderer in renderers)
                {
                    renderer.sharedMaterials = new[] { material }; renderer.enabled = true; renderer.gameObject.SetActive(true);
                    renderer.shadowCastingMode = entry.kind == "foliage" ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    renderer.receiveShadows = true; renderer.lightProbeUsage = LightProbeUsage.BlendProbes; renderer.reflectionProbeUsage = ReflectionProbeUsage.Simple;
                    if (renderer is SkinnedMeshRenderer skin)
                    {
                        skin.quality = SkinQuality.Bone2; skin.updateWhenOffscreen = false;
                        skin.rootBone = model.GetComponentsInChildren<Transform>(true).Single(t => t.name == "RB_P06_Rider_Rig");
                    }
                }
                var lods = new LOD[3];
                for (int level = 0; level < 3; level++)
                {
                    var members = renderers.Where(r => r.name.Contains("_L" + level + "_")).ToArray();
                    if (members.Length != (bike ? 3 : 1)) throw new InvalidOperationException("LOD renderer budget: " + entry.name);
                    lods[level] = new LOD(level == 0 ? .22f : level == 1 ? .075f : .009f, members);
                }
                var groupNew = root.AddComponent<LODGroup>(); groupNew.fadeMode = LODFadeMode.None; groupNew.SetLODs(lods); groupNew.RecalculateBounds();
                var bounds = lods[0].renderers[0].bounds;
                foreach (var renderer in lods[0].renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
                if (rider)
                {
                    var animator = model.GetComponentInChildren<Animator>();
                    if (animator == null) throw new InvalidOperationException("Generic rider animator missing.");
                    animator.applyRootMotion = false; animator.runtimeAnimatorController = null; animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                    SampleAndFitSkinBounds(model);
                    groupNew.localReferencePoint = new Vector3(0, .9f, 0); groupNew.size = 1.8f;
                    var capsule = root.AddComponent<CapsuleCollider>(); capsule.center = new Vector3(0, .9f, 0); capsule.height = 1.8f; capsule.radius = .28f;
                }
                else if (entry.primitiveCollider)
                {
                    if (entry.name.EndsWith("Streetlamp", StringComparison.Ordinal) || entry.name.EndsWith("SnowPole", StringComparison.Ordinal))
                    {
                        var collider = root.AddComponent<CapsuleCollider>(); collider.direction = 1;
                        collider.height = bounds.size.y; collider.center = new Vector3(0, bounds.center.y, 0);
                        collider.radius = entry.name.EndsWith("SnowPole", StringComparison.Ordinal) ? .055f : .10f;
                    }
                    else { var collider = root.AddComponent<BoxCollider>(); collider.center = bounds.center; collider.size = bounds.size; }
                }
                bool environment = entry.kind == "scenery" || entry.kind == "foliage" || entry.kind == "landmark";
                foreach (var transform in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(transform.gameObject, environment ? StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic : 0);
                PrefabUtility.SaveAsPrefabAsset(root, Prefabs + entry.name + ".prefab");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        private static void CreateSparkAlias()
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/RacingBois/Prefabs/P06/RB_P06_Motorcycle.prefab");
            if (source == null) throw new InvalidOperationException("Original Spark prefab missing.");
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(source);
            try { instance.name = "RB_P08_Bike_00"; PrefabUtility.SaveAsPrefabAsset(instance, Prefabs + instance.name + ".prefab"); }
            finally { UnityEngine.Object.DestroyImmediate(instance); }
        }

        private static void ValidateFacialExpressions(Mesh mesh)
        {
            foreach (string expression in new[] { "Happy", "Focused" })
            {
                int shape = Enumerable.Range(0, mesh.blendShapeCount).Where(i => mesh.GetBlendShapeName(i).EndsWith(expression, StringComparison.Ordinal)).DefaultIfEmpty(-1).First();
                if (shape < 0 || mesh.GetBlendShapeFrameCount(shape) != 1) throw new InvalidOperationException("P08 facial expression missing: " + expression);
                var positions = new Vector3[mesh.vertexCount];
                mesh.GetBlendShapeFrameVertices(shape, 0, positions, null, null);
                if (!positions.Any(v => v.sqrMagnitude > 1e-10f)) throw new InvalidOperationException("P08 facial expression has no deformation: " + expression);
            }
        }

        private static AnimationClip[] SharedClips() => AssetDatabase.LoadAllAssetsAtPath(SharedRiderSource).OfType<AnimationClip>()
            .Where(c => P06HeroAssetBuilder.ClipNames.Contains(c.name)).OrderBy(c => c.name).ToArray();

        private static long SampleAndFitSkinBounds(GameObject model)
        {
            var clips = SharedClips(); if (clips.Length != 12) throw new InvalidOperationException("P08 shared twelve-clip set incomplete.");
            var skins = model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var transforms = model.GetComponentsInChildren<Transform>(true);
            var positions = transforms.Select(t => t.localPosition).ToArray(); var rotations = transforms.Select(t => t.localRotation).ToArray();
            var scales = transforms.Select(t => t.localScale).ToArray(); var bounds = new Bounds[skins.Length]; var initialized = new bool[skins.Length];
            var mesh = new Mesh(); long count = 0;
            try
            {
                foreach (var clip in clips)
                {
                    float maximumBoneDelta = 0;
                    for (int phase = 0; phase <= 16; phase++)
                    {
                        clip.SampleAnimation(model, clip.length * phase / 16f);
                        for (int t = 0; t < transforms.Length; t++)
                            if (transforms[t].name.StartsWith("RB_P06_Rider_L0_", StringComparison.Ordinal))
                                maximumBoneDelta = Mathf.Max(maximumBoneDelta, Quaternion.Angle(rotations[t], transforms[t].localRotation));
                        for (int index = 0; index < skins.Length; index++)
                        {
                            var skin = skins[index]; skin.BakeMesh(mesh, false);
                            foreach (var vertex in mesh.vertices)
                            {
                                var point = skin.rootBone.InverseTransformPoint(skin.transform.TransformPoint(vertex));
                                if (float.IsNaN(point.x) || float.IsNaN(point.y) || float.IsNaN(point.z) || float.IsInfinity(point.x) || float.IsInfinity(point.y) || float.IsInfinity(point.z)) throw new InvalidOperationException("Nonfinite P08 skinned pose.");
                                if (!initialized[index]) { bounds[index] = new Bounds(point, Vector3.zero); initialized[index] = true; }
                                else bounds[index].Encapsulate(point);
                                count++;
                            }
                        }
                    }
                    if (clip.name != "RB_Idle" && maximumBoneDelta < 2) throw new InvalidOperationException("Shared rider clip does not bind to the P08 rig: " + clip.name);
                }
                for (int index = 0; index < skins.Length; index++) { bounds[index].Expand(.2f); skins[index].localBounds = bounds[index]; }
                foreach (var clip in clips) for (int phase = 0; phase <= 16; phase++)
                {
                    clip.SampleAnimation(model, clip.length * phase / 16f);
                    foreach (var skin in skins)
                    {
                        skin.BakeMesh(mesh, false); var worldBounds = skin.bounds; worldBounds.Expand(.002f);
                        foreach (var vertex in mesh.vertices)
                            if (!worldBounds.Contains(skin.transform.TransformPoint(vertex))) throw new InvalidOperationException("P08 animated vertex escapes renderer bounds: " + clip.name);
                    }
                }
                return count;
            }
            finally
            {
                for (int i = 0; i < transforms.Length; i++) { transforms[i].localPosition = positions[i]; transforms[i].localRotation = rotations[i]; transforms[i].localScale = scales[i]; }
                UnityEngine.Object.DestroyImmediate(mesh);
            }
        }

        private static Mesh MeshOf(Renderer renderer) => renderer is SkinnedMeshRenderer skin ? skin.sharedMesh : renderer.GetComponent<MeshFilter>()?.sharedMesh;

        [MenuItem("Racing Bois/P08/Validate Production Art")]
        public static void Validate()
        {
            var receipts = new List<AssetReceipt>();
            foreach (var entry in Entries())
            {
                string path = Prefabs + entry.name + ".prefab"; var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null || prefab.transform.localPosition != Vector3.zero || prefab.transform.localRotation != Quaternion.identity || prefab.transform.localScale != Vector3.one)
                    throw new InvalidOperationException("P08 prefab root identity: " + entry.name);
                foreach (var transform in prefab.GetComponentsInChildren<Transform>(true))
                    if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(transform.gameObject) != 0) throw new InvalidOperationException("Missing P08 script.");
                var lodGroup = prefab.GetComponent<LODGroup>(); if (lodGroup == null || lodGroup.lodCount != 3) throw new InvalidOperationException("P08 LOD contract.");
                var lods = lodGroup.GetLODs(); var triangles = new long[3]; var materials = new HashSet<Material>();
                for (int level = 0; level < 3; level++) foreach (var renderer in lods[level].renderers)
                {
                    var mesh = MeshOf(renderer);
                    if (mesh == null || mesh.vertexCount == 0 || mesh.subMeshCount != 1 || !mesh.HasVertexAttribute(VertexAttribute.Normal) || !mesh.HasVertexAttribute(VertexAttribute.Tangent) || !mesh.HasVertexAttribute(VertexAttribute.TexCoord0))
                        throw new InvalidOperationException("P08 mesh channels: " + entry.name);
                    if (renderer.sharedMaterials.Length != 1 || renderer.sharedMaterial == null || renderer.sharedMaterial.shader.name != "Universal Render Pipeline/Lit") throw new InvalidOperationException("P08 material pipeline.");
                    foreach (var map in new[] { "_BaseMap", "_BumpMap", "_MetallicGlossMap" }) if (renderer.sharedMaterial.GetTexture(map) == null) throw new InvalidOperationException("Missing PBR map.");
                    if (entry.name.StartsWith("RB_P08_Rider_", StringComparison.Ordinal)) ValidateFacialExpressions(mesh);
                    materials.Add(renderer.sharedMaterial); triangles[level] += (long)mesh.GetIndexCount(0) / 3;
                }
                if (materials.Count != 1 || triangles[0] <= triangles[1] || triangles[1] <= triangles[2] || triangles[2] < 4) throw new InvalidOperationException("P08 LOD reduction/material budget: " + entry.name);
                var colliders = prefab.GetComponentsInChildren<Collider>(true);
                if (colliders.Any(c => c is MeshCollider) || colliders.Length != (entry.primitiveCollider ? 1 : 0)) throw new InvalidOperationException("P08 collider budget.");
                bool rider = entry.kind == "rider" || entry.kind == "pedestrian"; long checkedVertices = 0;
                if (rider)
                {
                    var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    try
                    {
                        var animator = instance.GetComponentInChildren<Animator>();
                        if (animator == null || animator.avatar == null || !animator.avatar.isValid || animator.applyRootMotion) throw new InvalidOperationException("P08 generic avatar.");
                        checkedVertices = SampleAndFitSkinBounds(instance.transform.Find("Model").gameObject);
                    }
                    finally { UnityEngine.Object.DestroyImmediate(instance); }
                }
                var bounds = lods[0].renderers[0].bounds; foreach (var r in lods[0].renderers.Skip(1)) bounds.Encapsulate(r.bounds);
                receipts.Add(new AssetReceipt { name = entry.name, prefab = path, kind = entry.kind, passed = true, rootIdentity = true, channelsValid = true,
                    sharedRigClips = rider, renderers = prefab.GetComponentsInChildren<Renderer>(true).Length, colliders = colliders.Length, materials = materials.Count,
                    lodTriangles = triangles, bounds = bounds.size, posedVerticesChecked = checkedVertices, sampledClips = rider ? 12 : 0,
                    facialExpressionsChecked = entry.name.StartsWith("RB_P08_Rider_", StringComparison.Ordinal) ? 6 : 0 });
            }
            Directory.CreateDirectory("docs/p08/art"); File.WriteAllText("docs/p08/art/unity-validation.json", JsonUtility.ToJson(new Receipt { passed = true, unityVersion = Application.unityVersion, assets = receipts.ToArray() }, true));
            Debug.Log("RB_P08_ART_VALIDATION_PASS " + receipts.Count);
        }
    }
}
