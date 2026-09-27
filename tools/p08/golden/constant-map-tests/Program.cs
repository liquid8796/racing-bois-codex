using System.Text.Json;
using UnityEngine;
using Builder = RacingBois.Authoring.Editor.GoldenSampleBuilder;

var results = new List<object>();
int failures = 0;
void Test(string name, Action action)
{
    try { action(); results.Add(new { name, passed = true }); }
    catch (Exception error) { failures++; results.Add(new { name, passed = false, error = error.Message }); }
}
void Reject(Action action)
{
    bool rejected = false;
    try { action(); } catch (InvalidOperationException) { rejected = true; }
    if (!rejected) throw new InvalidOperationException("Invalid constant-map fixture accepted.");
}
Builder.InputFile Input() => new() { path = "Assets/test.png", sha256 = new string('a', 64) };
Builder.MaterialSpec Material() => new()
{
    sourceName = "ContractFixture", baseColor = Input(), normal = Input(), metallicSmoothness = Input(), occlusion = Input(), emission = Input()
};
byte[] Header(byte colorType = 6)
{
    var bytes = new byte[33];
    new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 }.CopyTo(bytes, 0);
    bytes[11] = 13; bytes[12] = (byte)'I'; bytes[13] = (byte)'H'; bytes[14] = (byte)'D'; bytes[15] = (byte)'R';
    bytes[19] = bytes[23] = 4; bytes[24] = 8; bytes[25] = colorType;
    return bytes;
}
Color32[] Pixels() => Enumerable.Repeat(new Color32(128, 128, 255, 191), 16).ToArray();
Test("ordinary_material_does_not_opt_in", () => Builder.ValidateConstantMapDeclarations(Material()));
Test("empty_declaration_is_ordinary", () => { var m = Material(); m.constantMaps = []; Builder.ValidateConstantMapDeclarations(m); });
Test("all_five_bound_roles_allowed", () => { var m = Material(); m.constantMaps = ["baseColor", "normal", "metallicSmoothness", "occlusion", "emission"]; Builder.ValidateConstantMapDeclarations(m); });
Test("duplicate_role_rejected", () => { var m = Material(); m.constantMaps = ["normal", "normal"]; Reject(() => Builder.ValidateConstantMapDeclarations(m)); });
Test("unknown_role_rejected", () => { var m = Material(); m.constantMaps = ["roughness"]; Reject(() => Builder.ValidateConstantMapDeclarations(m)); });
Test("null_role_rejected", () => { var m = Material(); m.constantMaps = [null!]; Reject(() => Builder.ValidateConstantMapDeclarations(m)); });
Test("missing_optional_input_rejected", () => { var m = Material(); m.emission = null; m.constantMaps = ["emission"]; Reject(() => Builder.ValidateConstantMapDeclarations(m)); });
Test("empty_input_path_rejected", () => { var m = Material(); m.normal.path = ""; m.constantMaps = ["normal"]; Reject(() => Builder.ValidateConstantMapDeclarations(m)); });
Test("unbound_input_hash_rejected", () => { var m = Material(); m.normal.sha256 = "not-a-hash"; m.constantMaps = ["normal"]; Reject(() => Builder.ValidateConstantMapDeclarations(m)); });
Test("exact_rgb_header_allowed", () => Builder.ValidateConstantPngHeader(Header(2)));
Test("exact_rgba_header_allowed", () => Builder.ValidateConstantPngHeader(Header()));
Test("source_width_rejected_even_if_importer_could_resize", () => { var bytes = Header(); bytes[18] = 2; Reject(() => Builder.ValidateConstantPngHeader(bytes)); });
Test("source_height_rejected", () => { var bytes = Header(); bytes[23] = 1; Reject(() => Builder.ValidateConstantPngHeader(bytes)); });
Test("sixteen_bit_precision_loss_rejected", () => { var bytes = Header(); bytes[24] = 16; Reject(() => Builder.ValidateConstantPngHeader(bytes)); });
Test("indexed_png_rejected", () => Reject(() => Builder.ValidateConstantPngHeader(Header(3))));
Test("truncated_header_rejected", () => Reject(() => Builder.ValidateConstantPngHeader(Header()[..24])));
Test("invalid_signature_rejected", () => { var bytes = Header(); bytes[0] = 0; Reject(() => Builder.ValidateConstantPngHeader(bytes)); });
Test("uniform_pixels_return_original_channels", () =>
{
    var pixel = Builder.ValidateConstantMapPixels(4, 4, Pixels());
    if (pixel.r != 128 || pixel.g != 128 || pixel.b != 255 || pixel.a != 191) throw new InvalidOperationException("Pixel channels changed.");
});
foreach (int channel in new[] { 0, 1, 2, 3 })
    Test("differing_pixel_channel_" + channel + "_rejected", () =>
    {
        var pixels = Pixels(); var value = pixels[15];
        if (channel == 0) value.r--; else if (channel == 1) value.g--; else if (channel == 2) value.b--; else value.a--;
        pixels[15] = value; Reject(() => Builder.ValidateConstantMapPixels(4, 4, pixels));
    });
Test("wrong_pixel_count_rejected", () => Reject(() => Builder.ValidateConstantMapPixels(4, 4, Pixels()[..15])));
Test("decoded_dimensions_rejected", () => Reject(() => Builder.ValidateConstantMapPixels(8, 2, Pixels())));
Test("null_pixels_rejected", () => Reject(() => Builder.ValidateConstantMapPixels(4, 4, null!)));
Test("original_source_hash_mismatch_rejected_before_native_decode", () =>
{
    string path = "_local/constant-map-contract/source.png";
    Directory.CreateDirectory(Path.GetDirectoryName(path)!); File.WriteAllBytes(path, Header());
    Reject(() => Builder.ValidateConstantMapSource(new Builder.InputFile { path = path, sha256 = new string('0', 64) }));
});
string output = args.Length == 0 ? "_local/constant-map-contract/tests.json" : args[0];
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output, JsonSerializer.Serialize(new { passed = failures == 0, tests = results.Count, failures, results,
    scope = "Production declaration/header/pixel/hash contract controls. Synthetic headers do not claim PNG decoding; actual Unity ImageConversion and TextureImporter require separate verification.",
    unityDecoded = false, visualAccepted = false }, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"CONSTANT MAP {(failures == 0 ? "PASS" : "FAIL")} {results.Count - failures}/{results.Count}");
return failures == 0 ? 0 : 1;
