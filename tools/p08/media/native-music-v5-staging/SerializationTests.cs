using RacingBois.NativeMusicChecksV5;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

int groups = 0;
void Check(bool value, string name) { if (!value) throw new Exception(name); }
var empty = JObject.Parse(ProbeReceipt.Serialize(new Result()));
foreach (string name in new[] { "checks", "readings", "directObservations", "pauseWindows" }) Check(empty[name] is JArray rows && rows.Count == 0, "Missing empty " + name);
groups++;
var source = new Result { failure = "Lỗi \"OGG\"\nD:\\test.ogg", finished = true, passed = false };
source.checks.Add(new Check { name = "x", passed = true }); source.checks.Add(new Check { name = "y", passed = false });
source.readings.Add(new Reading { phase = "paused", status = "error", lastErrorCode = "music-file-unavailable", samples = 123, requestBytes = 5688, requestPresent = false });
source.readings.Add(new Reading { phase = "loading", requestPresent = true, requestResult = "InProgress", elapsed = 2.75 });
source.directObservations.Add(new DirectAudioReading { pauseBeforeClip = true, playingAfterFrame = true, samplesAfterFrame = 480 });
source.audioBefore = new AudioDeviceReading { bufferLength = 1024, bufferCount = 4, outputSampleRate = 48000 };
source.pauseWindows.Add(new PauseWindow { kind = "source", device = source.audioBefore, clipSampleRate = 32000, pitch = 1, maximumClipAdvance = 2731,
    initialSamples = 100, settledSamples = 112, minimumHoldSamples = 112, maximumHoldSamples = 112, requestElapsed = 1, settledElapsed = 1.09, holdFinishedElapsed = 2.3 });
string json = ProbeReceipt.Serialize(source);
var restored = JsonConvert.DeserializeObject<Result>(json);
Check(restored.checks.Count == 2 && restored.readings.Count == 2, "Nested list evidence was omitted");
Check(restored.failure == source.failure && !restored.passed && restored.finished, "Escaped diagnostic/flags lost");
Check(restored.readings[0].lastErrorCode == "music-file-unavailable" && restored.readings[0].samples == 123 && restored.readings[1].elapsed == 2.75, "Native reading fields lost");
Check(restored.directObservations.Count == 1 && restored.directObservations[0].pauseBeforeClip && restored.directObservations[0].playingAfterFrame && restored.directObservations[0].samplesAfterFrame == 480, "Isolated observation changed or lost");
Check(restored.pauseWindows.Count == 1 && restored.pauseWindows[0].maximumClipAdvance == 2731 && restored.pauseWindows[0].settledElapsed == 1.09 && restored.audioBefore.outputSampleRate == 48000, "Device/pause-window evidence lost");
groups++;
foreach (Action<Result> missing in new Action<Result>[] { value => value.checks = null, value => value.readings = null, value => value.directObservations = null, value => value.pauseWindows = null })
{
    var invalid = new Result(); missing(invalid); bool rejected = false;
    try { ProbeReceipt.Serialize(invalid); } catch (ArgumentException) { rejected = true; }
    Check(rejected, "Missing collection accepted"); groups++;
}
var device = new AudioDeviceReading { bufferLength = 1024, bufferCount = 4, outputSampleRate = 48000 };
Check(PauseBudget.ClipSamples(device, 48000, 1) == 4096, "Equal sample-rate queue conversion");
Check(PauseBudget.ClipSamples(device, 24000, 1) == 2048 && PauseBudget.ClipSamples(device, 32000, 1) == 2731 && PauseBudget.ClipSamples(device, 44100, 1) == 3764, "Clip/output-rate conversion and fractional-sample ceiling");
Check(PauseBudget.ClipSamples(device, 48000, .5f) == 2048 && PauseBudget.ClipSamples(device, 48000, 2) == 8192, "Playback pitch conversion");
groups++;
foreach (Action bad in new Action[] { () => PauseBudget.ClipSamples(new AudioDeviceReading(), 48000, 1), () => PauseBudget.ClipSamples(device, 0, 1),
    () => PauseBudget.ClipSamples(device, 48000, float.NaN), () => PauseBudget.ClipSamples(device, 48000, float.PositiveInfinity),
    () => PauseBudget.ClipSamples(new AudioDeviceReading { bufferLength = int.MaxValue, bufferCount = int.MaxValue, outputSampleRate = 1 }, 48000, 1) })
{
    bool rejected = false; try { bad(); } catch (ArgumentException) { rejected = true; }
    Check(rejected, "Unavailable/nonfinite/overflow audio configuration accepted");
}
groups++;
Console.WriteLine($"PASS {groups} CLR serializer and measured-device sample-conversion groups; no Unity or playback acceptance.");
