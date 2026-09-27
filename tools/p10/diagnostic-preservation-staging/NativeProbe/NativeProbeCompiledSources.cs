using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEngine;

namespace RacingBois.Diagnostics.NativeProbe.Editor
{
    internal static class NativeProbeCompiledSources
    {
        internal static readonly string[] AssemblyNames = { "RacingBois.Diagnostics.NativeProbe", "RacingBois.Diagnostics.NativeProbe.Editor",
            "RacingBois.Client.Application", "RacingBois.Client.Adapters", "RacingBois.Gameplay.Definitions", "RacingBois.Protocol",
            "RacingBois.NetworkMapping", "RacingBois.Simulation", "RacingBois.Authoring.Editor" };
        [Serializable] private sealed class Proof { public int schema = 0; public bool passed = false; public AssemblyProof[] assemblies = Array.Empty<AssemblyProof>(); }
        [Serializable] private sealed class AssemblyProof
        { public string name = "", path = "", sha256 = "", pdbSha256 = "", mvid = ""; public bool passed = false, pdbMatchesAssembly = false; public Document[] documents = Array.Empty<Document>(); }
        [Serializable] private sealed class Document { public string path = "", sha256 = ""; public bool matches = false; }

        internal static void VerifyExecutingAssemblies(string path)
        {
            var proof = JsonUtility.FromJson<Proof>(File.ReadAllText(Inside(path)));
            if (proof == null || proof.schema != 1 || !proof.passed || proof.assemblies == null) throw new InvalidDataException("compiled_proof_required");
            foreach (string name in AssemblyNames)
            {
                var record = proof.assemblies.SingleOrDefault(row => row.name == name);
                var assembly = AppDomain.CurrentDomain.GetAssemblies().SingleOrDefault(value => value.GetName().Name == name);
                if (record == null || assembly == null || !record.passed || !record.pdbMatchesAssembly || assembly.ManifestModule.ModuleVersionId.ToString() != record.mvid)
                    throw new InvalidDataException("loaded_assembly_not_attested");
                if (Hash(Inside(record.path)) != record.sha256 || Hash(Inside(Path.ChangeExtension(record.path, ".pdb"))) != record.pdbSha256)
                    throw new InvalidDataException("compiled_binary_changed");
                if (record.documents == null || record.documents.Length == 0) throw new InvalidDataException("compiled_documents_missing");
                foreach (var document in record.documents)
                {
                    if (string.IsNullOrEmpty(document.sha256))
                    {
                        if (!document.path.StartsWith("Library/Bee/artifacts/", StringComparison.Ordinal) ||
                            !document.path.EndsWith("/Unity.SourceGenerators/Unity.MonoScriptGenerator.MonoScriptInfoGenerator/AssemblyMonoScriptTypes.generated.cs", StringComparison.Ordinal))
                            throw new InvalidDataException("unbound_source_document");
                        continue;
                    }
                    if (!document.matches || Hash(Inside(document.path)) != document.sha256) throw new InvalidDataException("compiled_source_changed");
                }
            }
        }
        private static string Inside(string path)
        {
            if (string.IsNullOrEmpty(path) || Path.IsPathRooted(path) || path.Contains("\\") || path.Split('/').Any(part => part == "" || part == "." || part == ".." || part.Contains(":")))
                throw new InvalidDataException("noncanonical_project_path");
            string root = Path.GetFullPath("."), full = Path.GetFullPath(path);
            if (!full.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("project_path_escape");
            for (string item = full; item != null && !string.Equals(item, root, StringComparison.OrdinalIgnoreCase); item = Path.GetDirectoryName(item))
                if ((File.Exists(item) || Directory.Exists(item)) && (File.GetAttributes(item) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException("source_reparse_point");
            return full;
        }
        private static string Hash(string path)
        { using (var hash = SHA256.Create()) using (var stream = File.OpenRead(path)) return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
    }
}
