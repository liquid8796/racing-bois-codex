using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Deterministic import and prefab validation for original P03/P04 art.</summary>
    public static class RaceAssetBuilder
    {
        private const string Root = "Assets/RacingBois/";
        private const string VehicleFolder = Root + "Art/Vehicles/";
        private const string CanyonFolder = Root + "Art/Props/Canyon/";
        private const string CharacterFolder = Root + "Art/Characters/";
        private static readonly string[] Names =
        {
            "RB_Motorcycle", "RB_PoliceMotorcycle", "RB_Rider", "RB_TrafficCoupe", "RB_TrafficVan",
            "RB_Sandstone", "RB_SageScrub", "RB_Pedestrian"
        };

        [MenuItem("Racing Bois/Race/Import Original Assets")]
        public static void Setup()
        {
            Directory.CreateDirectory(Root + "Materials");
            Directory.CreateDirectory(Root + "Prefabs");
            AssetDatabase.Refresh();
            foreach (var path in Directory.GetFiles(VehicleFolder, "*.png").Concat(Directory.GetFiles(CanyonFolder, "*.png")).Concat(Directory.GetFiles(CharacterFolder, "*.png")))
            {
                var texture = AssetImporter.GetAtPath(path.Replace('\\', '/')) as TextureImporter;
                if (texture == null) throw new InvalidOperationException("Texture importer missing: " + path);
                int size = path.Contains("Canyon") ? path.Contains("BaseColor") ? 128 : 32 : path.Contains("Pedestrian") ? 128 : 256;
                texture.maxTextureSize = size;
                texture.mipmapEnabled = true;
                texture.wrapMode = TextureWrapMode.Clamp;
                texture.filterMode = FilterMode.Bilinear;
                texture.sRGBTexture = path.Contains("BaseColor");
                texture.textureCompression = TextureImporterCompression.Compressed;
                if (path.Contains("Normal")) texture.textureType = TextureImporterType.NormalMap;
                texture.SetPlatformTextureSettings(new TextureImporterPlatformSettings
                {
                    name = "WebGL", overridden = true, maxTextureSize = size,
                    format = TextureImporterFormat.DXT5, compressionQuality = 70
                });
                texture.SaveAndReimport();
            }
            var race = CreateMaterial("RB_RacePalette", "RB_RacePalette_BaseColor");
            var police = CreateMaterial("RB_PolicePalette", "RB_PolicePalette_BaseColor");
            var canyon = CreateMaterial("RB_CanyonPalette", "RB_Canyon_BaseColor", CanyonFolder, "RB_Canyon");
            var pedestrian = CreateMaterial("RB_PedestrianPalette", "RB_Pedestrian_BaseColor", CharacterFolder, "RB_Pedestrian");
            foreach (var name in Names)
            {
                bool rider = name == "RB_Rider";
                bool isPedestrian = name == "RB_Pedestrian";
                bool character = rider || isPedestrian;
                bool environment = name == "RB_Sandstone" || name == "RB_SageScrub";
                var sourceName = name == "RB_PoliceMotorcycle" ? "RB_Motorcycle" : name;
                var path = Root + (environment ? "Art/Props/Canyon/" : character ? "Art/Characters/" : "Art/Vehicles/") + sourceName + ".fbx";
                var importer = AssetImporter.GetAtPath(path) as ModelImporter;
                if (importer == null) throw new InvalidOperationException("Model importer missing: " + path);
                importer.globalScale = 1;
                importer.bakeAxisConversion = true;
                importer.importAnimation = false;
                importer.importCameras = false;
                importer.importLights = false;
                importer.materialImportMode = ModelImporterMaterialImportMode.None;
                importer.meshCompression = ModelImporterMeshCompression.Low;
                // Tiny scenery meshes are combined once by the road view on
                // startup. Only those source meshes require CPU readability.
                importer.isReadable = environment;
                // Dynamic characters/vehicles use light probes, never baked static lightmaps.
                importer.generateSecondaryUV = environment;
                importer.importNormals = ModelImporterNormals.Import;
                importer.importTangents = ModelImporterTangents.CalculateMikk;
                importer.SaveAndReimport();
                var imported = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                // FBX unit metadata keeps nested joints at scale one. Preserve
                // the imported coordinate conversion under an identity prefab
                // root; resetting the imported rotation would lay it on its side.
                var instance = new GameObject(name);
                var model = (GameObject)PrefabUtility.InstantiatePrefab(imported);
                model.name = "Model";
                model.transform.SetParent(instance.transform, false);
                // FBX's right-handed -Z forward becomes Unity's -Z in this
                // importer. Rotate the preserved model basis to gameplay +Z.
                model.transform.localRotation = Quaternion.Euler(0, 180, 0) * model.transform.localRotation;
                foreach (var group in instance.GetComponentsInChildren<LODGroup>(true))
                    UnityEngine.Object.DestroyImmediate(group);
                var renderers = instance.GetComponentsInChildren<MeshRenderer>(true);
                foreach (var renderer in renderers)
                {
                    renderer.sharedMaterials = new[] {environment ? canyon : isPedestrian ? pedestrian : name == "RB_PoliceMotorcycle" ? police : race};
                    renderer.gameObject.SetActive(true);
                    renderer.enabled = true;
                    renderer.shadowCastingMode = ShadowCastingMode.On;
                    renderer.receiveShadows = true;
                    renderer.lightProbeUsage = LightProbeUsage.BlendProbes;
                    renderer.reflectionProbeUsage = ReflectionProbeUsage.Simple;
                }
                var lods = new LOD[3];
                var transitions = character ? new[] {.24f, .09f, .012f} : new[] {.28f, .11f, .015f};
                for (int level = 0; level < 3; level++)
                {
                    var marker = "_L" + level + "_";
                    var members = renderers.Where(r => r.name.Contains(marker)).Cast<Renderer>().ToArray();
                    if (members.Length == 0) throw new InvalidOperationException(name + " LOD " + level + " empty");
                    lods[level] = new LOD(transitions[level], members);
                }
                var lodGroup = instance.AddComponent<LODGroup>();
                lodGroup.fadeMode = LODFadeMode.None;
                lodGroup.SetLODs(lods);
                lodGroup.RecalculateBounds();
                if (environment)
                {
                    var bounds = lods[0].renderers[0].bounds;
                    foreach (var renderer in lods[0].renderers) bounds.Encapsulate(renderer.bounds);
                    var collider = instance.AddComponent<BoxCollider>();
                    collider.center = bounds.center;
                    collider.size = bounds.size;
                }
                else if (character)
                {
                    var collider = instance.AddComponent<CapsuleCollider>();
                    collider.center = new Vector3(0, isPedestrian ? .893f : .91f, 0);
                    collider.radius = isPedestrian ? .23f : .27f;
                    collider.height = isPedestrian ? 1.77f : 1.82f;
                }
                else
                {
                    var collider = instance.AddComponent<BoxCollider>();
                    bool motorcycle = name.Contains("Motorcycle");
                    bool van = name == "RB_TrafficVan";
                    collider.center = new Vector3(0, motorcycle ? .598f : van ? 1.145f : .68f, motorcycle ? -.01f : 0);
                    collider.size = motorcycle ? new Vector3(.95f, 1.196f, 2.12f)
                        : new Vector3(van ? 2.31f : 2.16f, van ? 2.29f : 1.36f, van ? 4.64f : 4.54f);
                }
                foreach (var transform in instance.GetComponentsInChildren<Transform>(true))
                    transform.gameObject.isStatic = environment;
                PrefabUtility.SaveAsPrefabAsset(instance, Root + "Prefabs/" + name + ".prefab");
                UnityEngine.Object.DestroyImmediate(instance);
            }
            AssetDatabase.SaveAssets();
            Validate();
            Debug.Log("RB_RACE_ASSETS_READY");
        }

        private static Material CreateMaterial(string name, string baseMap, string folder = VehicleFolder, string surfacePrefix = "RB_RacePalette")
        {
            var path = Root + "Materials/" + name + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(material, path);
            }
            material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(folder + baseMap + ".png"));
            material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(folder + surfacePrefix + "_Normal.png"));
            material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(folder + surfacePrefix + "_MetallicSmoothness.png"));
            material.SetFloat("_Smoothness", 1f);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        [MenuItem("Racing Bois/Race/Validate Original Assets")]
        public static void Validate()
        {
            var receipts = new List<AssetReceipt>();
            foreach (var name in Names)
            {
                bool environment = name == "RB_Sandstone" || name == "RB_SageScrub";
                var path = Root + "Prefabs/" + name + ".prefab";
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null) throw new InvalidOperationException("Missing prefab: " + path);
                if (prefab.transform.localPosition != Vector3.zero || prefab.transform.localRotation != Quaternion.identity || prefab.transform.localScale != Vector3.one)
                    throw new InvalidOperationException("Invalid root transform: " + name);
                var group = prefab.GetComponent<LODGroup>();
                if (group == null || group.lodCount != 3) throw new InvalidOperationException("Expected three LODs: " + name);
                var colliders = prefab.GetComponentsInChildren<Collider>(true);
                if (colliders.Length != 1 || colliders[0] is MeshCollider) throw new InvalidOperationException("Collider budget: " + name);
                foreach (var transform in prefab.GetComponentsInChildren<Transform>(true))
                    if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(transform.gameObject) != 0)
                        throw new InvalidOperationException("Missing script: " + name);
                var renderers = prefab.GetComponentsInChildren<MeshRenderer>(true);
                foreach (var renderer in renderers)
                    if (renderer.sharedMaterials.Length != 1 || renderer.sharedMaterial == null || renderer.sharedMaterial.shader == null)
                        throw new InvalidOperationException("Missing/duplicated material: " + renderer.name);
                var meshes = prefab.GetComponentsInChildren<MeshFilter>(true);
                foreach (var mesh in meshes)
                    if (mesh.sharedMesh == null || !mesh.sharedMesh.HasVertexAttribute(VertexAttribute.Normal) ||
                        !mesh.sharedMesh.HasVertexAttribute(VertexAttribute.Tangent) || !mesh.sharedMesh.HasVertexAttribute(VertexAttribute.TexCoord0))
                        throw new InvalidOperationException("Invalid mesh channels: " + mesh.name);
                var lods = group.GetLODs();
                var bounds = lods[0].renderers[0].bounds;
                foreach (var renderer in lods[0].renderers) bounds.Encapsulate(renderer.bounds);
                var triangles = lods.Select(l => l.renderers.Sum(r =>
                    (long)r.GetComponent<MeshFilter>().sharedMesh.GetIndexCount(0) / 3)).ToArray();
                if (triangles[0] <= triangles[1] || triangles[1] <= triangles[2])
                    throw new InvalidOperationException("LOD does not reduce geometry: " + name);
                if (bounds.size.y < (environment ? .2f : .8f) || bounds.size.y > 2.4f || bounds.size.z < .3f)
                    throw new InvalidOperationException("Unexpected imported scale/axis: " + name + " " + bounds.size);
                var parts = prefab.GetComponentsInChildren<Transform>(true);
                if (name.Contains("Motorcycle"))
                {
                    var front = parts.Single(t => t.name == "RB_Moto_L0_Wheel_Front");
                    var rear = parts.Single(t => t.name == "RB_Moto_L0_Wheel_Rear");
                    if (front.position.z <= rear.position.z || front.position.y < .30f)
                        throw new InvalidOperationException("Motorcycle must face gameplay +Z: " + name);
                }
                if (name == "RB_Rider" || name == "RB_Pedestrian")
                {
                    string prefix = name == "RB_Rider" ? "RB_Rider" : "RB_Ped";
                    var left = parts.Single(t => t.name == prefix + "_L0_UpperArm_L");
                    var right = parts.Single(t => t.name == prefix + "_L0_UpperArm_R");
                    if (left.position.x >= right.position.x || bounds.max.y < (name == "RB_Rider" ? 1.80f : 1.76f))
                        throw new InvalidOperationException("Rider anatomy axes invalid");
                }
                receipts.Add(new AssetReceipt
                {
                    name = name, path = path, passed = true, lodTriangles = triangles,
                    lod0Bounds = bounds.size, colliders = colliders.Length,
                    distinctMaterials = renderers.Select(r => r.sharedMaterial).Distinct().Count(),
                    meshCount = meshes.Length, missingScripts = 0, normalsTangentsUv = true,
                    rootIdentity = true, dynamicLightProbes = !environment
                });
            }
            Directory.CreateDirectory("docs/p03/assets");
            File.WriteAllText("docs/p03/assets/unity-validation.json", JsonUtility.ToJson(new PackReceipt
            {
                passed = true, unityVersion = Application.unityVersion, assets = receipts.ToArray()
            }, true));
            Debug.Log("RB_RACE_ASSET_VALIDATION_PASS");
        }

        [Serializable] private sealed class PackReceipt { public bool passed; public string unityVersion; public AssetReceipt[] assets; }
        [Serializable] private sealed class AssetReceipt
        {
            public string name, path;
            public bool passed, normalsTangentsUv, rootIdentity, dynamicLightProbes;
            public long[] lodTriangles;
            public Vector3 lod0Bounds;
            public int colliders, distinctMaterials, meshCount, missingScripts;
        }
    }
}
