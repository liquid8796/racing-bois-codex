using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.ExceptionServices;
using System.Text;
using RacingBois.Gameplay.Definitions;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace RacingBois.Authoring.Editor
{
    public static partial class P08DesktopBuilder
    {
        private const string OwnedBuildPrefix = "Assets/RacingBois/Diagnostics/P08DesktopBuild/";

        private static string BuildOwned(string outputRoot, string compileProof)
        {
            var receipt = new BuildReceipt
            {
                attemptId = Guid.NewGuid().ToString("N"), startedUtc = DateTime.UtcNow.ToString("O"),
                unityVersion = UnityEngine.Application.unityVersion, target = "StandaloneWindows64", scriptingBackend = "Mono2x",
                contentHash = GameplayRules.ContentHash, result = "Preparing", output = outputRoot, compileProof = compileProof,
                validationScope = "Isolated Windows desktop technical candidate, consumed-source/compiled-assembly binding and original state preservation. No art promotion, visual approval, gamewide language, native launch or release acceptance."
            };
            NativeBuildProjectSettingsScope settings = null;
            NativeBuildDirtyAssetGuard dirty = null;
            NativeBuildDirtyAssetGuard preparedDirty = null;
            NativeBuildFontPreservationScope fonts = null;
            P08OwnedUiAssets ui = null;
            ExceptionDispatchInfo failure = null;
            string output = null;
            bool buildSucceeded = false;
            ArchivePreviousBuildReceipt(); WriteBuildReceipt(receipt);
            try
            {
                NeedDesktop(!EditorApplication.isCompiling && !EditorApplication.isUpdating && !EditorApplication.isPlayingOrWillChangePlaymode && !BuildPipeline.isBuildingPlayer, "idle_editor_required");
                receipt.loadedScenesBefore = CaptureLoadedScenes();
                P08DesktopCompiledSources.VerifyExecutingAssemblies(compileProof);
                dirty = new NativeBuildDirtyAssetGuard(); receipt.preexistingDirtyAssets = dirty.Before;
                dirty.RejectUnsavedAuthoringAssets();
                Prepare();
                string candidate = Inside(outputRoot, "Build");
                string relative = Path.GetRelativePath(Path.GetFullPath("."), candidate).Replace('\\', '/');
                P08DesktopCompiledSources.Inside(relative);
                NeedDesktop(!Directory.Exists(candidate) && !File.Exists(candidate), "fresh_desktop_output_required");
                NeedDesktop(File.Exists(RaceBuilder.ScenePath), "reviewed_race_scene_missing");
                var sourcePipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(UrpProfileAuthoring.DesktopPipelinePath);
                NeedDesktop(sourcePipeline != null, "explicit_reviewed_desktop_pipeline_missing");
                dirty.RejectDirtyDependencies(AssetDatabase.GetDependencies(new[] { RaceBuilder.ScenePath, UrpProfileAuthoring.DesktopPipelinePath }, true));
                output = candidate; Directory.CreateDirectory(output); receipt.output = relative;
                settings = new NativeBuildProjectSettingsScope(); settings.PersistOriginalSettings(Path.Combine(output, "BuildEvidence/original"));
                receipt.ownedRoot = OwnedBuildPrefix + receipt.attemptId;
                P08DesktopCompiledSources.Inside(receipt.ownedRoot);
                NeedDesktop(!Directory.Exists(receipt.ownedRoot) && !File.Exists(receipt.ownedRoot) && !File.Exists(receipt.ownedRoot + ".meta"), "fresh_owned_desktop_asset_root_required");
                ui = P08OwnedUiAssets.Prepare(receipt.ownedRoot + "/Ui", "_local/p08-desktop/" + receipt.attemptId + "/original-ui-fonts");
                receipt.originalUiInputs = ui.OriginalFiles.Keys.OrderBy(path => path, StringComparer.Ordinal).Select(CheckedSourceRow).ToArray();
                receipt.ownedUiEvidence = "BuildEvidence/owned-ui.json";
                WriteAtomic(Path.Combine(output, receipt.ownedUiEvidence), ui.Snapshot());
                receipt.scene = receipt.ownedRoot + "/Race.unity";
                CopyOwnedScene(receipt.scene, ui);
                receipt.pipeline = receipt.ownedRoot + "/DesktopPipeline.asset";
                var pipeline = UnityEngine.Object.Instantiate(sourcePipeline); pipeline.name = "DesktopPipeline";
                AssetDatabase.CreateAsset(pipeline, receipt.pipeline);
                UrpProfileAuthoring.ConfigureDesktopRenderer(pipeline, receipt.ownedRoot + "/DesktopRenderer.asset");
                GraphicsSettings.defaultRenderPipeline = pipeline; QualitySettings.renderPipeline = pipeline;
                settings.UsePipelineAtEveryQuality(pipeline);
                PlayerSettings.productName = "Racing Bois"; PlayerSettings.bundleVersion = "0.8.0";
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                NeedDesktop(!PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64) &&
                    PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64).SequenceEqual(new[] { GraphicsDeviceType.Direct3D11 }), "explicit_dx11_policy_not_applied");
                PlayerSettings.defaultScreenWidth = 1920; PlayerSettings.defaultScreenHeight = 1080;
                PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow; PlayerSettings.resizableWindow = true;
                PlayerSettings.runInBackground = true; PlayerSettings.enableFrameTimingStats = true;
                var preprocessor = AppDomain.CurrentDomain.GetAssemblies().Select(assembly => assembly.GetType("UnityEditor.Rendering.Universal.ShaderBuildPreprocessor")).FirstOrDefault(type => type != null);
                var gather = preprocessor?.GetMethod("GatherShaderFeatures", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic);
                NeedDesktop(gather != null, "urp_prefilter_contract_missing"); gather.Invoke(null, new object[] { false });
                AssetDatabase.SaveAssetIfDirty(pipeline);
                settings.PersistEffectiveSettings(Path.Combine(output, "BuildEvidence/effective"));
                receipt.unityDependencyRoots = new[] { receipt.scene, receipt.pipeline };
                var dependencies = AssetDatabase.GetDependencies(receipt.unityDependencyRoots, true);
                NeedDesktop(!dependencies.Contains(RaceBuilder.ScenePath) && !dependencies.Any(ui.OriginalFiles.ContainsKey), "owned_scene_still_consumes_original_ui_or_scene");
                ui.VerifyOriginals(); ui.VerifyClosure(); dirty.VerifyUnchanged();
                // Imports may create new read-only Shader/empty TTF objects. Capture them at
                // this boundary under the unchanged strict guard, after checking entry state.
                // Newly dirty authored owners/atlases still fail the global preflight.
                preparedDirty = new NativeBuildDirtyAssetGuard(); receipt.preparedDirtyAssets = preparedDirty.Before;
                preparedDirty.RejectUnsavedAuthoringAssets(); preparedDirty.RejectDirtyDependencies(dependencies);
                receipt.fontEvidenceDirectory = "_local/p08-desktop/" + receipt.attemptId + "/global-font-preservation";
                fonts = new NativeBuildFontPreservationScope(dependencies, receipt.fontEvidenceDirectory);
                NeedDesktop(fonts.IsGlobalSelection, "global_font_selection_required");
                fonts.Apply(); fonts.VerifyProtected();
                receipt.sourceFiles = SourceSnapshot(receipt.unityDependencyRoots, ui.OriginalFiles.Keys, compileProof, out var captured);
                receipt.sourceFingerprint = SourceFingerprint(receipt.sourceFiles);
                receipt.unityDependencies = captured.files; receipt.unityPackages = captured.packages; receipt.unityBuiltInDependencies = captured.builtIns;
                receipt.unityDependencyFingerprint = DependencyFingerprint(captured, receipt.unityDependencyRoots);
                receipt.result = "Building"; WriteBuildReceipt(receipt);
                preparedDirty.RejectUnsavedAuthoringAssets(); fonts.VerifyProtected(); ui.VerifySourceFiles(); ui.VerifyOwnedFonts();
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { receipt.scene }, locationPathName = Path.Combine(output, "RacingBois.exe"), target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.DetailedBuildReport | BuildOptions.StrictMode | BuildOptions.CompressWithLz4HC
                });
                fonts.VerifyProtected(); ui.VerifySourceFiles(); ui.VerifyOwnedFonts(); P08DesktopCompiledSources.VerifyExecutingAssemblies(compileProof);
                receipt.ownedFontStatePreserved = true;
                receipt.result = report.summary.result.ToString(); receipt.errors = report.summary.totalErrors; receipt.warnings = report.summary.totalWarnings;
                receipt.bytes = (long)report.summary.totalSize; receipt.seconds = report.summary.totalTime.TotalSeconds;
                receipt.sourceFilesAfter = SourceSnapshot(receipt.unityDependencyRoots, ui.OriginalFiles.Keys, compileProof, out var afterDependencies);
                receipt.changedDuringBuild = receipt.sourceFiles.Select(row => row.path).Union(receipt.sourceFilesAfter.Select(row => row.path))
                    .Where(path => receipt.sourceFiles.FirstOrDefault(row => row.path == path)?.sha256 != receipt.sourceFilesAfter.FirstOrDefault(row => row.path == path)?.sha256)
                    .Union(settings.ChangedDuringBuild()).OrderBy(path => path, StringComparer.Ordinal).ToArray();
                receipt.sourceBindingPassed = receipt.changedDuringBuild.Length == 0 && receipt.sourceFingerprint == SourceFingerprint(receipt.sourceFilesAfter) &&
                    receipt.unityDependencyFingerprint == DependencyFingerprint(afterDependencies, receipt.unityDependencyRoots);
                NeedDesktop(report.summary.result == BuildResult.Succeeded && receipt.errors == 0 && receipt.sourceBindingPassed, "desktop_build_or_source_binding_failed");
                NeedDesktop(File.Exists(Path.Combine(output, "RacingBois.exe")) && File.Exists(Path.Combine(output, "UnityPlayer.dll")), "actual_player_files_missing");
                // This new installation alone receives the immutable distribution. Project StreamingAssets stays unchanged.
                string streaming = Path.Combine(output, "RacingBois_Data/StreamingAssets"); Directory.CreateDirectory(streaming);
                var manifest = ReadPack(PackRoot);
                receipt.installedContent = CopyPack(PackRoot, Path.Combine(streaming, "Content"), manifest);
                File.Copy(SelectedConfigPath(), Path.Combine(streaming, ConfigName), true); ValidateConfig(Path.Combine(streaming, ConfigName));
                receipt.manifestSha256 = Digest(Path.Combine(streaming, "Content/manifest.json"));
                NeedDesktop(receipt.manifestSha256 == receipt.sourceFiles.Single(row => row.path == PackRoot + "/manifest.json").sha256,
                    "installed_distribution_differs_from_frozen_pack_manifest");
                WritePlayerInstructions(output);
                var packagedInputs = SourceSnapshot(receipt.unityDependencyRoots, ui.OriginalFiles.Keys, compileProof, out var packagedDependencies);
                NeedDesktop(receipt.sourceFingerprint == SourceFingerprint(packagedInputs) &&
                    receipt.unityDependencyFingerprint == DependencyFingerprint(packagedDependencies, receipt.unityDependencyRoots) && settings.ChangedDuringBuild().Length == 0,
                    "source_or_distribution_changed_during_packaging");
                buildSucceeded = true;
            }
            catch (Exception error)
            { receipt.failureCode = error.GetType().Name + ":" + error.Message; failure = ExceptionDispatchInfo.Capture(error); }
            finally
            {
                var errors = new List<string>();
                try { if (settings != null) { settings.Restore(); receipt.editorStateRestored = true; CaptureRestoredSettings(output); } }
                catch (Exception error) { errors.Add("settings:" + error.GetType().Name + ":" + error.Message); }
                try { if (fonts != null) { fonts.Restore(); receipt.fontPreservationPassed = true; CopyFontSummary(output, receipt.fontEvidenceDirectory); } }
                catch (Exception error) { errors.Add("fonts:" + error.GetType().Name + ":" + error.Message); }
                try { if (dirty != null) { dirty.VerifyUnchanged(); receipt.unrelatedDirtyAssetsPreserved = true; } }
                catch (Exception error) { errors.Add("dirty-assets:" + error.GetType().Name + ":" + error.Message); }
                try { preparedDirty?.VerifyUnchanged(); }
                catch (Exception error) { errors.Add("prepared-dirty-assets:" + error.GetType().Name + ":" + error.Message); }
                try { if (ui != null) { ui.VerifyOriginals(); ui.VerifyOwnedFonts(); receipt.originalUiPreserved = true; WriteAtomic(Path.Combine(output, receipt.ownedUiEvidence), ui.Snapshot()); } }
                catch (Exception error) { errors.Add("original-ui:" + error.GetType().Name + ":" + error.Message); }
                try
                {
                    if (receipt.loadedScenesBefore != null)
                    {
                        receipt.loadedScenesAfter = CaptureLoadedScenes();
                        NeedDesktop(receipt.loadedScenesAfter == receipt.loadedScenesBefore, "loaded_scene_setup_or_source_changed");
                        receipt.loadedScenesPreserved = true;
                    }
                }
                catch (Exception error) { errors.Add("loaded-scenes:" + error.GetType().Name + ":" + error.Message); }
                receipt.restorationErrors = errors.ToArray();
                receipt.passed = buildSucceeded && failure == null && errors.Count == 0 && receipt.editorStateRestored && receipt.unrelatedDirtyAssetsPreserved && receipt.fontPreservationPassed && receipt.originalUiPreserved && receipt.ownedFontStatePreserved && receipt.loadedScenesPreserved;
                receipt.utc = DateTime.UtcNow.ToString("O");
                if (output != null) receipt.playerFiles = Directory.GetFiles(output, "*", SearchOption.AllDirectories).OrderBy(path => path, StringComparer.Ordinal).Select(path => FileRow(output, path)).ToArray();
                WriteBuildReceipt(receipt);
            }
            if (failure != null) failure.Throw();
            NeedDesktop(receipt.passed, "desktop_original_state_restoration_failed");
            return JsonUtility.ToJson(receipt, true);
        }

        private static void CopyOwnedScene(string destination, P08OwnedUiAssets ui)
        {
            NeedDesktop(!File.Exists(destination) && AssetDatabase.CopyAsset(RaceBuilder.ScenePath, destination), "owned_race_scene_copy_failed");
            byte[] original = File.ReadAllBytes(destination);
            string contents = new UTF8Encoding(false, true).GetString(original);
            foreach (var pair in new[] { new[] { P08OwnedUiAssets.SourceTree, ui.TreePath }, new[] { P08OwnedUiAssets.SourcePanel, ui.PanelPath } })
            {
                string oldGuid = AssetDatabase.AssetPathToGUID(pair[0]), newGuid = AssetDatabase.AssetPathToGUID(pair[1]);
                NeedDesktop(oldGuid.Length == 32 && newGuid.Length == 32 && oldGuid != newGuid, "owned_ui_guid_invalid");
                string token = "guid: " + oldGuid;
                NeedDesktop(contents.Split(new[] { token }, StringSplitOptions.None).Length == 2, "scene_ui_reference_must_be_unique:" + pair[0]);
                contents = contents.Replace(token, "guid: " + newGuid);
            }
            WriteAtomic(destination, contents);
            AssetDatabase.ImportAsset(destination, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
            // Never open the original or copied scene before references are safe. No scene/component callback is needed here.
            NeedDesktop(!AssetDatabase.GetDependencies(destination, true).Any(ui.OriginalFiles.ContainsKey), "owned_scene_ui_dependency_remap_failed");
        }

        private static void CaptureRestoredSettings(string output)
        {
            string directory = Path.Combine(output, "BuildEvidence/restored"); Directory.CreateDirectory(directory);
            foreach (string name in new[] { "ProjectSettings", "GraphicsSettings", "QualitySettings" }) File.Copy("ProjectSettings/" + name + ".asset", Path.Combine(directory, name + ".asset"), false);
        }
        [Serializable] private sealed class LoadedSceneEvidence
        { public LoadedSceneRow[] setup; public FileReceipt[] savedFiles; }
        [Serializable] private sealed class LoadedSceneRow
        { public string path; public bool loaded, active; }
        private static string CaptureLoadedScenes()
        {
            for (int i = 0; i < SceneManager.sceneCount; i++)
                NeedDesktop(!SceneManager.GetSceneAt(i).isDirty, "dirty_loaded_scene_before_or_after_build:" + SceneManager.GetSceneAt(i).path);
            var setup = EditorSceneManager.GetSceneManagerSetup();
            return JsonUtility.ToJson(new LoadedSceneEvidence
            {
                setup = setup.Select(scene => new LoadedSceneRow { path = scene.path, loaded = scene.isLoaded, active = scene.isActive }).ToArray(),
                savedFiles = setup.Where(scene => !string.IsNullOrEmpty(scene.path)).Select(scene => scene.path)
                    .SelectMany(path => File.Exists(path + ".meta") ? new[] { path, path + ".meta" } : new[] { path })
                    .Distinct().OrderBy(path => path, StringComparer.Ordinal).Select(CheckedSourceRow).ToArray()
            });
        }
        private static void CopyFontSummary(string output, string privateDirectory)
        {
            string summary = Path.Combine(privateDirectory, "restored.json"); NeedDesktop(File.Exists(summary), "font_restore_summary_missing");
            File.Copy(summary, Path.Combine(output, "BuildEvidence/font-preservation.json"), false);
        }
        private static void WriteAtomic(string path, string value)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)); string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                { byte[] bytes = new UTF8Encoding(false).GetBytes(value); stream.Write(bytes, 0, bytes.Length); stream.Flush(true); }
                if (File.Exists(path)) File.Replace(temporary, path, null); else File.Move(temporary, path);
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
        private static void NeedDesktop(bool value, string code) { if (!value) throw new InvalidOperationException(code); }
    }
}
