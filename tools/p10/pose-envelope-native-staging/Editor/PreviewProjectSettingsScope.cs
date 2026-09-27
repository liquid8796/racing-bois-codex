using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Diagnostics.PoseEnvelopePreview.Editor
{
    /// <summary>Persists only three build settings files, then restores their prior memory and disk states.</summary>
    internal sealed class PreviewProjectSettingsScope
    {
        private sealed class State
        {
            internal UnityEngine.Object Value;
            internal string Path, Json;
            internal byte[] Bytes;
            internal bool Dirty;
        }
        private readonly State[] states;
        internal PreviewProjectSettingsScope()
        {
            states = new[] { Capture(typeof(PlayerSettings), "ProjectSettings/ProjectSettings.asset"),
                Capture(typeof(GraphicsSettings), "ProjectSettings/GraphicsSettings.asset"),
                Capture(typeof(QualitySettings), "ProjectSettings/QualitySettings.asset") };
        }
        private static State Capture(Type type, string path)
        {
            var value = Resources.FindObjectsOfTypeAll(type).Single();
            return new State { Value = value, Path = path, Bytes = File.ReadAllBytes(path),
                Json = EditorJsonUtility.ToJson(value), Dirty = EditorUtility.IsDirty(value) };
        }
        internal void UsePipelineAtEveryQuality(RenderPipelineAsset pipeline)
        {
            var state = states.Single(value => value.Value is QualitySettings);
            var settings = new SerializedObject(state.Value);
            var levels = settings.FindProperty("m_QualitySettings");
            if (levels == null || !levels.isArray) throw new InvalidOperationException("quality_level_contract_changed");
            for (int i = 0; i < levels.arraySize; i++)
            {
                var field = levels.GetArrayElementAtIndex(i).FindPropertyRelative("customRenderPipeline");
                if (field == null) throw new InvalidOperationException("quality_pipeline_contract_changed");
                field.objectReferenceValue = pipeline;
            }
            settings.ApplyModifiedPropertiesWithoutUndo();
        }
        internal void PersistEffectiveSettings()
        {
            foreach (var state in states)
                UnityEditorInternal.InternalEditorUtility.SaveToSerializedFileAndForget(new[] { state.Value }, state.Path, true);
        }
        internal void Restore()
        {
            foreach (var state in states)
            {
                EditorJsonUtility.FromJsonOverwrite(state.Json, state.Value);
                File.WriteAllBytes(state.Path, state.Bytes);
                if (state.Dirty) EditorUtility.SetDirty(state.Value); else EditorUtility.ClearDirty(state.Value);
                if (EditorJsonUtility.ToJson(state.Value) != state.Json || !File.ReadAllBytes(state.Path).SequenceEqual(state.Bytes))
                    throw new InvalidOperationException("project_settings_restore_failed:" + state.Path);
            }
        }
    }
}
