using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Imports the original concept-guided club and checks its hand-attachment contract.</summary>
    public static class ClubAssetBuilder
    {
        private const string Folder = "Assets/RacingBois/Art/Weapons/Club/";
        public const string PrefabPath = "Assets/RacingBois/Prefabs/RB_Club.prefab";
        private const string MaterialPath = "Assets/RacingBois/Materials/RB_Club.mat";

        [MenuItem("Racing Bois/Race/Import Club Asset")]
        public static void Setup()
        {
            AssetDatabase.Refresh();
            foreach (var path in Directory.GetFiles(Folder, "*.png"))
            {
                var importer = AssetImporter.GetAtPath(path.Replace('\\', '/')) as TextureImporter;
                if (importer == null) throw new InvalidOperationException("Club texture not imported: " + path);
                int size = path.Contains("BaseColor") ? 512 : 256;
                importer.maxTextureSize = size;
                importer.mipmapEnabled = true;
                importer.wrapMode = TextureWrapMode.Clamp;
                importer.filterMode = FilterMode.Bilinear;
                importer.sRGBTexture = path.Contains("BaseColor");
                importer.textureCompression = TextureImporterCompression.Compressed;
                if (path.Contains("Normal")) importer.textureType = TextureImporterType.NormalMap;
                importer.SetPlatformTextureSettings(new TextureImporterPlatformSettings
                {
                    name = "WebGL", overridden = true, maxTextureSize = size,
                    format = TextureImporterFormat.DXT5, compressionQuality = 85
                });
                importer.SaveAndReimport();
            }
            var modelImporter = AssetImporter.GetAtPath(Folder + "RB_Club.fbx") as ModelImporter;
            if (modelImporter == null) throw new InvalidOperationException("Club FBX not imported");
            modelImporter.globalScale = 1;
            modelImporter.bakeAxisConversion = true;
            modelImporter.materialImportMode = ModelImporterMaterialImportMode.None;
            modelImporter.importAnimation = false;
            modelImporter.importCameras = false;
            modelImporter.importLights = false;
            modelImporter.isReadable = false;
            modelImporter.meshCompression = ModelImporterMeshCompression.Low;
            modelImporter.importNormals = ModelImporterNormals.Import;
            modelImporter.importTangents = ModelImporterTangents.CalculateMikk;
            modelImporter.generateSecondaryUV = false; // Dynamic hand prop, light probes rather than baked UV2.
            modelImporter.SaveAndReimport();
            var material = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            if (material == null)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(material, MaterialPath);
            }
            material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "RB_Club_BaseColor.png"));
            material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "RB_Club_Normal.png"));
            material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "RB_Club_MetallicSmoothness.png"));
            material.SetFloat("_Smoothness", 1);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            var root = new GameObject("RB_Club");
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(Folder + "RB_Club.fbx");
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = "Model";
            model.transform.SetParent(root.transform, false);
            model.transform.localRotation = Quaternion.Euler(0, 180, 0) * model.transform.localRotation;
            foreach (var existing in root.GetComponentsInChildren<LODGroup>(true)) UnityEngine.Object.DestroyImmediate(existing);
            var lods = new LOD[3];
            var transitions = new[] {.10f, .045f, .008f};
            for (int i = 0; i < 3; i++)
            {
                var renderer = root.GetComponentsInChildren<MeshRenderer>(true).Single(r => r.name == "RB_Club_L" + i);
                renderer.sharedMaterials = new[] {material};
                renderer.enabled = true;
                renderer.gameObject.SetActive(true);
                renderer.lightProbeUsage = LightProbeUsage.BlendProbes;
                renderer.shadowCastingMode = ShadowCastingMode.On;
                renderer.receiveShadows = true;
                lods[i] = new LOD(transitions[i], new Renderer[] {renderer});
            }
            var group = root.AddComponent<LODGroup>();
            group.SetLODs(lods);
            group.RecalculateBounds();
            var collider = root.AddComponent<CapsuleCollider>();
            collider.direction = 1;
            collider.center = new Vector3(0, .20f, 0);
            collider.radius = .045f;
            collider.height = .55f;
            foreach (var transform in root.GetComponentsInChildren<Transform>(true)) transform.gameObject.isStatic = false;
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            Validate();
            Debug.Log("RB_CLUB_ASSET_READY");
        }

        [MenuItem("Racing Bois/Race/Validate Club Asset")]
        public static void Validate()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null) throw new InvalidOperationException("Club prefab missing");
            if (prefab.transform.localPosition != Vector3.zero || prefab.transform.localRotation != Quaternion.identity || prefab.transform.localScale != Vector3.one)
                throw new InvalidOperationException("Club prefab root must be identity");
            var group = prefab.GetComponent<LODGroup>();
            if (group == null || group.lodCount != 3) throw new InvalidOperationException("Club LOD mismatch");
            var parts = prefab.GetComponentsInChildren<Transform>(true);
            var grip = parts.Single(p => p.name == "GripOrigin");
            var tip = parts.Single(p => p.name == "ClubTip");
            var butt = parts.Single(p => p.name == "ClubButt");
            if (grip.position.magnitude > .0001f || Vector3.Distance(tip.position, new Vector3(0, .475f, 0)) > .0002f ||
                Vector3.Distance(butt.position, new Vector3(0, -.075f, 0)) > .0002f)
                throw new InvalidOperationException("Club grip/length/axis attachment contract failed");
            foreach (var part in parts)
                if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(part.gameObject) > 0)
                    throw new InvalidOperationException("Missing script in club prefab");
            var meshes = prefab.GetComponentsInChildren<MeshFilter>(true);
            foreach (var mesh in meshes)
                if (mesh.sharedMesh == null || !mesh.sharedMesh.HasVertexAttribute(VertexAttribute.Normal) ||
                    !mesh.sharedMesh.HasVertexAttribute(VertexAttribute.Tangent) || !mesh.sharedMesh.HasVertexAttribute(VertexAttribute.TexCoord0))
                    throw new InvalidOperationException("Club mesh missing channels");
            var renderers = prefab.GetComponentsInChildren<MeshRenderer>(true);
            if (renderers.Any(r => r.sharedMaterials.Length != 1 || r.sharedMaterial == null || r.sharedMaterial.shader == null) || renderers.Select(r => r.sharedMaterial).Distinct().Count() != 1)
                throw new InvalidOperationException("Club material invalid");
            var colliders = prefab.GetComponentsInChildren<Collider>(true);
            if (colliders.Length != 1 || !(colliders[0] is CapsuleCollider capsule) || capsule.direction != 1)
                throw new InvalidOperationException("Club must have one simple Y capsule");
            var lods = group.GetLODs();
            var triangles = lods.Select(l => l.renderers.Sum(r => (long)r.GetComponent<MeshFilter>().sharedMesh.GetIndexCount(0) / 3)).ToArray();
            var bounds = lods[0].renderers[0].bounds;
            if (triangles[0] <= triangles[1] || triangles[1] <= triangles[2] ||
                Mathf.Abs(bounds.size.y - .55f) > .001f || Mathf.Abs(bounds.size.x - .09f) > .002f || Mathf.Abs(bounds.size.z - .09f) > .002f)
                throw new InvalidOperationException("Club LOD/scale invalid: " + bounds.size);
            Directory.CreateDirectory("docs/p04/club");
            File.WriteAllText("docs/p04/club/unity-validation.json", JsonUtility.ToJson(new Receipt
            {
                passed = true, unityVersion = Application.unityVersion, prefab = PrefabPath,
                rootIdentity = true, lodTriangles = triangles, materialCount = 1, colliders = 1,
                missingScripts = 0, normalsTangentsUv = true, boundsSize = bounds.size,
                grip = grip.position, tip = tip.position, butt = butt.position
            }, true));
            Debug.Log("RB_CLUB_ASSET_VALIDATION_PASS");
        }

        [Serializable] private sealed class Receipt
        {
            public bool passed, rootIdentity, normalsTangentsUv;
            public string unityVersion, prefab;
            public long[] lodTriangles;
            public int materialCount, colliders, missingScripts;
            public Vector3 boundsSize, grip, tip, butt;
        }
    }
}
