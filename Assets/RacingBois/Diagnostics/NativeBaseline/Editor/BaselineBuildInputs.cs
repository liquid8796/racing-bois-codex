using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Diagnostics.NativeBaseline.Editor
{
    [Serializable] public sealed class BaselineFile { public string path, sha256; public long bytes; }
    internal static class BaselineBuildInputs
    {
        internal static readonly string[] Assemblies = { "RacingBois.Diagnostics.NativeBaseline", "RacingBois.Diagnostics.NativeBaseline.Editor", "RacingBois.Client.Bootstrap", "RacingBois.Client.Presentation", "RacingBois.Client.Application", "RacingBois.Client.Adapters", "RacingBois.Simulation", "RacingBois.Gameplay.Definitions", "RacingBois.Authoring.Editor" };
        [Serializable] private sealed class Proof { public int schema; public bool passed; public AssemblyProof[] assemblies; }
        [Serializable] private sealed class AssemblyProof { public string name, path, sha256, pdbSha256, mvid; public bool passed, pdbMatchesAssembly; public Document[] documents; }
        [Serializable] private sealed class Document { public string path, sha256; public bool matches; }
        internal static void VerifyAssemblies(string path)
        {
            var proof = JsonUtility.FromJson<Proof>(File.ReadAllText(Inside(path)));
            Need(proof != null && proof.schema == 1 && proof.passed && proof.assemblies != null, "compiled_source_proof_required");
            foreach (string name in Assemblies)
            {
                var row = proof.assemblies.SingleOrDefault(x => x.name == name);
                var loaded = AppDomain.CurrentDomain.GetAssemblies().SingleOrDefault(x => x.GetName().Name == name);
                Need(row != null && loaded != null && row.passed && row.pdbMatchesAssembly && loaded.ManifestModule.ModuleVersionId.ToString() == row.mvid, "executing_assembly_not_attested");
                Need(Hash(Inside(row.path)) == row.sha256 && Hash(Inside(Path.ChangeExtension(row.path, ".pdb"))) == row.pdbSha256, "compiled_binary_changed");
                Need(row.documents != null && row.documents.Length > 0, "compiled_documents_missing");
                foreach (var document in row.documents)
                {
                    if (string.IsNullOrEmpty(document.sha256))
                    { Need(document.path.StartsWith("Library/Bee/artifacts/", StringComparison.Ordinal) && document.path.EndsWith("/Unity.SourceGenerators/Unity.MonoScriptGenerator.MonoScriptInfoGenerator/AssemblyMonoScriptTypes.generated.cs", StringComparison.Ordinal), "unbound_compiled_document"); continue; }
                    Need(document.matches && Hash(Inside(document.path)) == document.sha256, "compiled_source_changed");
                }
            }
        }
        internal static BaselineFile[] Snapshot(string scene, string originalScene, string pipeline, string originalPipeline, string proof)
        {
            var paths = new HashSet<string>(StringComparer.Ordinal);
            foreach (string root in new[] { "Assets/RacingBois/Client", "Assets/RacingBois/Editor", "Packages/com.racingbois.foundation/Runtime", NativeBaselineBuilder.AssetRoot })
                foreach (string path in Directory.GetFiles(root, "*", SearchOption.AllDirectories))
                    if (new[] { ".cs", ".asmdef", ".uxml", ".uss" }.Contains(Path.GetExtension(path))) Add(paths, path);
            // The original scene/pipeline bytes remain bound below as provenance.
            // Only the owned build roots define consumed assets; unused source-scene UI/font
            // dependencies must not be confused with the actual native workload closure.
            foreach (string logical in AssetDatabase.GetDependencies(new[] { scene, pipeline }, true))
            {
                if (logical == "Resources/unity_builtin_extra" || logical == "Library/unity default resources") continue;
                string physical = logical;
                if (logical.StartsWith("Packages/", StringComparison.Ordinal))
                {
                    var package = UnityEditor.PackageManager.PackageInfo.FindForAssetPath(logical);
                    string name = logical.Split('/')[1]; Need(package != null && package.name == name, "unresolved_package_dependency");
                    string directory = Relative(package.resolvedPath), prefix = "Library/PackageCache/" + name + "@";
                    Need(directory == "Packages/" + name || directory.StartsWith(prefix, StringComparison.Ordinal) && directory.Length > prefix.Length && !directory.Substring(prefix.Length).Contains("/"), "unbounded_package_root");
                    Add(paths, Path.Combine(package.resolvedPath, "package.json"));
                    physical = Path.Combine(package.resolvedPath, logical.Substring(("Packages/" + name + "/").Length));
                }
                Add(paths, physical);
            }
            foreach (string name in Assemblies)
            { Add(paths, "Library/ScriptAssemblies/" + name + ".dll"); Add(paths, "Library/ScriptAssemblies/" + name + ".pdb"); }
            foreach (string path in new[] { scene, originalScene, pipeline, originalPipeline, proof, "Packages/manifest.json", "Packages/packages-lock.json", "ProjectSettings/ProjectVersion.txt", "ProjectSettings/ProjectSettings.asset", "ProjectSettings/GraphicsSettings.asset", "ProjectSettings/QualitySettings.asset" }) Add(paths, path);
            return paths.OrderBy(x => x, StringComparer.Ordinal).Select(Row).ToArray();
        }
        private static void Add(HashSet<string> paths, string path)
        { string relative = Relative(path); Need(File.Exists(Inside(relative)), "dependency_missing"); paths.Add(relative); if (File.Exists(relative + ".meta")) { Inside(relative + ".meta"); paths.Add(relative + ".meta"); } }
        internal static BaselineFile Row(string path) => new BaselineFile { path = Relative(path), bytes = new FileInfo(path).Length, sha256 = Hash(path) };
        internal static string Fingerprint(BaselineFile[] rows) { using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", rows.Select(x => x.path + " " + x.sha256))))); }
        internal static string Hash(string path) { using (var sha = SHA256.Create()) using (var stream = File.OpenRead(path)) return Hex(sha.ComputeHash(stream)); }
        private static string Hex(byte[] data) => BitConverter.ToString(data).Replace("-", "").ToLowerInvariant();
        internal static string Relative(string path) => Path.GetRelativePath(Path.GetFullPath("."), Path.GetFullPath(path)).Replace('\\', '/');
        internal static string Inside(string path)
        {
            Need(!string.IsNullOrEmpty(path) && !Path.IsPathRooted(path) && !path.Contains("\\") && !path.Split('/').Any(x => x == "" || x == "." || x == ".." || x.Contains(":")), "noncanonical_source_path");
            string root = Path.GetFullPath("."), full = Path.GetFullPath(path);
            Need(full.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase), "source_path_escape");
            for (string item = full; item != null && !string.Equals(item, root, StringComparison.OrdinalIgnoreCase); item = Path.GetDirectoryName(item))
                Need(!(File.Exists(item) || Directory.Exists(item)) || (File.GetAttributes(item) & FileAttributes.ReparsePoint) == 0, "source_link_rejected");
            return full;
        }
        internal static void Need(bool value, string code) { if (!value) throw new InvalidOperationException(code); }
    }
}
