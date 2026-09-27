using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        private const string CompileProofPath = ReceiptRoot + "/compiled-sources.json";
        [Serializable] private sealed class CompileProof { public int schema = 0; public bool passed = false; public CompiledAssembly[] assemblies = Array.Empty<CompiledAssembly>(); }
        [Serializable] private sealed class CompiledAssembly
        {
            public string name = "", path = "", sha256 = "", pdbSha256 = "", mvid = "";
            public bool passed = false, pdbMatchesAssembly = false;
            public CompiledDocument[] documents = Array.Empty<CompiledDocument>();
        }
        [Serializable] private sealed class CompiledDocument { public string path = "", sha256 = ""; public bool matches = false; }

        private static void VerifyCompiledSources()
        {
            Require(File.Exists(CompileProofPath), "Run tools/p08/golden/CompileAudit after Unity has finished recompiling.");
            var proof = JsonUtility.FromJson<CompileProof>(File.ReadAllText(CompileProofPath));
            Require(proof != null && proof.schema == 1 && proof.passed && proof.assemblies != null, "Compiled source audit failed or is missing.");
            foreach (var assembly in new[] { typeof(GoldenSampleBuilder).Assembly, typeof(RacingBois.Client.Presentation.RiderAnimationSet).Assembly, typeof(RacingBois.Golden.GoldenSkinBounds).Assembly })
                VerifyAssembly(proof, assembly);
        }

        private static void VerifyAssembly(CompileProof proof, Assembly assembly)
        {
            var record = proof.assemblies.SingleOrDefault(row => row.name == assembly.GetName().Name);
            Require(record != null && record.passed && record.pdbMatchesAssembly && record.documents != null, "Compiled assembly audit missing: " + assembly.GetName().Name);
            ProjectPath(record.path, false);
            Require(assembly.ManifestModule.ModuleVersionId.ToString() == record.mvid, "Unity is executing a stale assembly; finish domain reload first.");
            Require(Digest(record.path) == record.sha256 && Digest(Path.ChangeExtension(record.path, ".pdb")) == record.pdbSha256,
                "Compiled assembly or symbols changed after audit.");
            foreach (var document in record.documents)
            {
                if (string.IsNullOrEmpty(document.sha256))
                {
                    Require(document.path.StartsWith("Library/Bee/artifacts/", StringComparison.Ordinal)
                        && document.path.EndsWith("/Unity.SourceGenerators/Unity.MonoScriptGenerator.MonoScriptInfoGenerator/AssemblyMonoScriptTypes.generated.cs", StringComparison.Ordinal),
                        "Unexpected unbound source document.");
                    continue;
                }
                Require(document.matches, "Compiled source checksum failed: " + document.path);
                ProjectPath(document.path, false);
                Require(Digest(document.path) == document.sha256, "Source changed since Unity compiled it: " + document.path);
            }
        }
    }
}
