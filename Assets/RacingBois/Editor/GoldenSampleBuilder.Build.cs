using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.ExceptionServices;
using RacingBois.Golden;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        [Serializable] private sealed class GoldenBuildReceipt
        {
            public int schema = 1;
            public string attemptId, utc, unityVersion, target = "StandaloneWindows64", backend = "Mono2x", graphicsApi = "Direct3D11";
            public string descriptor, output, sourceFingerprint, result, failure, scene, ownedPipeline, fontEvidenceDirectory;
            public bool passed, sourceBindingPassed, editorStateRestored, unrelatedDirtyAssetsPreserved, fontPreservationPassed;
            public int errors, warnings;
            public long bytes;
            public double seconds;
            public FileReceipt[] inputs, inputsAfter, playerFiles;
            public string[] changedDuringBuild, restorationErrors;
            public NativeBuildDirtyAssetGuard.Evidence[] preexistingDirtyAssets;
            public NativeBuildFontPreservationScope.FontRecord[] protectedFonts;
            public FileReceipt[] fontEvidence;
            public string scope = "Isolated native art-review player build. Not a Racing Bois release, gameplay acceptance, visual approval or performance certification.";
        }

        /// <summary>Builds into a new folder, persists only owned resources/settings, then verifies exact settings/user-asset restoration.</summary>
        public static string BuildReviewPlayer(string descriptorPath, string outputDirectory)
        {
            var receipt = new GoldenBuildReceipt { attemptId = Guid.NewGuid().ToString("N"), utc = DateTime.UtcNow.ToString("O"), unityVersion = Application.unityVersion, descriptor = descriptorPath, result = "Preparing" };
            NativeBuildProjectSettingsScope settings = null;
            NativeBuildDirtyAssetGuard dirtyAssets = null;
            NativeBuildFontPreservationScope fonts = null;
            ExceptionDispatchInfo failure = null;
            string output = null;
            WriteBuildReceipt(receipt); // An interrupted attempt cannot leave an older latest PASS.
            try
            {
                Require(!EditorApplication.isCompiling && !EditorApplication.isPlayingOrWillChangePlaymode && !BuildPipeline.isBuildingPlayer, "Editor must be idle for the golden review build.");
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64), "Windows64 module is missing.");
                string mono = Path.Combine(EditorApplication.applicationContentsPath, "PlaybackEngines/windowsstandalonesupport/Variations/win64_player_nondevelopment_mono");
                Require(Directory.Exists(mono), "Windows64 release Mono module is missing.");
                dirtyAssets = new NativeBuildDirtyAssetGuard(); receipt.preexistingDirtyAssets = dirtyAssets.Before;
                dirtyAssets.RejectUnsavedAuthoringAssets();
                Validate(descriptorPath);
                var descriptor = ReadDescriptor(descriptorPath);
                var sceneReceipt = JsonUtility.FromJson<SceneReceipt>(File.ReadAllText(ReceiptRoot + "/scene-latest.json"));
                string reviewScenePath = BoundReviewScenePath(sceneReceipt); receipt.scene = reviewScenePath;
                Require(sceneReceipt.passed && sceneReceipt.descriptorSha256 == Digest(descriptorPath) && sceneReceipt.sceneSha256 == Digest(reviewScenePath),
                    "The isolated review scene must be generated from the current descriptor.");
                foreach (var input in sceneReceipt.additionalInputs ?? Array.Empty<FileReceipt>()) VerifyInput(new InputFile { path = input.path, sha256 = input.sha256 });
                dirtyAssets.RejectDirtyDependencies(AssetDatabase.GetDependencies(reviewScenePath, true));
                string candidate = ProjectPath(outputDirectory, true);
                string expectedRoot = Path.GetFullPath("Build/Golden").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                Require(candidate.StartsWith(expectedRoot, StringComparison.OrdinalIgnoreCase) && !Directory.Exists(candidate) && !File.Exists(candidate), "Review output must be a new child folder of Build/Golden.");
                settings = new NativeBuildProjectSettingsScope();
                output = candidate; Directory.CreateDirectory(output); receipt.output = outputDirectory;
                settings.PersistOriginalSettings(Path.Combine(output, "BuildEvidence/original"));
                var sourcePipeline = ReviewScenePipeline(reviewScenePath);
                string owned = OutputRoot + "/Builds/" + receipt.attemptId;
                EnsureGoldenFolder(owned);
                var pipeline = UnityEngine.Object.Instantiate(sourcePipeline); pipeline.name = "GoldenBuildPipeline";
                receipt.ownedPipeline = owned + "/GoldenBuildPipeline.asset"; AssetDatabase.CreateAsset(pipeline, receipt.ownedPipeline);
                UrpProfileAuthoring.ConfigureDesktopRenderer(pipeline, owned + "/GoldenBuildRenderer.asset");
                GraphicsSettings.defaultRenderPipeline = pipeline; QualitySettings.renderPipeline = pipeline;
                settings.UsePipelineAtEveryQuality(pipeline);
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                Require(!PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64) &&
                    PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64).SequenceEqual(new[] { GraphicsDeviceType.Direct3D11 }),
                    "Golden review requires explicit Direct3D11-only graphics settings.");
                PlayerSettings.defaultScreenWidth = 1920; PlayerSettings.defaultScreenHeight = 1080;
                PlayerSettings.fullScreenMode = FullScreenMode.Windowed; PlayerSettings.resizableWindow = true;
                var preprocessor = AppDomain.CurrentDomain.GetAssemblies().Select(assembly => assembly.GetType("UnityEditor.Rendering.Universal.ShaderBuildPreprocessor")).FirstOrDefault(type => type != null);
                var gather = preprocessor?.GetMethod("GatherShaderFeatures", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic);
                Require(gather != null, "Installed URP prefilter contract is missing."); gather.Invoke(null, new object[] { false });
                AssetDatabase.SaveAssetIfDirty(pipeline);
                settings.PersistEffectiveSettings(Path.Combine(output, "BuildEvidence/effective"));
                var actualDependencies = AssetDatabase.GetDependencies(new[] { reviewScenePath, receipt.ownedPipeline }, true);
                dirtyAssets.RejectDirtyDependencies(actualDependencies);
                receipt.fontEvidenceDirectory = "_local/native-font-preservation/golden-" + receipt.attemptId;
                fonts = new NativeBuildFontPreservationScope(actualDependencies, receipt.fontEvidenceDirectory);
                Require(fonts.IsGlobalSelection, "A copied-font probe cannot protect a real build.");
                receipt.protectedFonts = fonts.Before;
                fonts.Apply(); fonts.VerifyProtected();
                receipt.inputs = BuildSnapshot(descriptorPath, descriptor, receipt.ownedPipeline); receipt.sourceFingerprint = Fingerprint(receipt.inputs);
                CaptureGoldenSettings(output, "before"); receipt.result = "Building"; WriteBuildReceipt(receipt);
                dirtyAssets.RejectUnsavedAuthoringAssets();
                fonts.VerifyProtected();
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { reviewScenePath }, locationPathName = Path.Combine(output, "RacingBoisGoldenReview.exe"), target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.DetailedBuildReport | BuildOptions.StrictMode | BuildOptions.CompressWithLz4HC
                });
                fonts.VerifyProtected();
                receipt.result = report.summary.result.ToString(); receipt.errors = report.summary.totalErrors; receipt.warnings = report.summary.totalWarnings;
                receipt.bytes = (long)report.summary.totalSize; receipt.seconds = report.summary.totalTime.TotalSeconds;
                receipt.inputsAfter = BuildSnapshot(descriptorPath, descriptor, receipt.ownedPipeline);
                receipt.changedDuringBuild = receipt.inputs.Select(row => row.path).Union(receipt.inputsAfter.Select(row => row.path))
                    .Where(path => receipt.inputs.FirstOrDefault(row => row.path == path)?.sha256 != receipt.inputsAfter.FirstOrDefault(row => row.path == path)?.sha256)
                    .Union(settings.ChangedDuringBuild()).OrderBy(path => path, StringComparer.Ordinal).ToArray();
                receipt.sourceBindingPassed = receipt.changedDuringBuild.Length == 0 && receipt.sourceFingerprint == Fingerprint(receipt.inputsAfter);
                CaptureGoldenSettings(output, "after");
                Require(report.summary.result == BuildResult.Succeeded && receipt.errors == 0, "Golden review build failed: " + receipt.result);
                Require(receipt.sourceBindingPassed, "Authoring/code/scene/effective settings changed during golden build.");
                Require(File.Exists(Path.Combine(output, "RacingBoisGoldenReview.exe")) && File.Exists(Path.Combine(output, "UnityPlayer.dll")), "Native player files are missing.");
                File.WriteAllText(Path.Combine(output, "ART_REVIEW.txt"),
                    "Racing Bois native art review\r\n\r\nTab changes subject; 1-6 changes camera; Space toggles turntable; L cycles LOD; H hides controls.\r\nThis is a quality review specimen, not a game release. No account/backend connection is made by the review scene.\r\n");
                receipt.passed = true;
            }
            catch (Exception error) { receipt.failure = error.GetType().Name + ": " + error.Message; failure = ExceptionDispatchInfo.Capture(error); }
            finally
            {
                var restoration = new List<string>();
                try { settings?.Restore(); receipt.editorStateRestored = true; if (output != null && settings != null) CaptureGoldenSettings(output, "restored"); }
                catch (Exception error) { restoration.Add("settings:" + error.GetType().Name + ":" + error.Message); }
                try
                {
                    if (fonts != null)
                    {
                        fonts.Restore(); receipt.fontPreservationPassed = true;
                        receipt.fontEvidence = Directory.GetFiles(receipt.fontEvidenceDirectory, "*.json", SearchOption.TopDirectoryOnly)
                            .OrderBy(path => path, StringComparer.Ordinal).Select(FileRow).ToArray();
                    }
                }
                catch (Exception error) { restoration.Add("fonts:" + error.GetType().Name + ":" + error.Message); }
                try { dirtyAssets?.VerifyUnchanged(); receipt.unrelatedDirtyAssetsPreserved = true; }
                catch (Exception error) { restoration.Add("unrelated-assets:" + error.GetType().Name + ":" + error.Message); }
                receipt.restorationErrors = restoration.ToArray();
                receipt.passed = receipt.passed && receipt.editorStateRestored && receipt.unrelatedDirtyAssetsPreserved && receipt.fontPreservationPassed && restoration.Count == 0 && failure == null;
                if (receipt.passed)
                    receipt.playerFiles = Directory.GetFiles(output, "*", SearchOption.AllDirectories).OrderBy(path => path, StringComparer.Ordinal)
                        .Select(path => new FileReceipt { path = Path.GetRelativePath(output, path).Replace('\\', '/'), sha256 = Digest(path), bytes = new FileInfo(path).Length }).ToArray();
                WriteBuildReceipt(receipt);
            }
            if (failure != null) failure.Throw();
            Require(receipt.passed, "Golden build could not verify settings and unrelated dirty-asset preservation.");
            return JsonUtility.ToJson(receipt, true);
        }

        private static RenderPipelineAsset ReviewScenePipeline(string scenePath)
        {
            var preview = EditorSceneManager.OpenPreviewScene(scenePath);
            try
            {
                var owners = preview.GetRootGameObjects().SelectMany(root => root.GetComponentsInChildren<GoldenReviewPipelineScope>(true)).ToArray();
                Require(owners.Length == 1 && owners[0].Pipeline != null, "Review scene must bind exactly one inspection pipeline.");
                return owners[0].Pipeline;
            }
            finally { EditorSceneManager.ClosePreviewScene(preview); }
        }
        private static void EnsureGoldenFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureGoldenFolder(parent); Require(!string.IsNullOrEmpty(AssetDatabase.CreateFolder(parent, Path.GetFileName(path))), "Could not create owned Golden build folder.");
        }
        private static void CaptureGoldenSettings(string output, string phase)
        {
            string directory = Path.Combine(output, "BuildEvidence", phase); Directory.CreateDirectory(directory);
            foreach (string name in new[] { "ProjectSettings", "GraphicsSettings", "QualitySettings" }) File.Copy("ProjectSettings/" + name + ".asset", Path.Combine(directory, name + ".asset"), false);
        }
        private static FileReceipt[] BuildSnapshot(string descriptorPath, Descriptor descriptor, string ownedPipeline)
        {
            var sceneReceipt = JsonUtility.FromJson<SceneReceipt>(File.ReadAllText(ReceiptRoot + "/scene-latest.json"));
            var paths = new HashSet<string>(InputSnapshot(descriptorPath, descriptor).Select(file => file.path), StringComparer.Ordinal);
            foreach (var input in sceneReceipt.additionalInputs ?? Array.Empty<FileReceipt>()) paths.Add(input.path);
            foreach (string logical in AssetDatabase.GetDependencies(new[] { BoundReviewScenePath(sceneReceipt), ownedPipeline }, true))
            {
                if (logical == "Resources/unity_builtin_extra" || logical == "Library/unity default resources") continue;
                string physical = logical;
                if (logical.StartsWith("Packages/", StringComparison.Ordinal))
                {
                    var package = UnityEditor.PackageManager.PackageInfo.FindForAssetPath(logical);
                    string name = logical.Split('/')[1]; Require(package != null && package.name == name, "Unresolved package dependency: " + logical);
                    string folder = Path.GetRelativePath(Path.GetFullPath("."), package.resolvedPath).Replace('\\', '/');
                    string prefix = "Library/PackageCache/" + name + "@";
                    Require(folder == "Packages/" + name || folder.StartsWith(prefix, StringComparison.Ordinal) && !folder.Substring(prefix.Length).Contains("/"), "Unbounded package dependency root.");
                    AddGoldenBuildPath(paths, Path.Combine(package.resolvedPath, "package.json"));
                    physical = Path.Combine(package.resolvedPath, logical.Substring(("Packages/" + name + "/").Length));
                }
                AddGoldenBuildPath(paths, physical);
            }
            foreach (string path in Directory.GetFiles("Assets/RacingBois/Golden/Runtime", "*", SearchOption.AllDirectories)) AddGoldenBuildPath(paths, path);
            foreach (string path in Directory.GetFiles("Assets/RacingBois/Editor", "GoldenSampleBuilder*", SearchOption.TopDirectoryOnly)) AddGoldenBuildPath(paths, path);
            foreach (string path in Directory.GetFiles("Assets/RacingBois/Editor", "NativeBuild*.cs", SearchOption.TopDirectoryOnly)) AddGoldenBuildPath(paths, path);
            foreach (string path in new[] { "Assets/RacingBois/Editor/RacingBois.Authoring.Editor.asmdef", "Packages/manifest.json", "Packages/packages-lock.json", "ProjectSettings/ProjectVersion.txt",
                "ProjectSettings/ProjectSettings.asset", "ProjectSettings/GraphicsSettings.asset", "ProjectSettings/QualitySettings.asset" }) AddGoldenBuildPath(paths, path);
            return paths.OrderBy(path => path, StringComparer.Ordinal).Select(FileRow).ToArray();
        }
        private static void AddGoldenBuildPath(HashSet<string> paths, string path)
        {
            string relative = Path.GetRelativePath(Path.GetFullPath("."), Path.GetFullPath(path)).Replace('\\', '/');
            ProjectPath(relative, false); paths.Add(relative);
            if (File.Exists(relative + ".meta")) { ProjectPath(relative + ".meta", false); paths.Add(relative + ".meta"); }
        }
        private static string BoundReviewScenePath(SceneReceipt receipt)
        {
            Require(receipt != null && !string.IsNullOrEmpty(receipt.scene) && receipt.scene.StartsWith(OutputRoot + "/", StringComparison.Ordinal) && receipt.scene.EndsWith(".unity", StringComparison.Ordinal), "Review scene must be a saved owned asset.");
            string full = ProjectPath(receipt.scene, false);
            string root = Path.GetFullPath(OutputRoot).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            Require(full.StartsWith(root, StringComparison.OrdinalIgnoreCase) && File.Exists(full), "Review scene escaped its generated root or is missing.");
            return receipt.scene;
        }
        private static void WriteBuildReceipt(GoldenBuildReceipt receipt)
        {
            Directory.CreateDirectory(ReceiptRoot); receipt.utc = DateTime.UtcNow.ToString("O"); string json = JsonUtility.ToJson(receipt, true);
            File.WriteAllText(ReceiptRoot + "/build-" + receipt.attemptId + ".json", json); File.WriteAllText(ReceiptRoot + "/build-latest.json", json);
        }
    }
}
