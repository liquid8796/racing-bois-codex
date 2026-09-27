using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Client.Bootstrap;

string root = Path.GetFullPath(Path.Combine("_local", "p10", "recorder-policy", Guid.NewGuid().ToString("N")));
Directory.CreateDirectory(root);
string install = Path.Combine(root, "installed"); Directory.CreateDirectory(install);
string build = Path.Combine(root, "build-receipt.json"); File.WriteAllText(build, "{}");
var checks = new List<object>(); int failures = 0;
DesktopAcceptanceConfiguration Fresh() => new() { runId = Guid.NewGuid().ToString("N"), outputDirectory = Path.Combine(root, "output-" + Guid.NewGuid().ToString("N")), buildReceiptPath = build,
    buildReceiptSha256 = new string('a', 64), sourceFingerprint = new string('b', 64), executableSha256 = new string('c', 64), bootstrapSha256 = new string('d', 64), manifestSha256 = new string('e', 64) };
void Test(string name, Action action)
{
    try { action(); checks.Add(new { name, passed = true }); }
    catch (Exception error) { failures++; checks.Add(new { name, passed = false, error = error.GetType().Name }); }
}
void Reject(Action action) { try { action(); } catch (Exception error) when (error is ArgumentException or IOException) { return; } throw new InvalidOperationException("Unsafe QA config accepted"); }
Test("explicit_fresh_external_run_and_full_build_identities_accepted", () => Fresh().Validate(install));
Test("installed_root_and_descendant_cannot_receive_qa_output", () => { foreach (string path in new[] { install, Path.Combine(install, "QA") }) { var c = Fresh(); c.outputDirectory = path; Reject(() => c.Validate(install)); } });
Test("dot_dot_path_cannot_bypass_immutable_install_boundary", () => { var c = Fresh(); c.outputDirectory = Path.Combine(root, "outside", "..", "installed", "QA"); Reject(() => c.Validate(install)); });
Test("sibling_with_installation_name_prefix_is_independent", () => { var c = Fresh(); c.outputDirectory = Path.Combine(root, "installed-other", "QA"); c.Validate(install); });
Test("existing_output_and_file_preserved", () => { var c = Fresh(); Directory.CreateDirectory(c.outputDirectory); Reject(() => c.Validate(install)); c = Fresh(); File.WriteAllText(c.outputDirectory, "preserve"); Reject(() => c.Validate(install)); if (File.ReadAllText(c.outputDirectory) != "preserve") throw new Exception(); });
Test("relative_output_or_receipt_cannot_depend_on_working_directory", () => { var c = Fresh(); c.outputDirectory = "relative"; Reject(() => c.Validate(install)); c = Fresh(); c.buildReceiptPath = "build.json"; Reject(() => c.Validate(install)); });
Test("shortened_duration_or_unbounded_wait_cannot_claim_ten_minutes", () => { foreach (int duration in new[] { 0, 30, 599, 601, int.MaxValue }) { var c = Fresh(); c.durationSeconds = duration; Reject(() => c.Validate(install)); } var longWait = Fresh(); longWait.raceWaitTimeoutSeconds = 1801; Reject(() => longWait.Validate(install)); });
Test("missing_or_oversized_build_receipt_rejected", () => { var c = Fresh(); c.buildReceiptPath = Path.Combine(root, "missing.json"); Reject(() => c.Validate(install)); string large = Path.Combine(root, "oversized.json"); using (var file = File.Create(large)) file.SetLength(8 * 1024 * 1024 + 1); c.buildReceiptPath = large; Reject(() => c.Validate(install)); });
Test("partial_invalid_or_missing_sha_and_invalid_run_identity_rejected", () => { foreach (string value in new[] { "", "sha", new string('a', 63), new string('z', 64) }) { var c = Fresh(); c.sourceFingerprint = value; Reject(() => c.Validate(install)); } var bad = Fresh(); bad.runId = "not-a-run"; Reject(() => bad.Validate(install)); });
string report = args.Length == 1 ? args[0] : throw new ArgumentException("A fresh report path is required.");
if (File.Exists(report)) throw new IOException("Preserve prior receipts.");
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(report))!);
string[] paths = ["Assets/RacingBois/Client/Bootstrap/DesktopAcceptanceConfiguration.cs", "tools/p10/RecorderConfigTests/Program.cs", "tools/p10/RecorderConfigTests/RecorderConfigTests.csproj"];
File.WriteAllText(report, JsonSerializer.Serialize(new { generatedUtc = DateTimeOffset.UtcNow, passed = checks.Count - failures, failed = failures, checks,
    sources = paths.Select(path => new { path, sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() }),
    scope = "Pure opt-in recorder configuration and filesystem-boundary tests; no Unity execution, player performance, visual or input acceptance." }, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"{(failures == 0 ? "PASS" : "FAIL")} recorder policy: {checks.Count - failures}/{checks.Count}");
return failures == 0 ? 0 : 1;
