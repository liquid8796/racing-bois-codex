using RacingBois.NativeMusicChecksV3;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

int groups = 0;
void Check(bool value, string name) { if (!value) throw new Exception(name); }
var empty = JObject.Parse(ProbeReceipt.Serialize(new Result()));
foreach (string name in new[] { "checks", "readings" }) Check(empty[name] is JArray rows && rows.Count == 0, "Missing empty " + name);
groups++;
var source = new Result { failure = "Lỗi \"OGG\"\nD:\\test.ogg", finished = true, passed = false };
source.checks.Add(new Check { name = "x", passed = true }); source.checks.Add(new Check { name = "y", passed = false });
source.readings.Add(new Reading { phase = "paused", status = "error", lastErrorCode = "music-file-unavailable", samples = 123, requestBytes = 5688, requestPresent = false });
source.readings.Add(new Reading { phase = "loading", requestPresent = true, requestResult = "InProgress", elapsed = 2.75 });
string json = ProbeReceipt.Serialize(source);
var restored = JsonConvert.DeserializeObject<Result>(json);
Check(restored.checks.Count == 2 && restored.readings.Count == 2, "Nested list evidence was omitted");
Check(restored.failure == source.failure && !restored.passed && restored.finished, "Escaped diagnostic/flags lost");
Check(restored.readings[0].lastErrorCode == "music-file-unavailable" && restored.readings[0].samples == 123 && restored.readings[1].elapsed == 2.75, "Native reading fields lost");
groups++;
foreach (Action<Result> missing in new Action<Result>[] { value => value.checks = null, value => value.readings = null })
{
    var invalid = new Result(); missing(invalid); bool rejected = false;
    try { ProbeReceipt.Serialize(invalid); } catch (ArgumentException) { rejected = true; }
    Check(rejected, "Missing collection accepted"); groups++;
}
Console.WriteLine($"PASS {groups} CLR serializer evidence groups; no Unity or playback acceptance.");
