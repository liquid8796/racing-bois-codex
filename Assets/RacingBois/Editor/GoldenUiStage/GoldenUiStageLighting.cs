#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using RacingBois.Golden;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Owns only the temporary comparison lights and restores the live scene's ambient/light state.</summary>
    internal sealed class GoldenUiStageLighting : IDisposable
    {
        private readonly List<Light> previousLights = new List<Light>();
        private readonly AmbientMode ambientMode;
        private readonly Color sky, equator, ground;
        private readonly float intensity;
        private readonly SphericalHarmonicsL2 probe;
        private readonly Light sun;
        private readonly Material previousSky;
        private readonly bool previousFog;
        private Material ownedSky;
        private VolumeProfile ownedProfile;
        private bool disposed;

        internal GoldenUiStageLighting(GameObject owner, GoldenUiStageConfiguration settings)
        {
            var pipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(settings.ReviewPipeline);
            if (pipeline == null) throw new InvalidOperationException("Generate the measured studio review pipeline before UI staging.");
            ambientMode = RenderSettings.ambientMode; sky = RenderSettings.ambientSkyColor;
            equator = RenderSettings.ambientEquatorColor; ground = RenderSettings.ambientGroundColor;
            intensity = RenderSettings.ambientIntensity; probe = RenderSettings.ambientProbe; sun = RenderSettings.sun;
            previousSky = RenderSettings.skybox; previousFog = RenderSettings.fog;
            foreach (var light in UnityEngine.Object.FindObjectsByType<Light>())
                if (light.enabled && light.gameObject.scene == owner.scene && light.type == LightType.Directional)
                { previousLights.Add(light); light.enabled = false; }
            try
            {
                owner.AddComponent<GoldenReviewPipelineScope>().Pipeline = pipeline;
                if (!string.IsNullOrEmpty(settings.MainSkyMaterial))
                {
                    var source = AssetDatabase.LoadAssetAtPath<Material>(settings.MainSkyMaterial);
                    if (source == null || !source.HasProperty("_Rotation") || !source.HasProperty("_Exposure"))
                        throw new InvalidOperationException("The declared panoramic menu sky is missing or incompatible.");
                    ownedSky = new Material(source) { name = "Golden menu sky - temporary", hideFlags = HideFlags.DontSave };
                    ownedSky.SetFloat("_Rotation", settings.MainSkyRotation); ownedSky.SetFloat("_Exposure", settings.MainSkyExposure);
                    RenderSettings.skybox = ownedSky;
                }
                // The original gameplay fog is not the menu overlook's atmospheric recipe.
                RenderSettings.fog = false;
                var key = Add(owner, "Fixture sunset key", Quaternion.LookRotation(-settings.MainSunDirection.normalized).eulerAngles, new Color(1, .83f, .62f), 1.8f);
                key.shadows = LightShadows.Soft; key.shadowBias = .02f; key.shadowNormalBias = .12f;
                Add(owner, "Fixture sky fill", Quaternion.LookRotation(-new Vector3(1.6f, .7f, 1).normalized).eulerAngles, new Color(.78f, .86f, 1), .65f);
                RenderSettings.sun = key; RenderSettings.ambientMode = AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = new Color(.30f, .33f, .37f);
                RenderSettings.ambientEquatorColor = new Color(.16f, .18f, .20f);
                RenderSettings.ambientGroundColor = new Color(.07f, .065f, .055f);
                RenderSettings.ambientIntensity = 1;
                var volume = new GameObject("Golden menu grade - temporary").AddComponent<Volume>();
                volume.transform.SetParent(owner.transform, false); volume.isGlobal = true; volume.priority = 10;
                ownedProfile = ScriptableObject.CreateInstance<VolumeProfile>(); ownedProfile.hideFlags = HideFlags.DontSave;
                volume.sharedProfile = ownedProfile;
                ownedProfile.Add<Tonemapping>(true).mode.Override(TonemappingMode.ACES);
                ownedProfile.Add<ColorAdjustments>(true).postExposure.Override(.3f);
                ownedProfile.Add<Bloom>(true).intensity.Override(.15f);
                var reflection = new GameObject("Fixture actor reflection").AddComponent<ReflectionProbe>();
                reflection.transform.SetParent(owner.transform, false); reflection.transform.localPosition = new Vector3(0, 1, 0);
                reflection.mode = ReflectionProbeMode.Realtime; reflection.refreshMode = ReflectionProbeRefreshMode.OnAwake;
                reflection.timeSlicingMode = ReflectionProbeTimeSlicingMode.IndividualFaces;
                reflection.size = new Vector3(8, 5, 8); reflection.resolution = 128;
                reflection.clearFlags = ReflectionProbeClearFlags.Skybox;
            }
            catch { Dispose(); throw; }
        }

        private static Light Add(GameObject owner, string name, Vector3 rotation, Color color, float intensity)
        {
            var light = new GameObject(name).AddComponent<Light>(); light.transform.SetParent(owner.transform, false);
            light.type = LightType.Directional; light.transform.localRotation = Quaternion.Euler(rotation);
            light.color = color; light.intensity = intensity; light.shadows = LightShadows.None; return light;
        }

        public void Dispose()
        {
            if (disposed) return; disposed = true;
            foreach (var light in previousLights) if (light != null) light.enabled = true;
            RenderSettings.ambientMode = ambientMode; RenderSettings.ambientSkyColor = sky;
            RenderSettings.ambientEquatorColor = equator; RenderSettings.ambientGroundColor = ground;
            RenderSettings.ambientIntensity = intensity; RenderSettings.ambientProbe = probe; RenderSettings.sun = sun;
            RenderSettings.skybox = previousSky; RenderSettings.fog = previousFog;
            if (ownedSky != null) UnityEngine.Object.DestroyImmediate(ownedSky);
            if (ownedProfile != null)
            {
                foreach (var component in ownedProfile.components) if (component != null) UnityEngine.Object.DestroyImmediate(component);
                UnityEngine.Object.DestroyImmediate(ownedProfile);
            }
        }
    }
}
#endif
