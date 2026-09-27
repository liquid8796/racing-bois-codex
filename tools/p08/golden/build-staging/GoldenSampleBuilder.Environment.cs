using System;
using System.IO;
using System.Linq;
using RacingBois.Golden;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        [Serializable] public sealed class EnvironmentRecipe
        {
            public string hdri, hdriSha256;
            public float unitySkyRotationDegrees = float.NaN;
            public float unitySkyExposure = 1f, unitySunIntensity = 1.8f;
            public float[] sunDirectionToLightUnity, sunColorLinear, cameraPositionUnity, cameraTargetUnity, fogColorLinear;
            public float cameraFocalLengthMm = 28f, sensorWidthMm = 36f, aspect = 2f, fogDensity;
        }

        /// <summary>Creates a separate inspection scene from measured environment inputs. Never configures a production scene.</summary>
        public static string CreateEnvironmentReviewScene(string descriptorPath, string recipePath)
        {
            Validate(descriptorPath);
            var descriptor = ReadDescriptor(descriptorPath);
            Require(descriptor.assets.Length == 1 && descriptor.assets[0].kind == "environment",
                "Environment review needs exactly one imported environment.");
            Require(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling,
                "Environment review requires an idle Editor.");
            ProjectPath(recipePath, false);
            var recipeFile = FileRow(recipePath);
            var recipe = JsonUtility.FromJson<EnvironmentRecipe>(File.ReadAllText(recipePath));
            Require(recipe != null, "Missing environment recipe.");
            VerifyInput(new InputFile { path = recipe.hdri, sha256 = recipe.hdriSha256 });
            Require(recipe.hdri.StartsWith("Assets/", StringComparison.Ordinal), "Review HDRI must be a project asset.");
            Require(FiniteFloat(recipe.unitySkyRotationDegrees) && recipe.unitySkyExposure > 0 && recipe.unitySkyExposure <= 8
                && recipe.unitySunIntensity > 0 && recipe.unitySunIntensity <= 10, "Explicit bounded Unity sky and sun settings required.");
            Require(recipe.aspect > .5f && recipe.aspect < 4 && recipe.cameraFocalLengthMm >= 10 && recipe.cameraFocalLengthMm <= 150
                && recipe.sensorWidthMm >= 10 && recipe.sensorWidthMm <= 80 && recipe.fogDensity >= 0 && recipe.fogDensity <= .02f,
                "Invalid camera or fog recipe.");
            var sunDirection = RecipeVector(recipe.sunDirectionToLightUnity);
            Require(sunDirection.sqrMagnitude > .9f && sunDirection.sqrMagnitude < 1.1f, "Sun direction must be normalized.");
            var cameraPosition = RecipeVector(recipe.cameraPositionUnity);
            var cameraTarget = RecipeVector(recipe.cameraTargetUnity);
            Require(Vector3.Distance(cameraPosition, cameraTarget) > 1f, "Camera target is too close.");
            var sunColor = RecipeColor(recipe.sunColorLinear);
            var fogColor = RecipeColor(recipe.fogColorLinear);
            for (int i = 0; i < SceneManager.sceneCount; i++)
                Require(!SceneManager.GetSceneAt(i).isDirty, "Save existing scenes before creating the isolated review.");

            var importer = AssetImporter.GetAtPath(recipe.hdri) as TextureImporter;
            Require(importer != null, "HDRI importer missing.");
            importer.textureShape = TextureImporterShape.Texture2D;
            importer.sRGBTexture = false; importer.mipmapEnabled = true; importer.isReadable = false;
            importer.maxTextureSize = 4096; importer.wrapMode = TextureWrapMode.Repeat;
            importer.SetPlatformTextureSettings(new TextureImporterPlatformSettings
            { name = "Standalone", overridden = true, maxTextureSize = 4096, format = TextureImporterFormat.BC6H, compressionQuality = 100 });
            importer.SaveAndReimport();
            var skyTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(recipe.hdri);
            Require(skyTexture != null, "HDRI import failed.");
            var skyShader = Shader.Find("Skybox/Panoramic");
            Require(skyShader != null, "Installed panoramic sky shader missing.");
            string skyPath = OutputRoot + "/Materials/GoldenEnvironmentSky.mat";
            var sky = AssetDatabase.LoadAssetAtPath<Material>(skyPath);
            if (sky == null) { sky = new Material(skyShader); AssetDatabase.CreateAsset(sky, skyPath); }
            Require(sky.HasProperty("_MainTex") && sky.HasProperty("_Rotation") && sky.HasProperty("_Exposure"),
                "Installed sky shader does not expose the expected panorama inputs.");
            sky.SetTexture("_MainTex", skyTexture); sky.SetFloat("_Rotation", recipe.unitySkyRotationDegrees);
            sky.SetFloat("_Exposure", recipe.unitySkyExposure); sky.SetColor("_Tint", Color.gray);

            Scene original = SceneManager.GetActiveScene();
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            try
            {
                SceneManager.SetActiveScene(scene);
                AddReviewPipeline(true);
                var spec = descriptor.assets[0];
                var root = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(spec)), scene);
                var camera = new GameObject("Environment Review Camera").AddComponent<Camera>();
                camera.tag = "MainCamera"; camera.clearFlags = CameraClearFlags.Skybox;
                camera.allowHDR = true; camera.allowMSAA = true; camera.nearClipPlane = .05f; camera.farClipPlane = 2000;
                camera.transform.position = cameraPosition; camera.transform.LookAt(cameraTarget);
                float verticalFov = 2 * Mathf.Atan(recipe.sensorWidthMm / recipe.aspect / (2 * recipe.cameraFocalLengthMm)) * Mathf.Rad2Deg;
                camera.fieldOfView = verticalFov;
                var key = new GameObject("Measured Sunset Direction").AddComponent<Light>();
                key.type = LightType.Directional; key.transform.rotation = Quaternion.LookRotation(-sunDirection);
                key.color = sunColor; key.intensity = recipe.unitySunIntensity; key.shadows = LightShadows.Soft;
                key.shadowBias = .02f; key.shadowNormalBias = .12f;
                RenderSettings.skybox = sky; RenderSettings.sun = key;
                RenderSettings.ambientMode = AmbientMode.Skybox; RenderSettings.ambientIntensity = 1f;
                RenderSettings.fog = recipe.fogDensity > 0; RenderSettings.fogMode = FogMode.Exponential;
                RenderSettings.fogDensity = recipe.fogDensity; RenderSettings.fogColor = fogColor;
                var probe = new GameObject("Road Reflection Probe").AddComponent<ReflectionProbe>();
                probe.mode = ReflectionProbeMode.Realtime; probe.refreshMode = ReflectionProbeRefreshMode.OnAwake;
                probe.timeSlicingMode = ReflectionProbeTimeSlicingMode.IndividualFaces;
                probe.resolution = 128; probe.size = new Vector3(1700, 300, 2000);
                probe.transform.position = new Vector3(0, 4, 40); probe.farClipPlane = 2000;
                probe.clearFlags = ReflectionProbeClearFlags.Skybox; probe.boxProjection = false;
                var controller = new GameObject("Environment Review Controls").AddComponent<GoldenReviewController>();
                controller.ReviewCamera = camera;
                controller.gameObject.AddComponent<GoldenCaptureRunner>();
                var renderer = root.GetComponentsInChildren<Renderer>(true)[0];
                var bounds = renderer.bounds;
                foreach (var other in root.GetComponentsInChildren<Renderer>(true).Skip(1)) bounds.Encapsulate(other.bounds);
                controller.Subjects = new[] { new GoldenReviewController.Subject
                {
                    Id = spec.id, Root = root, Center = bounds.center, Size = bounds.size, IsEnvironment = true,
                    GameplayPosition = cameraPosition, GameplayTarget = cameraTarget, GameplayVerticalFov = verticalFov
                } };
                EditorSceneManager.MarkSceneDirty(scene);
                Require(EditorSceneManager.SaveScene(scene, ScenePath), "Could not save environment review scene.");
                EditorUtility.SetDirty(sky); AssetDatabase.SaveAssetIfDirty(sky);
                Require(recipeFile.sha256 == Digest(recipePath), "Environment recipe changed while creating its scene.");
                VerifyInput(new InputFile { path = recipe.hdri, sha256 = recipe.hdriSha256 });
                var receipt = new SceneReceipt
                {
                    passed = true, utc = DateTime.UtcNow.ToString("O"), scene = ScenePath, sceneSha256 = Digest(ScenePath),
                    descriptor = descriptorPath, descriptorSha256 = Digest(descriptorPath), assetIds = new[] { spec.id },
                    additionalInputs = new[] { recipeFile, FileRow(recipe.hdri) }
                };
                string json = JsonUtility.ToJson(receipt, true);
                File.WriteAllText(ReceiptRoot + "/scene-latest.json", json);
                return json;
            }
            finally
            {
                if (original.IsValid() && original.isLoaded) SceneManager.SetActiveScene(original);
                EditorSceneManager.CloseScene(scene, true);
            }
        }

        private static bool FiniteFloat(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static Vector3 RecipeVector(float[] values)
        {
            Require(values != null && values.Length == 3 && values.All(FiniteFloat), "Expected three finite recipe coordinates.");
            return new Vector3(values[0], values[1], values[2]);
        }
        private static Color RecipeColor(float[] values)
        {
            var value = RecipeVector(values);
            Require(value.x >= 0 && value.y >= 0 && value.z >= 0 && value.x <= 1 && value.y <= 1 && value.z <= 1,
                "Recipe color must be linear RGB in0..1.");
            return new Color(value.x, value.y, value.z);
        }
    }
}
