#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Rebuilds Unity's runtime probe lookup only on its data-ready signal; never writes probe/lightmap assets.</summary>
    [InitializeOnLoad]
    internal static class GoldenWorkshopProbeRefresh
    {
        private const string Key = "RacingBois.GoldenUiWorkshop.ProbeRefreshPending";
        private static bool listening;
        internal static bool Pending => SessionState.GetBool(Key, false);
        static GoldenWorkshopProbeRefresh() { if (Pending) Listen(); }
        internal static void ExpectChange() { SessionState.SetBool(Key, true); Listen(); }
        private static void Listen()
        {
            if (listening) return; listening = true;
            LightProbes.needsRetetrahedralization += DataReady;
            EditorApplication.playModeStateChanged += OnPlayMode;
        }
        private static void DataReady()
        {
            if (EditorApplication.isPlaying && LightmapSettings.lightProbes != null && LightmapSettings.lightProbes.count >= 4) LightProbes.Tetrahedralize();
            SessionState.SetBool(Key, false);
        }
        // On reload the native unload may have completed before the new managed callback
        // subscribed. Rebuild the currently loaded data once; later Unity data-ready signals
        // remain responsible for any still-pending external probe load.
        internal static void RecoverCompletedUnload()
        {
            if (!EditorApplication.isPlaying) { Clear(); return; }
            if (LightmapSettings.lightProbes != null && LightmapSettings.lightProbes.count >= 4) LightProbes.Tetrahedralize();
            // Keep listening until Play mode exits. Unity can deliver another external
            // probe-data update after the scene-unload callback or a managed reload.
            SessionState.SetBool(Key, false); Listen();
        }
        internal static void CancelUnstartedChange() { SessionState.SetBool(Key, false); }
        private static void OnPlayMode(PlayModeStateChange state) { if (state == PlayModeStateChange.EnteredEditMode) Clear(); }
        private static void Clear()
        {
            SessionState.SetBool(Key, false);
            if (!listening) return; listening = false;
            LightProbes.needsRetetrahedralization -= DataReady; EditorApplication.playModeStateChanged -= OnPlayMode;
        }
    }
}
#endif
