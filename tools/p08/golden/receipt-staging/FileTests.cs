using System.IO.MemoryMappedFiles;
using System.Text;
using System.Text.Json;
using RacingBois.Authoring.Editor;

string root = Path.Combine(Path.GetTempPath(), "rb-atomic-receipt-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
var results = new List<object>();
void Need(bool value, string message) { if (!value) throw new Exception(message); }
void Test(string name, Action action)
{
    try { action(); results.Add(new { name, passed = true }); }
    catch (Exception error) { results.Add(new { name, passed = false, failure = error.ToString() }); Environment.ExitCode = 1; }
}
string FileOf(string name) => Path.Combine(root, name + ".json");
try
{
    Test("first receipt writes complete UTF8 without BOM", () =>
    {
        string path = FileOf("first"), json = "{\"passed\":false,\"message\":\"giữ nguyên\"}";
        GoldenReceiptFiles.WriteAtomic(path, json);
        Need(File.ReadAllBytes(path).SequenceEqual(new UTF8Encoding(false).GetBytes(json)), "Byte encoding changed");
        using var document = JsonDocument.Parse(File.ReadAllBytes(path)); Need(document.RootElement.GetProperty("passed").ValueKind == JsonValueKind.False, "JSON not complete");
    });
    Test("ordinary replacement swaps the whole receipt", () =>
    {
        string path = FileOf("replace"); GoldenReceiptFiles.WriteAtomic(path, "{\"old\":true}");
        GoldenReceiptFiles.WriteAtomic(path, "{\"new\":true,\"longer\":\"payload\"}");
        Need(File.ReadAllText(path) == "{\"new\":true,\"longer\":\"payload\"}", "New bytes missing");
    });
    Test("mapped old reader retains old bytes while atomic publication succeeds", () =>
    {
        string path = FileOf("mapped"), old = "{\"passed\":false,\"value\":\"old\"}";
        GoldenReceiptFiles.WriteAtomic(path, old);
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        using var map = MemoryMappedFile.CreateFromFile(stream, null, 0, MemoryMappedFileAccess.Read, HandleInheritability.None, true);
        using var view = map.CreateViewStream(0, 0, MemoryMappedFileAccess.Read);
        GoldenReceiptFiles.WriteAtomic(path, "{\"passed\":true,\"failure\":\"\",\"value\":\"new complete payload\"}");
        byte[] previous = new byte[Encoding.UTF8.GetByteCount(old)]; view.ReadExactly(previous);
        Need(Encoding.UTF8.GetString(previous) == old, "Mapped reader lost its prior view");
        using var document = JsonDocument.Parse(File.ReadAllBytes(path)); Need(document.RootElement.GetProperty("value").GetString() == "new complete payload", "Publication incomplete");
    });
    Test("exclusive reader failure never truncates prior receipt or leaks temporary", () =>
    {
        string path = FileOf("locked"), old = "{\"old\":\"retained\"}"; GoldenReceiptFiles.WriteAtomic(path, old);
        using (var blocker = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            bool failed = false;
            try { GoldenReceiptFiles.WriteAtomic(path, "{\"replacement\":true}"); }
            catch (IOException) { failed = true; }
            catch (UnauthorizedAccessException) { failed = true; }
            if (OperatingSystem.IsWindows()) Need(failed, "Expected Windows exclusive sharing rejection");
            if (failed)
            {
                byte[] bytes = new byte[Encoding.UTF8.GetByteCount(old)]; blocker.ReadExactly(bytes);
                Need(Encoding.UTF8.GetString(bytes) == old, "Failure altered mapped/open old bytes");
            }
        }
        Need(!Directory.GetFiles(root, "*.tmp").Any(), "Owned temp file leaked");
    });
    Test("directory collision preserves directory and removes only owned temporary", () =>
    {
        string path = FileOf("directory"); Directory.CreateDirectory(path); bool failed = false;
        try { GoldenReceiptFiles.WriteAtomic(path, "{}"); } catch (IOException) { failed = true; }
        Need(failed && Directory.Exists(path) && !Directory.EnumerateFileSystemEntries(path).Any(), "Collision changed destination");
        Need(!Directory.GetFiles(root, "*.tmp").Any(), "Owned temp file leaked");
    });
    Test("positive import requires both success bits and empty failure", () =>
    {
        Need(GoldenReceiptFiles.ImportSucceeded(true, true, ""), "Empty successful import rejected");
        Need(GoldenReceiptFiles.ImportSucceeded(true, true, null), "Legacy null successful failure rejected");
        Need(!GoldenReceiptFiles.ImportSucceeded(false, true, ""), "Failed operation accepted");
        Need(!GoldenReceiptFiles.ImportSucceeded(true, false, ""), "Unbound operation accepted");
        Need(!GoldenReceiptFiles.ImportSucceeded(true, true, "IOException: Win32 IO returned 1224"), "Contradiction accepted");
        Need(!GoldenReceiptFiles.ImportSucceeded(true, true, " "), "Nonempty failure accepted");
    });
    Test("actual retained contradictory native artifact is rejected unchanged", () =>
    {
        string path = Path.Combine(Directory.GetCurrentDirectory(), "docs/p08/golden/unity/import-b89d27372abd44b6a0d80e4528ec1c70.json");
        byte[] before = File.ReadAllBytes(path); using var document = JsonDocument.Parse(before); var row = document.RootElement;
        Need(!GoldenReceiptFiles.ImportSucceeded(row.GetProperty("passed").GetBoolean(), row.GetProperty("sourceBindingPassed").GetBoolean(), row.GetProperty("failure").GetString()), "Actual contradictory artifact accepted");
        Need(before.SequenceEqual(File.ReadAllBytes(path)), "Historical receipt changed");
    });
    Console.WriteLine(JsonSerializer.Serialize(new { passed = Environment.ExitCode == 0, tests = results, nativeImportRun = false, scope = "Real filesystem/mapped-reader controls and import-status predicate only. No Unity import or visual acceptance." }, new JsonSerializerOptions { WriteIndented = true }));
}
finally
{
    string expected = Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
    string owned = Path.GetFullPath(root);
    if (owned.StartsWith(expected, StringComparison.OrdinalIgnoreCase) && Path.GetFileName(owned).StartsWith("rb-atomic-receipt-", StringComparison.Ordinal)) Directory.Delete(owned, true);
}
