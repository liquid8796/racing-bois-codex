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
        public static string CreateReviewScene(string descriptorPath)
        {
            Validate(descriptorPath);
            Require(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling,
                "Scene creation requires the Editor to be idle outside Play mode.");
            var descriptor = ReadDescriptor(descriptorPath);
            for (int i = 0; i < SceneManager.sceneCount; i++)
                Require(!SceneManager.GetSceneAt(i).isDirty, "Save existing scene changes before generating the isolated review scene.");
            Directory.CreateDirectory(OutputRoot);
            Scene original = SceneManager.GetActiveScene();
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            try
            {
                SceneManager.SetActiveScene(scene);
                AddReviewPipeline(false);
                var camera = new GameObject("Golden Review Camera").AddComponent<Camera>();
                camera.tag = "MainCamera"; camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(.045f, .06f, .075f); camera.allowHDR = true; camera.allowMSAA = true;
                camera.transform.position = new Vector3(3, 1.9f, 3.5f); camera.transform.LookAt(new Vector3(0, .75f, 0));
                camera.fieldOfView = 38; camera.nearClipPlane = .05f; camera.farClipPlane = 80;

                var inspection = new GameObject("Golden Review Controls").AddComponent<GoldenReviewController>();
                inspection.ReviewCamera = camera;
                inspection.gameObject.AddComponent<GoldenCaptureRunner>();
                inspection.Subjects = descriptor.assets.Select((spec, index) =>
                {
                    var root = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(spec)), scene);
                    root.name = spec.id;
                    var renderers = HasInput(spec.moduleLodMap)
                        ? ModuleInspectionLods(root, spec, ReadModuleLodMap(spec.moduleLodMap, spec))[0].renderers
                        : root.GetComponent<LODGroup>().GetLODs()[0].renderers;
                    Bounds bounds = CurrentGeometryBounds(renderers[0]);
                    foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(CurrentGeometryBounds(renderer));
                    root.SetActive(index == 0);
                    return new GoldenReviewController.Subject { Id = spec.id, Root = root, Center = bounds.center, Size = bounds.size };
                }).ToArray();

                // A neutral measured studio floor is inspection infrastructure, not a new game/environment asset.
                var floor = GameObject.CreatePrimitive(PrimitiveType.Plane); floor.name = "Inspection Floor - 20 Metres";
                floor.transform.localScale = new Vector3(2, 1, 2); floor.transform.position = new Vector3(0, -.012f, 0);
                UnityEngine.Object.DestroyImmediate(floor.GetComponent<Collider>());
                string floorMaterialPath = OutputRoot + "/Materials/GoldenInspectionFloor.mat";
                var floorMaterial = AssetDatabase.LoadAssetAtPath<Material>(floorMaterialPath);
                if (floorMaterial == null) { floorMaterial = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(floorMaterial, floorMaterialPath); }
                floorMaterial.SetColor("_BaseColor", new Color(.14f, .155f, .17f)); floorMaterial.SetFloat("_Smoothness", .24f); floorMaterial.SetFloat("_Metallic", 0);
                floor.GetComponent<Renderer>().sharedMaterial = floorMaterial;

                var key = AddLight("Neutral Key", new Vector3(38, -32, 0), Color.white, 2.2f); key.shadows = LightShadows.Soft;
                key.shadowBias = .5f; key.shadowNormalBias = .5f;
                AddLight("Cool Fill", new Vector3(30, 115, 0), new Color(.80f, .88f, 1), .65f);
                AddLight("Warm Rim", new Vector3(15, 190, 0), new Color(1, .92f, .81f), 1.15f);
                RenderSettings.sun = key; RenderSettings.ambientMode = AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = new Color(.23f, .27f, .32f);
                RenderSettings.ambientEquatorColor = new Color(.10f, .12f, .14f);
                RenderSettings.ambientGroundColor = new Color(.045f, .045f, .05f);
                RenderSettings.fog = false;
                var probe = new GameObject("Inspection Reflection Probe").AddComponent<ReflectionProbe>();
                probe.mode = ReflectionProbeMode.Realtime; probe.refreshMode = ReflectionProbeRefreshMode.OnAwake;
                probe.timeSlicingMode = ReflectionProbeTimeSlicingMode.IndividualFaces;
                probe.resolution = 256; probe.size = new Vector3(15, 8, 15); probe.transform.position = new Vector3(0, 1.1f, 0);
                probe.clearFlags = ReflectionProbeClearFlags.SolidColor; probe.backgroundColor = new Color(.12f, .14f, .17f);
                probe.boxProjection = true; probe.intensity = 1;
                EditorSceneManager.MarkSceneDirty(scene);
                Require(EditorSceneManager.SaveScene(scene, ScenePath), "Unable to save isolated golden review scene.");
                AssetDatabase.SaveAssets();
                var report = new SceneReceipt
                {
                    passed = true, utc = DateTime.UtcNow.ToString("O"), scene = ScenePath, sceneSha256 = Digest(ScenePath),
                    descriptor = descriptorPath, descriptorSha256 = Digest(descriptorPath), assetIds = descriptor.assets.Select(asset => asset.id).ToArray()
                };
                Directory.CreateDirectory(ReceiptRoot); string json = JsonUtility.ToJson(report, true);
                File.WriteAllText(ReceiptRoot + "/scene-latest.json", json); return json;
            }
            finally
            {
                if (original.IsValid() && original.isLoaded) SceneManager.SetActiveScene(original);
                EditorSceneManager.CloseScene(scene, true);
            }
        }

        private static Light AddLight(string name, Vector3 rotation, Color color, float intensity)
        {
            var light = new GameObject(name).AddComponent<Light>(); light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(rotation); light.color = color; light.intensity = intensity;
            light.shadows = LightShadows.None; return light;
        }

        [Serializable] private sealed class SceneReceipt
        { public bool passed; public string utc, scene, sceneSha256, descriptor, descriptorSha256; public string[] assetIds; public FileReceipt[] additionalInputs; }
    }
}
