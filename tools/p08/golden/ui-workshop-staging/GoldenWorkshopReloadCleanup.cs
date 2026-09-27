#if UNITY_EDITOR
using System;
using RacingBois.Golden;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Finishes only the exact owned Play-mode scene unload across a managed assembly reload.</summary>
    [InitializeOnLoad]
    internal static class GoldenWorkshopReloadCleanup
    {
        private const string Key = "RacingBois.GoldenUiWorkshop.PendingCleanup";
        [Serializable] private sealed class Pending { public ulong handle; public string path; }
        private static Pending pending;
        private static AsyncOperation operation;
        static GoldenWorkshopReloadCleanup()
        {
            string value = SessionState.GetString(Key, ""); if (value.Length == 0) return;
            pending = JsonUtility.FromJson<Pending>(value);
            SceneManager.sceneLoaded += Loaded; EditorApplication.update += Poll;
            EditorApplication.playModeStateChanged += PlayMode;
        }
        internal static void Remember(ulong handle, string path)
        { SessionState.SetString(Key, JsonUtility.ToJson(new Pending { handle = handle, path = path })); }
        private static bool Matches(Scene scene) => pending != null && scene.handle.GetRawData() == pending.handle && scene.path == pending.path;
        private static void Loaded(Scene scene, LoadSceneMode mode) { if (Matches(scene)) Unload(scene); }
        private static void Poll()
        {
            if (!EditorApplication.isPlaying) { Clear(); return; }
            if (operation != null) return;
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i); if (!Matches(scene)) continue;
                if (scene.isLoaded) Unload(scene); return;
            }
            GoldenWorkshopProbeRefresh.RecoverCompletedUnload(); Clear();
        }
        private static void Unload(Scene scene)
        {
            if (!EditorApplication.isPlaying || !Matches(scene) || operation != null) return;
            foreach (var root in scene.GetRootGameObjects())
            {
                foreach (var camera in root.GetComponentsInChildren<Camera>(true)) camera.enabled = false;
                foreach (var listener in root.GetComponentsInChildren<AudioListener>(true)) listener.enabled = false;
                foreach (var controller in root.GetComponentsInChildren<GoldenReviewController>(true)) controller.enabled = false;
                foreach (var capture in root.GetComponentsInChildren<GoldenCaptureRunner>(true)) capture.enabled = false;
                foreach (var pipeline in root.GetComponentsInChildren<GoldenReviewPipelineScope>(true)) pipeline.enabled = false;
                root.SetActive(false);
            }
            GoldenWorkshopProbeRefresh.ExpectChange(); operation = SceneManager.UnloadSceneAsync(scene);
            if (operation != null) operation.completed += Completed;
        }
        private static void Completed(AsyncOperation value) { if (operation == value) { operation.completed -= Completed; operation = null; Clear(); } }
        private static void PlayMode(PlayModeStateChange state) { if (state == PlayModeStateChange.EnteredEditMode) Clear(); }
        private static void Clear()
        {
            pending = null; SessionState.EraseString(Key); SceneManager.sceneLoaded -= Loaded;
            EditorApplication.update -= Poll; EditorApplication.playModeStateChanged -= PlayMode;
        }
    }
}
#endif
