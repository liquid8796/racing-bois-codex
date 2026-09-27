using System;
using System.IO;
using System.Linq;
using System.Runtime.ExceptionServices;
using RacingBois.Client.Bootstrap;
using RacingBois.Authoring.Editor;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace RacingBois.Diagnostics.NativeBaseline.Editor
{
    public static class NativeBaselineBuilder
    {
        public const string AssetRoot = "Assets/RacingBois/Diagnostics/NativeBaseline";
        [Serializable] private sealed class Receipt
        {
            public int schema = 1, errors, warnings; public bool passed, sourceBindingPassed, editorStateRestored, settingsChanged;
            public string attemptId, startedUtc, completedUtc, unityVersion, target = "StandaloneWindows64", backend = "Mono2x", output, result, failureCode, sourceFingerprint, scene, sourceScene, sourceSceneSha256;
            public double buildSeconds; public BaselineFile[] sources, sourcesAfter, playerFiles, baselinePrefabs;
            public string[] changedDuringBuild, restorationErrors, builtInDependencies;
            public NativeBuildDirtyAssetGuard.Evidence[] dirtyAssetsBefore;
            public BaselineFile fontPreservationReport;
            public string scope = "Isolated native baseline P06 workload build with actual baseline prefabs. No P08 roster/content promotion, gameplay UI, physical input or final-release acceptance.";
        }
        public static string Build(string outputDirectory, bool stress = false, string compileProof = "docs/p10/native-baseline/compiled-sources.json", string pipelinePath = "Assets/RacingBois/Settings/Desktop/DesktopPipeline.asset")
        {
            var result = new Receipt { attemptId = Guid.NewGuid().ToString("N"), startedUtc = DateTime.UtcNow.ToString("O"), unityVersion = Application.unityVersion, result = "Preparing" };
            BaselineBuildScope scope = null; string output = null, fontEvidence = null; ExceptionDispatchInfo failure = null;
            NativeBuildFontPreservationScope fonts = null;
            try
            {
                Need(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !BuildPipeline.isBuildingPlayer, "editor_must_be_idle");
                BaselineBuildInputs.VerifyAssemblies(compileProof);
                Need(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64), "windows_module_missing");
                Need(Directory.Exists(Path.Combine(EditorApplication.applicationContentsPath, "PlaybackEngines/windowsstandalonesupport/Variations/win64_player_nondevelopment_mono")), "mono_player_missing");
                result.sourceScene = stress ? "Assets/RacingBois/Scenes/StressBenchmark.unity" : "Assets/RacingBois/Scenes/ArtBenchmark.unity";
                Need(File.Exists(result.sourceScene), "baseline_scene_missing"); result.sourceSceneSha256 = BaselineBuildInputs.Hash(result.sourceScene);
                var sourcePipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(pipelinePath);
                Need(sourcePipeline != null, "explicit_desktop_pipeline_required");
                string candidate = BaselineBuildInputs.Inside(BaselineBuildInputs.Relative(outputDirectory));
                Need(candidate.StartsWith(Path.GetFullPath("Build/NativeBaseline") + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) && !Directory.Exists(candidate) && !File.Exists(candidate), "fresh_native_baseline_output_required");
                var active = SceneManager.GetActiveScene();
                var previousPipeline = GraphicsSettings.defaultRenderPipeline; var previousQualityPipeline = QualitySettings.renderPipeline;
                var backend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone); var apis = PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
                bool defaultApis = PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64);
                scope = new BaselineBuildScope();
                var dirtyAssets = new NativeBuildDirtyAssetGuard(); result.dirtyAssetsBefore = dirtyAssets.Before;
                dirtyAssets.RejectUnsavedAuthoringAssets();
                scope.Own("unrelated_dirty_assets", dirtyAssets.VerifyUnchanged);
                // Reverse-order cleanup restores settings first, then fonts, then checks unrelated dirty assets.
                scope.Own("unreferenced_dynamic_fonts", () => { if (fonts != null) fonts.Restore(); });
                var settings = new NativeBuildProjectSettingsScope(); scope.Own("settings_memory_disk", settings.Restore);
                output = candidate; Directory.CreateDirectory(output); result.output = BaselineBuildInputs.Relative(output);
                settings.PersistOriginalSettings(Path.Combine(output, "BuildEvidence/original"));
                string owned = AssetRoot + "/Generated/" + result.attemptId; Directory.CreateDirectory(owned);
                result.scene = owned + "/NativeBaseline.unity";
                Need(AssetDatabase.CopyAsset(result.sourceScene, result.scene), "baseline_scene_copy_failed");
                scope.Own("active_scene", () => { Need(active.IsValid() && active.isLoaded, "prior_scene_missing"); if (SceneManager.GetActiveScene() != active) SceneManager.SetActiveScene(active); Need(SceneManager.GetActiveScene() == active, "active_scene_restore_failed"); });
                var scene = EditorSceneManager.OpenScene(result.scene, OpenSceneMode.Additive);
                scope.Own("owned_scene", () => { if (scene.IsValid() && scene.isLoaded) Need(EditorSceneManager.CloseScene(scene, true), "owned_scene_close_failed"); });
                SceneManager.SetActiveScene(scene);
                var all = scene.GetRootGameObjects();
                var workload = all.SelectMany(x => x.GetComponentsInChildren<P06BenchmarkRunner>(true)).Single();
                Need(workload.Stage != null && workload.Stage.Road != null && workload.Stage.ViewCamera != null && workload.VisualQuality != null && workload.AudioBank != null && workload.AudioBank.IsComplete, "baseline_workload_references_missing");
                // Keep component identities alive for UI Toolkit's Editor live-reload tracker.
                // The workload shares this GameObject; deleting the owner would delete its stage controls.
                // Only the owned scene copy is altered. Disabled/detached bootstrap/UI never start.
                foreach (var document in all.SelectMany(x => x.GetComponentsInChildren<UIDocument>(true)))
                { document.enabled = false; document.visualTreeAsset = null; document.panelSettings = null; }
                foreach (var boot in all.SelectMany(x => x.GetComponentsInChildren<RaceBootstrap>(true)))
                { boot.enabled = false; boot.Document = null; }
                workload.AutoStart = false; workload.enabled = true; workload.Stress = stress; workload.BuildStageOnStart = true;
                workload.EnableAudio = true; workload.ReducedMotion = false; workload.QualityIndex = 1; workload.WarmupSeconds = 10;
                workload.RuntimeSourceRevision = "native-baseline-bound-in-player-receipt";
                workload.gameObject.AddComponent<NativeBaselineRecorder>().Workload = workload;
                var stage = workload.Stage;
                var prefabs = new[] { stage.MotorcyclePrefab, stage.RiderPrefab, stage.PoliceMotorcyclePrefab, stage.PoliceRiderPrefab, stage.CoupePrefab, stage.VanPrefab, stage.PedestrianPrefab, stage.ClubPrefab };
                Need(prefabs.All(x => x != null && PrefabUtility.IsPartOfPrefabAsset(x)), "baseline_actor_prefabs_missing");
                result.baselinePrefabs = prefabs.Select(x => AssetDatabase.GetAssetPath(x)).Distinct().OrderBy(x => x, StringComparer.Ordinal).Select(BaselineBuildInputs.Row).ToArray();
                Need(EditorSceneManager.SaveScene(scene), "owned_scene_save_failed");
                string ownedPipelinePath = owned + "/BaselinePipeline.asset";
                var pipeline = UnityEngine.Object.Instantiate(sourcePipeline); AssetDatabase.CreateAsset(pipeline, ownedPipelinePath);
                scope.Change("pipeline", () => { GraphicsSettings.defaultRenderPipeline = pipeline; QualitySettings.renderPipeline = pipeline; }, () => { GraphicsSettings.defaultRenderPipeline = previousPipeline; QualitySettings.renderPipeline = previousQualityPipeline; });
                scope.Change("backend", () => PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x), () => PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, backend));
                // Unity requires an explicit API list before disabling automatic selection.
                scope.Change("graphics", () => { PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 }); PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false); }, () => { PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, apis); PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, defaultApis); });
                PlayerSettings.productName = "Racing Bois Native Baseline Diagnostic"; PlayerSettings.runInBackground = true;
                PlayerSettings.defaultScreenWidth = 1920; PlayerSettings.defaultScreenHeight = 1080; PlayerSettings.fullScreenMode = FullScreenMode.Windowed; PlayerSettings.resizableWindow = false;
                PlayerSettings.enableFrameTimingStats = true;
                settings.UsePipelineAtEveryQuality(pipeline);
                var preprocessor = AppDomain.CurrentDomain.GetAssemblies().Select(x => x.GetType("UnityEditor.Rendering.Universal.ShaderBuildPreprocessor")).FirstOrDefault(x => x != null);
                var gather = preprocessor?.GetMethod("GatherShaderFeatures", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic);
                Need(gather != null, "urp_prefilter_contract_missing"); gather.Invoke(null, new object[] { false });
                AssetDatabase.SaveAssetIfDirty(pipeline);
                Need(!PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64)
                    && PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64).SequenceEqual(new[] { GraphicsDeviceType.Direct3D11 }), "explicit_dx11_policy_not_applied");
                settings.PersistEffectiveSettings(Path.Combine(output, "BuildEvidence/effective"));
                var actualDependencies = AssetDatabase.GetDependencies(new[] { result.scene, ownedPipelinePath }, true);
                dirtyAssets.RejectDirtyDependencies(actualDependencies);
                // Private backup bytes never enter the player directory or committed evidence.
                fontEvidence = "_local/p10/native-baseline/" + result.attemptId + "/font-preservation";
                fonts = new NativeBuildFontPreservationScope(actualDependencies, fontEvidence);
                fonts.Apply(); fonts.VerifyProtected();
                result.sources = BaselineBuildInputs.Snapshot(result.scene, result.sourceScene, ownedPipelinePath, pipelinePath, compileProof);
                result.sourceFingerprint = BaselineBuildInputs.Fingerprint(result.sources);
                result.builtInDependencies = AssetDatabase.GetDependencies(new[] { result.scene, ownedPipelinePath }, true).Where(x => x == "Resources/unity_builtin_extra" || x == "Library/unity default resources").Distinct().OrderBy(x => x).ToArray();
                CaptureSettings(output, "before"); result.result = "Building"; Write(output, result);
                dirtyAssets.RejectUnsavedAuthoringAssets();
                fonts.VerifyProtected();
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { result.scene }, target = BuildTarget.StandaloneWindows64,
                    locationPathName = Path.Combine(output, "RacingBoisNativeBaseline.exe"), options = BuildOptions.StrictMode | BuildOptions.DetailedBuildReport | BuildOptions.CompressWithLz4HC });
                fonts.VerifyProtected();
                result.result = report.summary.result.ToString(); result.errors = report.summary.totalErrors; result.warnings = report.summary.totalWarnings; result.buildSeconds = report.summary.totalTime.TotalSeconds;
                result.sourcesAfter = BaselineBuildInputs.Snapshot(result.scene, result.sourceScene, ownedPipelinePath, pipelinePath, compileProof);
                result.changedDuringBuild = result.sources.Select(x => x.path).Union(result.sourcesAfter.Select(x => x.path)).Where(path => result.sources.FirstOrDefault(x => x.path == path)?.sha256 != result.sourcesAfter.FirstOrDefault(x => x.path == path)?.sha256).Union(settings.ChangedDuringBuild()).OrderBy(x => x, StringComparer.Ordinal).ToArray();
                result.sourceBindingPassed = result.changedDuringBuild.Length == 0 && result.sourceFingerprint == BaselineBuildInputs.Fingerprint(result.sourcesAfter);
                CaptureSettings(output, "after"); Need(result.result == "Succeeded" && result.sourceBindingPassed && result.errors == 0, "native_build_or_binding_failed");
                Need(BaselineBuildInputs.Hash(result.sourceScene) == result.sourceSceneSha256, "original_benchmark_scene_changed");
                var binding = new NativeBaselineRecorder.Binding { sourceFingerprint = result.sourceFingerprint, unityVersion = Application.unityVersion, sourceScene = result.sourceScene, route = "TrackDefinition.Default / baseline Canyon", width = 1920, height = 1080, quality = 1, seconds = 600, warmup = 10, targetFrameRate = -1, vSyncCount = 0, stress = stress };
                File.WriteAllText(Path.Combine(output, "NativeBaseline.binding.json"), JsonUtility.ToJson(binding, true));
                result.passed = true;
            }
            catch (Exception error) { result.failureCode = error.GetType().Name; failure = ExceptionDispatchInfo.Capture(error); }
            finally
            {
                result.settingsChanged = scope != null && scope.Changed; result.restorationErrors = scope == null ? Array.Empty<string>() : scope.Restore();
                result.editorStateRestored = result.restorationErrors.Length == 0;
                if (!result.editorStateRestored) result.passed = false;
                result.completedUtc = DateTime.UtcNow.ToString("O");
                if (output != null)
                {
                    CaptureSettings(output, "restored");
                    if (fontEvidence != null)
                    {
                        string summary = new[] { "restored.json", "restore-failed.json", "prepared.json" }.Select(name => Path.Combine(fontEvidence, name)).FirstOrDefault(File.Exists);
                        if (summary != null)
                        {
                            string copied = Path.Combine(output, "BuildEvidence/font-preservation.json");
                            File.Copy(summary, copied, false); result.fontPreservationReport = BaselineBuildInputs.Row(copied);
                        }
                    }
                    result.playerFiles = Directory.GetFiles(output, "*", SearchOption.AllDirectories).Where(x => Path.GetFileName(x) != "NativeBaseline.build.json").OrderBy(x => x, StringComparer.Ordinal).Select(x => new BaselineFile { path = Path.GetRelativePath(output, x).Replace('\\', '/'), bytes = new FileInfo(x).Length, sha256 = BaselineBuildInputs.Hash(x) }).ToArray();
                    Write(output, result);
                }
            }
            if (failure != null) failure.Throw(); Need(result.editorStateRestored, "editor_restore_failed"); return JsonUtility.ToJson(result, true);
        }
        private static void CaptureSettings(string output, string phase)
        { string folder = Path.Combine(output, "BuildEvidence", phase); Directory.CreateDirectory(folder); foreach (string name in new[] { "ProjectSettings", "GraphicsSettings", "QualitySettings" }) File.Copy("ProjectSettings/" + name + ".asset", Path.Combine(folder, name + ".asset"), true); }
        private static void Write(string output, Receipt result) => File.WriteAllText(Path.Combine(output, "NativeBaseline.build.json"), JsonUtility.ToJson(result, true));
        private static void Need(bool value, string code) => BaselineBuildInputs.Need(value, code);
    }
}
