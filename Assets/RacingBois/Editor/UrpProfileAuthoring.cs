using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Creates owned renderer resources without changing the source or Web profile.</summary>
    internal static class UrpProfileAuthoring
    {
        internal const string DesktopPipelinePath = "Assets/RacingBois/Settings/Desktop/DesktopPipeline.asset";

        internal static UniversalRenderPipelineAsset PrepareDesktop()
        {
            const string sourcePath = "Assets/RacingBois/Settings/WebURP.asset";
            var source = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(sourcePath);
            if (source == null) throw new InvalidOperationException("The reviewed foundation URP profile is missing.");
            Directory.CreateDirectory(Path.GetDirectoryName(DesktopPipelinePath));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(DesktopPipelinePath);
            if (pipeline == null)
            {
                pipeline = UnityEngine.Object.Instantiate(source); pipeline.name = "DesktopPipeline";
                AssetDatabase.CreateAsset(pipeline, DesktopPipelinePath);
            }
            else EditorUtility.CopySerialized(source, pipeline);
            pipeline.name = "DesktopPipeline";
            ConfigureDesktopRenderer(pipeline, "Assets/RacingBois/Settings/Desktop/DesktopRenderer.asset");
            return pipeline;
        }

        internal static void ConfigureDesktopRenderer(RenderPipelineAsset pipeline, string rendererPath)
        {
            if (!(pipeline is UniversalRenderPipelineAsset)) throw new InvalidOperationException("A URP profile is required.");
            var settings = new SerializedObject(pipeline);
            var renderers = settings.FindProperty("m_RendererDataList");
            if (renderers == null || renderers.arraySize != 1 || !(renderers.GetArrayElementAtIndex(0).objectReferenceValue is UniversalRendererData source))
                throw new InvalidOperationException("Expected one explicit URP renderer before creating the desktop profile.");
            var post = AssetDatabase.LoadAssetAtPath<PostProcessData>("Packages/com.unity.render-pipelines.universal/Runtime/Data/PostProcessData.asset");
            if (post == null) throw new InvalidOperationException("Installed URP post-process shader resources are missing.");
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(rendererPath);
            if (renderer == source) throw new InvalidOperationException("The owned renderer must not overwrite its source.");
            if (renderer == null)
            {
                renderer = UnityEngine.Object.Instantiate(source);
                renderer.name = Path.GetFileNameWithoutExtension(rendererPath);
                AssetDatabase.CreateAsset(renderer, rendererPath);
            }
            else EditorUtility.CopySerialized(source, renderer);
            renderer.name = Path.GetFileNameWithoutExtension(rendererPath);
            var rendererSettings = new SerializedObject(renderer);
            var resource = rendererSettings.FindProperty("postProcessData");
            if (resource == null) throw new InvalidOperationException("Installed URP renderer resource contract changed.");
            resource.objectReferenceValue = post;
            rendererSettings.ApplyModifiedPropertiesWithoutUndo();
            renderers.GetArrayElementAtIndex(0).objectReferenceValue = renderer;
            settings.FindProperty("m_ReflectionProbeBoxProjection").boolValue = true;
            settings.FindProperty("m_ReflectionProbeBlending").boolValue = true;
            settings.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(renderer); AssetDatabase.SaveAssetIfDirty(renderer);
            EditorUtility.SetDirty(pipeline); AssetDatabase.SaveAssetIfDirty(pipeline);
        }
    }
}
