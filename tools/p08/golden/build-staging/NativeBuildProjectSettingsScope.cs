using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Owns only the three native build settings files; preserves their original memory, bytes and dirty state.</summary>
    public sealed class NativeBuildProjectSettingsScope
    {
        private sealed class State
        {
            internal UnityEngine.Object Value;
            internal string Path, Json, EffectiveJson;
            internal byte[] Bytes;
            internal bool Dirty;
        }
        private readonly State[] states;
        private bool restored;

        public NativeBuildProjectSettingsScope()
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
        public void PersistOriginalSettings(string directory)
        {
            Directory.CreateDirectory(directory);
            foreach (var state in states) WriteNew(Path.Combine(directory, Path.GetFileName(state.Path)), state.Bytes);
        }
        public void UsePipelineAtEveryQuality(RenderPipelineAsset pipeline)
        {
            if (restored || pipeline == null) throw new InvalidOperationException("native_settings_scope_unavailable");
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
        public void PersistEffectiveSettings(string evidenceDirectory)
        {
            if (restored) throw new InvalidOperationException("native_settings_scope_restored");
            Directory.CreateDirectory(evidenceDirectory);
            foreach (var state in states)
            {
                state.EffectiveJson = EditorJsonUtility.ToJson(state.Value);
                string path = Path.Combine(evidenceDirectory, Path.GetFileName(state.Path));
                if (File.Exists(path)) throw new InvalidOperationException("fresh_settings_evidence_required");
                UnityEngine.Object copy = null;
                try
                {
                    // Proven native path: persistent ProjectSettings objects cannot be passed
                    // directly to SaveToSerializedFileAndForget or persisted by SaveAssetIfDirty.
                    copy = UnityEngine.Object.Instantiate(state.Value);
                    if (copy == null || copy == state.Value || EditorUtility.IsPersistent(copy) || EditorJsonUtility.ToJson(copy) != state.EffectiveJson)
                        throw new InvalidOperationException("effective_settings_clone_failed:" + state.Path);
                    UnityEditorInternal.InternalEditorUtility.SaveToSerializedFileAndForget(new[] { copy }, path, true);
                    if (!File.Exists(path) || new FileInfo(path).Length == 0) throw new InvalidOperationException("effective_settings_serialization_failed:" + state.Path);
                    File.Copy(path, state.Path, true);
                }
                finally { if (copy != null && copy != state.Value && !EditorUtility.IsPersistent(copy)) UnityEngine.Object.DestroyImmediate(copy); }
                if (EditorJsonUtility.ToJson(state.Value) != state.EffectiveJson) throw new InvalidOperationException("effective_settings_memory_changed:" + state.Path);
            }
        }
        public string[] ChangedDuringBuild() => states.Where(state => state.EffectiveJson == null || EditorJsonUtility.ToJson(state.Value) != state.EffectiveJson).Select(state => state.Path).ToArray();
        public void Restore()
        {
            if (restored) return;
            restored = true;
            var failures = new List<string>();
            // Attempt every independent restore even if a previous object/disk write failed.
            foreach (var state in states)
            {
                Attempt(() => EditorJsonUtility.FromJsonOverwrite(state.Json, state.Value), state.Path + ":memory", failures);
                Attempt(() => File.WriteAllBytes(state.Path, state.Bytes), state.Path + ":disk", failures);
                Attempt(() => { if (state.Dirty) EditorUtility.SetDirty(state.Value); else EditorUtility.ClearDirty(state.Value); }, state.Path + ":dirty", failures);
                Attempt(() =>
                {
                    if (EditorJsonUtility.ToJson(state.Value) != state.Json || !File.ReadAllBytes(state.Path).SequenceEqual(state.Bytes) || EditorUtility.IsDirty(state.Value) != state.Dirty)
                        throw new InvalidOperationException("original_settings_mismatch");
                }, state.Path + ":verify", failures);
            }
            if (failures.Count != 0) throw new InvalidOperationException("project_settings_restore_failed:" + string.Join(",", failures));
        }
        private static void Attempt(Action operation, string label, List<string> failures) { try { operation(); } catch (Exception error) { failures.Add(label + ":" + error.GetType().Name); } }
        private static void WriteNew(string path, byte[] bytes) { using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write)) stream.Write(bytes, 0, bytes.Length); }
    }
}
