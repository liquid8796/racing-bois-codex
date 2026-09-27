using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

string root = Path.GetFullPath(args.Length > 0 ? args[0] : ".");
string destination = Path.GetFullPath(Path.Combine(root, args.Length > 1 ? args[1] : "docs/p10/pose-envelope-native-staging/compiled-sources.json"));
string[] names = ["RacingBois.Diagnostics.PoseEnvelopePreview", "RacingBois.Diagnostics.PoseEnvelopePreview.Editor", "RacingBois.Client.Presentation", "RacingBois.Gameplay.Definitions", "RacingBois.Golden"];
var assemblies = new List<object>();
bool passed = true;
foreach (string name in names)
{
    string path = Path.Combine(root, "Library", "ScriptAssemblies", name + ".dll");
    string pdb = Path.ChangeExtension(path, ".pdb");
    try
    {
        using var peStream = File.OpenRead(path);
        using var pe = new PEReader(peStream);
        var metadata = pe.GetMetadataReader();
        string mvid = metadata.GetGuid(metadata.GetModuleDefinition().Mvid).ToString();
        var codeViewEntry = pe.ReadDebugDirectory().Single(entry => entry.Type == DebugDirectoryEntryType.CodeView);
        var codeView = pe.ReadCodeViewDebugDirectoryData(codeViewEntry);
        using var symbols = File.OpenRead(pdb);
        using var provider = MetadataReaderProvider.FromPortablePdbStream(symbols);
        var reader = provider.GetMetadataReader();
        var header = reader.DebugMetadataHeader ?? throw new InvalidDataException("Missing portable PDB identity.");
        bool pdbMatchesAssembly = new Guid(header.Id.Take(16).ToArray()) == codeView.Guid;
        var documents = new List<object>();
        bool sourcesMatch = true;
        int physicalSources = 0;
        foreach (var handle in reader.Documents)
        {
            var document = reader.GetDocument(handle);
            string source = Path.GetFullPath(reader.GetString(document.Name), root);
            string relative = Path.GetRelativePath(root, source).Replace('\\', '/');
            byte[] expected = reader.GetBlobBytes(document.Hash);
            Guid algorithm = reader.GetGuid(document.HashAlgorithm);
            byte[]? bytes = File.Exists(source) ? File.ReadAllBytes(source) : null;
            bool generated = bytes is null && relative.StartsWith("Library/Bee/artifacts/", StringComparison.Ordinal)
                && relative.EndsWith("/Unity.SourceGenerators/Unity.MonoScriptGenerator.MonoScriptInfoGenerator/AssemblyMonoScriptTypes.generated.cs", StringComparison.Ordinal);
            if (generated)
            {
                documents.Add(new { path = relative, sha256 = "", symbolChecksum = Hex(expected), matches = (bool?)null, scope = "Unity-generated virtual document; PE/PDB identity bound, no physical project source claimed" });
                continue;
            }
            physicalSources++;
            byte[] actual = bytes is null ? [] : algorithm == new Guid("8829d00f-11b8-4213-878b-770e8597ac16")
                ? SHA256.HashData(bytes) : algorithm == new Guid("ff1816ec-aa5e-4d10-87f7-6f4963833460")
                    ? SHA1.HashData(bytes) : [];
            bool matches = actual.Length > 0 && expected.AsSpan().SequenceEqual(actual);
            sourcesMatch &= matches;
            documents.Add(new { path = relative, sha256 = bytes is null ? "" : Hex(SHA256.HashData(bytes)), symbolChecksum = Hex(expected), matches });
        }
        bool valid = pdbMatchesAssembly && sourcesMatch && physicalSources > 0;
        passed &= valid;
        assemblies.Add(new { name, path = Path.GetRelativePath(root, path).Replace('\\', '/'), sha256 = Hash(path), pdbSha256 = Hash(pdb), mvid, passed = valid, pdbMatchesAssembly, documents });
        Console.WriteLine($"{name}: {(valid ? "PASS" : "FAIL")} ({documents.Count} source documents)");
    }
    catch (Exception error)
    {
        passed = false;
        assemblies.Add(new { name, passed = false, failure = error.GetType().Name + ": " + error.Message });
    }
}
Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
File.WriteAllText(destination, JsonSerializer.Serialize(new { schema = 1, utc = DateTime.UtcNow, passed, scope = "Compiled PE/PDB identity and actual source checksums; not visual acceptance", assemblies }, new JsonSerializerOptions { WriteIndented = true }));
Environment.ExitCode = passed ? 0 : 1;
static string Hex(byte[] bytes) => Convert.ToHexString(bytes).ToLowerInvariant();
static string Hash(string path) => Hex(SHA256.HashData(File.ReadAllBytes(path)));
