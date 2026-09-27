using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using RacingBois.Authoring.Editor;
using Builder = RacingBois.Authoring.Editor.GoldenSampleBuilder;

string directory = "_local/p08-module-contract-tests";
Directory.CreateDirectory(directory);
string sourcePath = directory + "/fixture.fbx";
File.WriteAllText(sourcePath, "Parser fixture only; never imported into Unity.");
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
var source = new Builder.InputFile { path = sourcePath, sha256 = Hash(sourcePath) };
var asset = new Builder.AssetSpec
{
    id = "test-environment", kind = "environment", isStatic = true, fbx = source,
    lods = Enumerable.Range(0, 3).Select(level => new Builder.LodSpec
    { height = new[] { .5f, .15f, .025f }[level], rendererPaths = new[] { "Alpha_L" + level, "Beta_L" + level } }).ToArray()
};
string valid = JsonSerializer.Serialize(new
{
    schema = 1, assetId = asset.id, source = new { source.path, source.sha256 }, scope = "Test data only",
    modules = new[] { "Alpha", "Beta" }.Select(id => new
    { id, lods = Enumerable.Range(0, 3).Select(level => new { height = asset.lods[level].height, rendererPaths = new[] { id + "_L" + level } }) })
});
var results = new List<object>();
void Check(string name, string json, bool succeeds, Builder.AssetSpec? specification = null)
{
    string path = directory + "/" + name + ".json";
    File.WriteAllText(path, json);
    Exception? failure = null;
    Builder.ModuleLodMap? result = null;
    try { result = Builder.ReadModuleLodMap(new Builder.InputFile { path = path, sha256 = Hash(path) }, specification ?? asset); }
    catch (Exception error) { failure = error; }
    if ((failure == null) != succeeds) throw new InvalidOperationException(name + " had unexpected result", failure);
    results.Add(new { name, passed = true, accepted = succeeds, moduleCount = result?.modules.Length ?? 0, rejection = failure?.GetType().Name });
}
string Mutate(Action<JsonNode> edit)
{
    var node = JsonNode.Parse(valid)!;
    edit(node);
    return node.ToJsonString();
}
Check("valid", valid, true);
Check("unknown-root-field", Mutate(n => n["ignored"] = true), false);
Check("unknown-root-type-metadata", Mutate(n => n["__type"] = "unexpected:#namespace"), false);
Check("unknown-source-type-metadata", Mutate(n => n["source"]!["__type"] = "unexpected:#namespace"), false);
Check("duplicate-root-field", valid.Replace("\"schema\":1", "\"schema\":1,\"schema\":1"), false);
Check("escaped-duplicate-field", valid.Replace("\"schema\":1", "\"schema\":1,\"\\u0073chema\":1"), false);
Check("unknown-source-field", Mutate(n => n["source"]!["extra"] = 1), false);
Check("unknown-lod-field", Mutate(n => n["modules"]![0]!["lods"]![0]!["bias"] = 1), false);
Check("wrong-source", Mutate(n => n["source"]!["sha256"] = new string('0', 64)), false);
Check("wrong-asset", Mutate(n => n["assetId"] = "another"), false);
Check("empty-modules", Mutate(n => n["modules"] = new JsonArray()), false);
Check("duplicate-module-case", Mutate(n => n["modules"]![1]!["id"] = "aLPHa"), false);
Check("reserved-module-id", Mutate(n => n["modules"]![0]!["id"] = ".."), false);
Check("missing-coverage", Mutate(n => n["modules"]!.AsArray().RemoveAt(1)), false);
Check("duplicated-renderer", Mutate(n => n["modules"]![1]!["lods"]![0]!["rendererPaths"]![0] = "Alpha_L0"), false);
Check("wrong-logical-lod", Mutate(n => n["modules"]![0]!["lods"]![1]!["rendererPaths"]![0] = "Alpha_L0"), false);
Check("unsafe-renderer-path", Mutate(n => n["modules"]![0]!["lods"]![0]!["rendererPaths"]![0] = "../Alpha_L0"), false);
Check("increasing-height", Mutate(n => n["modules"]![0]!["lods"]![1]!["height"] = .8), false);
Check("string-height", Mutate(n => n["modules"]![0]!["lods"]![0]!["height"] = "0.5"), false);
Check("overflow-height", valid.Replace("\"height\":0.5", "\"height\":1e1000"), false);
Check("string-schema", Mutate(n => n["schema"] = "1"), false);

using (var actual = JsonDocument.Parse(File.ReadAllText("docs/p08/golden/canyon/v13/descriptor-lighting.json")))
{
    var value = actual.RootElement.GetProperty("assets")[0];
    var fbx = value.GetProperty("fbx");
    var actualAsset = new Builder.AssetSpec
    {
        id = value.GetProperty("id").GetString(), kind = "environment", isStatic = true,
        fbx = new Builder.InputFile { path = fbx.GetProperty("path").GetString(), sha256 = fbx.GetProperty("sha256").GetString() },
        lods = value.GetProperty("lods").EnumerateArray().Select(lod => new Builder.LodSpec
        { height = lod.GetProperty("height").GetSingle(), rendererPaths = lod.GetProperty("rendererPaths").EnumerateArray().Select(path => path.GetString()).ToArray() }).ToArray()
    };
    Check("actual-canyon-217-modules", File.ReadAllText("docs/p08/golden/canyon/v13/module-lod-mapping.json"), true, actualAsset);
}
File.WriteAllText("docs/p08/golden/canyon/module-contract-tests.json", JsonSerializer.Serialize(new
{
    passed = true, scope = "Strict schema/hash/coverage parsing only; native Unity hierarchy, mesh and culling checks require ProbeModuleLods.",
    utc = DateTime.UtcNow, count = results.Count, results,
    implementationSha256 = Hash("tools/p08/golden/canyon-staging/GoldenSampleBuilder.Modules.cs")
}, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine("MODULE_CONTRACT_TESTS_PASS " + results.Count);
