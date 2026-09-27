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
            const string sourcePath = UrpProfileAuthoring.DesktopPipelinePath;
            ProjectPath(sourcePath, false);
            var source = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(sourcePath);
            Require(source != null && AssetDatabase.GetAssetPath(source) == sourcePath,
                "The explicit reviewed desktop URP asset is required: " + sourcePath);
            Require(!EditorUtility.IsDirty(source), "The reviewed desktop pipeline has unsaved changes.");
            string path = OutputRoot + (environment ? "/EnvironmentReviewPipeline.asset" : "/StudioReviewPipeline.asset");
            var pipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(path);
            Require(pipeline != source && path != sourcePath, "Review pipeline must not overwrite its desktop source.");
            if (pipeline == null)
            {
                pipeline = UnityEngine.Object.Instantiate(source);
                AssetDatabase.CreateAsset(pipeline, path);
            }
            else EditorUtility.CopySerialized(source, pipeline);
            pipeline.name = environment ? "EnvironmentReviewPipeline" : "StudioReviewPipeline";
            UrpProfileAuthoring.ConfigureDesktopRenderer(pipeline,
                OutputRoot + (environment ? "/EnvironmentReviewRenderer.asset" : "/StudioReviewRenderer.asset"));
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
            EditorUtility.SetDirty(pipeline); AssetDatabase.SaveAssetIfDirty(pipeline);
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
