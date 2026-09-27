using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using Builder = RacingBois.Authoring.Editor.GoldenSampleBuilder;

string repository = Directory.GetCurrentDirectory();
string ownedRoot = Path.GetFullPath(Path.Combine(repository, "_local", "import-output-tests")) + Path.DirectorySeparatorChar;
string fixture = Path.Combine(ownedRoot, Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(fixture);
var checks = new List<object>();
int failures = 0;
var snapshotMethod = typeof(Builder).GetMethod("ImportedOutputSnapshot", BindingFlags.NonPublic | BindingFlags.Static)!;
var verifyMethod = typeof(Builder).GetMethod("VerifyInput", BindingFlags.NonPublic | BindingFlags.Static)!;

void Check(string name, Action action)
{
    try { action(); checks.Add(new { name, passed = true }); }
    catch (Exception error) { failures++; checks.Add(new { name, passed = false, error = (error.InnerException ?? error).Message }); }
}
void Need(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
void Reject(Action action)
{
    bool failed = false;
    try { action(); } catch (Exception error) when ((error.InnerException ?? error) is InvalidOperationException or IOException) { failed = true; }
    Need(failed, "Invalid selected output was accepted.");
}
void Write(string path, string contents)
{
    Directory.CreateDirectory(Path.GetDirectoryName(path)!); File.WriteAllText(path, contents);
}
string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
Builder.InputFile Input(string path) => new() { path = path, sha256 = new string('a', 64) };
Builder.AssetSpec Asset(string id) => new()
{
    id = id, concept = Input("ArtSource/concept.png"), conceptReview = Input("docs/concept.md"), source = Input("ArtSource/source.blend"),
    fbx = Input("Assets/Selected/model.fbx"), moduleLodMap = Input("Assets/Selected/modules.json"),
    materials = new[] { new Builder.MaterialSpec { sourceName = "Pearl", baseColor = Input("Assets/Selected/color.png"),
        normal = Input("Assets/Selected/normal.png"), metallicSmoothness = Input("Assets/Selected/metal.png"), emission = Input("Assets/Selected/emission.png") } },
    clips = new[] { new Builder.ClipSpec { path = "Assets/Selected/clip.fbx", name = "Ride", sha256 = new string('b', 64) } },
    previewClips = new[] { new Builder.ClipSpec { path = "Assets/Selected/clip.fbx", name = "Menu", sha256 = new string('b', 64) } }
};
Builder.FileReceipt[] Snapshot(params Builder.AssetSpec[] assets) =>
    (Builder.FileReceipt[])snapshotMethod.Invoke(null, new object[] { new Builder.Descriptor { schema = 1, assets = assets } })!;
void Verify(IEnumerable<Builder.FileReceipt> rows)
{
    foreach (var row in rows) verifyMethod.Invoke(null, new object[] { new Builder.InputFile { path = row.path, sha256 = row.sha256 } });
}
string[] Generated(string id) => new[] { Builder.OutputRoot + "/Prefabs/" + id + ".prefab", Builder.OutputRoot + "/Materials/" + id + "_Pearl.mat" };

try
{
    Directory.SetCurrentDirectory(fixture);
    var selected = Asset("Apex");
    string[] imports = { "model.fbx", "modules.json", "color.png", "normal.png", "metal.png", "emission.png", "clip.fbx" };
    foreach (string name in imports) { Write("Assets/Selected/" + name, "selected input"); Write("Assets/Selected/" + name + ".meta", "selected importer metadata"); }
    foreach (string path in Generated("Apex").Concat(Generated("Other"))) { Write(path, "generated selected candidate"); Write(path + ".meta", "generated GUID"); }
    string floor = Builder.OutputRoot + "/Materials/GoldenInspectionFloor.mat";
    string pipeline = Builder.OutputRoot + "/ReviewPipeline.asset";
    Write(floor, "original studio"); Write(floor + ".meta", "floor GUID"); Write(pipeline + ".meta", "pipeline GUID");
    var baseline = Snapshot(selected);
    string[] expected = Generated("Apex").SelectMany(path => new[] { path, path + ".meta" })
        .Concat(imports.Select(name => "Assets/Selected/" + name + ".meta")).OrderBy(path => path, StringComparer.Ordinal).ToArray();
    Check("exact_descriptor_selected_outputs_and_importer_metadata", () => Need(baseline.Select(row => row.path).SequenceEqual(expected), "Selected file set differs."));
    Check("real_file_lengths_and_sha256", () => Need(baseline.All(row => row.bytes == new FileInfo(row.path).Length && row.sha256 == Sha(row.path)), "File binding differs."));
    Check("unchanged_selected_outputs_verify", () => Verify(baseline));
    Check("unrelated_review_floor_mutation_does_not_invalidate", () => { Write(floor, "changed studio"); Verify(baseline); Need(Snapshot(selected).Select(row => row.sha256).SequenceEqual(baseline.Select(row => row.sha256)), "Unrelated floor entered selected snapshot."); });
    Check("unrelated_pipeline_metadata_mutation_does_not_invalidate", () => { Write(pipeline + ".meta", "new pipeline GUID"); Verify(baseline); });
    Check("other_candidate_mutation_does_not_invalidate", () => { Write(Generated("Other")[0], "other candidate changed"); Verify(baseline); });
    Check("new_unrelated_outputs_do_not_change_selected_inventory", () => { Write(Builder.OutputRoot + "/Prefabs/New.prefab", "unrelated"); Need(Snapshot(selected).Select(row => row.path).SequenceEqual(expected), "Inventory grew beyond selected descriptor."); });
    foreach (string path in new[] { Generated("Apex")[0], Generated("Apex")[0] + ".meta", Generated("Apex")[1], Generated("Apex")[1] + ".meta",
        "Assets/Selected/model.fbx.meta", "Assets/Selected/color.png.meta", "Assets/Selected/clip.fbx.meta", "Assets/Selected/modules.json.meta", "Assets/Selected/emission.png.meta" })
    {
        Check("selected_mutation_rejected:" + path, () => { string original = File.ReadAllText(path); try { Write(path, original + "changed"); Reject(() => Verify(baseline)); } finally { Write(path, original); } });
    }
    Check("missing_selected_metadata_cannot_be_silently_omitted", () =>
    {
        string path = "Assets/Selected/model.fbx.meta", original = File.ReadAllText(path);
        try { File.Delete(path); Reject(() => Snapshot(selected)); Reject(() => Verify(baseline)); } finally { Write(path, original); }
    });
    Check("shared_input_metadata_is_bound_once", () =>
    {
        var rows = Snapshot(selected, Asset("Other"));
        Need(rows.Length == baseline.Length + 4 && rows.Count(row => row.path == "Assets/Selected/clip.fbx.meta") == 1, "Shared imported input metadata duplicated.");
    });
    Check("non_asset_source_metadata_is_not_an_import_output", () => Need(!baseline.Any(row => row.path.StartsWith("ArtSource/", StringComparison.Ordinal) || row.path.StartsWith("docs/", StringComparison.Ordinal)), "External source metadata treated as Unity output."));
    Check("empty_descriptor_rejected", () => Reject(() => Snapshot()));
}
finally
{
    Directory.SetCurrentDirectory(repository);
    string resolved = Path.GetFullPath(fixture);
    if (!resolved.StartsWith(ownedRoot, StringComparison.OrdinalIgnoreCase) || Path.GetFileName(resolved).Length != 32)
        throw new InvalidOperationException("Test cleanup escaped the owned fixture directory.");
    Directory.Delete(resolved, true);
}
var report = new { schema = 1, passed = failures == 0, checks = checks.Count, failures,
    scope = "Real staged production output selector and hash verifier against isolated file fixtures. Not native Unity import or visual evidence.", results = checks };
Console.WriteLine(JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
if (args.Length > 0) File.WriteAllText(Path.GetFullPath(args[0]), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Environment.ExitCode = failures == 0 ? 0 : 1;
