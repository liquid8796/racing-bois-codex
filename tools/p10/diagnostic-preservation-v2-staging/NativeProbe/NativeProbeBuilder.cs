using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Runtime.ExceptionServices;
using System.Text;
using RacingBois.Diagnostics.NativeProbe;
using RacingBois.Authoring.Editor;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using App = UnityEngine.Application;

namespace RacingBois.Diagnostics.NativeProbe.Editor
{
    public static class NativeProbeBuilder
    {
        public const string AssetRoot = "Assets/RacingBois/Diagnostics/NativeProbe";
        [Serializable] private sealed class FileRow { public string path, sha256; public long bytes; }
        [Serializable] private sealed class Binding
        { public string sourceFingerprint, backend, unityVersion; public int protocolVersion; }
        [Serializable] private sealed class Receipt
        {
            public int schema = 1, protocolVersion, errors, warnings; public bool passed, sourceBindingPassed, editorSettingsChanged, editorStateRestored;
            public string attemptId, startedUtc, completedUtc, unityVersion, target = "StandaloneWindows64", backend = "Mono2x", apiCompatibility, sourceFingerprint, output, scene, result, failureCode, contentHash, sourcePipeline, ownedPipeline;
            public double buildSeconds; public FileRow[] sources, sourcesAfter, playerFiles; public string[] restorationErrors, changedDuringBuild;
            public NativeBuildDirtyAssetGuard.Evidence[] preexistingDirtyAssets;
            public FileRow fontPreservationReport;
            public string scope = "Isolated source-bound Windows Mono transport diagnostic build. Compilation/build only; actual native WSS/TLS/resume requires its separate runtime report. No game/render/asset/quality acceptance.";
        }
        public static string Build(string outputDirectory, string compileProofPath = "docs/p10/diagnostic-preservation/native-probe-compiled-sources.json")
        {
            var receipt = new Receipt { attemptId = Guid.NewGuid().ToString("N"), startedUtc = DateTime.UtcNow.ToString("O"), unityVersion = App.unityVersion,
                protocolVersion = MultiplayerProtocol.Version, contentHash = GameplayRules.ContentHash, result = "Preparing" };
            string output = null, fontEvidence = null; NativeProbeBuildScope scope = null; ExceptionDispatchInfo failure = null;
            NativeBuildFontPreservationScope fonts = null;
            try
            {
                // Every preflight is read-only. A rejected request must not invoke setters,
                // save dirty assets, create directories/scenes or run restoration setters.
                Require(!EditorApplication.isCompiling && !EditorApplication.isPlayingOrWillChangePlaymode && !BuildPipeline.isBuildingPlayer, "editor_must_be_idle");
                NativeProbeCompiledSources.VerifyExecutingAssemblies(compileProofPath);
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64), "windows64_module_missing");
                string mono = Path.Combine(EditorApplication.applicationContentsPath, "PlaybackEngines/windowsstandalonesupport/Variations/win64_player_nondevelopment_mono");
                Require(Directory.Exists(mono), "windows_mono_player_missing");
                string candidateOutput = Path.GetFullPath(outputDirectory);
                string allowed = Path.GetFullPath("Build/NativeProbe").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                Require(candidateOutput.StartsWith(allowed, StringComparison.OrdinalIgnoreCase), "output_must_be_new_native_probe_child");
                Require(!Directory.Exists(candidateOutput) && !File.Exists(candidateOutput), "fresh_probe_output_required");
                NativeProbeCompiledSources.Inside(Relative(candidateOutput));
                Require(Directory.Exists(AssetRoot + "/Runtime") && Directory.Exists(AssetRoot + "/Editor"), "probe_sources_not_installed");
                var originalPipeline = GraphicsSettings.defaultRenderPipeline; var originalQualityPipeline = QualitySettings.renderPipeline;
                var sourcePipeline = originalQualityPipeline != null ? originalQualityPipeline : originalPipeline;
                Require(sourcePipeline != null && sourcePipeline.GetType().FullName == "UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset", "project_urp_pipeline_required");
                receipt.sourcePipeline = AssetDatabase.GetAssetPath(sourcePipeline);
                Require(!string.IsNullOrEmpty(receipt.sourcePipeline), "persistent_source_pipeline_required");
                var oldBackend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone);
                var oldApis = PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
                bool oldDefaultApis = PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64), oldBackground = PlayerSettings.runInBackground;
                string oldProduct = PlayerSettings.productName; Scene originalActive = SceneManager.GetActiveScene();
                scope = new NativeProbeBuildScope();
                var dirtyAssets = new NativeBuildDirtyAssetGuard(); receipt.preexistingDirtyAssets = dirtyAssets.Before;
                dirtyAssets.RejectUnsavedAuthoringAssets();
                scope.Own("unrelated_dirty_assets", dirtyAssets.VerifyUnchanged);
                scope.Own("unreferenced_dynamic_fonts", () => { if (fonts != null) fonts.Restore(); });
                // Getter-based API rollback cannot recover the hidden explicit list while
                // automatic selection is enabled. Restore the original serialized memory,
                // disk bytes and dirty flags after all ordinary setting/scene callbacks.
                var projectSettings = new NativeBuildProjectSettingsScope();
                scope.Own("project_settings_memory_and_disk", projectSettings.Restore);
                output = candidateOutput;
                Directory.CreateDirectory(output); receipt.output = Relative(output);
                projectSettings.PersistOriginalSettings(Path.Combine(output, "BuildEvidence/original"));
                string generated = AssetRoot + "/Generated"; Directory.CreateDirectory(generated);
                receipt.scene = generated + "/NativeProbe-" + receipt.attemptId + ".unity";
                scope.Own("active_scene", () =>
                {
                    Require(originalActive.IsValid() && originalActive.isLoaded, "original_scene_unavailable");
                    // Closing the owned additive scene may already reactivate the original.
                    // Unity returns false for SetActiveScene on that already-active scene.
                    if (SceneManager.GetActiveScene() != originalActive) SceneManager.SetActiveScene(originalActive);
                    Require(SceneManager.GetActiveScene() == originalActive, "active_scene_restore_failed");
                });
                Scene created = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
                scope.Own("owned_probe_scene", () => { if (created.IsValid() && created.isLoaded) Require(EditorSceneManager.CloseScene(created, true), "owned_scene_close_failed"); });
                SceneManager.SetActiveScene(created);
                var host = new GameObject("RacingBoisNativeWssProbe"); SceneManager.MoveGameObjectToScene(host, created); host.AddComponent<NativeWssProbe>();
                var cameraObject = new GameObject("ProbeCamera"); SceneManager.MoveGameObjectToScene(cameraObject, created);
                var camera = cameraObject.AddComponent<Camera>(); camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.05f, .06f, .07f);
                Require(EditorSceneManager.SaveScene(created, receipt.scene), "probe_scene_save_failed");
                string resources = generated + "/Resources-" + receipt.attemptId;
                if (!AssetDatabase.IsValidFolder(generated)) AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                Require(AssetDatabase.IsValidFolder(generated) && !AssetDatabase.IsValidFolder(resources), "fresh_probe_resource_folder_required");
                AssetDatabase.CreateFolder(generated, "Resources-" + receipt.attemptId);
                var pipeline = UnityEngine.Object.Instantiate(sourcePipeline); pipeline.name = "NativeProbePipeline";
                receipt.ownedPipeline = resources + "/NativeProbePipeline.asset"; AssetDatabase.CreateAsset(pipeline, receipt.ownedPipeline);
                scope.ChangeSetting("graphics_pipeline", () => { GraphicsSettings.defaultRenderPipeline = pipeline; QualitySettings.renderPipeline = pipeline; },
                    () => { GraphicsSettings.defaultRenderPipeline = originalPipeline; QualitySettings.renderPipeline = originalQualityPipeline; });
                projectSettings.UsePipelineAtEveryQuality(pipeline);
                if (oldProduct != "Racing Bois Native WSS Probe") scope.ChangeSetting("product_name", () => PlayerSettings.productName = "Racing Bois Native WSS Probe", () => PlayerSettings.productName = oldProduct);
                if (!oldBackground) scope.ChangeSetting("run_in_background", () => PlayerSettings.runInBackground = true, () => PlayerSettings.runInBackground = oldBackground);
                if (oldBackend != ScriptingImplementation.Mono2x) scope.ChangeSetting("scripting_backend", () => PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x), () => PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, oldBackend));
                if (oldDefaultApis || !oldApis.SequenceEqual(new[] { GraphicsDeviceType.Direct3D11 })) scope.ChangeSetting("graphics_apis", () =>
                {
                    PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
                    PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                }, () =>
                {
                    PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, oldApis);
                    PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, oldDefaultApis);
                    Require(PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64) == oldDefaultApis &&
                        PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64).SequenceEqual(oldApis), "graphics_settings_restore_failed");
                });
                Require(!PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64) &&
                    PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64).SequenceEqual(new[] { GraphicsDeviceType.Direct3D11 }), "direct3d11_graphics_settings_required");
                receipt.apiCompatibility = PlayerSettings.GetApiCompatibilityLevel(NamedBuildTarget.Standalone).ToString();
                var preprocessor = AppDomain.CurrentDomain.GetAssemblies().Select(assembly => assembly.GetType("UnityEditor.Rendering.Universal.ShaderBuildPreprocessor")).FirstOrDefault(type => type != null);
                var gather = preprocessor?.GetMethod("GatherShaderFeatures", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic);
                Require(gather != null, "installed_urp_prefilter_contract_missing"); gather.Invoke(null, new object[] { false });
                // Persist only the owned pipeline and effective settings, never globally save assets.
                AssetDatabase.SaveAssetIfDirty(pipeline); projectSettings.PersistEffectiveSettings(Path.Combine(output, "BuildEvidence/effective"));
                var actualDependencies = AssetDatabase.GetDependencies(new[] { receipt.scene, receipt.ownedPipeline }, true);
                dirtyAssets.RejectDirtyDependencies(actualDependencies);
                fontEvidence = "_local/p10/native-probe/" + receipt.attemptId + "/font-preservation";
                fonts = new NativeBuildFontPreservationScope(actualDependencies, fontEvidence);
                fonts.Apply(); fonts.VerifyProtected();
                receipt.sources = Sources(receipt.scene, receipt.sourcePipeline, receipt.ownedPipeline, compileProofPath); receipt.sourceFingerprint = Fingerprint(receipt.sources);
                CaptureSettings(output, "before"); receipt.result = "Building"; Write(output, receipt);
                dirtyAssets.RejectUnsavedAuthoringAssets(); fonts.VerifyProtected();
                var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { receipt.scene },
                    target = BuildTarget.StandaloneWindows64, locationPathName = Path.Combine(output, "RacingBoisNativeProbe.exe"),
                    options = BuildOptions.StrictMode | BuildOptions.DetailedBuildReport | BuildOptions.CompressWithLz4HC | BuildOptions.CleanBuildCache });
                fonts.VerifyProtected(); NativeProbeCompiledSources.VerifyExecutingAssemblies(compileProofPath);
                receipt.result = build.summary.result.ToString(); receipt.errors = build.summary.totalErrors; receipt.warnings = build.summary.totalWarnings; receipt.buildSeconds = build.summary.totalTime.TotalSeconds;
                receipt.sourcesAfter = Sources(receipt.scene, receipt.sourcePipeline, receipt.ownedPipeline, compileProofPath);
                receipt.changedDuringBuild = receipt.sources.Select(row => row.path).Union(receipt.sourcesAfter.Select(row => row.path))
                    .Where(path => receipt.sources.FirstOrDefault(row => row.path == path)?.sha256 != receipt.sourcesAfter.FirstOrDefault(row => row.path == path)?.sha256)
                    .Union(projectSettings.ChangedDuringBuild()).OrderBy(path => path, StringComparer.Ordinal).ToArray();
                receipt.sourceBindingPassed = receipt.changedDuringBuild.Length == 0 && receipt.sourceFingerprint == Fingerprint(receipt.sourcesAfter);
                CaptureSettings(output, "after");
                Require(build.summary.result == BuildResult.Succeeded && receipt.sourceBindingPassed, "build_failed_or_source_changed");
                Require(PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone) == ScriptingImplementation.Mono2x, "mono_backend_changed");
                Require(File.Exists(Path.Combine(output, "RacingBoisNativeProbe.exe")) && File.Exists(Path.Combine(output, "UnityPlayer.dll")), "player_files_missing");
                File.WriteAllText(Path.Combine(output, "NativeProbe.binding.json"), JsonUtility.ToJson(new Binding
                { sourceFingerprint = receipt.sourceFingerprint, backend = receipt.backend, protocolVersion = receipt.protocolVersion, unityVersion = receipt.unityVersion }, true));
                receipt.playerFiles = Directory.GetFiles(output, "*", SearchOption.AllDirectories).Where(p => Path.GetFileName(p) != "NativeProbe.build.json")
                    .OrderBy(p => p, StringComparer.Ordinal).Select(p => Row(p, Path.GetRelativePath(output, p).Replace('\\', '/'))).ToArray();
                receipt.passed = true;
            }
            catch (Exception error)
            { receipt.failureCode = error.GetType().Name; failure = ExceptionDispatchInfo.Capture(error); }
            finally
            {
                receipt.editorSettingsChanged = scope != null && scope.SettingsChanged;
                receipt.restorationErrors = scope == null ? Array.Empty<string>() : scope.Restore();
                receipt.editorStateRestored = receipt.restorationErrors.Length == 0;
                if (!receipt.editorStateRestored) { receipt.passed = false; if (failure == null) receipt.failureCode = "editor_state_restore_failed"; }
                receipt.completedUtc = DateTime.UtcNow.ToString("O");
                if (output != null && Directory.Exists(output))
                {
                    CaptureSettings(output, "restored");
                    if (fontEvidence != null)
                    {
                        string summary = new[] { "restored.json", "restore-failed.json", "prepared.json" }.Select(name => Path.Combine(fontEvidence, name)).FirstOrDefault(File.Exists);
                        if (summary != null)
                        {
                            string copied = Path.Combine(output, "BuildEvidence/font-preservation.json"); Directory.CreateDirectory(Path.GetDirectoryName(copied));
                            File.Copy(summary, copied, false); receipt.fontPreservationReport = Row(copied, Relative(copied));
                        }
                    }
                    if (receipt.passed) receipt.playerFiles = Directory.GetFiles(output, "*", SearchOption.AllDirectories).Where(p => Path.GetFileName(p) != "NativeProbe.build.json")
                        .OrderBy(p => p, StringComparer.Ordinal).Select(p => Row(p, Path.GetRelativePath(output, p).Replace('\\', '/'))).ToArray();
                    Write(output, receipt);
                }
            }
            if (failure != null) failure.Throw();
            Require(receipt.editorStateRestored, "editor_state_restore_failed");
            return JsonUtility.ToJson(receipt, true);
        }
        private static FileRow[] Sources(string scene, string originalPipeline, string pipeline, string compileProofPath)
        {
            var files = new HashSet<string>(StringComparer.Ordinal);
            foreach (string folder in new[] { "Assets/RacingBois/Client", "Packages/com.racingbois.foundation/Runtime", AssetRoot })
                foreach (string file in Directory.GetFiles(folder, "*", SearchOption.AllDirectories))
                    if (Path.GetExtension(file) == ".cs" || Path.GetExtension(file) == ".asmdef") AddSource(files, file);
            foreach (string logical in AssetDatabase.GetDependencies(new[] { scene, pipeline }, true))
                AddLogicalDependency(files, logical);
            AddLogicalDependency(files, originalPipeline);
            foreach (string path in new[] { scene, pipeline, compileProofPath, "Packages/manifest.json", "Packages/packages-lock.json", "ProjectSettings/ProjectVersion.txt",
                "ProjectSettings/ProjectSettings.asset", "ProjectSettings/GraphicsSettings.asset", "ProjectSettings/QualitySettings.asset" }) AddSource(files, path);
            foreach (string helper in new[] { "NativeBuildProjectSettingsScope", "NativeBuildDirtyAssetGuard", "NativeBuildFontPreservationScope" })
            { files.Add("Assets/RacingBois/Editor/" + helper + ".cs"); files.Add("Assets/RacingBois/Editor/" + helper + ".cs.meta"); }
            files.Add("Assets/RacingBois/Editor/RacingBois.Authoring.Editor.asmdef"); files.Add("Assets/RacingBois/Editor/RacingBois.Authoring.Editor.asmdef.meta");
            files.Add(compileProofPath);
            foreach (string name in NativeProbeCompiledSources.AssemblyNames)
            { files.Add("Library/ScriptAssemblies/" + name + ".dll"); files.Add("Library/ScriptAssemblies/" + name + ".pdb"); }
            return files.OrderBy(p => p, StringComparer.Ordinal).Select(p => Row(p, Relative(p))).ToArray();
        }
        private static void AddLogicalDependency(HashSet<string> files, string logical)
        {
            if (logical == "Resources/unity_builtin_extra" || logical == "Library/unity default resources") return;
            string physical = logical;
            if (logical.StartsWith("Packages/", StringComparison.Ordinal))
            {
                var package = UnityEditor.PackageManager.PackageInfo.FindForAssetPath(logical); string name = logical.Split('/')[1];
                Require(package != null && package.name == name, "virtual_package_unresolved");
                string root = Relative(package.resolvedPath), prefix = "Library/PackageCache/" + name + "@";
                Require(root == "Packages/" + name || root.StartsWith(prefix, StringComparison.Ordinal) && root.Length > prefix.Length && !root.Substring(prefix.Length).Contains("/"), "package_root_not_bounded");
                AddSource(files, Path.Combine(package.resolvedPath, "package.json"));
                physical = Path.Combine(package.resolvedPath, logical.Substring(("Packages/" + name + "/").Length));
            }
            AddSource(files, physical);
        }
        private static void AddSource(HashSet<string> files, string path)
        {
            string relative = Relative(path); Require(File.Exists(NativeProbeCompiledSources.Inside(relative)), "source_dependency_missing"); files.Add(relative);
            if (File.Exists(relative + ".meta")) { NativeProbeCompiledSources.Inside(relative + ".meta"); files.Add(relative + ".meta"); }
        }
        private static void CaptureSettings(string output, string phase)
        {
            string folder = Path.Combine(output, "BuildEvidence", phase); Directory.CreateDirectory(folder);
            foreach (string name in new[] { "ProjectSettings", "GraphicsSettings", "QualitySettings" })
                File.Copy("ProjectSettings/" + name + ".asset", Path.Combine(folder, name + ".asset"), true);
        }
        private static FileRow Row(string path, string relative) => new FileRow { path = relative, sha256 = Digest(path), bytes = new FileInfo(path).Length };
        private static string Relative(string path) => Path.GetRelativePath(Path.GetFullPath("."), Path.GetFullPath(path)).Replace('\\', '/');
        private static string Digest(string path) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
        private static string Fingerprint(IEnumerable<FileRow> files)
        { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", files.Select(f => f.path + ":" + f.sha256))))).Replace("-", "").ToLowerInvariant(); }
        private static void Write(string output, Receipt receipt) => File.WriteAllText(Path.Combine(output, "NativeProbe.build.json"), JsonUtility.ToJson(receipt, true));
        private static void Require(bool valid, string code) { if (!valid) throw new InvalidOperationException(code); }
    }
}
