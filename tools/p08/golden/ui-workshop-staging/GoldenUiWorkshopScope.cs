#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using RacingBois.Golden;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Owns one newly loaded baked workshop scene; never adopts or unloads a pre-existing scene.</summary>
    public sealed class GoldenUiWorkshopScope : IDisposable
    {
        private const string AllowedRoot = "Assets/RacingBois/Golden/Generated/Garage/";
        private static GoldenUiWorkshopScope currentOwner;
        private readonly string scenePath;
        private readonly string roomIdentity;
        private readonly GameObject lifetimeOwner;
        private readonly Behaviour[] conflictingLighting;
        private readonly Dictionary<Behaviour, bool> suspended = new Dictionary<Behaviour, bool>();
        private readonly HashSet<ulong> priorHandles = new HashSet<ulong>();
        private Scene owned, previousActive;
        private GoldenWorkshopEnvironment previousEnvironment;
        private AsyncOperation unloading;
        private bool requested, disposed, environmentApplied, hooks;
        private double began;
        public string State { get; private set; } = "Main";
        public string ErrorCode { get; private set; } = "";
        public string LoadedSceneSha256 { get; private set; } = "";
        public int DisabledReviewCameras { get; private set; }
        public int DisabledReviewBehaviours { get; private set; }
        public int BakedRendererCount { get; private set; }
        public int BakedReflectionCount { get; private set; }
        public int AuthoredProbePositions { get; private set; }
        public GameObject RoomRoot { get; private set; }
        public bool IsReady => State == "Garage" && owned.IsValid() && owned.isLoaded && !GoldenWorkshopProbeRefresh.Pending;
        public bool IsTransitioning => State == "Loading" || State == "Unloading";
        public ulong OwnedSceneHandle => owned.IsValid() ? owned.handle.GetRawData() : 0UL;
        public event Action Changed;

        public GoldenUiWorkshopScope(string path, string expectedRoomIdentity, GameObject owner, IEnumerable<Behaviour> lightingToSuspend = null)
        {
            scenePath = (path ?? "").Replace('\\', '/'); roomIdentity = expectedRoomIdentity; lifetimeOwner = owner;
            if (!scenePath.StartsWith(AllowedRoot, StringComparison.Ordinal) || !scenePath.EndsWith(".unity", StringComparison.Ordinal) ||
                scenePath.Split('/').Contains("..") || AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) == null)
                throw new ArgumentException("A saved Golden garage scene is required.", nameof(path));
            if (string.IsNullOrWhiteSpace(roomIdentity)) throw new ArgumentException("Pass the actual root identity from the baked scene descriptor.", nameof(expectedRoomIdentity));
            if (owner == null || !owner.scene.IsValid() || !owner.scene.isLoaded) throw new ArgumentException("Pass the actual live fixture owner.", nameof(owner));
            conflictingLighting = lightingToSuspend == null ? Array.Empty<Behaviour>() : lightingToSuspend.Where(value => value != null).Distinct().ToArray();
            foreach (var value in conflictingLighting)
                if (!(value is Light) && !(value is ReflectionProbe) && !(value is Volume))
                    throw new ArgumentException("Only explicitly supplied fixture lights/reflection probes/volumes may be suspended.");
        }
        public void SetGarageVisible(bool visible)
        {
            if (disposed) throw new ObjectDisposedException(nameof(GoldenUiWorkshopScope));
            requested = visible;
            if (!visible) { Leave(); return; }
            Hook();
            if (State == "Main" && !GoldenWorkshopProbeRefresh.Pending) Enter();
        }
        private void Enter()
        {
            if (!EditorApplication.isPlaying || EditorApplication.isCompiling || lifetimeOwner == null)
                throw new InvalidOperationException("Workshop staging requires the live idle Play-mode fixture.");
            if (currentOwner != null && currentOwner != this) throw new InvalidOperationException("Another workshop scope owns a scene.");
            priorHandles.Clear();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i); priorHandles.Add(scene.handle.GetRawData());
                if (scene.path == scenePath) throw new InvalidOperationException("This garage scene is already loaded/loading; it is not owned by this scope.");
            }
            string sceneDigest = Digest(scenePath);
            currentOwner = this; Hook(); ErrorCode = ""; State = "Loading"; began = EditorApplication.timeSinceStartup;
            LoadedSceneSha256 = sceneDigest; GoldenWorkshopProbeRefresh.ExpectChange();
            try
            {
                // This API returns a loading Scene; sceneLoaded runs after OnEnable and before Start.
                var loaded = EditorSceneManager.LoadSceneInPlayMode(scenePath, new LoadSceneParameters(LoadSceneMode.Additive));
                if (!loaded.IsValid() || priorHandles.Contains(loaded.handle.GetRawData())) throw new InvalidOperationException("Owned scene identity was not established.");
                owned = loaded; Notify();
            }
            catch (Exception error)
            {
                if (!owned.IsValid()) GoldenWorkshopProbeRefresh.CancelUnstartedChange();
                Fail(error); throw;
            }
        }
        private void OnLoaded(Scene scene, LoadSceneMode mode)
        {
            if (!Owns(scene)) return;
            try
            {
                DisableReviewComponents(scene);
                if (!requested || disposed || lifetimeOwner == null) { Leave(); return; }
                if (Digest(scenePath) != LoadedSceneSha256) throw new InvalidOperationException("Garage scene changed while loading.");
                previousActive = SceneManager.GetActiveScene(); previousEnvironment = new GoldenWorkshopEnvironment();
                environmentApplied = true;
                foreach (var value in conflictingLighting)
                    if (value != null) { suspended[value] = value.enabled; value.enabled = false; }
                if (SceneManager.GetActiveScene() != scene) SceneManager.SetActiveScene(scene);
                if (SceneManager.GetActiveScene() != scene) throw new InvalidOperationException("Could not activate the owned garage lighting environment.");
                // Arrays/indices are left to Unity's additive scene merge. No copied lightmaps,
                // rebaked probes, replacement materials or fake scene-image background.
                var roots = scene.GetRootGameObjects();
                var rooms = roots.Where(root => root.name == roomIdentity).ToArray();
                if (rooms.Length != 1) throw new InvalidOperationException("Expected room root is missing or ambiguous in the owned scene.");
                RoomRoot = rooms[0];
                BakedRendererCount = roots.SelectMany(root => root.GetComponentsInChildren<Renderer>(true))
                    .Count(renderer => renderer.lightmapIndex >= 0 && renderer.lightmapIndex < LightmapSettings.lightmaps.Length && LightmapSettings.lightmaps[renderer.lightmapIndex].lightmapColor != null);
                BakedReflectionCount = roots.SelectMany(root => root.GetComponentsInChildren<ReflectionProbe>(true))
                    .Count(probe => (probe.mode == ReflectionProbeMode.Baked && probe.bakedTexture != null) ||
                        (probe.mode == ReflectionProbeMode.Custom && probe.customBakedTexture != null));
                AuthoredProbePositions = roots.SelectMany(root => root.GetComponentsInChildren<LightProbeGroup>(true)).Sum(group => group.probePositions.Length);
                if (BakedRendererCount == 0 || BakedReflectionCount == 0 || AuthoredProbePositions == 0)
                    throw new InvalidOperationException("Loaded garage lacks its actual baked maps/reflection/probe group.");
                State = "Garage"; Notify();
            }
            catch (Exception error) { Fail(error); }
        }
        private void DisableReviewComponents(Scene scene)
        {
            var roots = scene.GetRootGameObjects(); DisabledReviewCameras = DisabledReviewBehaviours = 0;
            foreach (var root in roots)
            {
                foreach (var camera in root.GetComponentsInChildren<Camera>(true)) { camera.enabled = false; DisabledReviewCameras++; }
                foreach (var listener in root.GetComponentsInChildren<AudioListener>(true)) listener.enabled = false;
                foreach (var control in root.GetComponentsInChildren<GoldenReviewController>(true)) { control.enabled = false; DisabledReviewBehaviours++; }
                foreach (var capture in root.GetComponentsInChildren<GoldenCaptureRunner>(true)) { capture.enabled = false; DisabledReviewBehaviours++; }
                foreach (var pipeline in root.GetComponentsInChildren<GoldenReviewPipelineScope>(true)) { pipeline.enabled = false; DisabledReviewBehaviours++; }
            }
            // Known pipeline OnEnable can already have run; its own OnDisable restores the
            // previous pipeline. Never overwrite an unrelated newer pipeline with a stale snapshot.
        }
        private bool Owns(Scene scene) => owned.IsValid() && scene.handle == owned.handle && scene.path == scenePath && !priorHandles.Contains(scene.handle.GetRawData());
        private void Leave()
        {
            // Restoration errors must not prevent owned-scene cleanup.
            try { RestoreEnvironment(); }
            catch (Exception error) { RecordCleanupError(error); }
            if (State == "Loading" && owned.IsValid() && !owned.isLoaded) return; // Cancel-after-load callback owns cleanup before Start.
            if (unloading != null) return;
            if (!owned.IsValid() || !owned.isLoaded) { FinishUnload(); return; }
            if (!Owns(owned)) throw new InvalidOperationException("Refusing to unload a scene not owned by this scope.");
            DisableReviewComponents(owned);
            foreach (var root in owned.GetRootGameObjects()) root.SetActive(false);
            State = "Unloading"; GoldenWorkshopProbeRefresh.ExpectChange();
            unloading = SceneManager.UnloadSceneAsync(owned);
            if (unloading == null) throw new InvalidOperationException("Owned scene unload did not start.");
            unloading.completed += OnUnloadCompleted; Notify();
        }
        private void RestoreEnvironment()
        {
            if (!environmentApplied) return;
            environmentApplied = false;
            try
            {
                if (previousActive.IsValid() && previousActive.isLoaded)
                {
                    if (SceneManager.GetActiveScene() != previousActive) SceneManager.SetActiveScene(previousActive);
                    if (SceneManager.GetActiveScene() != previousActive) throw new InvalidOperationException("Previous active scene was not restored.");
                    // If the caller destroyed its owner first, do not overwrite its later teardown
                    // with an old fixture-light snapshot. The active scene retains its current environment.
                    if (lifetimeOwner != null) previousEnvironment?.Restore();
                }
            }
            finally
            {
                previousEnvironment = null;
                foreach (var entry in suspended)
                    try { if (entry.Key != null) entry.Key.enabled = entry.Value; }
                    catch (Exception error) { RecordCleanupError(error); }
                suspended.Clear();
            }
        }
        private void OnUnloadCompleted(AsyncOperation operation)
        { if (unloading != operation) return; unloading.completed -= OnUnloadCompleted; unloading = null; FinishUnload(); }
        private void FinishUnload()
        {
            owned = default; RoomRoot = null; State = disposed ? "Closed" : "Main"; if (currentOwner == this) currentOwner = null;
            if (disposed) Unhook();
            Notify();
            // A rapid Main→Garage request waits for unload and probe removal before loading anew.
        }
        private void Tick()
        {
            if (!EditorApplication.isPlaying) { Unhook(); if (currentOwner == this) currentOwner = null; return; }
            if (!disposed && lifetimeOwner == null) Dispose();
            try
            {
                if (State == "Main" && requested && !disposed && !GoldenWorkshopProbeRefresh.Pending) Enter();
                if (State == "Loading" && requested && EditorApplication.timeSinceStartup - began > 15) Fail(new TimeoutException("Garage scene load exceeded 15 s."));
            }
            catch (Exception error) { Fail(error); }
        }
        private void Fail(Exception error)
        {
            ErrorCode = error.GetType().Name + ":" + error.Message; requested = false;
            Debug.LogError("Golden workshop scope: " + ErrorCode);
            try { Leave(); } catch (Exception cleanup) { Debug.LogError("Golden workshop cleanup: " + cleanup.GetType().Name); }
            Notify();
        }
        private void Hook()
        {
            if (hooks) return; hooks = true;
            SceneManager.sceneLoaded += OnLoaded; EditorApplication.update += Tick;
            EditorApplication.playModeStateChanged += OnPlayMode; AssemblyReloadEvents.beforeAssemblyReload += BeforeReload;
        }
        private void Unhook()
        {
            if (!hooks) return; hooks = false;
            SceneManager.sceneLoaded -= OnLoaded; EditorApplication.update -= Tick;
            EditorApplication.playModeStateChanged -= OnPlayMode; AssemblyReloadEvents.beforeAssemblyReload -= BeforeReload;
        }
        private void OnPlayMode(PlayModeStateChange state)
        {
            if (state == PlayModeStateChange.ExitingPlayMode) Dispose();
            if (state == PlayModeStateChange.EnteredEditMode) { Unhook(); if (currentOwner == this) currentOwner = null; }
        }
        private void BeforeReload()
        {
            try { Dispose(); }
            finally { if (owned.IsValid()) GoldenWorkshopReloadCleanup.Remember(owned.handle.GetRawData(), scenePath); Unhook(); }
        }
        public void Dispose()
        {
            if (disposed) return; disposed = true; requested = false;
            if (EditorApplication.isPlaying) Leave();
            else { environmentApplied = false; previousEnvironment = null; suspended.Clear(); State = "Closed"; Unhook(); if (currentOwner == this) currentOwner = null; }
        }
        private void Notify()
        { try { Changed?.Invoke(); } catch (Exception error) { Debug.LogError("Golden workshop observer: " + error.GetType().Name); } }
        private void RecordCleanupError(Exception error)
        { ErrorCode += (ErrorCode.Length == 0 ? "" : ";") + "cleanup:" + error.GetType().Name; Debug.LogError("Golden workshop cleanup: " + error.GetType().Name); }
        private static string Digest(string path)
        { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
    }
}
#endif
