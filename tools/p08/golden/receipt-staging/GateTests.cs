using System.IO.Compression;
using System.Text;
using System.Text.Json;
using RacingBois.Authoring.Editor;
using Gate = RacingBois.Authoring.Editor.GoldenProductionGate;

var json = new JsonSerializerOptions { IncludeFields = true, WriteIndented = true };
object Parse(string source, Type type) => JsonSerializer.Deserialize(source, type, json);
if (args.Length == 2 && args[0] == "--manifest")
{
    try
    {
        var manifest = new Gate(Directory.GetCurrentDirectory(), Parse).Read(args[1]);
        Console.WriteLine(JsonSerializer.Serialize(new { evidenceIntegrityPassed = true, bindings = manifest.bindings.Length, nativeUnityRevalidated = false, visualAcceptanceProved = false,
            scope = "Read-only evidence integrity. Native GoldenProductionBindings.Load revalidates the actual prefab before pack use. This CLI neither performs visual review nor creates acceptance." }, json));
    }
    catch (Exception error) { Console.Error.WriteLine(error.Message); Environment.ExitCode = 1; }
    return;
}
if (args.Length != 0) throw new ArgumentException("Usage: dotnet run --project tools/p08/promotion/GateTests.csproj [-- --manifest repository/path.json]");

var results = new List<object>();
void Test(string name, Action<Fixture> test)
{
    using var fixture = new Fixture(json, Parse);
    try { test(fixture); results.Add(new { name, passed = true }); }
    catch (Exception error) { results.Add(new { name, passed = false, error = error.ToString() }); Environment.ExitCode = 1; }
}
void Reject(Fixture fixture, Action mutation, string contains)
{
    mutation(); fixture.SaveReviewAndManifest();
    try { fixture.Gate.Read(fixture.ManifestPath); throw new Exception("Expected rejection did not occur: " + contains); }
    catch (InvalidDataException error) { if (!error.Message.Contains(contains, StringComparison.Ordinal)) throw; }
}

Test("synthetic complete corresponding-view contract is accepted as evidence only", f => f.Gate.Read(f.ManifestPath));
Test("unaccepted candidate rejected even with successful native import", f => Reject(f, () => f.Review.visualAccepted = false, "Explicit accepted visual review"));
Test("pending candidate cannot substitute a true boolean", f => Reject(f, () => f.Review.status = "pending", "Explicit accepted visual review"));
Test("omitted difference list rejected", f => Reject(f, () => f.Review.remainingDifferences = null, "difference list"));
Test("known mismatch remains rejected", f => Reject(f, () => f.Review.remainingDifferences = new[] { "Tank silhouette still differs" }, "difference list"));
Test("empty reviewer rejected", f => Reject(f, () => f.Review.reviewer = "", "reviewer"));
Test("required rear view cannot be omitted", f => Reject(f, () => f.Review.comparisons = f.Review.comparisons.Where(x => x.view != "rear").ToArray(), "Required corresponding views"));
Test("one view cannot stand in twice", f => Reject(f, () => f.Review.comparisons[1].view = "quarter", "Required corresponding views"));
Test("color dimension cannot be omitted", f => Reject(f, () => f.Review.comparisons[0].criteria = f.Review.comparisons[0].criteria.Where(x => x.aspect != "color").ToArray(), "Every visual dimension"));
Test("blank material observation rejected", f => Reject(f, () => f.Review.comparisons[0].criteria.Single(x => x.aspect == "materials").observation = "", "Blank or mismatching"));
Test("geometry mismatch rejected", f => Reject(f, () => f.Review.comparisons[0].criteria.Single(x => x.aspect == "geometry").result = "mismatch", "Blank or mismatching"));
Test("unreviewed lighting rejected", f => Reject(f, () => f.Review.comparisons[0].lightingReview = "", "framing and lighting"));
Test("stale descriptor rejected", f => Reject(f, () => File.AppendAllText(f.PathOf("descriptor.json"), " "), "Bound file changed"));
Test("stale concept rejected", f => Reject(f, () => File.AppendAllText(f.PathOf("concept.png"), "changed pixels"), "Bound file changed"));
Test("stale render rejected", f => Reject(f, () => File.AppendAllText(f.PathOf("quarter.png"), "changed pixels"), "Bound file changed"));
Test("new capture hash cannot conceal stale descriptor binding", f => Reject(f, () => { f.Captures[0].descriptor.sha256 = new string('0', 64); f.SaveCapture(0); }, "Capture is stale"));
Test("render dimensions checked against PNG", f => Reject(f, () => { f.Captures[0].width = 1280; f.SaveCapture(0); }, "dimensions differ"));
Test("concept cannot substitute runtime render", f => Reject(f, () => { f.Captures[0].image = f.Gate.Bind("concept.png"); f.SaveCapture(0); }, "Concept image"));
Test("duplicate pixels cannot supply different angles", f => Reject(f, () => { f.Captures[1].image = f.Gate.Bind("quarter.png"); f.SaveCapture(1); }, "Duplicate pixels"));
Test("fabricated non-native capture type rejected", f => Reject(f, () => { f.Captures[0].engine = "ImageGen"; f.SaveCapture(0); }, "native Unity capture"));
Test("omitted forced LOD policy rejected", f => Reject(f, () => { f.Captures[0].lodPolicy = null; f.SaveCapture(0); }, "controlled LOD0"));
Test("review cannot predate capture", f => Reject(f, () => f.Review.reviewedUtc = "2026-01-01T00:00:00.0000000+00:00", "predates"));
Test("failed native import rejected", f => Reject(f, () => { f.Native.passed = false; f.SaveNative(); }, "Successful source-bound"));
Test("contradictory successful native import with failure text rejected", f => Reject(f, () => { f.Native.failure = "IOException: Win32 IO returned 1224"; f.SaveNative(); }, "Successful source-bound"));
Test("whitespace native failure text is not an empty failure", f => Reject(f, () => { f.Native.failure = " "; f.SaveNative(); }, "Successful source-bound"));
Test("missing native material preservation gate rejected", f => Reject(f, () => { f.Native.assets[0].materialSlotsPreserved = false; f.SaveNative(); }, "material/reference gates"));
Test("collapsed native LOD declaration rejected", f => Reject(f, () => { f.Native.assets[0].lodTriangles[1] = f.Native.assets[0].lodTriangles[0]; f.SaveNative(); }, "decreasing native LODs"));
Test("accepted material bytes cannot change during binding", f => Reject(f, () => File.AppendAllText(f.PathOf("surface.mat"), "changed material slots"), "Bound file changed"));
Test("accepted prefab rig and LOD bytes cannot change", f => Reject(f, () => File.AppendAllText(f.PathOf(f.Binding.prefab.path), "changed skeleton or LOD hierarchy"), "Bound file changed"));
Test("accepted mesh and rig source bytes cannot change", f => Reject(f, () => File.AppendAllText(f.PathOf("subject.fbx"), "changed skin weights"), "Bound file changed"));
Test("duplicated semantic bindings rejected", f => { f.Manifest.bindings = new[] { f.Binding, f.Binding }; Reject(f, () => { }, "duplicate semantic"); });
Test("bike cannot map to wrong content kind", f => Reject(f, () => f.Binding.kind = "environment", "Environment cannot occupy"));
Test("wrong catalog index rejected", f => Reject(f, () => f.Binding.semanticName = "RB_P08_Bike_15", "catalog slot"));
Test("review cannot be rebound to another valid catalog identity", f => Reject(f, () => f.Binding.semanticName = "RB_P08_Bike_01", "semantic identity"));
Test("environment cannot replace a police rider", f => Reject(f, () => { f.Binding.kind = "environment"; f.Binding.semanticName = "RB_P06_PoliceRider"; }, "Environment cannot occupy"));
Test("environment cannot replace a protected weapon", f => Reject(f, () => { f.Binding.kind = "environment"; f.Binding.semanticName = "RB_Club"; }, "Environment cannot occupy"));
Test("removed manifest cannot leave an unchecked Golden actor in a pack", f =>
{
    try { Gate.ValidateResolvedPrefab(f.Binding.semanticName, f.Binding.prefab.path, Array.Empty<Gate.Binding>()); throw new Exception("Expected rejection"); }
    catch (InvalidDataException error) { if (!error.Message.Contains("no active accepted binding")) throw; }
});
Test("empty manifest retains ordinary legacy prefab support", f => Gate.ValidateResolvedPrefab("RB_P08_Bike_00", "Assets/RacingBois/Prefabs/P08/RB_P08_Bike_00.prefab", Array.Empty<Gate.Binding>()));
Test("mapped slot cannot silently retain a previous different prefab", f =>
{
    try { Gate.ValidateResolvedPrefab(f.Binding.semanticName, "Assets/RacingBois/Prefabs/P08/RB_P08_Bike_00.prefab", f.Manifest.bindings); throw new Exception("Expected rejection"); }
    catch (InvalidDataException error) { if (!error.Message.Contains("exact accepted Golden prefab")) throw; }
});
Test("missing native prefab output rejected", f => Reject(f, () => { f.Native.outputs = f.Native.outputs.Where(x => x.path != f.Binding.prefab.path).ToArray(); f.SaveNative(); }, "bind descriptor/prefab"));
Test("repository traversal rejected", f => Reject(f, () => f.Binding.acceptance.path = "../acceptance.json", "Canonical repository"));
Test("rider requires native rig result", f =>
{
    f.SetRider();
    f.Gate.Read(f.ManifestPath);
    Reject(f, () => { f.Native.assets[0].rigValid = false; f.SaveNative(); }, "rig/clip gates");
});
Console.WriteLine(JsonSerializer.Serialize(new { passed = Environment.ExitCode == 0, tests = results, syntheticFixturesOnly = true, visualAcceptanceProved = false,
    scope = "Contract rejection and immutable binding controls. No real asset is accepted, imported, rendered or changed by these tests." }, json));

sealed class Fixture : IDisposable
{
    public readonly string Root = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "rb-promotion-contract-" + Guid.NewGuid().ToString("N"));
    public readonly string ManifestPath = "production-bindings.json";
    public Gate Gate;
    public Gate.Binding Binding;
    public Gate.VisualAcceptance Review;
    public Gate.CaptureEvidence[] Captures;
    public Gate.Manifest Manifest;
    public Gate.NativeReceipt Native;
    private readonly JsonSerializerOptions json;
    private readonly Gate.Descriptor descriptor;
    public Fixture(JsonSerializerOptions options, Func<string, Type, object> parse)
    {
        json = options; Directory.CreateDirectory(Root); Gate = new Gate(Root, parse);
        Write("concept.png", Png(99));
        Write("concept-review.md", Encoding.UTF8.GetBytes("SYNTHETIC TEST FIXTURE ONLY. This is deliberately not a production visual review and cannot accept any real asset."));
        foreach (string path in new[] { "subject.blend", "subject.fbx", "surface.png", "surface.mat" }) Write(path, Encoding.UTF8.GetBytes("Synthetic contract test bytes: " + path));
        string prefab = Gate.PrefabRoot + "SyntheticBike.prefab";
        Write(prefab, Encoding.UTF8.GetBytes("Synthetic prefab byte binding; material slots + rig + three LODs are not real Unity objects."));
        descriptor = new Gate.Descriptor { schema = 1, assets = new[] { new Gate.Asset { id = "SyntheticBike", kind = "bike", concept = Gate.Bind("concept.png"), conceptReview = Gate.Bind("concept-review.md"), source = Gate.Bind("subject.blend"), fbx = Gate.Bind("subject.fbx"), materials = new[] { new Gate.Material { baseColor = Gate.Bind("surface.png"), normal = Gate.Bind("surface.png"), metallicSmoothness = Gate.Bind("surface.png") } } } } };
        Save("descriptor.json", descriptor);
        Native = new Gate.NativeReceipt { schema = 1, passed = true, sourceBindingPassed = true, descriptor = "descriptor.json", descriptorSha256 = Gate.Bind("descriptor.json").sha256,
            inputs = new[] { "descriptor.json", "concept.png", "concept-review.md", "subject.blend", "subject.fbx", "surface.png" }.Select(Gate.Bind).ToArray(),
            outputs = new[] { prefab, "surface.mat" }.Select(Gate.Bind).ToArray(), assets = new[] { new Gate.NativeAsset { id = "SyntheticBike", kind = "bike", prefab = prefab, passed = true, rootIdentity = true, materialSlotsPreserved = true, missingReferencesAbsent = true, handednessValid = true, lodTriangles = new long[] { 300, 150, 60 } } } };
        Save("native-import.json", Native);
        Binding = new Gate.Binding { semanticName = "RB_P08_Bike_00", assetId = "SyntheticBike", kind = "bike", descriptor = Gate.Bind("descriptor.json"), nativeImport = Gate.Bind("native-import.json"), prefab = Gate.Bind(prefab) };
        Captures = Gate.ActorViews.Select((view, i) =>
        {
            Write(view + ".png", Png(i));
            return new Gate.CaptureEvidence { schema = 1, completed = true, assetId = Binding.assetId, view = view, conceptView = view + " view on synthetic sheet", engine = "UnityEditor", lodPolicy = "fresh-instance-lod0", capturedUtc = "2026-01-02T00:00:00.0000000+00:00", width = 640, height = 360, descriptor = Copy(Binding.descriptor), nativeImport = Copy(Binding.nativeImport), prefab = Copy(Binding.prefab), concept = Gate.Bind("concept.png"), image = Gate.Bind(view + ".png"), cameraState = "Synthetic camera metadata only", subjectState = "Synthetic subject metadata only" };
        }).ToArray();
        Review = new Gate.VisualAcceptance { schema = 1, assetId = Binding.assetId, semanticName = Binding.semanticName, visualAccepted = true, status = "accepted", reviewer = "Synthetic fixture author", reviewedUtc = "2026-01-03T00:00:00.0000000+00:00", descriptor = Copy(Binding.descriptor), nativeImport = Copy(Binding.nativeImport), prefab = Copy(Binding.prefab), concept = Gate.Bind("concept.png"), review = Gate.Bind("concept-review.md"), remainingDifferences = Array.Empty<string>(),
            comparisons = Captures.Select(c => new Gate.Comparison { view = c.view, conceptView = c.conceptView, framingReview = "Synthetic framing control; not visual evidence", lightingReview = "Synthetic lighting control; not visual evidence", criteria = Gate.VisualCriteria.Select(aspect => new Gate.Criterion { aspect = aspect, result = "match", observation = "Synthetic parser control only; no actual visual acceptance" }).ToArray() }).ToArray() };
        for (int i = 0; i < Captures.Length; i++) SaveCapture(i);
        Manifest = new Gate.Manifest { schema = 1, bindings = new[] { Binding } };
        SaveReviewAndManifest();
    }
    public void SetRider()
    {
        Binding.kind = "rider"; Binding.semanticName = "RB_P08_Rider_00"; Review.semanticName = Binding.semanticName; descriptor.assets[0].kind = "rider"; Save("descriptor.json", descriptor);
        Binding.descriptor = Gate.Bind("descriptor.json"); Review.descriptor = Copy(Binding.descriptor);
        Native.descriptorSha256 = Binding.descriptor.sha256; Native.inputs[0] = Copy(Binding.descriptor); Native.assets[0].kind = "rider"; Native.assets[0].rigValid = true;
        foreach (var capture in Captures) capture.descriptor = Copy(Binding.descriptor);
        SaveNative(); SaveReviewAndManifest();
    }
    public void SaveNative()
    {
        Save("native-import.json", Native); Binding.nativeImport = Gate.Bind("native-import.json"); Review.nativeImport = Copy(Binding.nativeImport);
        for (int i = 0; i < Captures.Length; i++) { Captures[i].nativeImport = Copy(Binding.nativeImport); SaveCapture(i); }
    }
    public void SaveCapture(int index) { Save(Captures[index].view + ".capture.json", Captures[index]); Review.comparisons[index].capture = Gate.Bind(Captures[index].view + ".capture.json"); }
    public void SaveReviewAndManifest() { Save("acceptance.json", Review); Binding.acceptance ??= new Gate.FileRef { path = "acceptance.json" }; Binding.acceptance.sha256 = Gate.Bind("acceptance.json").sha256; Save(ManifestPath, Manifest); }
    public string PathOf(string path) => System.IO.Path.Combine(Root, path);
    private void Save(string path, object value) => Write(path, Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value, json)));
    private void Write(string path, byte[] bytes) { Directory.CreateDirectory(System.IO.Path.GetDirectoryName(PathOf(path))); File.WriteAllBytes(PathOf(path), bytes); }
    private static Gate.FileRef Copy(Gate.FileRef value) => new Gate.FileRef { path = value.path, sha256 = value.sha256 };
    public void Dispose()
    {
        string actual = System.IO.Path.GetFullPath(Root), parent = System.IO.Path.GetFullPath(System.IO.Path.GetTempPath()).TrimEnd(System.IO.Path.DirectorySeparatorChar) + System.IO.Path.DirectorySeparatorChar;
        if (actual.StartsWith(parent, StringComparison.OrdinalIgnoreCase) && System.IO.Path.GetFileName(actual).StartsWith("rb-promotion-contract-", StringComparison.Ordinal)) Directory.Delete(actual, true);
    }
    private static byte[] Png(int seed)
    {
        // Valid deterministic test PNGs; never production captures or generated concept assets.
        using var output = new MemoryStream(); output.Write(new byte[] {137,80,78,71,13,10,26,10});
        byte[] header = new byte[13]; Put(header, 0, 640); Put(header, 4, 360); header[8] = 8; header[9] = 2; Chunk(output, "IHDR", header);
        using var compressed = new MemoryStream();
        using (var z = new ZLibStream(compressed, CompressionLevel.Fastest, true))
        {
            var random = new Random(seed); byte[] row = new byte[640 * 3 + 1];
            for (int y = 0; y < 360; y++) { random.NextBytes(row.AsSpan(1)); row[0] = 0; z.Write(row); }
        }
        Chunk(output, "IDAT", compressed.ToArray()); Chunk(output, "IEND", Array.Empty<byte>()); return output.ToArray();
    }
    private static void Chunk(Stream target, string name, byte[] bytes)
    {
        byte[] size = new byte[4]; Put(size, 0, bytes.Length); target.Write(size); byte[] type = Encoding.ASCII.GetBytes(name); target.Write(type); target.Write(bytes);
        uint crc = 0xffffffff; foreach (byte value in type.Concat(bytes)) { crc ^= value; for (int bit = 0; bit < 8; bit++) crc = (crc >> 1) ^ ((crc & 1) != 0 ? 0xedb88320u : 0); }
        Put(size, 0, unchecked((int)(crc ^ 0xffffffff))); target.Write(size);
    }
    private static void Put(byte[] bytes, int offset, int value) { bytes[offset] = (byte)(value >> 24); bytes[offset + 1] = (byte)(value >> 16); bytes[offset + 2] = (byte)(value >> 8); bytes[offset + 3] = (byte)value; }
}
