using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Imports the original, concept-led P06 canyon kit without editing earlier art.</summary>
    public static class P06EnvironmentAssetBuilder
    {
        private const string Root = "Assets/RacingBois/";
        private const string Source = Root + "Art/P06/Environment/";
        private const string Prefabs = Root + "Prefabs/P06/";
        private const string Materials = Root + "Materials/P06/";
        private static readonly string[] Names = { "RockA", "RockB", "Sage", "DryGrass", "Guardrail", "Chevron", "UtilityPole" };
        private static readonly string[] Surfaces = { "Sandstone", "Foliage", "Roadside", "Asphalt", "Gravel" };
        private static readonly string[] Maps = { "BaseColor", "Normal", "MetallicSmoothness", "Roughness" };

        [MenuItem("Racing Bois/P06/Import Canyon Environment")]
        public static void Setup()
        {
            Directory.CreateDirectory(Prefabs); Directory.CreateDirectory(Materials); AssetDatabase.Refresh();
            foreach (var surface in Surfaces)
            {
                foreach (var map in Maps) ImportTexture(surface, map);
                CreateMaterial(surface);
            }
            foreach (var name in Names) CreatePrefab(name);
            AssetDatabase.SaveAssets(); Validate();
            Debug.Log("RB_P06_ENVIRONMENT_READY");
        }

        private static void ImportTexture(string surface, string map)
        {
            string path = Source + "RB_P06_" + surface + "_" + map + ".png";
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null) throw new InvalidOperationException("Missing P06 environment texture: " + path);
            int size = surface == "Sandstone" || surface == "Roadside" ? 1024 : 512;
            importer.textureType = map == "Normal" ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = map == "BaseColor"; importer.mipmapEnabled = true; importer.isReadable = false;
            importer.alphaSource = map == "MetallicSmoothness" ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
            importer.wrapMode = surface == "Roadside" || surface == "Foliage" ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
            importer.filterMode = FilterMode.Trilinear; importer.anisoLevel = surface == "Asphalt" || surface == "Gravel" ? 4 : 2;
            importer.maxTextureSize = size; importer.textureCompression = TextureImporterCompression.Compressed;
            importer.SetPlatformTextureSettings(new TextureImporterPlatformSettings
            {
                name = "WebGL", overridden = true, maxTextureSize = size, compressionQuality = 80,
                format = map == "Normal" || map == "MetallicSmoothness" ? TextureImporterFormat.DXT5 : TextureImporterFormat.DXT1
            });
            importer.SaveAndReimport();
        }

        private static Material CreateMaterial(string surface)
        {
            string name = "RB_P06_" + surface, path = Materials + name + ".mat";
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) throw new InvalidOperationException("URP Lit shader is not available.");
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null) { material = new Material(shader); AssetDatabase.CreateAsset(material, path); }
            material.shader = shader; material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Source + name + "_BaseColor.png"));
            material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Source + name + "_Normal.png"));
            material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Source + name + "_MetallicSmoothness.png"));
            material.SetFloat("_Smoothness", 1); material.SetFloat("_SmoothnessTextureChannel", 0);
            material.SetFloat("_BumpScale", surface == "Sandstone" ? .28f : surface=="Asphalt"||surface=="Gravel" ? .35f : .6f);
            material.SetFloat("_Surface", 0); material.SetFloat("_Cull", (float)CullMode.Back);
            material.EnableKeyword("_NORMALMAP"); material.EnableKeyword("_METALLICSPECGLOSSMAP");
            material.DisableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A"); material.enableInstancing = true;
            EditorUtility.SetDirty(material); return material;
        }

        private static void CreatePrefab(string shortName)
        {
            string name = "RB_P06_" + shortName, path = Source + name + ".fbx";
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("Missing P06 environment model: " + path);
            importer.globalScale = 1; importer.bakeAxisConversion = true; importer.importAnimation = false;
            importer.importCameras = false; importer.importLights = false; importer.importVisibility = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.meshCompression = ModelImporterMeshCompression.Low; importer.isReadable = true;
            // All scenery uses dynamic sun/ambient lighting. No baked lightmaps are authored for the slice.
            importer.generateSecondaryUV = false; importer.importNormals = ModelImporterNormals.Import;
            importer.importTangents = ModelImporterTangents.CalculateMikk; importer.SaveAndReimport();
            var imported = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var instance = new GameObject(name);
            try
            {
                var model = (GameObject)PrefabUtility.InstantiatePrefab(imported); model.name = "Model";
                model.transform.SetParent(instance.transform, false);
                model.transform.localRotation = Quaternion.Euler(0, 180, 0) * model.transform.localRotation;
                foreach (var old in instance.GetComponentsInChildren<LODGroup>(true)) UnityEngine.Object.DestroyImmediate(old);
                var renderers = instance.GetComponentsInChildren<MeshRenderer>(true);
                if (renderers.Length != 3) throw new InvalidOperationException(name + " expects one renderer per LOD.");
                string surface = shortName.StartsWith("Rock", StringComparison.Ordinal) ? "Sandstone" : IsFoliage(shortName) ? "Foliage" : "Roadside";
                var material = AssetDatabase.LoadAssetAtPath<Material>(Materials + "RB_P06_" + surface + ".mat");
                foreach (var renderer in renderers)
                {
                    renderer.sharedMaterials = new[] { material }; renderer.gameObject.SetActive(true); renderer.enabled = true;
                    renderer.shadowCastingMode = IsFoliage(shortName) ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    renderer.receiveShadows = true; renderer.lightProbeUsage = LightProbeUsage.BlendProbes;
                    renderer.reflectionProbeUsage = ReflectionProbeUsage.Simple;
                }
                var lods = new LOD[3];
                for (int level = 0; level < 3; level++)
                {
                    var renderer = renderers.Single(r => r.name.Contains("_L" + level + "_"));
                    lods[level] = new LOD(level == 0 ? .22f : level == 1 ? .075f : .008f, new Renderer[] { renderer });
                }
                var group = instance.AddComponent<LODGroup>(); group.fadeMode = LODFadeMode.None; group.SetLODs(lods); group.RecalculateBounds();
                var bounds = lods[0].renderers[0].bounds;
                if (shortName == "UtilityPole")
                {
                    var capsule = instance.AddComponent<CapsuleCollider>(); capsule.direction = 1; capsule.radius = .13f;
                    capsule.height = 7; capsule.center = new Vector3(0, 3.5f, 0);
                }
                else if (!IsFoliage(shortName))
                {
                    var box = instance.AddComponent<BoxCollider>(); box.center = bounds.center; box.size = bounds.size;
                }
                foreach (var part in instance.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(part.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
                PrefabUtility.SaveAsPrefabAsset(instance, Prefabs + name + ".prefab");
            }
            finally { UnityEngine.Object.DestroyImmediate(instance); }
        }

        private static bool IsFoliage(string name) => name == "Sage" || name == "DryGrass";

        [MenuItem("Racing Bois/P06/Validate Canyon Environment")]
        public static void Validate()
        {
            var receipts = new List<AssetReceipt>();
            foreach (var shortName in Names)
            {
                string name = "RB_P06_" + shortName, path = Prefabs + name + ".prefab";
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null) throw new InvalidOperationException("Missing environment prefab: " + path);
                if (prefab.transform.localPosition != Vector3.zero || prefab.transform.localRotation != Quaternion.identity || prefab.transform.localScale != Vector3.one)
                    throw new InvalidOperationException("Prefab root must be identity: " + name);
                var group = prefab.GetComponent<LODGroup>();
                if (group == null || group.lodCount != 3) throw new InvalidOperationException("Expected three LODs: " + name);
                var lods = group.GetLODs(); var triangles = new long[3]; var vertices = new int[3];
                var materials = new HashSet<Material>();
                for (int level = 0; level < 3; level++)
                {
                    if (lods[level].renderers.Length != 1) throw new InvalidOperationException("LOD renderer count: " + name);
                    var renderer = lods[level].renderers[0];
                    if (renderer == null || renderer.sharedMaterials.Length != 1 || renderer.sharedMaterial == null || renderer.sharedMaterial.shader == null || renderer.sharedMaterial.shader.name != "Universal Render Pipeline/Lit")
                        throw new InvalidOperationException("URP material reference: " + name);
                    materials.Add(renderer.sharedMaterial);
                    foreach (var textureName in new[] { "_BaseMap", "_BumpMap", "_MetallicGlossMap" })
                        if (renderer.sharedMaterial.GetTexture(textureName) == null) throw new InvalidOperationException("Missing map " + textureName + ": " + name);
                    var filter = renderer.GetComponent<MeshFilter>(); var mesh = filter == null ? null : filter.sharedMesh;
                    if (mesh == null || !mesh.isReadable || mesh.subMeshCount != 1 || !mesh.HasVertexAttribute(VertexAttribute.Normal) || !mesh.HasVertexAttribute(VertexAttribute.Tangent) || !mesh.HasVertexAttribute(VertexAttribute.TexCoord0))
                        throw new InvalidOperationException("Mesh channels/readability/submesh budget: " + name);
                    triangles[level] = (long)mesh.GetIndexCount(0) / 3; vertices[level] = mesh.vertexCount;
                    foreach (var uv in mesh.uv)
                        if (uv.x < -.002f || uv.x > 1.002f || uv.y < -.002f || uv.y > 1.002f) throw new InvalidOperationException("UV outside intended atlas: " + name);
                }
                if (materials.Count != 1 || triangles[0] <= triangles[1] || triangles[1] <= triangles[2] || triangles[2] < 4)
                    throw new InvalidOperationException("LOD/material budget: " + name);
                var colliders = prefab.GetComponentsInChildren<Collider>(true);
                if (colliders.Length != (IsFoliage(shortName) ? 0 : 1) || colliders.Any(c => c is MeshCollider)) throw new InvalidOperationException("Simple collider budget: " + name);
                foreach (var part in prefab.GetComponentsInChildren<Transform>(true))
                    if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(part.gameObject) != 0 || !part.gameObject.isStatic)
                        throw new InvalidOperationException("Missing script/static state: " + name);
                var bounds = lods[0].renderers[0].bounds; CheckBounds(shortName, bounds);
                receipts.Add(new AssetReceipt { name = name, prefab = path, passed = true, lodTriangles = triangles, lodVertices = vertices,
                    lod0Bounds = bounds.size, rootIdentity = true, readableSources = true, normalsTangentsUv = true,
                    colliders = colliders.Length, distinctMaterials = materials.Count, rendererCount = 3 });
            }
            foreach (var surface in Surfaces) foreach (var map in Maps)
            {
                var importer = (TextureImporter)AssetImporter.GetAtPath(Source + "RB_P06_" + surface + "_" + map + ".png");
                if (!importer.mipmapEnabled || importer.isReadable || importer.sRGBTexture != (map == "BaseColor") ||
                    (map == "Normal" && importer.textureType != TextureImporterType.NormalMap) || !importer.GetPlatformTextureSettings("WebGL").overridden)
                    throw new InvalidOperationException("Texture import contract: " + surface + "/" + map);
            }
            Directory.CreateDirectory("docs/p06/environment");
            File.WriteAllText("docs/p06/environment/unity-validation.json", JsonUtility.ToJson(new Receipt
            { passed = true, unityVersion = Application.unityVersion, assets = receipts.ToArray(), dynamicLighting = true, sourceUvReuseIntentional = true }, true));
            Debug.Log("RB_P06_ENVIRONMENT_VALIDATION_PASS");
        }

        private static void CheckBounds(string name, Bounds b)
        {
            float minHeight = name == "RockA" ? 4.1f : name == "RockB" ? 2.1f : name == "UtilityPole" ? 6.8f : name == "Chevron" ? 1.7f : name == "Guardrail" ? .85f : name == "Sage" ? .6f : .3f;
            float maxHeight = name == "RockA" ? 4.6f : name == "RockB" ? 2.6f : name == "UtilityPole" ? 7.2f : name == "Chevron" ? 2.1f : name == "Guardrail" ? 1.1f : name == "Sage" ? 1.2f : .7f;
            if (b.size.y < minHeight || b.size.y > maxHeight || Mathf.Abs(b.min.y) > .08f || b.size.x < .04f || b.size.z < .01f)
                throw new InvalidOperationException("Unexpected scale/ground pivot: " + name + " " + b);
            if (name == "Guardrail" && (b.size.z < 3.9f || b.size.x > .3f)) throw new InvalidOperationException("Guardrail must span local forward +Z.");
            if (name == "UtilityPole" && b.size.x < 2.1f) throw new InvalidOperationException("Cross-arm axis is not horizontal.");
        }
        [Serializable] private sealed class Receipt { public bool passed, dynamicLighting, sourceUvReuseIntentional; public string unityVersion; public AssetReceipt[] assets; }
        [Serializable] private sealed class AssetReceipt
        {
            public bool passed, rootIdentity, readableSources, normalsTangentsUv;
            public string name, prefab; public long[] lodTriangles; public int[] lodVertices;
            public Vector3 lod0Bounds; public int colliders, distinctMaterials, rendererCount;
        }
    }
}
