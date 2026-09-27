#if UNITY_EDITOR
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Captures scene environment values only; additive lightmap/probe arrays stay owned by Unity.</summary>
    internal sealed class GoldenWorkshopEnvironment
    {
        private readonly Material skybox = RenderSettings.skybox;
        private readonly Light sun = RenderSettings.sun;
        private readonly bool fog = RenderSettings.fog;
        private readonly FogMode fogMode = RenderSettings.fogMode;
        private readonly Color fogColor = RenderSettings.fogColor, sky = RenderSettings.ambientSkyColor,
            equator = RenderSettings.ambientEquatorColor, ground = RenderSettings.ambientGroundColor, ambient = RenderSettings.ambientLight;
        private readonly float fogDensity = RenderSettings.fogDensity, fogStart = RenderSettings.fogStartDistance, fogEnd = RenderSettings.fogEndDistance,
            intensity = RenderSettings.ambientIntensity, reflectionIntensity = RenderSettings.reflectionIntensity;
        private readonly AmbientMode ambientMode = RenderSettings.ambientMode;
        private readonly DefaultReflectionMode reflectionMode = RenderSettings.defaultReflectionMode;
        private readonly int reflectionResolution = RenderSettings.defaultReflectionResolution, reflectionBounces = RenderSettings.reflectionBounces;
        private readonly Texture reflection = RenderSettings.customReflectionTexture;
        private readonly SphericalHarmonicsL2 ambientProbe = RenderSettings.ambientProbe;
        internal void Restore()
        {
            RenderSettings.skybox = skybox; RenderSettings.sun = sun; RenderSettings.fog = fog; RenderSettings.fogMode = fogMode;
            RenderSettings.fogColor = fogColor; RenderSettings.fogDensity = fogDensity; RenderSettings.fogStartDistance = fogStart; RenderSettings.fogEndDistance = fogEnd;
            RenderSettings.ambientMode = ambientMode; RenderSettings.ambientLight = ambient; RenderSettings.ambientSkyColor = sky;
            RenderSettings.ambientEquatorColor = equator; RenderSettings.ambientGroundColor = ground; RenderSettings.ambientIntensity = intensity; RenderSettings.ambientProbe = ambientProbe;
            RenderSettings.defaultReflectionMode = reflectionMode; RenderSettings.defaultReflectionResolution = reflectionResolution;
            RenderSettings.reflectionBounces = reflectionBounces; RenderSettings.reflectionIntensity = reflectionIntensity; RenderSettings.customReflectionTexture = reflection;
        }
    }
}
#endif
