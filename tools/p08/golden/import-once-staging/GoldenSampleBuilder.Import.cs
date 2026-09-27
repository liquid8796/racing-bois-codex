using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        public static string Import(string descriptorPath)
        {
            var receipt = new ImportReceipt
            {
                attemptId = Guid.NewGuid().ToString("N"), utc = DateTime.UtcNow.ToString("O"),
                unityVersion = Application.unityVersion, descriptor = descriptorPath
            };
            try
            {
                Require(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling,
                    "Golden import requires the Editor to be idle outside Play mode.");
                var descriptor = ReadDescriptor(descriptorPath);
                receipt.descriptorSha256 = Digest(descriptorPath);
                receipt.inputs = InputSnapshot(descriptorPath, descriptor);
                receipt.sourceFingerprint = Fingerprint(receipt.inputs);
                Directory.CreateDirectory(OutputRoot + "/Materials"); Directory.CreateDirectory(OutputRoot + "/Prefabs");
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                var assets = new List<AssetReceipt>();
                foreach (var spec in descriptor.assets)
                {
                    var materials = spec.materials.ToDictionary(m => m.sourceName, m => ImportMaterial(spec.id, m), StringComparer.Ordinal);
                    ImportModel(spec, materials);
                    CreatePrefab(spec, materials);
                    assets.Add(ValidateAsset(spec, materials));
                    // Save only this descriptor's generated materials; unrelated dirty assets belong to the user.
                    foreach (var material in materials.Values) AssetDatabase.SaveAssetIfDirty(material);
                }
                receipt.sourceBindingPassed = receipt.sourceFingerprint == Fingerprint(InputSnapshot(descriptorPath, descriptor));
                Require(receipt.sourceBindingPassed, "Golden authoring inputs changed during import.");
                receipt.assets = assets.ToArray();
                receipt.outputs = ImportedOutputSnapshot(descriptor);
                receipt.passed = true;
                WriteReceipt("import", receipt);
                return JsonUtility.ToJson(receipt, true);
            }
            catch (Exception error)
            {
                receipt.passed = false; receipt.failure = error.GetType().Name + ": " + error.Message;
                WriteReceipt("import", receipt); throw;
            }
        }

        private static void WriteReceipt(string name, ImportReceipt receipt)
        {
            Directory.CreateDirectory(ReceiptRoot);
            receipt.utc = DateTime.UtcNow.ToString("O");
            GoldenReceiptFiles.WriteAtomic(ReceiptRoot + "/" + name + "-" + receipt.attemptId + ".json", JsonUtility.ToJson(receipt, true));
            GoldenReceiptFiles.WriteAtomic(ReceiptRoot + "/" + name + "-latest.json", JsonUtility.ToJson(receipt, true));
        }

        private static Texture2D ImportTexture(InputFile file, int maximumSize, bool normal, bool color, bool alpha, bool constantMap = false)
        {
            Require(file.path.StartsWith("Assets/", StringComparison.Ordinal), "Texture input must be inside Assets: " + file.path);
            if (constantMap) ValidateConstantMapSource(file);
            var importer = AssetImporter.GetAtPath(file.path) as TextureImporter;
            Require(importer != null, "Texture importer is missing: " + file.path);
            string previousSettings = EditorJsonUtility.ToJson(importer);
            bool previousDirty = EditorUtility.IsDirty(importer);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = color;
            importer.convertToNormalmap = false;
            importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.isReadable = false;
            importer.alphaSource = alpha ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
            importer.alphaIsTransparency = false;
            importer.wrapMode = TextureWrapMode.Repeat; importer.filterMode = FilterMode.Trilinear; importer.anisoLevel = 8;
            importer.maxTextureSize = maximumSize; importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SetPlatformTextureSettings(new TextureImporterPlatformSettings
            {
                name = "Standalone", overridden = true, maxTextureSize = maximumSize,
                format = normal ? TextureImporterFormat.BC5 : TextureImporterFormat.BC7, compressionQuality = 100
            });
            ReimportChangedSettings(importer, previousSettings, previousDirty);
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(file.path);
            Require(texture != null && (constantMap ? texture.width == 4 && texture.height == 4 : texture.width >= 256 && texture.height >= 256),
                "Missing texture or dimensions outside declared texture policy: " + file.path);
            return texture;
        }

        private static Material ImportMaterial(string assetId, MaterialSpec spec)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            Require(shader != null, "URP Lit shader unavailable.");
            string path = OutputRoot + "/Materials/" + assetId + "_" + spec.sourceName + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(shader); AssetDatabase.CreateAsset(material, path);
                // Let the installed URP postprocessor add its version subasset before recording output hashes.
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                material = AssetDatabase.LoadAssetAtPath<Material>(path);
            }
            material.shader = shader;
            material.SetColor("_BaseColor", new Color(1, 1, 1, spec.opacity));
            material.SetTexture("_BaseMap", ImportTexture(spec.baseColor, spec.maxSize, false, true, spec.transparent, IsConstantMap(spec, "baseColor")));
            material.SetTexture("_BumpMap", ImportTexture(spec.normal, spec.maxSize, true, false, false, IsConstantMap(spec, "normal")));
            material.SetTexture("_MetallicGlossMap", ImportTexture(spec.metallicSmoothness, spec.maxSize, false, false, true, IsConstantMap(spec, "metallicSmoothness")));
            material.SetTexture("_OcclusionMap", HasInput(spec.occlusion) ? ImportTexture(spec.occlusion, spec.maxSize, false, false, false, IsConstantMap(spec, "occlusion")) : null);
            material.SetTexture("_EmissionMap", HasInput(spec.emission) ? ImportTexture(spec.emission, spec.maxSize, false, true, false, IsConstantMap(spec, "emission")) : null);
            material.SetColor("_EmissionColor", HasInput(spec.emission) ? Color.white * spec.emissionIntensity : Color.black);
            material.globalIlluminationFlags = HasInput(spec.emission)
                ? MaterialGlobalIlluminationFlags.RealtimeEmissive : MaterialGlobalIlluminationFlags.EmissiveIsBlack;
            material.SetFloat("_Smoothness", 1); material.SetFloat("_Metallic", 1); material.SetFloat("_SmoothnessTextureChannel", 0);
            material.SetFloat("_BumpScale", spec.normalScale); material.SetFloat("_OcclusionStrength", 1);
            material.SetFloat("_Cull", (float)(spec.doubleSided ? CullMode.Off : CullMode.Back)); material.SetFloat("_AlphaClip", 0);
            material.doubleSidedGI = spec.doubleSided;
            material.SetFloat("_Surface", spec.transparent ? 1 : 0); material.SetFloat("_Blend", 0);
            material.SetFloat("_SrcBlend", (float)(spec.transparent ? BlendMode.SrcAlpha : BlendMode.One));
            material.SetFloat("_DstBlend", (float)(spec.transparent ? BlendMode.OneMinusSrcAlpha : BlendMode.Zero));
            material.SetFloat("_ZWrite", spec.transparent ? 0 : 1);
            material.SetOverrideTag("RenderType", spec.transparent ? "Transparent" : "Opaque");
            material.renderQueue = (int)(spec.transparent ? RenderQueue.Transparent : RenderQueue.Geometry);
            SetKeyword(material, "_SURFACE_TYPE_TRANSPARENT", spec.transparent);
            SetKeyword(material, "_NORMALMAP", true); SetKeyword(material, "_METALLICSPECGLOSSMAP", true);
            SetKeyword(material, "_OCCLUSIONMAP", HasInput(spec.occlusion)); SetKeyword(material, "_EMISSION", HasInput(spec.emission));
            SetKeyword(material, "_ALPHATEST_ON", false); SetKeyword(material, "_ALPHAPREMULTIPLY_ON", false);
            SetKeyword(material, "_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A", false);
            material.SetShaderPassEnabled("ShadowCaster", !spec.transparent);
            // URP owns dependent blend keywords, alpha blend factors, depth/motion passes and GI flags.
            // Finalize them now, rather than allowing a later Inspector/render refresh to mutate a signed result.
            FinalizeUrpMaterial(material);
            material.enableInstancing = true; EditorUtility.SetDirty(material);
            return material;
        }

        private static void FinalizeUrpMaterial(Material material)
        {
            var materialEditor = UnityEditor.Editor.CreateEditor(material) as MaterialEditor;
            try
            {
                Require(materialEditor != null && materialEditor.customShaderGUI != null, "Installed URP material validator unavailable.");
                materialEditor.customShaderGUI.ValidateMaterial(material);
            }
            finally { if (materialEditor != null) UnityEngine.Object.DestroyImmediate(materialEditor); }
        }

        private static void SetKeyword(Material material, string keyword, bool enabled)
        { if (enabled) material.EnableKeyword(keyword); else material.DisableKeyword(keyword); }

        private static void ReimportChangedSettings(AssetImporter importer, string previousSettings, bool previousDirty)
        {
            // The operation begins with a synchronous AssetDatabase refresh, so source-file changes
            // are already imported. Do not recompress unchanged textures or regenerate unchanged lightmap UVs.
            if (!string.Equals(previousSettings, EditorJsonUtility.ToJson(importer), StringComparison.Ordinal))
                importer.SaveAndReimport();
            else if (EditorUtility.IsDirty(importer) != previousDirty)
            {
                // Idempotent setters can dirty the importer without changing settings.
                // Restore only the flag we observed; never clear a pre-existing dirty edit.
                if (previousDirty) EditorUtility.SetDirty(importer);
                else EditorUtility.ClearDirty(importer);
            }
        }

        private static void ImportModel(AssetSpec spec, Dictionary<string, Material> materials)
        {
            var importer = AssetImporter.GetAtPath(spec.fbx.path) as ModelImporter;
            Require(importer != null, "FBX importer missing: " + spec.fbx.path);
            string previousSettings = EditorJsonUtility.ToJson(importer);
            bool previousDirty = EditorUtility.IsDirty(importer);
            // Import starts with a synchronous source refresh. A fresh, unmapped model can
            // therefore prove its used embedded material identities before changing settings.
            // Never infer original names from an external/generated material after remapping.
            bool combineFreshMaterialRemaps = HasFreshEmbeddedMaterialSources(importer, spec, materials);
            importer.globalScale = 1; importer.useFileScale = true; importer.bakeAxisConversion = true;
            importer.importCameras = false; importer.importLights = false; importer.importVisibility = false;
            importer.meshCompression = ModelImporterMeshCompression.Off;
            // CPU mesh access is intentionally retained for an inspection asset, not prescribed for shipping assets.
            importer.isReadable = true;
            importer.importNormals = ModelImporterNormals.Import; importer.importTangents = ModelImporterTangents.CalculateMikk;
            importer.generateSecondaryUV = spec.isStatic && spec.lightmapUv == "generated";
            importer.importAnimation = spec.kind == "rider";
            if (spec.kind == "rider") importer.animationCompression = ModelImporterAnimationCompression.Off;
            importer.importBlendShapes = spec.kind == "rider";
            importer.animationType = spec.kind == "rider" ? ModelImporterAnimationType.Generic : ModelImporterAnimationType.None;
            if (spec.kind == "rider") importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            ApplyAnimationPolicy(importer, spec);
            importer.optimizeGameObjects = false;
            importer.skinWeights = ModelImporterSkinWeights.Custom; importer.maxBonesPerVertex = 4; importer.minBoneWeight = .001f;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
            var currentRemaps = importer.GetExternalObjectMap().Where(entry => entry.Key.type == typeof(Material)).ToArray();
            bool mappingsMatch = currentRemaps.Length == materials.Count && currentRemaps.All(entry =>
                materials.TryGetValue(entry.Key.name, out var expected) && entry.Value == expected);
            if (!mappingsMatch)
                foreach (var remap in currentRemaps) importer.RemoveRemap(remap.Key);
            if (combineFreshMaterialRemaps)
            {
                foreach (var material in materials)
                    importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), material.Key), material.Value);
                // This branch necessarily adds remaps to an empty map. Save once with the
                // final settings and bindings, so generated lightmap UVs run only once.
                importer.SaveAndReimport();
                ValidateRemappedModelMaterialSet(AssetDatabase.LoadAssetAtPath<GameObject>(spec.fbx.path), spec, materials);
                return;
            }
            ReimportChangedSettings(importer, previousSettings, previousDirty);
            var imported = AssetDatabase.LoadAssetAtPath<GameObject>(spec.fbx.path);
            if (mappingsMatch)
            {
                ValidateRemappedModelMaterialSet(imported, spec, materials);
                return;
            }
            var sourceNames = imported.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials)
                .Select(material => material == null ? "" : material.name).Distinct(StringComparer.Ordinal).ToArray();
            Require(sourceNames.Length == materials.Count && sourceNames.All(materials.ContainsKey),
                "FBX material slots differ from descriptor: " + spec.id + " [" + string.Join(", ", sourceNames) + "]");
            foreach (var material in materials)
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), material.Key), material.Value);
            importer.SaveAndReimport();
        }

        private static bool HasFreshEmbeddedMaterialSources(ModelImporter importer, AssetSpec spec, Dictionary<string, Material> materials)
        {
            // Any remap, including a non-material override, keeps the existing strict path.
            // GetExternalObjectMap exposes bindings, not the model's original source list.
            if (importer.GetExternalObjectMap().Count != 0) return false;
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(spec.fbx.path);
            if (model == null) return false;
            var renderers = model.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) return false;
            var slots = renderers.SelectMany(renderer => renderer.sharedMaterials).ToArray();
            if (slots.Length == 0 || slots.Any(material => material == null || !AssetDatabase.IsSubAsset(material)
                || !string.Equals(AssetDatabase.GetAssetPath(material), spec.fbx.path, StringComparison.Ordinal))) return false;
            var embedded = slots.Distinct().ToArray();
            var names = embedded.Select(material => material.name).ToArray();
            // Two distinct embedded assets sharing a name are ambiguous for a name-keyed remap.
            if (names.Any(string.IsNullOrEmpty) || names.Distinct(StringComparer.Ordinal).Count() != names.Length) return false;
            Require(names.Length == materials.Count && names.All(materials.ContainsKey),
                "FBX embedded source material slots differ from descriptor: " + spec.id + " [" + string.Join(", ", names) + "]");
            return true;
        }

        private static void ValidateRemappedModelMaterialSet(GameObject model, AssetSpec spec, Dictionary<string, Material> materials)
        {
            Require(model != null, "Remapped FBX model is missing: " + spec.id);
            var actual = model.GetComponentsInChildren<Renderer>(true).SelectMany(renderer => renderer.sharedMaterials).Distinct().ToArray();
            Require(actual.Length == materials.Count && actual.All(materials.ContainsValue),
                "Remapped FBX material set differs from descriptor: " + spec.id);
        }

        private static string PrefabPath(AssetSpec spec) => OutputRoot + "/Prefabs/" + spec.id + ".prefab";

        private static void CreatePrefab(AssetSpec spec, Dictionary<string, Material> materials)
        {
            var root = new GameObject(spec.id);
            try
            {
                var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(spec.fbx.path));
                model.name = "Model"; model.transform.SetParent(root.transform, false);
                model.transform.localRotation = Quaternion.Euler(spec.modelRotationEuler) * model.transform.localRotation;
                foreach (var lod in model.GetComponentsInChildren<LODGroup>(true)) UnityEngine.Object.DestroyImmediate(lod);
                var renderers = model.GetComponentsInChildren<Renderer>(true);
                foreach (var renderer in renderers)
                {
                    Require(renderer.sharedMaterials.All(materials.ContainsValue), "Unmapped source material: " + renderer.name);
                    renderer.enabled = true; renderer.gameObject.SetActive(true);
                    renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true;
                    renderer.lightProbeUsage = LightProbeUsage.BlendProbes; renderer.reflectionProbeUsage = ReflectionProbeUsage.BlendProbes;
                    if (renderer is SkinnedMeshRenderer skin)
                    {
                        skin.quality = SkinQuality.Bone4; skin.updateWhenOffscreen = false;
                        skin.rootBone = Find(model.transform, spec.rigRoot);
                    }
                }
                if (HasInput(spec.moduleLodMap))
                    CreateModuleLodGroups(root, model.transform, spec, ReadModuleLodMap(spec.moduleLodMap, spec));
                else
                {
                    var group = root.AddComponent<LODGroup>();
                    group.fadeMode = LODFadeMode.CrossFade; group.animateCrossFading = true;
                    group.SetLODs(spec.lods.Select(lod => new LOD(lod.height,
                        lod.rendererPaths.Select(path => FindRenderer(model.transform, path)).ToArray()) { fadeTransitionWidth = .15f }).ToArray());
                    group.RecalculateBounds();
                }
                foreach (var animator in model.GetComponentsInChildren<Animator>(true))
                { animator.applyRootMotion = false; animator.runtimeAnimatorController = null; animator.cullingMode = AnimatorCullingMode.AlwaysAnimate; }
                if (spec.kind == "rider")
                {
                    var clips = spec.clips.Select(clipSpec => AssetDatabase.LoadAllAssetsAtPath(clipSpec.path)
                        .OfType<AnimationClip>().Single(clip => clip.name == clipSpec.name)).ToArray();
                    root.AddComponent<RacingBois.Client.Presentation.RiderAnimationSet>().Configure(clips, spec.fallenRootOffset);
                }
                foreach (var collider in spec.colliders ?? Array.Empty<ColliderSpec>())
                {
                    if (collider.type == "box") { var component = root.AddComponent<BoxCollider>(); component.center = collider.center; component.size = collider.size; }
                    else { var component = root.AddComponent<CapsuleCollider>(); component.center = collider.center; component.radius = collider.radius; component.height = collider.height; component.direction = collider.direction; }
                }
                foreach (var child in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(child.gameObject, spec.isStatic
                        ? StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic |
                            (spec.lightmapUv == "none" ? 0 : StaticEditorFlags.ContributeGI) : 0);
                RestoreDeclaredRestPose(model, spec);
                if (spec.kind == "rider") SampleAnimations(model, spec, true);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(spec));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        private static Transform Find(Transform root, string path)
        {
            var result = path == "." ? root : root.Find(path);
            Require(result != null, "Missing declared model transform: " + path);
            return result;
        }
        private static Renderer FindRenderer(Transform root, string path)
        {
            var result = Find(root, path).GetComponent<Renderer>();
            Require(result != null, "Declared transform has no renderer: " + path); return result;
        }
    }
}
