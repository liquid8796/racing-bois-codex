using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using RacingBois.Golden;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        private const string GarageBakeSessionKey = "RacingBois.Golden.GarageBake.v1";

        [Serializable] public sealed class GarageRecipe
        {
            public int schema;
            public InputFile source, descriptor, lockedUi;
            public float[] cameraPositionUnity, cameraTargetUnity, ambientColorLinear;
            public float cameraFocalLengthMm, sensorWidthMm, aspect, ambientStrength;
            public GarageArea[] areaLights;
            public GarageProbe reflectionProbe;
            public float unityLightmapTexelsPerMetre = 24, diagnosticFillIntensity;
            public float postExposure, bloomIntensity;
            public float reflectionEmissionMultiplier = 1;
            public float realtimeDoorKeyIntensity;
            public bool staticShadowsBakedOnly;
            public bool toneMappingAces;
            public int unityLightmapMaxSize = 2048, unityDirectSamples = 64, unityIndirectSamples = 256;
        }
        [Serializable] public sealed class GarageArea
        {
            public string name;
            public float[] positionUnity, targetUnity, colorLinear;
            public float widthMetres, heightMetres, blenderWatts;
            public float unityIntensity = float.NaN;
        }
        [Serializable] public sealed class GarageProbe
        {
            public float[] positionUnity, sizeMetres;
            public bool boxProjection;
            public float near, far;
            public int suggestedResolution;
        }
        [Serializable] private sealed class GarageSceneState
        { public string path; public bool isLoaded, isActive; }
        [Serializable] private sealed class GarageBakeSession
        {
            public string descriptorPath, descriptorSha256, recipePath, recipeSha256, scenePath, sceneBeforeBakeSha256, startUtc;
            public GarageSceneState[] originals;
        }
        [Serializable] private sealed class GarageBakeReport
        {
            public bool passed, visualAccepted;
            public string utc, descriptor, recipe, scene;
            public int lightmaps, lightmappedRenderers, secondaryUvCheckedRenderers;
            public FileReceipt[] bakedInputs;
            public string scope = "Native indoor lighting data and renderer binding only. No concept fidelity or performance acceptance.";
        }

        private static GarageRecipe ReadGarageRecipe(string descriptorPath, string recipePath)
        {
            ProjectPath(recipePath, false);
            var recipe = JsonUtility.FromJson<GarageRecipe>(File.ReadAllText(recipePath));
            Require(recipe != null && recipe.schema == 1, "Unsupported indoor recipe schema.");
            VerifyInput(recipe.source); VerifyInput(recipe.descriptor); VerifyInput(recipe.lockedUi);
            Require(recipe.descriptor.path == descriptorPath && recipe.descriptor.sha256 == Digest(descriptorPath), "Indoor recipe binds another descriptor.");
            var descriptor = ReadDescriptor(descriptorPath);
            Require(descriptor.assets.Length == 1 && descriptor.assets[0].kind == "environment", "Garage needs one imported environment.");
            Require(descriptor.assets[0].isStatic && descriptor.assets[0].lightmapUv != "none", "Baked garage lighting requires an explicit lightmap UV policy.");
            Require(recipe.source.path == descriptor.assets[0].source.path && recipe.source.sha256 == descriptor.assets[0].source.sha256, "Indoor authoring source mismatch.");
            Require(recipe.areaLights != null && recipe.areaLights.Length == 7, "Indoor recipe needs six strip emitters and one doorway fill.");
            Require(recipe.areaLights.Select(a => a.name).Distinct(StringComparer.Ordinal).Count() == 7, "Duplicate indoor emitter name.");
            Require(recipe.areaLights.Take(6).Select(a => a.name).SequenceEqual(Enumerable.Range(0, 6).Select(i => "Practical_" + i)) && recipe.areaLights[6].name == "DoorSoftAmbient", "Unexpected emitter ownership.");
            foreach (var area in recipe.areaLights)
            {
                Require(Vector3.Distance(RecipeVector(area.positionUnity), RecipeVector(area.targetUnity)) > .1f, "Invalid area direction.");
                RecipeColor(area.colorLinear);
                Require(FiniteFloat(area.widthMetres) && area.widthMetres > .01f && area.widthMetres <= 8 &&
                    FiniteFloat(area.heightMetres) && area.heightMetres > .01f && area.heightMetres <= 8, "Invalid emitter size.");
                Require(FiniteFloat(area.unityIntensity) && area.unityIntensity > 0 && area.unityIntensity <= 100,
                    "Explicit calibrated or diagnostic Unity intensity required; Blender watts are never copied implicitly.");
            }
            Require(Vector3.Distance(RecipeVector(recipe.cameraPositionUnity), RecipeVector(recipe.cameraTargetUnity)) > 1, "Invalid garage camera.");
            Require(recipe.cameraFocalLengthMm >= 10 && recipe.cameraFocalLengthMm <= 150 && recipe.sensorWidthMm >= 10 && recipe.sensorWidthMm <= 80 && recipe.aspect > .5f && recipe.aspect < 4, "Invalid camera intrinsics.");
            RecipeColor(recipe.ambientColorLinear);
            Require(FiniteFloat(recipe.ambientStrength) && recipe.ambientStrength >= 0 && recipe.ambientStrength <= 1, "Invalid ambient intensity.");
            Require(FiniteFloat(recipe.diagnosticFillIntensity) && recipe.diagnosticFillIntensity >= 0 && recipe.diagnosticFillIntensity <= 2, "Invalid diagnostic fill.");
            Require(FiniteFloat(recipe.postExposure) && recipe.postExposure >= -3 && recipe.postExposure <= 3 &&
                FiniteFloat(recipe.bloomIntensity) && recipe.bloomIntensity >= 0 && recipe.bloomIntensity <= 1, "Unbounded indoor post processing.");
            Require(FiniteFloat(recipe.reflectionEmissionMultiplier) && recipe.reflectionEmissionMultiplier >= 1 && recipe.reflectionEmissionMultiplier <= 64,
                "Unbounded reflection-emitter calibration.");
            Require(FiniteFloat(recipe.realtimeDoorKeyIntensity) && recipe.realtimeDoorKeyIntensity >= 0 && recipe.realtimeDoorKeyIntensity <= 2,
                "Unbounded realtime door key.");
            Require(recipe.unityLightmapTexelsPerMetre >= 8 && recipe.unityLightmapTexelsPerMetre <= 64 &&
                (recipe.unityLightmapMaxSize == 1024 || recipe.unityLightmapMaxSize == 2048) &&
                recipe.unityDirectSamples >= 16 && recipe.unityDirectSamples <= 512 && recipe.unityIndirectSamples >= 32 && recipe.unityIndirectSamples <= 1024, "Unbounded indoor bake settings.");
            Require(recipe.reflectionProbe != null, "Indoor local reflection probe required.");
            var size = RecipeVector(recipe.reflectionProbe.sizeMetres); RecipeVector(recipe.reflectionProbe.positionUnity);
            Require(size.x > 0 && size.y > 0 && size.z > 0 && size.magnitude < 50 && recipe.reflectionProbe.boxProjection &&
                recipe.reflectionProbe.near >= .01f && recipe.reflectionProbe.far > 5 && recipe.reflectionProbe.far <= 80 &&
                (recipe.reflectionProbe.suggestedResolution == 128 || recipe.reflectionProbe.suggestedResolution == 256), "Invalid bounded indoor probe.");
            return recipe;
        }

        /// <summary>Builds a separate indoor specimen. Its scene receipt remains failed until a real light bake is verified.</summary>
        public static string CreateGarageReviewScene(string descriptorPath, string recipePath)
        {
            GarageRequireIdle(); Validate(descriptorPath);
            Require(string.IsNullOrEmpty(SessionState.GetString(GarageBakeSessionKey, "")), "Complete or cancel the existing garage bake first.");
            var recipe = ReadGarageRecipe(descriptorPath, recipePath); var spec = ReadDescriptor(descriptorPath).assets[0];
            var recipeFile = FileRow(recipePath); var original = SceneManager.GetActiveScene();
            string lightingFolder = OutputRoot + "/Garage/" + spec.id + "_" + recipeFile.sha256.Substring(0, 12);
            string garageScenePath = lightingFolder + "/GarageReview.unity";
            Require(!Directory.Exists(lightingFolder) || !Directory.EnumerateFileSystemEntries(lightingFolder).Any(), "Preserve the existing indoor lighting revision; use a new recipe hash.");
            Directory.CreateDirectory(lightingFolder); AssetDatabase.Refresh();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            try
            {
                SceneManager.SetActiveScene(scene); AddReviewPipeline(false);
                var room = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(spec)), scene);
                room.name = spec.id;
                var lods = HasInput(spec.moduleLodMap) ? ModuleInspectionLods(room, spec, ReadModuleLodMap(spec.moduleLodMap, spec)) : room.GetComponent<LODGroup>().GetLODs();
                var high = new HashSet<Renderer>(lods[0].renderers);
                var emissiveCopies = new Dictionary<Material, Material>();
                foreach (var renderer in room.GetComponentsInChildren<MeshRenderer>(true))
                {
                    bool isHigh = high.Contains(renderer);
                    GameObjectUtility.SetStaticEditorFlags(renderer.gameObject, StaticEditorFlags.ReflectionProbeStatic | (isHigh ? StaticEditorFlags.ContributeGI : 0));
                    renderer.receiveGI = isHigh ? ReceiveGI.Lightmaps : ReceiveGI.LightProbes;
                    renderer.scaleInLightmap = isHigh ? 1f : 0f;
                    renderer.lightProbeUsage = LightProbeUsage.BlendProbes;
                    if (isHigh) GarageCheckSecondaryUv(renderer);
                    var assigned = renderer.sharedMaterials;
                    for (int i = 0; i < assigned.Length; i++)
                    {
                        var source = assigned[i];
                        if (!source.HasProperty("_EmissionMap") || source.GetTexture("_EmissionMap") == null) continue;
                        if (!emissiveCopies.TryGetValue(source, out var copy))
                        {
                            copy = new Material(source) { name = source.name + "_BakedGarage", globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive };
                            copy.EnableKeyword("_EMISSION");
                            string copyPath = lightingFolder + "/" + copy.name + ".mat";
                            AssetDatabase.CreateAsset(copy, copyPath);
                            AssetDatabase.ImportAsset(copyPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                            copy = AssetDatabase.LoadAssetAtPath<Material>(copyPath);
                            copy.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
                            FinalizeUrpMaterial(copy); EditorUtility.SetDirty(copy);
                            emissiveCopies.Add(source, copy);
                        }
                        assigned[i] = copy;
                    }
                    renderer.sharedMaterials = assigned;
                }
                var camera = new GameObject("Garage Reference Camera").AddComponent<Camera>();
                camera.tag = "MainCamera"; camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = Color.black;
                camera.allowHDR = true; camera.allowMSAA = true; camera.nearClipPlane = .03f; camera.farClipPlane = 50;
                var position = RecipeVector(recipe.cameraPositionUnity); var target = RecipeVector(recipe.cameraTargetUnity);
                camera.transform.position = position; camera.transform.LookAt(target);
                float fov = 2 * Mathf.Atan(recipe.sensorWidthMm / recipe.aspect / (2 * recipe.cameraFocalLengthMm)) * Mathf.Rad2Deg;
                camera.fieldOfView = fov;
                camera.GetUniversalAdditionalCameraData().renderPostProcessing = true;
                var volume = new GameObject("Garage Reference Post Processing").AddComponent<Volume>();
                volume.isGlobal = true;
                var profile = ScriptableObject.CreateInstance<VolumeProfile>();
                profile.name = "PostProcessing";
                AssetDatabase.CreateAsset(profile, lightingFolder + "/PostProcessing.asset");
                var exposure = profile.Add<ColorAdjustments>(true); exposure.postExposure.Override(recipe.postExposure);
                var bloom = profile.Add<Bloom>(true); bloom.intensity.Override(recipe.bloomIntensity); bloom.threshold.Override(.8f); bloom.scatter.Override(.6f);
                var tone = profile.Add<Tonemapping>(true); tone.mode.Override(recipe.toneMappingAces ? TonemappingMode.ACES : TonemappingMode.None);
                foreach (var component in profile.components) AssetDatabase.AddObjectToAsset(component, profile);
                EditorUtility.SetDirty(profile); AssetDatabase.SaveAssetIfDirty(profile); volume.sharedProfile = profile;
                foreach (var area in recipe.areaLights)
                {
                    var light = new GameObject(area.name + " - Baked Area").AddComponent<Light>();
                    light.type = LightType.Rectangle; light.lightmapBakeType = LightmapBakeType.Baked;
                    light.transform.position = RecipeVector(area.positionUnity); light.transform.LookAt(RecipeVector(area.targetUnity));
                    light.areaSize = new Vector2(area.widthMetres, area.heightMetres);
                    light.color = RecipeColor(area.colorLinear); light.intensity = area.unityIntensity; light.bounceIntensity = 1; light.shadows = LightShadows.Soft;
                }
                if (recipe.realtimeDoorKeyIntensity > 0)
                {
                    // A bounded directional approximation of the broad open doorway
                    // supplies dynamic actor highlights/contact shadows; baked area
                    // lights cannot shadow a bike instantiated later by the garage UI.
                    var door = recipe.areaLights[6];
                    var key = new GameObject("Realtime Door Key - Dynamic Actor Shadows").AddComponent<Light>();
                    key.type = LightType.Directional; key.lightmapBakeType = LightmapBakeType.Realtime;
                    key.transform.position = RecipeVector(door.positionUnity); key.transform.LookAt(RecipeVector(door.targetUnity));
                    key.color = RecipeColor(door.colorLinear); key.intensity = recipe.realtimeDoorKeyIntensity;
                    key.shadows = LightShadows.Soft; key.shadowBias = .5f; key.shadowNormalBias = .5f;
                    RenderSettings.sun = key;
                }
                if (recipe.diagnosticFillIntensity > 0)
                {
                    var fill = new GameObject("Diagnostic Realtime Door Fill - Not Baked Area Parity").AddComponent<Light>();
                    fill.type = LightType.Spot; fill.lightmapBakeType = LightmapBakeType.Realtime;
                    fill.transform.position = RecipeVector(recipe.areaLights[6].positionUnity); fill.transform.LookAt(RecipeVector(recipe.areaLights[6].targetUnity));
                    fill.color = RecipeColor(recipe.areaLights[6].colorLinear); fill.intensity = recipe.diagnosticFillIntensity;
                    fill.range = 18; fill.spotAngle = 100; fill.innerSpotAngle = 60; fill.shadows = LightShadows.Soft;
                }
                RenderSettings.skybox = null; if (recipe.realtimeDoorKeyIntensity <= 0) RenderSettings.sun = null; RenderSettings.fog = false;
                RenderSettings.ambientMode = AmbientMode.Flat;
                RenderSettings.ambientLight = RecipeColor(recipe.ambientColorLinear) * recipe.ambientStrength;
                var probe = new GameObject("Garage Local Baked Reflection").AddComponent<ReflectionProbe>();
                probe.mode = ReflectionProbeMode.Baked; probe.boxProjection = true; probe.resolution = recipe.reflectionProbe.suggestedResolution;
                probe.transform.position = RecipeVector(recipe.reflectionProbe.positionUnity); probe.size = RecipeVector(recipe.reflectionProbe.sizeMetres);
                probe.nearClipPlane = recipe.reflectionProbe.near; probe.farClipPlane = recipe.reflectionProbe.far;
                probe.clearFlags = ReflectionProbeClearFlags.SolidColor; probe.backgroundColor = Color.black;
                var probes = new GameObject("Garage Dynamic Actor Light Probes").AddComponent<LightProbeGroup>();
                var positions = new List<Vector3>();
                foreach (float x in new[] { -2f, 0f, 3f }) foreach (float y in new[] { .25f, 1.2f, 2.4f }) foreach (float z in new[] { -3f, 0f, 2.7f }) positions.Add(new Vector3(x, y, z));
                probes.probePositions = positions.ToArray();
                var settings = new LightingSettings
                {
                    bakedGI = true, realtimeGI = false,
                    lightmapper = LightingSettings.Lightmapper.ProgressiveCPU,
                    lightmapResolution = recipe.unityLightmapTexelsPerMetre, lightmapMaxSize = recipe.unityLightmapMaxSize,
                    directSampleCount = recipe.unityDirectSamples, indirectSampleCount = recipe.unityIndirectSamples,
                    environmentSampleCount = 64, maxBounces = 4, ao = false
                };
                string settingsPath = lightingFolder + "/LightingSettings.lighting";
                Require(!File.Exists(settingsPath), "This recipe already has lighting settings; preserve it and use a new recipe revision.");
                AssetDatabase.CreateAsset(settings, settingsPath); Lightmapping.lightingSettings = settings;
                var controls = new GameObject("Garage Review Controls").AddComponent<GoldenReviewController>();
                controls.ReviewCamera = camera; controls.gameObject.AddComponent<GoldenCaptureRunner>();
                var bounds = CurrentGeometryBounds(lods[0].renderers[0]);
                foreach (var r in lods[0].renderers.Skip(1)) bounds.Encapsulate(CurrentGeometryBounds(r));
                controls.Subjects = new[] { new GoldenReviewController.Subject { Id = spec.id, Root = room, Center = bounds.center, Size = bounds.size, IsEnvironment = true, GameplayPosition = position, GameplayTarget = target, GameplayVerticalFov = fov } };
                EditorSceneManager.MarkSceneDirty(scene); Require(EditorSceneManager.SaveScene(scene, garageScenePath), "Garage scene save failed.");
                AssetDatabase.SaveAssets(); Require(recipeFile.sha256 == Digest(recipePath), "Indoor recipe changed during creation.");
                var initialInputs = new[] { recipeFile, FileRow(settingsPath), FileRow(recipe.lockedUi.path), FileRow(AssetDatabase.GetAssetPath(profile)) }.Concat(emissiveCopies.Values.Select(m => FileRow(AssetDatabase.GetAssetPath(m)))).ToArray();
                var receipt = new SceneReceipt { passed = false, utc = DateTime.UtcNow.ToString("O"), scene = garageScenePath, sceneSha256 = Digest(garageScenePath), descriptor = descriptorPath, descriptorSha256 = Digest(descriptorPath), assetIds = new[] { spec.id }, additionalInputs = initialInputs };
                Directory.CreateDirectory(ReceiptRoot); string json = JsonUtility.ToJson(receipt, true); File.WriteAllText(ReceiptRoot + "/scene-latest.json", json); return json;
            }
            finally { if (original.IsValid() && original.isLoaded) SceneManager.SetActiveScene(original); EditorSceneManager.CloseScene(scene, true); }
        }

        /// <summary>Closes only saved scenes for an isolated asynchronous bake; explicit completion restores their setup.</summary>
        public static string StartGarageReviewBake(string descriptorPath, string recipePath)
        {
            GarageRequireIdle(); Validate(descriptorPath); ReadGarageRecipe(descriptorPath, recipePath);
            Require(!Lightmapping.isRunning && string.IsNullOrEmpty(SessionState.GetString(GarageBakeSessionKey, "")), "Another bake is active.");
            var receipt = JsonUtility.FromJson<SceneReceipt>(File.ReadAllText(ReceiptRoot + "/scene-latest.json"));
            string scenePath = BoundReviewScenePath(receipt);
            Require(scenePath.StartsWith(OutputRoot + "/Garage/", StringComparison.Ordinal), "Garage scene must own its bake-output directory.");
            Require(receipt.descriptor == descriptorPath && receipt.descriptorSha256 == Digest(descriptorPath) && receipt.sceneSha256 == Digest(scenePath), "Garage scene provenance changed.");
            Require(receipt.additionalInputs.Any(f => f.path == recipePath && f.sha256 == Digest(recipePath)), "Scene does not bind this indoor recipe.");
            foreach (var input in receipt.additionalInputs) Require(input.sha256 == Digest(input.path), "Indoor pre-bake input changed: " + input.path);
            var originals = EditorSceneManager.GetSceneManagerSetup();
            Require(originals.All(s => !string.IsNullOrEmpty(s.path)), "Save untitled scenes before isolated lighting work.");
            var session = new GarageBakeSession { descriptorPath = descriptorPath, descriptorSha256 = Digest(descriptorPath), recipePath = recipePath, recipeSha256 = Digest(recipePath), scenePath = scenePath, sceneBeforeBakeSha256 = Digest(scenePath), startUtc = DateTime.UtcNow.ToString("O"), originals = originals.Select(s => new GarageSceneState { path = s.path, isActive = s.isActive, isLoaded = s.isLoaded }).ToArray() };
            SessionState.SetString(GarageBakeSessionKey, JsonUtility.ToJson(session)); bool started = false;
            try
            {
                var scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
                Require(SceneManager.sceneCount == 1 && scene.path == scenePath, "Other scenes must not contribute to the garage bake.");
                foreach (var group in scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<LODGroup>(true))) group.ForceLOD(0);
                receipt.passed = false; File.WriteAllText(ReceiptRoot + "/scene-latest.json", JsonUtility.ToJson(receipt, true));
                started = Lightmapping.BakeAsync(); Require(started, "Unity did not start the indoor bake.");
                return "Garage bake started. Poll Lightmapping.isRunning; then call CompleteGarageReviewBake. Original saved scenes will be restored there.";
            }
            finally { if (!started) RestoreGarageScenes(session); }
        }

        public static string CompleteGarageReviewBake()
        {
            Require(!Lightmapping.isRunning, "Lighting bake is still running.");
            var text = SessionState.GetString(GarageBakeSessionKey, ""); Require(!string.IsNullOrEmpty(text), "No bound garage bake session.");
            var session = JsonUtility.FromJson<GarageBakeSession>(text);
            try
            {
                Require(session.descriptorSha256 == Digest(session.descriptorPath) && session.recipeSha256 == Digest(session.recipePath), "Bake inputs changed while running.");
                var initialReceipt = JsonUtility.FromJson<SceneReceipt>(File.ReadAllText(ReceiptRoot + "/scene-latest.json"));
                Require(initialReceipt.descriptor == session.descriptorPath && initialReceipt.sceneSha256 == session.sceneBeforeBakeSha256, "Another operation replaced the bound bake receipt.");
                foreach (var input in initialReceipt.additionalInputs) Require(input.sha256 == Digest(input.path), "Indoor authored lighting input changed during bake: " + input.path);
                var recipe = ReadGarageRecipe(session.descriptorPath, session.recipePath);
                var scene = SceneManager.GetActiveScene(); Require(SceneManager.sceneCount == 1 && scene.path == session.scenePath, "Wrong bake scene.");
                var spec = ReadDescriptor(session.descriptorPath).assets[0];
                var room = scene.GetRootGameObjects().Single(o => o.name == spec.id);
                var high = HasInput(spec.moduleLodMap) ? ModuleInspectionLods(room, spec, ReadModuleLodMap(spec.moduleLodMap, spec))[0].renderers : room.GetComponent<LODGroup>().GetLODs()[0].renderers;
                Require(Lightmapping.lightingDataAsset != null && LightmapSettings.lightmaps != null && LightmapSettings.lightmaps.Length > 0, "Unity produced no baked lighting data.");
                foreach (var r in high)
                {
                    GarageCheckSecondaryUv((MeshRenderer)r);
                    Require(r.lightmapIndex >= 0 && r.lightmapIndex < LightmapSettings.lightmaps.Length && LightmapSettings.lightmaps[r.lightmapIndex].lightmapColor != null, "Unbound lightmap renderer: " + r.name);
                    Require(r.lightmapScaleOffset.x > 0 && r.lightmapScaleOffset.y > 0 && new[] { r.lightmapScaleOffset.x, r.lightmapScaleOffset.y, r.lightmapScaleOffset.z, r.lightmapScaleOffset.w }.All(FiniteFloat), "Invalid lightmap scale/offset: " + r.name);
                }
                var probe = scene.GetRootGameObjects().SelectMany(o => o.GetComponentsInChildren<ReflectionProbe>()).Single();
                string lightingFolder = Path.GetDirectoryName(AssetDatabase.GetAssetPath(Lightmapping.lightingSettings)).Replace('\\', '/');
                Require(lightingFolder.StartsWith(OutputRoot + "/Garage/", StringComparison.Ordinal), "Unexpected lighting asset owner.");
                // URP baked rectangles provide diffuse GI, but no live rectangular
                // specular lobe. Calibrate the visible emitter radiance separately
                // for the native reflection cube, preserving the completed GI bake
                // and the source material's roughness/normal response.
                if (recipe.reflectionEmissionMultiplier != 1)
                    foreach (var material in room.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Distinct())
                    {
                        string path = AssetDatabase.GetAssetPath(material);
                        if (!path.StartsWith(lightingFolder + "/", StringComparison.Ordinal) || !material.HasProperty("_EmissionColor") || material.GetTexture("_EmissionMap") == null) continue;
                        material.SetColor("_EmissionColor", material.GetColor("_EmissionColor") * recipe.reflectionEmissionMultiplier);
                        // Installed URP derives _EMISSION from AnyEmissive flags.
                        // RealtimeEmissive keeps visible radiance enabled without
                        // adding it to a future baked-GI contribution.
                        material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                        FinalizeUrpMaterial(material);
                        EditorUtility.SetDirty(material); AssetDatabase.SaveAssetIfDirty(material);
                    }
                if (recipe.staticShadowsBakedOnly)
                    foreach (var renderer in room.GetComponentsInChildren<Renderer>(true))
                        renderer.shadowCastingMode = ShadowCastingMode.Off;
                string reflectionPath = lightingFolder + "/Reflection.exr";
                Require(Lightmapping.BakeReflectionProbe(probe, reflectionPath), "Local reflection bake failed.");
                var reflection = AssetDatabase.LoadAssetAtPath<Cubemap>(reflectionPath);
                Require(reflection != null, "Local reflection cubemap was not imported.");
                // Baked mode can be rebound by LightingDataAsset when the scene reloads.
                // Bind the explicitly regenerated cube so its signed identity survives reload.
                probe.mode = ReflectionProbeMode.Custom; probe.customBakedTexture = reflection;
                Require(probe.texture == reflection, "Local reflection texture binding failed.");
                foreach (var group in room.GetComponentsInChildren<LODGroup>(true)) group.ForceLOD(-1);
                EditorSceneManager.MarkSceneDirty(scene); Require(EditorSceneManager.SaveScene(scene), "Baked garage scene save failed."); AssetDatabase.SaveAssets();
                var paths = new HashSet<string>(StringComparer.Ordinal) { session.recipePath, recipe.lockedUi.path, AssetDatabase.GetAssetPath(Lightmapping.lightingSettings), AssetDatabase.GetAssetPath(Lightmapping.lightingDataAsset), AssetDatabase.GetAssetPath(probe.texture) };
                foreach (var volume in scene.GetRootGameObjects().SelectMany(o => o.GetComponentsInChildren<Volume>()))
                    if (volume.sharedProfile != null) paths.Add(AssetDatabase.GetAssetPath(volume.sharedProfile));
                foreach (var material in room.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Distinct())
                {
                    string path = AssetDatabase.GetAssetPath(material);
                    if (path.StartsWith(lightingFolder + "/", StringComparison.Ordinal)) paths.Add(path);
                }
                foreach (var lightmap in LightmapSettings.lightmaps)
                    foreach (var texture in new[] { lightmap.lightmapColor, lightmap.lightmapDir, lightmap.shadowMask })
                        if (texture != null) paths.Add(AssetDatabase.GetAssetPath(texture));
                Require(paths.All(p => !string.IsNullOrEmpty(p) && File.Exists(p)), "A lighting output has no saved file identity.");
                var inputs = paths.OrderBy(p => p, StringComparer.Ordinal).Select(FileRow).ToArray();
                var report = new GarageBakeReport { passed = true, visualAccepted = false, utc = DateTime.UtcNow.ToString("O"), descriptor = session.descriptorPath, recipe = session.recipePath, scene = session.scenePath, lightmaps = LightmapSettings.lightmaps.Length, lightmappedRenderers = high.Length, secondaryUvCheckedRenderers = high.Length, bakedInputs = inputs };
                var receipt = new SceneReceipt { passed = true, utc = report.utc, scene = session.scenePath, sceneSha256 = Digest(session.scenePath), descriptor = session.descriptorPath, descriptorSha256 = session.descriptorSha256, assetIds = new[] { spec.id }, additionalInputs = inputs };
                File.WriteAllText(ReceiptRoot + "/scene-latest.json", JsonUtility.ToJson(receipt, true));
                string json = JsonUtility.ToJson(report, true); File.WriteAllText(ReceiptRoot + "/garage-bake-latest.json", json); return json;
            }
            finally { RestoreGarageScenes(session); }
        }

        public static string CancelGarageReviewBake()
        {
            var text = SessionState.GetString(GarageBakeSessionKey, ""); Require(!string.IsNullOrEmpty(text), "No garage bake session.");
            if (Lightmapping.isRunning) Lightmapping.Cancel();
            Require(!Lightmapping.isRunning, "Cancellation is pending; call again after Unity stops baking.");
            RestoreGarageScenes(JsonUtility.FromJson<GarageBakeSession>(text));
            return "Garage bake cancelled; original saved scenes restored. No passed lighting receipt was created.";
        }

        private static void GarageRequireIdle()
        {
            Require(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !Lightmapping.isRunning, "Indoor work requires an idle Editor without an active bake.");
            for (int i = 0; i < SceneManager.sceneCount; i++) Require(!SceneManager.GetSceneAt(i).isDirty, "Save existing scenes before indoor review work.");
        }
        private static void RestoreGarageScenes(GarageBakeSession session)
        {
            EditorSceneManager.RestoreSceneManagerSetup(session.originals.Select(s => new SceneSetup { path = s.path, isActive = s.isActive, isLoaded = s.isLoaded }).ToArray());
            SessionState.EraseString(GarageBakeSessionKey);
        }
        private static void GarageCheckSecondaryUv(MeshRenderer renderer)
        {
            var mesh = renderer.GetComponent<MeshFilter>()?.sharedMesh;
            ValidateSecondaryUv(mesh, renderer.name);
        }
        private static void ValidateSecondaryUv(Mesh mesh, string identity)
        {
            Require(mesh != null && mesh.uv2.Length == mesh.vertexCount, "Secondary UVs missing: " + identity);
            var uv = mesh.uv2;
            Require(uv.All(p => FiniteFloat(p.x) && FiniteFloat(p.y) && p.x >= -.0001f && p.x <= 1.0001f && p.y >= -.0001f && p.y <= 1.0001f), "Invalid secondary UV range: " + identity);
            for (int sub = 0; sub < mesh.subMeshCount; sub++)
            {
                var triangles = mesh.GetTriangles(sub);
                for (int i = 0; i < triangles.Length; i += 3)
                {
                    var a = uv[triangles[i]]; var b = uv[triangles[i + 1]] - a; var c = uv[triangles[i + 2]] - a;
                    Require(Math.Abs((double)b.x * c.y - (double)b.y * c.x) > 1e-14, "Degenerate secondary UV triangle: " + identity);
                }
            }
        }
    }
}
