using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Composes a relocatable Windows player with only the audited immutable P08 distribution.</summary>
    public static class P08DesktopBuilder
    {
        public const string PackRoot = "Build/Content-desktop";
        public const string PlayerRoot = "Build/Desktop-P08";
        public const string ContentRoot = "Assets/StreamingAssets/Content";
        private const string ConfigName = "RacingBois.runtime.json";
        private const string ReceiptRoot = "docs/p08/desktop/";

        [Serializable] private sealed class FileReceipt
        { public string path, sha256; public long bytes; }
        [Serializable] private sealed class PreparationReceipt
        {
            public int schema = 1; public bool passed; public string utc, unityVersion, target, scriptingBackend, contentHash, sourceManifestSha256;
            public string contentDestination, configSha256; public FileReceipt[] contentFiles;
        }
        [Serializable] private sealed class BuildReceipt
        {
            public int schema = 1; public bool passed; public string utc, unityVersion, target, scriptingBackend, result, output, contentHash;
            public string attemptId, startedUtc, failureCode;
            public string sourceFingerprint, manifestSha256; public long bytes; public int errors, warnings; public double seconds; public bool sourceBindingPassed;
            public FileReceipt[] installedContent, playerFiles, sourceFiles; public string validationScope;
            public int unityDependencySchema = 2; public string[] unityDependencyRoots;
            public DependencyFileReceipt[] unityDependencies; public PackageReceipt[] unityPackages; public string[] unityBuiltInDependencies; public string unityDependencyFingerprint;
        }
        [Serializable] private sealed class Description
        {
            public string unityVersion, target, plannedBackend, graphicsApi, packRoot, playerRoot, installedContentRoot;
            public bool targetSupported, monoPlayerPresent, windowsIl2CppPlayerPresent, contentReady;
            public string acceptanceScope;
        }

        public static string Describe()
        {
            string modules = Path.Combine(EditorApplication.applicationContentsPath, "PlaybackEngines", "windowsstandalonesupport", "Variations");
            var description = new Description
            {
                unityVersion = UnityEngine.Application.unityVersion, target = BuildTarget.StandaloneWindows64.ToString(),
                plannedBackend = "Mono2x", graphicsApi = "Direct3D11", packRoot = PackRoot, playerRoot = PlayerRoot,
                installedContentRoot = "RacingBois_Data/StreamingAssets/Content",
                targetSupported = BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64),
                monoPlayerPresent = Directory.Exists(Path.Combine(modules, "win64_player_nondevelopment_mono")),
                windowsIl2CppPlayerPresent = Directory.Exists(Path.Combine(modules, "win64_player_nondevelopment_il2cpp")),
                contentReady = File.Exists(Path.Combine(PackRoot, "manifest.json")),
                acceptanceScope = "Module and output-path description only. Build, launch, graphics, audio and performance require actual receipts."
            };
            string json = JsonUtility.ToJson(description, true);
            Directory.CreateDirectory(ReceiptRoot); File.WriteAllText(ReceiptRoot + "description.json", json);
            return json;
        }

        public static void Prepare()
        {
            if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64))
                throw new InvalidOperationException("Windows64 player support is not installed.");
            string mono = Path.Combine(EditorApplication.applicationContentsPath, "PlaybackEngines", "windowsstandalonesupport", "Variations", "win64_player_nondevelopment_mono");
            if (!Directory.Exists(mono)) throw new InvalidOperationException("The selected Windows64 release Mono player is not installed.");
            P08ContentPackBuilder.Validate();
            var manifest = ReadPack(PackRoot);
            RejectUnexpectedStreamingFiles(manifest);
            var copied = CopyPack(PackRoot, ContentRoot, manifest);
            string configPath = "Assets/StreamingAssets/" + ConfigName;
            if (!File.Exists(configPath))
            {
                const string template = "tools/p08/desktop/RacingBois.runtime.json";
                ValidateConfig(template); File.Copy(template, configPath);
            }
            ValidateConfig(configPath);
            var desktopPipeline = UrpProfileAuthoring.PrepareDesktop();
            GraphicsSettings.defaultRenderPipeline = desktopPipeline;
            QualitySettings.renderPipeline = desktopPipeline;
            PlayerSettings.productName = "Racing Bois"; PlayerSettings.bundleVersion = "0.8.0";
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
            if (PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64) ||
                !PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64).SequenceEqual(new[] { GraphicsDeviceType.Direct3D11 }))
                throw new InvalidOperationException("Desktop build requires explicit Direct3D11-only graphics settings.");
            PlayerSettings.defaultScreenWidth = 1920; PlayerSettings.defaultScreenHeight = 1080;
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow; PlayerSettings.resizableWindow = true;
            PlayerSettings.runInBackground = true; PlayerSettings.enableFrameTimingStats = true;
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport); AssetDatabase.SaveAssets();
            Directory.CreateDirectory(ReceiptRoot);
            File.WriteAllText(ReceiptRoot + "preparation.json", JsonUtility.ToJson(new PreparationReceipt
            {
                passed = true, utc = DateTime.UtcNow.ToString("O"), unityVersion = UnityEngine.Application.unityVersion,
                target = BuildTarget.StandaloneWindows64.ToString(), scriptingBackend = "Mono2x", contentHash = GameplayRules.ContentHash,
                sourceManifestSha256 = Digest(Path.Combine(PackRoot, "manifest.json")), contentDestination = ContentRoot,
                configSha256 = Digest(configPath), contentFiles = copied
            }, true));
            Debug.Log("RB_P08_DESKTOP_PREPARED");
        }

        public static string Build() => BuildTo(PlayerRoot);

        public static string BuildTo(string outputRoot)
        {
            var receipt = new BuildReceipt
            {
                attemptId = Guid.NewGuid().ToString("N"), startedUtc = DateTime.UtcNow.ToString("O"),
                unityVersion = UnityEngine.Application.unityVersion, target = BuildTarget.StandaloneWindows64.ToString(),
                scriptingBackend = "Mono2x", output = outputRoot, contentHash = GameplayRules.ContentHash, result = "Preparing",
                validationScope = "Unity release build and installed distribution hashes/Unity CRC only. Native launch, audio, quality and sustained performance are separate gates."
            };
            ArchivePreviousBuildReceipt(); WriteBuildReceipt(receipt);
            try
            {
                string playerRoot = Inside(outputRoot, "Build");
                if (Directory.Exists(playerRoot))
                {
                    RejectReparsePoints(playerRoot);
                    if (Directory.EnumerateFileSystemEntries(playerRoot).Any())
                        throw new InvalidOperationException("The output folder is not empty. Use BuildTo with a fresh folder under Build; existing releases are preserved.");
                }
                Directory.CreateDirectory(playerRoot); receipt.output = Path.GetRelativePath(Path.GetFullPath("."), playerRoot).Replace('\\', '/');
                Prepare();
                if (!File.Exists(RaceBuilder.ScenePath)) throw new InvalidOperationException("The reviewed Race scene is missing.");
                var sourceFiles = SourceSnapshot(out var dependencies); string fingerprint = SourceFingerprint(sourceFiles);
                receipt.unityDependencyRoots = new[] { RaceBuilder.ScenePath, UrpProfileAuthoring.DesktopPipelinePath };
                receipt.unityDependencies = dependencies.files; receipt.unityPackages = dependencies.packages; receipt.unityBuiltInDependencies = dependencies.builtIns; receipt.unityDependencyFingerprint = DependencyFingerprint(dependencies);
                receipt.sourceFiles = sourceFiles; receipt.sourceFingerprint = fingerprint; receipt.result = "Building";
                WriteBuildReceipt(receipt);
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { RaceBuilder.ScenePath }, locationPathName = Path.Combine(playerRoot, "RacingBois.exe"),
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.DetailedBuildReport | BuildOptions.StrictMode | BuildOptions.CompressWithLz4HC
                });
                var summary = report.summary;
                receipt.result = summary.result.ToString(); receipt.bytes = (long)summary.totalSize;
                receipt.errors = summary.totalErrors; receipt.warnings = summary.totalWarnings; receipt.seconds = summary.totalTime.TotalSeconds;
                receipt.scriptingBackend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone).ToString();
                var after = SourceSnapshot(out var dependenciesAfter);
                receipt.sourceBindingPassed = fingerprint == SourceFingerprint(after) &&
                    receipt.unityDependencyFingerprint == DependencyFingerprint(dependenciesAfter);
                if (summary.result != BuildResult.Succeeded) throw new InvalidOperationException("P08 Windows player build failed: " + receipt.result);
                if (!receipt.sourceBindingPassed) throw new InvalidOperationException("Authoring inputs changed during the player build; its source binding needs review.");
                WritePlayerInstructions(playerRoot);
                string installed = Path.Combine(playerRoot, "RacingBois_Data", "StreamingAssets", "Content");
                var manifest = ReadPack(installed); receipt.manifestSha256 = Digest(Path.Combine(installed, "manifest.json"));
                receipt.installedContent = AuditPack(installed, manifest);
                ValidateConfig(Path.Combine(playerRoot, "RacingBois_Data", "StreamingAssets", ConfigName));
                receipt.playerFiles = Directory.GetFiles(playerRoot, "*", SearchOption.AllDirectories)
                    .OrderBy(x => x, StringComparer.Ordinal).Select(path => FileRow(playerRoot, path)).ToArray();
                receipt.passed = true; receipt.utc = DateTime.UtcNow.ToString("O");
                string json = WriteBuildReceipt(receipt); Debug.Log("RB_P08_DESKTOP_BUILT"); return json;
            }
            catch (Exception error)
            {
                receipt.passed = false; receipt.failureCode = error.GetType().Name; receipt.utc = DateTime.UtcNow.ToString("O");
                WriteBuildReceipt(receipt); throw;
            }
        }

        public static string Validate() => ValidateAt(PlayerRoot);

        public static string ValidateAt(string outputRoot)
        {
            string playerRoot = Inside(outputRoot, "Build");
            RejectReparsePoints(playerRoot);
            if (!File.Exists(Path.Combine(playerRoot, "RacingBois.exe")) || !File.Exists(Path.Combine(playerRoot, "UnityPlayer.dll")))
                throw new InvalidOperationException("The actual Windows player output is missing.");
            string installed = Path.Combine(playerRoot, "RacingBois_Data", "StreamingAssets", "Content");
            var manifest = ReadPack(installed); var files = AuditPack(installed, manifest);
            ValidateConfig(Path.Combine(playerRoot, "RacingBois_Data", "StreamingAssets", ConfigName));
            var receipt = new PreparationReceipt
            {
                passed = true, utc = DateTime.UtcNow.ToString("O"), unityVersion = UnityEngine.Application.unityVersion,
                target = "StandaloneWindows64", scriptingBackend = "Mono2x", contentHash = GameplayRules.ContentHash,
                sourceManifestSha256 = Digest(Path.Combine(installed, "manifest.json")), contentDestination = Path.GetRelativePath(Path.GetFullPath("."), installed).Replace('\\', '/'),
                configSha256 = Digest(Path.Combine(playerRoot, "RacingBois_Data", "StreamingAssets", ConfigName)), contentFiles = files
            };
            string json = JsonUtility.ToJson(receipt, true); Directory.CreateDirectory(ReceiptRoot);
            File.WriteAllText(ReceiptRoot + "installed-validation.json", json); return json;
        }

        private static P08ContentManifest ReadPack(string root)
        {
            if (!Directory.Exists(root)) throw new InvalidDataException("Desktop content folder is missing.");
            RejectReparsePoints(root);
            string path = Path.Combine(root, "manifest.json");
            if (!File.Exists(path) || new FileInfo(path).Length > 131072) throw new InvalidDataException("Desktop content manifest missing or oversized.");
            var manifest = JsonUtility.FromJson<P08ContentManifest>(File.ReadAllText(path));
            ContentManifestRules.Validate(manifest, GameplayRules.ContentHash, new Uri(Path.GetFullPath(root) + Path.DirectorySeparatorChar), "StandaloneWindows64");
            if (manifest.bundles.Length != 31 || manifest.bundles.Count(x => x.kind == "music") != 25)
                throw new InvalidDataException("Desktop requires six Unity bundles and all 25 authored Ogg resources.");
            AuditPack(root, manifest); return manifest;
        }

        private static FileReceipt[] AuditPack(string root, P08ContentManifest manifest)
        {
            var receipts = new List<FileReceipt>();
            foreach (var entry in manifest.bundles)
            {
                string path = Inside(Path.Combine(root, entry.url), root);
                string suffix = entry.kind == "music" ? ".ogg" : ".bundle";
                if (!entry.url.EndsWith(entry.sha256 + suffix, StringComparison.Ordinal) || !File.Exists(path) || new FileInfo(path).Length != entry.bytes || Digest(path) != entry.sha256)
                    throw new InvalidDataException("Desktop distribution fingerprint differs: " + entry.id);
                if (entry.kind != "music" && (!BuildPipeline.GetCRCForAssetBundle(path, out uint crc) || crc != entry.crc))
                    throw new InvalidDataException("Desktop Unity CRC differs: " + entry.id);
                if (entry.kind == "music")
                    using (var stream = File.OpenRead(path))
                        if (stream.ReadByte() != 'O' || stream.ReadByte() != 'g' || stream.ReadByte() != 'g' || stream.ReadByte() != 'S')
                            throw new InvalidDataException("Desktop music container is invalid: " + entry.id);
                receipts.Add(FileRow(root, path));
            }
            receipts.Add(FileRow(root, Path.Combine(root, "manifest.json"))); return receipts.ToArray();
        }

        private static void RejectUnexpectedStreamingFiles(P08ContentManifest next)
        {
            const string streamingRoot = "Assets/StreamingAssets";
            if (!Directory.Exists(streamingRoot)) return;
            RejectReparsePoints(streamingRoot);
            var allowed = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { Path.GetFullPath(streamingRoot + "/" + ConfigName) };
            foreach (var entry in next.bundles) allowed.Add(Inside(Path.Combine(ContentRoot, entry.url), ContentRoot));
            allowed.Add(Path.GetFullPath(ContentRoot + "/manifest.json"));
            if (File.Exists(ContentRoot + "/manifest.json"))
            {
                var previous = JsonUtility.FromJson<P08ContentManifest>(File.ReadAllText(ContentRoot + "/manifest.json"));
                ContentManifestRules.Validate(previous, previous.contentHash, new Uri(Path.GetFullPath(ContentRoot) + Path.DirectorySeparatorChar), "StandaloneWindows64");
                foreach (var entry in previous.bundles) allowed.Add(Inside(Path.Combine(ContentRoot, entry.url), ContentRoot));
            }
            foreach (string file in Directory.GetFiles(streamingRoot, "*", SearchOption.AllDirectories))
                if (!file.EndsWith(".meta", StringComparison.OrdinalIgnoreCase) && !allowed.Contains(Path.GetFullPath(file)))
                    throw new InvalidDataException("Unregistered StreamingAssets file would ship: " + file);
        }

        private static FileReceipt[] CopyPack(string source, string destination, P08ContentManifest manifest)
        {
            Directory.CreateDirectory(destination); RejectReparsePoints(destination);
            var wanted = new HashSet<string>(manifest.bundles.Select(x => Inside(Path.Combine(destination, x.url), destination)), StringComparer.OrdinalIgnoreCase);
            wanted.Add(Path.GetFullPath(Path.Combine(destination, "manifest.json")));
            foreach (string relative in manifest.bundles.Select(x => x.url).Concat(new[] { "manifest.json" }))
            {
                string target = Inside(Path.Combine(destination, relative), destination); Directory.CreateDirectory(Path.GetDirectoryName(target));
                File.Copy(Inside(Path.Combine(source, relative), source), target, true);
            }
            // RejectUnexpectedStreamingFiles established that every non-metadata file belongs to the current or prior manifest.
            foreach (string old in Directory.GetFiles(destination, "*", SearchOption.AllDirectories))
                if (!old.EndsWith(".meta", StringComparison.OrdinalIgnoreCase) && !wanted.Contains(Path.GetFullPath(old)))
                {
                    File.Delete(Inside(old, destination)); if (File.Exists(old + ".meta")) File.Delete(Inside(old + ".meta", destination));
                }
            return AuditPack(destination, manifest);
        }

        private static void ValidateConfig(string path)
        {
            if (!File.Exists(path) || new FileInfo(path).Length > DesktopRuntimeConfigRules.MaximumConfigBytes)
                throw new InvalidDataException("Public desktop configuration is missing or oversized.");
            var config = JsonUtility.FromJson<DesktopRuntimeConfig>(File.ReadAllText(path));
            DesktopRuntimeConfigRules.BackendEndpoint(config);
            DesktopRuntimeConfigRules.ContentBase(config, Path.GetDirectoryName(Path.GetFullPath(path)), false);
            if (!string.IsNullOrEmpty(config.contentBaseUrl))
                throw new InvalidDataException("This offline-ready desktop release requires installed content. Set contentBaseUrl to empty; online backend WSS remains configurable.");
        }
        private static string Inside(string path, string root)
        {
            string boundary = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string resolved = Path.GetFullPath(path);
            if (!resolved.StartsWith(boundary, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Path escapes the owned distribution root.");
            return resolved;
        }
        private static void RejectReparsePoints(string root)
        {
            if ((File.GetAttributes(root) & FileAttributes.ReparsePoint) != 0 || Directory.GetFileSystemEntries(root, "*", SearchOption.AllDirectories).Any(x => (File.GetAttributes(x) & FileAttributes.ReparsePoint) != 0))
                throw new InvalidDataException("Distribution roots must not contain junctions or symlinks.");
        }
        private static FileReceipt FileRow(string root, string path) => new FileReceipt
        { path = Path.GetRelativePath(Path.GetFullPath(root), Path.GetFullPath(path)).Replace('\\', '/'), bytes = new FileInfo(path).Length, sha256 = Digest(path) };
        private sealed class DependencyCapture
        {
            public DependencyFileReceipt[] files;
            public PackageReceipt[] packages;
            public string[] builtIns;
        }
        [Serializable] private sealed class DependencyFileReceipt
        { public string assetPath, path, sha256; public long bytes; }
        [Serializable] private sealed class PackageReceipt
        { public string name, version, resolvedPath; public FileReceipt manifest; }

        private static FileReceipt CheckedSourceRow(string path)
        {
            string full = Inside(path, "."), project = Path.GetFullPath(".");
            for (string current = full; current != null && !string.Equals(current, project, StringComparison.OrdinalIgnoreCase); current = Path.GetDirectoryName(current))
                if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("Source dependencies must not traverse symlinks or junctions.");
            return FileRow(".", full);
        }
        private static FileReceipt[] SourceSnapshot(out DependencyCapture capture)
        {
            var roots = new[] { RaceBuilder.ScenePath, UrpProfileAuthoring.DesktopPipelinePath };
            if (roots.Any(path => !File.Exists(path))) throw new InvalidDataException("A desktop dependency root is missing.");
            var logicalPaths = AssetDatabase.GetDependencies(roots, true).Select(path => path.Replace('\\', '/'))
                .Distinct().OrderBy(path => path, StringComparer.Ordinal).ToArray();
            if (roots.Any(root => !logicalPaths.Contains(root))) throw new InvalidDataException("Engine dependency roots are incomplete.");
            var records = new List<DependencyFileReceipt>();
            var packages = new Dictionary<string, PackageReceipt>(StringComparer.Ordinal);
            var builtIns = new List<string>();
            foreach (string logical in logicalPaths)
            {
                if (logical == "Resources/unity_builtin_extra" || logical == "Library/unity default resources")
                { builtIns.Add(logical); continue; }
                string physical;
                if (logical.StartsWith("Assets/", StringComparison.Ordinal)) physical = logical;
                else if (logical.StartsWith("Packages/", StringComparison.Ordinal))
                {
                    var info = UnityEditor.PackageManager.PackageInfo.FindForAssetPath(logical);
                    string name = logical.Split('/')[1];
                    if (info == null || info.name != name || string.IsNullOrEmpty(info.version) || string.IsNullOrEmpty(info.resolvedPath))
                        throw new InvalidDataException("A virtual package dependency could not be resolved.");
                    string resolved = Path.GetRelativePath(Path.GetFullPath("."), Inside(info.resolvedPath, ".")).Replace('\\', '/');
                    string cachePrefix = "Library/PackageCache/" + name + "@";
                    if (resolved != "Packages/" + name && !(resolved.StartsWith(cachePrefix, StringComparison.Ordinal) && resolved.Length > cachePrefix.Length && !resolved.Substring(cachePrefix.Length).Contains("/")))
                        throw new InvalidDataException("Package resolution is outside its exact embedded/cache directory.");
                    var package = new PackageReceipt { name = name, version = info.version, resolvedPath = resolved,
                        manifest = CheckedSourceRow(Path.Combine(info.resolvedPath, "package.json")) };
                    if (packages.TryGetValue(name, out var previous) && (previous.resolvedPath != resolved || previous.version != info.version || previous.manifest.sha256 != package.manifest.sha256))
                        throw new InvalidDataException("Package identity changed during dependency capture.");
                    packages[name] = package;
                    physical = Path.Combine(info.resolvedPath, logical.Substring(("Packages/" + name + "/").Length));
                    Inside(physical, info.resolvedPath);
                }
                else throw new InvalidDataException("Unresolved engine dependency: " + logical);
                if (!File.Exists(physical)) throw new InvalidDataException("Engine dependency has no physical file: " + logical);
                var file = CheckedSourceRow(physical);
                records.Add(new DependencyFileReceipt { assetPath = logical, path = file.path, bytes = file.bytes, sha256 = file.sha256 });
            }
            capture = new DependencyCapture { files = records.ToArray(), packages = packages.Values.OrderBy(p => p.name, StringComparer.Ordinal).ToArray(),
                builtIns = builtIns.OrderBy(path => path, StringComparer.Ordinal).ToArray() };
            var files = Directory.GetFiles("Assets/RacingBois", "*", SearchOption.AllDirectories).Where(x => x.EndsWith(".cs") || x.EndsWith(".uxml") || x.EndsWith(".uss"))
                .Concat(Directory.GetFiles("Packages/com.racingbois.foundation", "*.cs", SearchOption.AllDirectories))
                .Concat(capture.files.Select(file => file.path)).Concat(capture.packages.Select(package => package.manifest.path))
                .Concat(new[] { RaceBuilder.ScenePath, "ProjectSettings/ProjectSettings.asset", "ProjectSettings/GraphicsSettings.asset", "ProjectSettings/QualitySettings.asset", "ProjectSettings/EditorBuildSettings.asset", "Packages/manifest.json", "Packages/packages-lock.json" })
                .Select(path => path.Replace('\\', '/')).Distinct().OrderBy(path => path, StringComparer.Ordinal);
            return files.Select(CheckedSourceRow).ToArray();
        }
        private static string DependencyFingerprint(DependencyCapture capture)
        {
            var lines = new List<string> { "unity " + UnityEngine.Application.unityVersion,
                "root " + RaceBuilder.ScenePath, "root " + UrpProfileAuthoring.DesktopPipelinePath };
            lines.AddRange(capture.files.Select(row => "asset " + row.assetPath + " " + row.path + " " + row.sha256));
            lines.AddRange(capture.packages.Select(row => "package " + row.name + " " + row.version + " " + row.resolvedPath + " " + row.manifest.sha256));
            lines.AddRange(capture.builtIns.Select(path => "builtin " + path));
            using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", lines))));
        }

        private static string SourceFingerprint(FileReceipt[] files)
        {
            string canonical = string.Join("\n", files.Select(x => x.path + " " + x.sha256));
            using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(canonical)));
        }
        private static string Digest(string path) { using (var sha = SHA256.Create()) using (var stream = File.OpenRead(path)) return Hex(sha.ComputeHash(stream)); }
        private static string Hex(byte[] value) => BitConverter.ToString(value).Replace("-", "").ToLowerInvariant();
        private static void ArchivePreviousBuildReceipt()
        {
            string path = ReceiptRoot + "build.json";
            if (!File.Exists(path)) return;
            string archive = ReceiptRoot + "history/build-" + Digest(path) + ".json";
            Directory.CreateDirectory(ReceiptRoot + "history");
            if (!File.Exists(archive)) File.Copy(path, archive);
        }
        private static string WriteBuildReceipt(BuildReceipt receipt)
        {
            Directory.CreateDirectory(ReceiptRoot); string json = JsonUtility.ToJson(receipt, true);
            File.WriteAllText(ReceiptRoot + "build.json", json); return json;
        }
        private static void WritePlayerInstructions(string root)
        {
            File.WriteAllText(Path.Combine(root, "README.txt"),
                "Racing Bois P08 - Windows 10/11 x64\r\n\r\n" +
                "Keep the entire folder together. Start RacingBois.exe. Local racing and all installed content/music work without Internet.\r\n" +
                "Player preferences and credentials are stored in Unity's per-user persistent data directory, never in this installation.\r\n\r\n" +
                "LAN: start the separately distributed LAN host on the host PC. Set the endpoint in the multiplayer menu to\r\n" +
                "ws://HOST-LAN-IP:7777/multiplayer and enter the room code. The default endpoint uses this PC.\r\n" +
                "A Windows Firewall permission may be needed on the LAN host only. No browser or QR scan is required.\r\n\r\n" +
                "Online: the public configuration is RacingBois_Data/StreamingAssets/RacingBois.runtime.json.\r\n" +
                "Use connectionMode online and the deployed OCI WSS endpoint with a trusted certificate.\r\n" +
                "No public OCI endpoint is claimed by this local build. Do not put passwords or tokens in the config.\r\n\r\n" +
                "Build backend: release Mono, Direct3D 11. Unity build success is separate from hardware/performance acceptance.\r\n");
        }
    }
}
