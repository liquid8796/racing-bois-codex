using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Reproducible import of original concept-guided P06 hero sources.</summary>
    public static class P06HeroAssetBuilder
    {
        public const string ArtFolder = "Assets/RacingBois/Art/P06/Hero/";
        public const string PrefabFolder = "Assets/RacingBois/Prefabs/P06/";
        public const string MaterialFolder = "Assets/RacingBois/Materials/P06/";
        public static readonly string[] ClipNames = {"RB_Idle", "RB_Ride", "RB_LeanLeft", "RB_LeanRight", "RB_AttackLeft", "RB_AttackRight", "RB_KickLeft", "RB_KickRight", "RB_Hit", "RB_Fall", "RB_Run", "RB_Remount"};
        private static readonly string[] AssetNames = {"RB_P06_Motorcycle", "RB_P06_Rider", "RB_P06_TrafficCoupe", "RB_P06_TrafficVan", "RB_P06_PoliceMotorcycle", "RB_P06_PoliceRider"};
        private static string SourceName(string name) => name == "RB_P06_PoliceRider" ? "RB_P06_Rider" : name;
        private static string MaterialName(string name) => name.Contains("Traffic") ? "RB_P06_Traffic" : name;
        private static string SurfaceName(string name) => name == "RB_P06_PoliceRider" ? "RB_P06_Rider" : MaterialName(name);
        private static string[] AvailableAssets()
        {
            var available = AssetNames.Where(n => File.Exists(ArtFolder + SourceName(n) + ".fbx") &&
                File.Exists(ArtFolder + MaterialName(n) + "_BaseColor.png") &&
                new[] {"_Normal.png", "_MetallicSmoothness.png", "_Roughness.png"}.All(s => File.Exists(ArtFolder + SurfaceName(n) + s))).ToArray();
            if (!available.Contains("RB_P06_Motorcycle") || !available.Contains("RB_P06_Rider")) throw new InvalidOperationException("Mandatory P06 hero source/maps are incomplete");
            return available;
        }

        [MenuItem("Racing Bois/P06/Import Hero Assets")]
        public static void Setup()
        {
            Directory.CreateDirectory(PrefabFolder);
            Directory.CreateDirectory(MaterialFolder);
            AssetDatabase.Refresh();
            foreach (var path in Directory.GetFiles(ArtFolder, "*.png"))
            {
                var texture = AssetImporter.GetAtPath(path.Replace('\\', '/')) as TextureImporter;
                if (texture == null) throw new InvalidOperationException("Hero texture missing: " + path);
                bool color = path.Contains("BaseColor");
                int size = color ? 1024 : 512;
                texture.maxTextureSize = size;
                texture.mipmapEnabled = true;
                texture.wrapMode = TextureWrapMode.Clamp;
                texture.filterMode = FilterMode.Trilinear;
                texture.anisoLevel = 2;
                texture.sRGBTexture = color;
                texture.textureType = path.Contains("Normal") ? TextureImporterType.NormalMap : TextureImporterType.Default;
                texture.textureCompression = TextureImporterCompression.Compressed;
                texture.SetPlatformTextureSettings(new TextureImporterPlatformSettings
                {
                    name = "WebGL", overridden = true, maxTextureSize = size,
                    format = TextureImporterFormat.DXT5, compressionQuality = 85
                });
                texture.SaveAndReimport();
            }
            foreach (var name in AvailableAssets())
            {
                bool rider = name.EndsWith("Rider", StringComparison.Ordinal);
                bool motorcycle = name.Contains("Motorcycle");
                string path = ArtFolder + SourceName(name) + ".fbx";
                var importer = AssetImporter.GetAtPath(path) as ModelImporter;
                if (importer == null) throw new InvalidOperationException("Hero model missing: " + path);
                importer.globalScale = 1;
                importer.bakeAxisConversion = true;
                importer.materialImportMode = ModelImporterMaterialImportMode.None;
                importer.importCameras = false;
                importer.importLights = false;
                importer.meshCompression = ModelImporterMeshCompression.Low;
                importer.isReadable = false;
                importer.importNormals = ModelImporterNormals.Import;
                importer.importTangents = ModelImporterTangents.CalculateMikk;
                importer.generateSecondaryUV = false;
                importer.importAnimation = rider;
                importer.animationType = rider ? ModelImporterAnimationType.Generic : ModelImporterAnimationType.None;
                if (rider)
                {
                    importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                    importer.optimizeGameObjects = false; // Expose authored hand sockets for weapons.
                    importer.animationCompression = ModelImporterAnimationCompression.Optimal;
                    importer.animationRotationError = .15f;
                    importer.animationPositionError = .05f;
                    importer.animationScaleError = .05f;
                    importer.SaveAndReimport();
                    var clips = importer.defaultClipAnimations;
                    foreach (var clip in clips)
                    {
                        string clean = ClipNames.FirstOrDefault(n => clip.name.EndsWith(n, StringComparison.Ordinal));
                        if (clean == null) throw new InvalidOperationException("Unexpected hero animation take: " + clip.name);
                        clip.name = clean;
                        clip.loopTime = clean == "RB_Idle" || clean == "RB_Ride" || clean == "RB_Run" || clean.StartsWith("RB_Lean", StringComparison.Ordinal);
                        clip.loopPose = clip.loopTime;
                        clip.lockRootRotation = true;
                        clip.lockRootHeightY = true;
                        clip.lockRootPositionXZ = true;
                        clip.keepOriginalOrientation = true;
                        clip.keepOriginalPositionY = true;
                        clip.keepOriginalPositionXZ = true;
                    }
                    importer.clipAnimations = clips;
                }
                importer.SaveAndReimport();
                var material = CreateMaterial(MaterialName(name));
                var root = new GameObject(name);
                try
                {
                    var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
                    model.name = "Model";
                    model.transform.SetParent(root.transform, false);
                    model.transform.localRotation = Quaternion.Euler(0, 180, 0) * model.transform.localRotation;
                    foreach (var group in root.GetComponentsInChildren<LODGroup>(true)) UnityEngine.Object.DestroyImmediate(group);
                    var renderers = root.GetComponentsInChildren<Renderer>(true);
                    foreach (var renderer in renderers)
                    {
                        renderer.sharedMaterials = new[] {material};
                        renderer.enabled = true;
                        renderer.gameObject.SetActive(true);
                        renderer.shadowCastingMode = ShadowCastingMode.On;
                        renderer.receiveShadows = true;
                        renderer.lightProbeUsage = LightProbeUsage.BlendProbes;
                        renderer.reflectionProbeUsage = ReflectionProbeUsage.Simple;
                        if (renderer is SkinnedMeshRenderer skin)
                        {
                            skin.quality = SkinQuality.Bone2;
                            skin.updateWhenOffscreen = false;
                            // Stable armature space owns culling. Bone matrices and
                            // bindposes still reference the original 15 deform bones.
                            skin.rootBone = model.GetComponentsInChildren<Transform>(true).Single(t => t.name == "RB_P06_Rider_Rig");
                            // Includes authored lean/attack/kick/fall poses. Prevents an
                            // offscreen bind-pose AABB hiding an extended arm/weapon.
                            skin.localBounds = new Bounds(new Vector3(0, 0, .90f), new Vector3(2.3f, 2.4f, 2.5f));
                        }
                    }
                    var lods = new LOD[3];
                    var transitions = new[] {.22f, .085f, .012f};
                    for (int level = 0; level < 3; level++)
                    {
                        var members = renderers.Where(r => r.name.Contains("_L" + level + "_")).ToArray();
                        if (members.Length != (motorcycle ? 3 : 1)) throw new InvalidOperationException("Hero renderer budget mismatch: " + name);
                        lods[level] = new LOD(transitions[level], members);
                    }
                    var lodGroup = root.AddComponent<LODGroup>();
                    lodGroup.fadeMode = LODFadeMode.None;
                    lodGroup.SetLODs(lods);
                    lodGroup.RecalculateBounds();
                    if (rider)
                    {
                        // Explicit reference diameter keeps the animated conservative
                        // skin bounds from selecting an unnecessarily expensive LOD.
                        lodGroup.localReferencePoint = new Vector3(0, .90f, 0);
                        lodGroup.size = 1.8f;
                        var collider = root.AddComponent<CapsuleCollider>();
                        collider.center = new Vector3(0, .90f, 0);
                        collider.radius = .28f;
                        collider.height = 1.8f;
                        var animator = model.GetComponentInChildren<Animator>();
                        if (animator == null) throw new InvalidOperationException("Generic hero animator missing");
                        animator.applyRootMotion = false;
                        animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                        animator.runtimeAnimatorController = null; // Authority-tick playable graph owns sampling.
                        FitAndValidateSkinBounds(root, model, path, name);
                    }
                    else
                    {
                        var collider = root.AddComponent<BoxCollider>();
                        bool van = name.EndsWith("Van", StringComparison.Ordinal);
                        collider.center = motorcycle ? new Vector3(0, .64f, .03f) : new Vector3(0, van ? 1.145f : .68f, 0);
                        collider.size = motorcycle ? new Vector3(.82f, 1.28f, 2.17f) : new Vector3(van ? 2.31f : 2.16f, van ? 2.29f : 1.36f, van ? 4.64f : 4.54f);
                    }
                    foreach (var part in root.GetComponentsInChildren<Transform>(true)) part.gameObject.isStatic = false;
                    PrefabUtility.SaveAsPrefabAsset(root, PrefabFolder + name + ".prefab");
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(root);
                }
            }
            AssetDatabase.SaveAssets();
            Validate();
            Debug.Log("RB_P06_HERO_ASSETS_READY");
        }

        private static Material CreateMaterial(string name)
        {
            string path = MaterialFolder + name + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(material, path);
            }
            material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(ArtFolder + name + "_BaseColor.png"));
            material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(ArtFolder + SurfaceName(name) + "_Normal.png"));
            material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(ArtFolder + SurfaceName(name) + "_MetallicSmoothness.png"));
            material.SetFloat("_Smoothness", 1);
            material.SetFloat("_BumpScale", .65f);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void FitAndValidateSkinBounds(GameObject root, GameObject model, string path, string name)
        {
            var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>()
                .Where(c => ClipNames.Contains(c.name)).OrderBy(c => c.name).ToArray();
            if (clips.Length != ClipNames.Length) throw new InvalidOperationException("Cannot sample incomplete hero clips");
            var skins = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var transforms = model.GetComponentsInChildren<Transform>(true);
            var restRotations = transforms.Select(t => t.localRotation).ToArray();
            var restPositions = transforms.Select(t => t.localPosition).ToArray();
            var restScales = transforms.Select(t => t.localScale).ToArray();
            var fitted = new Bounds[skins.Length];
            var initialized = new bool[skins.Length];
            var baked = new Mesh();
            var clipChecks = new List<ClipReceipt>();
            try
            {
                clips.Single(c => c.name == "RB_Idle").SampleAnimation(model, 0);
                var idleRotations = transforms.Select(t => t.localRotation).ToArray();
                foreach (var clip in clips)
                {
                    float maxBoneDelta = 0, maxTemporalDelta = 0;
                    Quaternion[] firstSampleRotations = null;
                    for (int sample = 0; sample <= 16; sample++)
                    {
                        clip.SampleAnimation(model, clip.length * sample / 16f);
                        if (sample == 0) firstSampleRotations = transforms.Select(t => t.localRotation).ToArray();
                        for (int t = 0; t < transforms.Length; t++)
                            if (transforms[t].name.StartsWith("RB_P06_Rider_L0_", StringComparison.Ordinal))
                            {
                                maxBoneDelta = Mathf.Max(maxBoneDelta, Quaternion.Angle(idleRotations[t], transforms[t].localRotation));
                                maxTemporalDelta = Mathf.Max(maxTemporalDelta, Quaternion.Angle(firstSampleRotations[t], transforms[t].localRotation));
                            }
                        for (int s = 0; s < skins.Length; s++)
                        {
                            skins[s].BakeMesh(baked, false);
                            foreach (var vertex in baked.vertices)
                            {
                                if (float.IsNaN(vertex.x) || float.IsNaN(vertex.y) || float.IsNaN(vertex.z) || float.IsInfinity(vertex.x) || float.IsInfinity(vertex.y) || float.IsInfinity(vertex.z))
                                    throw new InvalidOperationException("Nonfinite posed vertex: " + name + "/" + clip.name);
                                // BakeMesh vertices use renderer space, whereas
                                // SkinnedMeshRenderer culling uses rootBone space.
                                var boundsSpace = skins[s].rootBone != null ? skins[s].rootBone : skins[s].transform;
                                var local = boundsSpace.InverseTransformPoint(skins[s].transform.TransformPoint(vertex));
                                if (!initialized[s]) { fitted[s] = new Bounds(local, Vector3.zero); initialized[s] = true; }
                                else fitted[s].Encapsulate(local);
                            }
                        }
                    }
                    int bindings = AnimationUtility.GetCurveBindings(clip).Length;
                    if (bindings == 0 || (clip.name != "RB_Idle" && maxBoneDelta < 2)) throw new InvalidOperationException("Hero clip did not bind to imported bones: " + clip.name);
                    bool constantPose = clip.name == "RB_Idle" || clip.name == "RB_Ride" || clip.name.StartsWith("RB_Lean", StringComparison.Ordinal);
                    if (!constantPose && maxTemporalDelta < 5) throw new InvalidOperationException("Hero motion clip does not animate across phases: " + clip.name);
                    clipChecks.Add(new ClipReceipt {name = clip.name, durationSeconds = clip.length, samples = 17, curveBindings = bindings, maxBoneRotationDegrees = maxBoneDelta, maxTemporalRotationDegrees = maxTemporalDelta});
                }
                for (int s = 0; s < skins.Length; s++)
                {
                    fitted[s].Expand(.20f);
                    skins[s].localBounds = fitted[s];
                }
                long checkedVertices = 0;
                foreach (var clip in clips)
                {
                    for (int sample = 0; sample <= 16; sample++)
                    {
                        clip.SampleAnimation(model, clip.length * sample / 16f);
                        foreach (var skin in skins)
                        {
                            skin.BakeMesh(baked, false);
                            var worldBounds = skin.bounds;
                            worldBounds.Expand(.002f);
                            foreach (var vertex in baked.vertices)
                            {
                                if (!worldBounds.Contains(skin.transform.TransformPoint(vertex))) throw new InvalidOperationException("Animated skin escapes imported renderer bounds: " + name + "/" + skin.name + "/" + clip.name + " rootBone=" + (skin.rootBone == null ? "null" : skin.rootBone.name) + " world=" + worldBounds + " local=" + skin.localBounds + " vertex=" + skin.transform.TransformPoint(vertex));
                                checkedVertices++;
                            }
                        }
                    }
                }
                Directory.CreateDirectory("docs/p06/hero");
                File.WriteAllText("docs/p06/hero/" + name + "-unity-poses.json", JsonUtility.ToJson(new PoseReceipt
                {
                    passed = true, name = name, method = "Imported Unity clips sampled at 17 phases; CPU BakeMesh linear skin; fitted bounds plus 10cm margin checked in renderer world bounds", checkedVertices = checkedVertices,
                    clips = clipChecks.ToArray(), skins = skins.Select((s, i) => new SkinReceipt {name = s.name, rootBone = s.rootBone == null ? null : s.rootBone.name, rendererLocalPosition = s.transform.localPosition, rendererLocalRotation = s.transform.localRotation, localBounds = fitted[i]}).ToArray()
                }, true));
            }
            finally
            {
                for (int i = 0; i < transforms.Length; i++)
                {
                    transforms[i].localPosition = restPositions[i];
                    transforms[i].localRotation = restRotations[i];
                    transforms[i].localScale = restScales[i];
                }
                UnityEngine.Object.DestroyImmediate(baked);
            }
        }

        [MenuItem("Racing Bois/P06/Validate Hero Assets")]
        public static void Validate()
        {
            var receipts = new List<AssetReceipt>();
            foreach (string name in AvailableAssets())
            {
                var root = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabFolder + name + ".prefab");
                if (root == null || root.transform.localPosition != Vector3.zero || root.transform.localRotation != Quaternion.identity || root.transform.localScale != Vector3.one)
                    throw new InvalidOperationException("Hero root must be identity: " + name);
                foreach (var transform in root.GetComponentsInChildren<Transform>(true))
                    if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(transform.gameObject) != 0) throw new InvalidOperationException("Missing hero script");
                var group = root.GetComponent<LODGroup>();
                if (group == null || group.lodCount != 3) throw new InvalidOperationException("Hero LOD count");
                var colliders = root.GetComponentsInChildren<Collider>(true);
                if (colliders.Length != 1 || colliders[0] is MeshCollider) throw new InvalidOperationException("Hero collider budget");
                var renderers = root.GetComponentsInChildren<Renderer>(true);
                if (renderers.Any(r => r.sharedMaterials.Length != 1 || r.sharedMaterial == null || r.sharedMaterial.shader == null) || renderers.Select(r => r.sharedMaterial).Distinct().Count() != 1)
                    throw new InvalidOperationException("Hero material budget");
                var material = renderers[0].sharedMaterial;
                if (material.GetTexture("_BaseMap") == null || material.GetTexture("_BumpMap") == null || material.GetTexture("_MetallicGlossMap") == null)
                    throw new InvalidOperationException("Hero PBR texture reference missing");
                foreach (var renderer in renderers)
                {
                    var mesh = GetMesh(renderer);
                    if (mesh == null || !mesh.HasVertexAttribute(VertexAttribute.Normal) || !mesh.HasVertexAttribute(VertexAttribute.Tangent) || !mesh.HasVertexAttribute(VertexAttribute.TexCoord0))
                        throw new InvalidOperationException("Hero mesh channels missing");
                }
                long[] triangles = group.GetLODs().Select(l => l.renderers.Sum(r => (long)GetMesh(r).GetIndexCount(0) / 3)).ToArray();
                if (triangles[0] <= triangles[1] || triangles[1] <= triangles[2]) throw new InvalidOperationException("Hero LOD reduction");
                var transforms = root.GetComponentsInChildren<Transform>(true);
                bool rider = name.EndsWith("Rider", StringComparison.Ordinal);
                string[] clips = Array.Empty<string>();
                if (rider)
                {
                    var skins = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                    if (skins.Length != 3 || skins.Any(s => s.bones.Length == 0 || s.bones.Any(b => b == null) || s.sharedMesh.bindposes.Length == 0)) throw new InvalidOperationException("Hero skin/rig incomplete");
                    var left = transforms.Single(t => t.name == "RB_P06_Rider_L0_Hand_L");
                    var right = transforms.Single(t => t.name == "RB_P06_Rider_L0_Hand_R");
                    if (left.position.x >= right.position.x) throw new InvalidOperationException("Hero hand axis contract");
                    var animator = root.GetComponentInChildren<Animator>();
                    if (animator == null || animator.avatar == null || !animator.avatar.isValid || animator.applyRootMotion) throw new InvalidOperationException("Generic avatar invalid");
                    clips = AssetDatabase.LoadAllAssetsAtPath(ArtFolder + SourceName(name) + ".fbx").OfType<AnimationClip>().Where(c => !c.name.StartsWith("__", StringComparison.Ordinal)).Select(c => c.name).OrderBy(n => n).ToArray();
                    if (clips.Length != ClipNames.Length || ClipNames.Any(n => !clips.Contains(n))) throw new InvalidOperationException("Hero animation clips incomplete: " + string.Join(",", clips));
                }
                else if (name.Contains("Motorcycle"))
                {
                    var front = transforms.Single(t => t.name.EndsWith("_Wheel_Front", StringComparison.Ordinal));
                    var rear = transforms.Single(t => t.name.EndsWith("_Wheel_Rear", StringComparison.Ordinal));
                    if (Vector3.Distance(front.position, new Vector3(0, .32f, .80f)) > .002f || Vector3.Distance(rear.position, new Vector3(0, .32f, -.73f)) > .002f)
                        throw new InvalidOperationException("Hero wheel scale/pivot/+Z contract");
                }
                else
                {
                    var front = transforms.Single(t => t.name == name + "_FrontMarker");
                    var rear = transforms.Single(t => t.name == name + "_RearMarker");
                    if (front.position.z <= rear.position.z || Mathf.Abs(front.position.y - .6f) > .002f) throw new InvalidOperationException("Traffic scale/+Z contract");
                    bool van = name.EndsWith("Van", StringComparison.Ordinal);
                    var collider = root.GetComponent<BoxCollider>();
                    var expected = new Vector3(van ? 2.31f : 2.16f, van ? 2.29f : 1.36f, van ? 4.64f : 4.54f);
                    if (collider == null || Vector3.Distance(collider.size, expected) > .001f) throw new InvalidOperationException("Traffic authority collider dimensions changed");
                    var geometry = group.GetLODs()[0].renderers[0].bounds;
                    var envelope = new Bounds(collider.center, collider.size + Vector3.one * .01f);
                    if (!envelope.Contains(geometry.min) || !envelope.Contains(geometry.max)) throw new InvalidOperationException("Traffic mesh protrudes beyond authority envelope: " + name + " " + geometry);
                }
                receipts.Add(new AssetReceipt {name = name, passed = true, lodTriangles = triangles, rendererCount = renderers.Length, materialCount = 1, colliderCount = 1, normalsTangentsUv = true, rootIdentity = true, skinned = rider, clips = clips});
            }
            Directory.CreateDirectory("docs/p06/hero");
            File.WriteAllText("docs/p06/hero/unity-validation.json", JsonUtility.ToJson(new Receipt {passed = true, unityVersion = Application.unityVersion, assets = receipts.ToArray()}, true));
            Debug.Log("RB_P06_HERO_VALIDATION_PASS");
        }

        private static Mesh GetMesh(Renderer renderer) => renderer is SkinnedMeshRenderer skin ? skin.sharedMesh : renderer.GetComponent<MeshFilter>().sharedMesh;
        [Serializable] private sealed class Receipt { public bool passed; public string unityVersion; public AssetReceipt[] assets; }
        [Serializable] private sealed class AssetReceipt { public string name; public bool passed, normalsTangentsUv, rootIdentity, skinned; public long[] lodTriangles; public int rendererCount, materialCount, colliderCount; public string[] clips; }
        [Serializable] private sealed class PoseReceipt { public bool passed; public string name, method; public long checkedVertices; public ClipReceipt[] clips; public SkinReceipt[] skins; }
        [Serializable] private sealed class ClipReceipt { public string name; public float durationSeconds, maxBoneRotationDegrees, maxTemporalRotationDegrees; public int samples, curveBindings; }
        [Serializable] private sealed class SkinReceipt { public string name, rootBone; public Vector3 rendererLocalPosition; public Quaternion rendererLocalRotation; public Bounds localBounds; }
    }
}
