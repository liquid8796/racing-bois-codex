using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
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
            public string descriptor, output, sourceFingerprint, result, failure;
            public bool passed, sourceBindingPassed;
            public int errors, warnings;
            public long bytes;
            public double seconds;
            public FileReceipt[] inputs, playerFiles;
            public string scope = "Isolated native art-review player build. Not a Racing Bois release, gameplay acceptance, visual approval or performance certification.";
        }

        /// <summary>Builds into a new explicit folder under Build/Golden. Existing builds are never overwritten.</summary>
        public static string BuildReviewPlayer(string descriptorPath, string outputDirectory)
        {
            var receipt = new GoldenBuildReceipt { attemptId = Guid.NewGuid().ToString("N"), utc = DateTime.UtcNow.ToString("O"), unityVersion = Application.unityVersion, descriptor = descriptorPath };
            var oldBackend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone);
            bool oldDefaultApis = PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64);
            var oldApis = PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
            int oldWidth = PlayerSettings.defaultScreenWidth, oldHeight = PlayerSettings.defaultScreenHeight;
            var oldFullscreen = PlayerSettings.fullScreenMode; bool oldResizable = PlayerSettings.resizableWindow;
            try
            {
                Require(!EditorApplication.isCompiling && !EditorApplication.isPlayingOrWillChangePlaymode, "Editor must be idle for the golden review build.");
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64), "Windows64 module is missing.");
                string mono = Path.Combine(EditorApplication.applicationContentsPath, "PlaybackEngines/windowsstandalonesupport/Variations/win64_player_nondevelopment_mono");
                Require(Directory.Exists(mono), "Windows64 release Mono module is missing.");
                Validate(descriptorPath);
                var descriptor = ReadDescriptor(descriptorPath);
                var sceneReceipt = JsonUtility.FromJson<SceneReceipt>(File.ReadAllText(ReceiptRoot + "/scene-latest.json"));
                string reviewScenePath = BoundReviewScenePath(sceneReceipt);
                Require(sceneReceipt.passed && sceneReceipt.descriptorSha256 == Digest(descriptorPath) && sceneReceipt.sceneSha256 == Digest(reviewScenePath),
                    "The isolated review scene must be generated from the current descriptor.");
                foreach (var input in sceneReceipt.additionalInputs ?? Array.Empty<FileReceipt>())
                    VerifyInput(new InputFile { path = input.path, sha256 = input.sha256 });
                string output = ProjectPath(outputDirectory, true);
                string expectedRoot = Path.GetFullPath("Build/Golden").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                Require(output.StartsWith(expectedRoot, StringComparison.OrdinalIgnoreCase), "Review builds must use a new child folder of Build/Golden.");
                Require(!Directory.Exists(output) || !Directory.EnumerateFileSystemEntries(output).Any(), "Review output folder must be empty; previous builds are preserved.");
                Directory.CreateDirectory(output); receipt.output = outputDirectory;
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
                PlayerSettings.defaultScreenWidth = 1920; PlayerSettings.defaultScreenHeight = 1080;
                PlayerSettings.fullScreenMode = FullScreenMode.Windowed; PlayerSettings.resizableWindow = true;
                AssetDatabase.SaveAssets();
                receipt.inputs = BuildSnapshot(descriptorPath, descriptor); receipt.sourceFingerprint = Fingerprint(receipt.inputs);
                receipt.result = "Building"; WriteBuildReceipt(receipt);
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { reviewScenePath }, locationPathName = Path.Combine(output, "RacingBoisGoldenReview.exe"),
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.DetailedBuildReport | BuildOptions.StrictMode | BuildOptions.CompressWithLz4HC
                });
                receipt.result = report.summary.result.ToString(); receipt.errors = report.summary.totalErrors; receipt.warnings = report.summary.totalWarnings;
                receipt.bytes = (long)report.summary.totalSize; receipt.seconds = report.summary.totalTime.TotalSeconds;
                receipt.sourceBindingPassed = receipt.sourceFingerprint == Fingerprint(BuildSnapshot(descriptorPath, descriptor));
                Require(report.summary.result == BuildResult.Succeeded, "Golden review build failed: " + receipt.result);
                Require(receipt.sourceBindingPassed, "Authoring/code/scene inputs changed during golden build.");
                Require(File.Exists(Path.Combine(output, "RacingBoisGoldenReview.exe")) && File.Exists(Path.Combine(output, "UnityPlayer.dll")), "Native player files are missing.");
                File.WriteAllText(Path.Combine(output, "ART_REVIEW.txt"),
                    "Racing Bois native art review\r\n\r\nTab changes subject; 1-6 changes camera; Space toggles turntable; L cycles LOD; H hides controls.\r\nThis is a quality review specimen, not a game release. No account/backend connection is made by the review scene.\r\n");
                receipt.playerFiles = Directory.GetFiles(output, "*", SearchOption.AllDirectories).OrderBy(path => path, StringComparer.Ordinal)
                    .Select(path => new FileReceipt { path = Path.GetRelativePath(output, path).Replace('\\', '/'), sha256 = Digest(path), bytes = new FileInfo(path).Length }).ToArray();
                receipt.passed = true; WriteBuildReceipt(receipt); return JsonUtility.ToJson(receipt, true);
            }
            catch (Exception error)
            { receipt.failure = error.GetType().Name + ": " + error.Message; WriteBuildReceipt(receipt); throw; }
            finally
            {
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, oldBackend);
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, oldDefaultApis);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, oldApis);
                PlayerSettings.defaultScreenWidth = oldWidth; PlayerSettings.defaultScreenHeight = oldHeight;
                PlayerSettings.fullScreenMode = oldFullscreen; PlayerSettings.resizableWindow = oldResizable;
                AssetDatabase.SaveAssets();
            }
        }

        private static FileReceipt[] BuildSnapshot(string descriptorPath, Descriptor descriptor)
        {
            var sceneReceipt = JsonUtility.FromJson<SceneReceipt>(File.ReadAllText(ReceiptRoot + "/scene-latest.json"));
            var paths = InputSnapshot(descriptorPath, descriptor).Select(file => file.path)
                .Concat((sceneReceipt.additionalInputs ?? Array.Empty<FileReceipt>()).Select(file => file.path))
                .Concat(AssetDatabase.GetDependencies(BoundReviewScenePath(sceneReceipt), true).Where(File.Exists))
                .Concat(Directory.GetFiles("Assets/RacingBois/Golden/Runtime", "*", SearchOption.AllDirectories))
                .Concat(Directory.GetFiles("Assets/RacingBois/Editor", "GoldenSampleBuilder*", SearchOption.TopDirectoryOnly))
                .Concat(new[] { "Assets/RacingBois/Editor/RacingBois.Authoring.Editor.asmdef", "Packages/manifest.json", "Packages/packages-lock.json", "ProjectSettings/ProjectVersion.txt", "ProjectSettings/ProjectSettings.asset", "ProjectSettings/GraphicsSettings.asset", "ProjectSettings/QualitySettings.asset" });
            return paths.Select(path => path.Replace('\\', '/')).Distinct(StringComparer.Ordinal).OrderBy(path => path, StringComparer.Ordinal).Select(FileRow).ToArray();
        }

        private static string BoundReviewScenePath(SceneReceipt receipt)
        {
            Require(receipt != null && !string.IsNullOrEmpty(receipt.scene) &&
                receipt.scene.StartsWith(OutputRoot + "/", StringComparison.Ordinal) &&
                receipt.scene.EndsWith(".unity", StringComparison.Ordinal), "Review scene must be a saved owned asset.");
            string full = ProjectPath(receipt.scene, false);
            string root = Path.GetFullPath(OutputRoot).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            Require(full.StartsWith(root, StringComparison.OrdinalIgnoreCase) && File.Exists(full), "Review scene escaped its generated root or is missing.");
            return receipt.scene;
        }

        private static void WriteBuildReceipt(GoldenBuildReceipt receipt)
        {
            Directory.CreateDirectory(ReceiptRoot); receipt.utc = DateTime.UtcNow.ToString("O");
            string json = JsonUtility.ToJson(receipt, true);
            File.WriteAllText(ReceiptRoot + "/build-" + receipt.attemptId + ".json", json);
            File.WriteAllText(ReceiptRoot + "/build-latest.json", json);
        }
    }
}
