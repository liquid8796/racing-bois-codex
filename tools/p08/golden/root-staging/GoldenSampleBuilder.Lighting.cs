using RacingBois.Golden;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        private static void AddReviewPipeline(bool environment)
        {
            var source = GraphicsSettings.currentRenderPipeline;
            Require(source != null, "A current URP pipeline is required for the review.");
            string path = OutputRoot + (environment ? "/EnvironmentReviewPipeline.asset" : "/StudioReviewPipeline.asset");
            var pipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(path);
            if (pipeline == null)
            {
                pipeline = UnityEngine.Object.Instantiate(source);
                AssetDatabase.CreateAsset(pipeline, path);
            }
            else EditorUtility.CopySerialized(source, pipeline);
            pipeline.name = environment ? "Environment Review Pipeline" : "Studio Review Pipeline";
            // Values refer to actual serialized properties inspected in the installed URP package.
            // The gameplay/Web pipeline asset is never changed by this review configuration.
            var settings = new SerializedObject(pipeline);
            SetReviewFloat(settings, "m_ShadowDistance", environment ? 160f : 25f);
            SetReviewFloat(settings, "m_ShadowDepthBias", .5f);
            SetReviewFloat(settings, "m_ShadowNormalBias", .5f);
            SetReviewFloat(settings, "m_Cascade2Split", .35f);
            var cascades = settings.FindProperty("m_ShadowCascadeCount");
            var resolution = settings.FindProperty("m_MainLightShadowmapResolution");
            Require(cascades != null && resolution != null, "Installed URP shadow configuration changed.");
            cascades.intValue = environment ? 4 : 2;
            resolution.intValue = 4096;
            settings.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(pipeline);
            new GameObject("Inspection Pipeline Scope").AddComponent<GoldenReviewPipelineScope>().Pipeline = pipeline;
        }

        private static void SetReviewFloat(SerializedObject settings, string property, float value)
        {
            var target = settings.FindProperty(property);
            Require(target != null && target.propertyType == SerializedPropertyType.Float, "Missing URP property: " + property);
            target.floatValue = value;
        }
    }
}
