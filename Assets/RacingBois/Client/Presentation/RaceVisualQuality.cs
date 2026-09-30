using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RacingBois.Client.Presentation
{
    /// <summary>Owns one runtime pipeline clone; cosmetic settings never modify authority or source assets.</summary>
    public sealed class RaceVisualQuality : MonoBehaviour
    {
        public Camera ViewCamera;
        public Volume PostProcess;
        private UniversalRenderPipelineAsset original, runtime;
        private RenderPipelineAsset originalQualityPipeline;
        private RaceTextureStreamingScope textureStreaming;
        public int Index { get; private set; } = 1;
        public void Apply(int index)
        {
            Index = Mathf.Clamp(index, 0, 2);
            if (runtime == null)
            {
                original = GraphicsSettings.defaultRenderPipeline as UniversalRenderPipelineAsset;
                if (original == null) return;
                originalQualityPipeline = QualitySettings.renderPipeline;
                runtime = Instantiate(original);
                runtime.name = "Racing Bois runtime quality";
                GraphicsSettings.defaultRenderPipeline = runtime;
                QualitySettings.renderPipeline = runtime;
                textureStreaming = new RaceTextureStreamingScope();
            }
            textureStreaming.Apply(Index);
            runtime.renderScale = Index == 0 ? .78f : 1;
            runtime.msaaSampleCount = Index == 2 ? 4 : 2;
            runtime.shadowDistance = Index == 0 ? 35 : Index == 1 ? 70 : 100;
            runtime.mainLightShadowmapResolution = Index == 0 ? 1024 : 2048;
            if(RenderSettings.sun!=null)RenderSettings.sun.shadows=Index==0?LightShadows.Hard:LightShadows.Soft;
            QualitySettings.lodBias = Index == 0 ? .65f : Index == 1 ? 1 : 1.3f;
            QualitySettings.anisotropicFiltering = AnisotropicFiltering.Enable;
            if (ViewCamera != null)
            {
                var data = ViewCamera.GetUniversalAdditionalCameraData();
                data.renderPostProcessing = Index > 0;
                data.antialiasing = AntialiasingMode.None;
                ViewCamera.farClipPlane = Index == 0 ? 420 : 650;
            }
            if (PostProcess != null) PostProcess.enabled = Index > 0;
        }
        private void OnDestroy()
        {
            textureStreaming?.Dispose();
            if (runtime == null) return;
            if (GraphicsSettings.defaultRenderPipeline == runtime) GraphicsSettings.defaultRenderPipeline = original;
            if (QualitySettings.renderPipeline == runtime) QualitySettings.renderPipeline = originalQualityPipeline;
            Destroy(runtime);
        }
    }
}
