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
            internal string Path, Json, EffectiveJson;
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
        internal void PersistEffectiveSettings(string evidenceDirectory)
        {
            Directory.CreateDirectory(evidenceDirectory);
            foreach (var state in states)
            {
                state.EffectiveJson = EditorJsonUtility.ToJson(state.Value);
                string path = Path.Combine(evidenceDirectory, Path.GetFileName(state.Path));
                if (File.Exists(path)) throw new InvalidOperationException("fresh_settings_evidence_required");
                UnityEngine.Object copy = null;
                try
                {
                    // Project settings are persistent native objects: SaveToSerializedFileAndForget
                    // rejects them, while SaveAssetIfDirty does not save these settings files.
                    copy = UnityEngine.Object.Instantiate(state.Value);
                    if (copy == null || copy == state.Value || EditorUtility.IsPersistent(copy) ||
                        EditorJsonUtility.ToJson(copy) != state.EffectiveJson)
                        throw new InvalidOperationException("effective_settings_clone_failed:" + state.Path);
                    UnityEditorInternal.InternalEditorUtility.SaveToSerializedFileAndForget(new[] { copy }, path, true);
                    if (!File.Exists(path) || new FileInfo(path).Length == 0)
                        throw new InvalidOperationException("effective_settings_serialization_failed:" + state.Path);
                    File.Copy(path, state.Path, true);
                }
                finally
                {
                    if (copy != null && copy != state.Value && !EditorUtility.IsPersistent(copy))
                        UnityEngine.Object.DestroyImmediate(copy);
                }
                if (EditorJsonUtility.ToJson(state.Value) != state.EffectiveJson)
                    throw new InvalidOperationException("effective_settings_memory_changed:" + state.Path);
            }
        }
        internal string[] ChangedDuringBuild() => states.Where(state => state.EffectiveJson == null ||
            EditorJsonUtility.ToJson(state.Value) != state.EffectiveJson).Select(state => state.Path).ToArray();
        internal void Restore()
        {
            var cleanup = new PreviewBuildScope();
            foreach (var state in states)
            {
                // Every step is attempted even if another settings object or disk write fails.
                cleanup.Own(state.Path + ":verify", () =>
                {
                    if (EditorJsonUtility.ToJson(state.Value) != state.Json ||
                        !File.ReadAllBytes(state.Path).SequenceEqual(state.Bytes) || EditorUtility.IsDirty(state.Value) != state.Dirty)
                        throw new InvalidOperationException("project_settings_restore_failed:" + state.Path);
                });
                cleanup.Own(state.Path + ":dirty", () => { if (state.Dirty) EditorUtility.SetDirty(state.Value); else EditorUtility.ClearDirty(state.Value); });
                cleanup.Own(state.Path + ":disk", () => File.WriteAllBytes(state.Path, state.Bytes));
                cleanup.Own(state.Path + ":memory", () => EditorJsonUtility.FromJsonOverwrite(state.Json, state.Value));
            }
            var failures = cleanup.Restore();
            if (failures.Length != 0) throw new InvalidOperationException("project_settings_restore_failed:" + string.Join(",", failures));
        }
    }
}
