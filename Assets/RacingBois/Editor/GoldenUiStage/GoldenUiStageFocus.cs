#if UNITY_EDITOR
using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Owns the optional garage-preview focus effect; never edits a project profile.</summary>
    internal sealed class GoldenUiStageFocus : IDisposable
    {
        private readonly Volume volume;
        private readonly VolumeProfile profile;
        private readonly DepthOfField depth;
        private readonly UniversalAdditionalCameraData cameraData;
        private readonly bool previousPost;
        private readonly CameraOverrideOption previousDepth;
        private bool disposed;

        internal GoldenUiStageFocus(GameObject owner, Camera camera)
        {
            cameraData = camera.GetUniversalAdditionalCameraData();
            previousPost = cameraData.renderPostProcessing; previousDepth = cameraData.requiresDepthOption;
            volume = new GameObject("Garage preview focus - temporary").AddComponent<Volume>();
            volume.transform.SetParent(owner.transform, false); volume.isGlobal = true; volume.priority = 100; volume.enabled = false;
            profile = ScriptableObject.CreateInstance<VolumeProfile>(); profile.hideFlags = HideFlags.DontSave;
            volume.sharedProfile = profile; depth = profile.Add<DepthOfField>(true);
            depth.mode.Override(DepthOfFieldMode.Gaussian); depth.gaussianMaxRadius.Override(.9f); depth.highQualitySampling.Override(true);
        }
        internal void Apply(bool garage, float subjectDistance)
        {
            if (disposed) return;
            volume.enabled = garage;
            cameraData.renderPostProcessing = garage || previousPost;
            cameraData.requiresDepthOption = garage ? CameraOverrideOption.On : previousDepth;
            if (!garage) return;
            depth.gaussianStart.Override(Mathf.Max(.1f, subjectDistance + 1.4f));
            depth.gaussianEnd.Override(Mathf.Max(.2f, subjectDistance + 7f));
        }
        public void Dispose()
        {
            if (disposed) return; disposed = true;
            if (cameraData != null) { cameraData.renderPostProcessing = previousPost; cameraData.requiresDepthOption = previousDepth; }
            if (volume != null) UnityEngine.Object.DestroyImmediate(volume.gameObject);
            if (profile != null)
            {
                foreach (var component in profile.components) if (component != null) UnityEngine.Object.DestroyImmediate(component);
                UnityEngine.Object.DestroyImmediate(profile);
            }
        }
    }
}
#endif
