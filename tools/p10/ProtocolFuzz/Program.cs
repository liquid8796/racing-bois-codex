using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using RacingBois.Protocol;
using RacingBois.Server.Application.Multiplayer;
using RacingBois.Server.Host;
using RacingBois.Server.Host.Multiplayer;

const int seed = 0x504130;
var random = new Random(seed); var watch = Stopwatch.StartNew(); var checks = new List<object>();
int rejected = 0, mutationCases = 0, randomCases = 0, randomAccepted = 0, failures = 0;
var unexpected = new List<object>();
using var corpus = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
void Check(string name, bool passed) { checks.Add(new { name, passed }); if (!passed) failures++; }
void Reject(string name, byte[] bytes)
{
    mutationCases++; corpus.AppendData(bytes);
    try { MultiplayerJson.Parse(bytes); Check(name, false); }
    catch (JsonException) { rejected++; }
    catch (Exception error) { Check(name + "_unexpected_" + error.GetType().Name, false); }
}
object[] templates = [new MpHello { requestNonce = new string('a', 32), displayName = "Seed rider", freshGuest = true },
    new MpCreateRoom { name = "Seed room" }, new MpJoinRoom { code = "ABCDEF" }, new MpSetReady(), new MpStartRace(),
    new MpLeaveRoom(), new MpReturnToLobby(), new MpListRooms(), new MpGoodbye(), new MpInput(), new MpPing(), new MpAck()];
var unicodeHello = new MpHello { requestNonce = new string('b', 32), displayName = "Đua xe 🏍", freshGuest = true };
Check("valid_vietnamese_and_surrogate_pair_preserved", ((MpHello)MultiplayerJson.Parse(WireJson.Serialize(unicodeHello))).displayName == unicodeHello.displayName);
Reject("invalid_utf8_kind_reproduction", Convert.FromBase64String("eyJyb29tSWQiOiIiLCJraW5kIjoibdJTdGFydCIsInByb3RvY29sVmVyc2lvbiI6NCwic2Vzc2lvbkVwb2NoIjowLCJyZXF1ZXN0SWQiOjB9"));
Reject("unpaired_high_surrogate", Encoding.UTF8.GetBytes("{\"kind\":\"\\uD800\"}"));
Reject("unpaired_low_surrogate", Encoding.UTF8.GetBytes("{\"kind\":\"\\uDC00\"}"));
foreach (object message in templates)
{
    byte[] original = WireJson.Serialize(message); var node = JsonNode.Parse(original)!.AsObject(); string kind = node["kind"]!.GetValue<string>();
    Check(kind + "_valid_roundtrip", MultiplayerJson.Parse(original).GetType() == message.GetType());
    foreach (var property in node.ToArray())
    {
        var missing = node.DeepClone().AsObject(); missing.Remove(property.Key); Reject(kind + "_missing_" + property.Key, Encoding.UTF8.GetBytes(missing.ToJsonString()));
        string raw = Encoding.UTF8.GetString(original); string duplicate = raw[..^1] + "," + JsonSerializer.Serialize(property.Key) + ":" + property.Value!.ToJsonString() + "}";
        Reject(kind + "_duplicate_" + property.Key, Encoding.UTF8.GetBytes(duplicate));
        var wrongType = node.DeepClone().AsObject(); wrongType[property.Key] = new JsonObject { ["unexpected"] = true }; Reject(kind + "_wrong_type_" + property.Key, Encoding.UTF8.GetBytes(wrongType.ToJsonString()));
    }
    foreach (string claim in new[] { "damage", "health", "credits", "reward", "teleport", "speed", "qualified" })
    {
        var injected = node.DeepClone().AsObject(); injected[claim] = int.MaxValue;
        Reject(kind + "_authority_claim_" + claim, Encoding.UTF8.GetBytes(injected.ToJsonString()));
    }
}
for (int i = 0; i < 20000; i++)
{
    byte[] bytes;
    if (i % 2 == 0) { bytes = new byte[random.Next(0, 4097)]; random.NextBytes(bytes); }
    else
    {
        bytes = WireJson.Serialize(templates[random.Next(templates.Length)]);
        for (int j = 0; j < random.Next(1, 9); j++) bytes[random.Next(bytes.Length)] = (byte)random.Next(256);
    }
    randomCases++; corpus.AppendData(bytes);
    try { MultiplayerJson.Parse(bytes); randomAccepted++; }
    catch (JsonException) { rejected++; }
    catch (Exception error) { unexpected.Add(new { index = i, type = error.GetType().Name, error.Message, frameBase64 = Convert.ToBase64String(bytes) }); Check("seeded_parser_unexpected_" + error.GetType().Name, false); break; }
}
Check("seeded_20000_cases_do_not_escape_codec_with_unhandled_exception", randomCases == 20000 && failures == 0);
// Schema-correct adversarial numbers must still be fenced by the authoritative input timeline.
int invalidRanges = 0; var timeline = new InputTimeline();
for (int i = 0; i < 50000; i++)
{
    long tick = i + 1;
    int outside = i % 2 == 0 ? int.MaxValue : int.MinValue;
    var input = new MpInput { sequence = 1, targetTick = tick, throttlePermille = 1000 };
    switch (i % 4) { case 0: input.throttlePermille = outside; break; case 1: input.brakePermille = outside; break; case 2: input.steerPermille = outside; break; default: input.attackSide = outside; break; }
    if (timeline.Add(input, tick - 1) != "input_range") invalidRanges++;
    timeline.Sample(tick);
}
Check("50000_adversarial_integer_inputs_cannot_enter_authority_queue", invalidRanges == 0 && timeline.Count == 0);
var paths = Directory.GetFiles("Packages/com.racingbois.foundation/Runtime", "*.cs", SearchOption.AllDirectories)
    .Concat(Directory.GetFiles("tools/p10/ProtocolFuzz", "*.cs", SearchOption.TopDirectoryOnly))
    .Concat(new[] { "src/Server/RacingBois.Server.Host/WireJson.cs", "src/Server/RacingBois.Server.Host/Multiplayer/MultiplayerJson.cs", "src/Server/RacingBois.Server.Application/Multiplayer/InputTimeline.cs", "tools/p10/ProtocolFuzz/ProtocolFuzz.csproj" });
string output = args.Length == 1 ? args[0] : throw new ArgumentException("An unused report path is required.");
if (File.Exists(output)) throw new IOException("Do not overwrite prior fuzz evidence.");
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
var report = new { schema = 1, generatedUtc = DateTimeOffset.UtcNow, status = failures == 0 ? "PASS" : "FAIL", seed,
    mutationCases, randomCases, randomAccepted, rejected, adversarialAuthorityInputs = 50000, failures, checks, unexpected,
    corpusSha256 = Convert.ToHexString(corpus.GetHashAndReset()).ToLowerInvariant(), elapsedMilliseconds = watch.Elapsed.TotalMilliseconds,
    sources = paths.OrderBy(p => p, StringComparer.Ordinal).Select(path => new { path = path.Replace('\\', '/'), sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() }),
    scope = "Seeded bounded parser mutation and authoritative input-range corpus. Randomly mutated messages may remain schema valid. This is not exhaustive fuzzing, network or full security audit evidence." };
File.WriteAllText(output, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"{report.status}: {mutationCases} schema mutations, {randomCases} seeded frames, 50000 authority range attempts; failures={failures}");
return failures == 0 ? 0 : 1;
