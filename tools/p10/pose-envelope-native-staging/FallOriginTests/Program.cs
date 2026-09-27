using System.Text.Json;
using RacingBois.Client.Presentation;
using Builder = RacingBois.Authoring.Editor.GoldenSampleBuilder;

var results = new List<object>();
int failures = 0;
void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
void Test(string name, Action action)
{
    try { action(); results.Add(new { name, passed = true }); }
    catch (Exception error) { failures++; results.Add(new { name, passed = false, error = error.Message }); }
}
var options = new JsonSerializerOptions { IncludeFields = true };
Test("legacy_descriptor_default_preserved", () =>
    Check(new Builder.AssetSpec().fallenRootOffset == -.55f, "Legacy descriptor default changed."));
Test("absent_metadata_keeps_legacy_origin", () =>
    Check(JsonSerializer.Deserialize<Builder.AssetSpec>("{}", options)!.fallenRootOffset == -.55f, "Absent field lost initializer."));
Test("authored_zero_is_explicit_and_valid", () =>
{
    var spec = JsonSerializer.Deserialize<Builder.AssetSpec>("{\"fallenRootOffset\":0}", options)!;
    RiderAnimationSet.ValidateFallenRootOffset(spec.fallenRootOffset);
    Check(spec.fallenRootOffset == 0, "Explicit ground origin changed.");
});
Test("finite_domain_endpoints_and_legacy_are_valid", () =>
{
    foreach (float offset in new[] { -1f, -.55f, 0f, 1f }) RiderAnimationSet.ValidateFallenRootOffset(offset);
});
foreach (var (name, value) in new[] { ("nan", float.NaN), ("positive_infinity", float.PositiveInfinity),
    ("negative_infinity", float.NegativeInfinity), ("below_range", -1.001f), ("above_range", 1.001f) })
    Test("rejects_" + name, () =>
    {
        bool rejected = false;
        try { RiderAnimationSet.ValidateFallenRootOffset(value); }
        catch (ArgumentOutOfRangeException) { rejected = true; }
        Check(rejected, "Invalid fall-origin metadata accepted.");
    });
string output = args.Length == 0 ? "_local/pose-settings-tests/fall-origin-tests.json" : args[0];
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output, JsonSerializer.Serialize(new { passed = failures == 0, tests = results.Count, failures, results,
    scope = "Actual metadata initializer and finite/range validator only. JSON fixture uses System.Text.Json; Unity deserialization/prefab/native placement require live verification.",
    nativeRendered = false, visualAccepted = false }, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"FALL ORIGIN {(failures == 0 ? "PASS" : "FAIL")} {results.Count - failures}/{results.Count}");
return failures == 0 ? 0 : 1;
