using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using RacingBois.Client.Bootstrap;
using RacingBois.Gameplay.Definitions;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Process = System.Diagnostics.Process;

namespace RacingBois.Diagnostics.NativeBaseline
{
    [DefaultExecutionOrder(10000)]
    public sealed class NativeBaselineRecorder : MonoBehaviour
    {
        public P06BenchmarkRunner Workload;
        private const int Capacity = 1000000;
        private Frame[] frames;
        private readonly List<Memory> memory = new List<Memory>(700);
        private readonly List<Image> images = new List<Image>(2);
        private readonly FrameTiming[] timing = new FrameTiming[1];
        private ProfilerRecorder gc;
        private Process process;
        private string output, installation, expectedBuildHash, fingerprint;
        private Build build;
        private Binding binding;
        private bool active, finishing, finished, warmupImage, outputOwned;
        private string measurementStartedUtc, measurementFinishedUtc;
        private double began, measured = -1, previous, lastMemory, lastStatus;
        private int count, warnings, errors;
        private long startupWorkingSet, startupPrivateBytes;
        private int memoryReadFailures;
        private int startupMemoryError;
        [Serializable] public sealed class FileRow { public string path, sha256; public long bytes; }
        [Serializable] public sealed class Binding
        { public string sourceFingerprint, unityVersion, sourceScene, route; public int width, height, quality, seconds, warmup, targetFrameRate, vSyncCount; public bool stress; }
        [Serializable] private sealed class Build
        { public bool passed, sourceBindingPassed, editorStateRestored; public string result, sourceFingerprint; public FileRow[] playerFiles; }
        [Serializable] private sealed class WorkloadSummary
        { public string status; public bool editor, measurementCoverageValid, requiredDensityPresentEverySample; public double measuredSeconds; public long measuredSimulationTicks, droppedSimulationTicks; public int frames; }
        private struct Frame
        {
            public double seconds, deltaMs, cpuMs, gpuMs;
            public long tick, measuredTicks, gcBytes;
            public ulong timingTimestamp;
            public int unityFrame, cycle, width, height, quality, riders, traffic, pedestrians, targetFrameRate, vSyncCount;
            public bool focused, cpuAvailable, gpuAvailable, gcAvailable;
        }
        [Serializable] private sealed class Memory
        { public double seconds; public bool processAvailable; public int processError; public long workingSet, privateBytes, unityAllocated, managed, graphicsDriver; }
        [Serializable] private sealed class Image
        { public string path, sha256; public int width, height; public long bytes; }
        [Serializable] private sealed class Receipt
        {
            public int schema = 1, frames, frameCapacity = Capacity, warnings, errors, routeMask, bikeMask, riderMask, targetFrameRate, vSyncCount;
            public bool completed, identityStable, workloadCoveragePassed, timingBudgetPassed, memoryBudgetPassed, releaseAccepted = false, p08Accepted = false;
            public string status, failureCode, startedUtc, finishedUtc, sourceFingerprint, buildReceiptSha256, platform, unityVersion, graphicsApi, graphicsDevice, operatingSystem, workloadSha256, rawSha256, memorySha256;
            public double measuredSeconds, meanFps, p50Ms, p95Ms, maxMs;
            public long peakWorkingSet, peakPrivateBytes;
            public string processMemoryApi = NativeProcessMemory.Api;
            public int processMemoryStructureBytes = NativeProcessMemory.StructureBytes, memoryReadFailures, startupMemoryError;
            public long startupWorkingSet, startupPrivateBytes;
            public Binding binding; public Image[] captures;
            public string scope = "Actual 600-second uncapped Medium1080 native Windows baseline P06 scripted simulation/render/audio/effects throughput and pacing specimen only. No production P08, full-game UI/input/campaign, physical LAN or release acceptance.";
            public string measurement = "Unfiltered chronological LateUpdate wall-clock intervals; observer storage/memory sampling included. Warmup is outside the window. Timing counters may repeat/lag; timestamps retained. Blank counters are unavailable. Graphics-driver allocation is not dedicated GPU residency. Installed-file checks warm OS caches.";
        }
        private IEnumerator Start()
        {
#if UNITY_EDITOR
            yield break;
#else
            try
            {
                var args = Environment.GetCommandLineArgs();
                output = Argument(args, "--rb-baseline-output");
                if (output == null) yield break;
                expectedBuildHash = Argument(args, "--rb-baseline-buildsha"); fingerprint = Argument(args, "--rb-baseline-fingerprint");
                Need(Application.platform == RuntimePlatform.WindowsPlayer && Type.GetType("Mono.Runtime") != null && IntPtr.Size == 8, "windows_x64_mono_required");
                Need(Workload != null && !Workload.AutoStart && !Workload.Running && Workload.Stage != null && Workload.Stage.ViewCamera != null, "fresh_workload_required");
                Need(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null, "actual_graphics_device_required");
                installation = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
                Need(Path.IsPathFullyQualified(output) && !File.Exists(output) && !Directory.Exists(output), "fresh_absolute_output_required");
                output = Path.GetFullPath(output);
                Need(!output.StartsWith(installation + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase), "output_outside_player_required");
                NoLinks(output);
                Need(Hash(Path.Combine(installation, "NativeBaseline.build.json")) == expectedBuildHash, "selected_build_receipt_changed");
                build = JsonUtility.FromJson<Build>(File.ReadAllText(Path.Combine(installation, "NativeBaseline.build.json")));
                binding = JsonUtility.FromJson<Binding>(File.ReadAllText(Path.Combine(installation, "NativeBaseline.binding.json")));
                Need(build.passed && build.sourceBindingPassed && build.editorStateRestored && build.result == "Succeeded" && build.sourceFingerprint == fingerprint
                    && binding.sourceFingerprint == fingerprint && binding.seconds == 600 && binding.warmup == 10 && binding.quality == 1
                    && binding.width == 1920 && binding.height == 1080 && binding.targetFrameRate == -1 && binding.vSyncCount == 0 && Workload.Stress == binding.stress, "build_binding_mismatch");
                process = Process.GetCurrentProcess();
                VerifyPlayerFile(process.MainModule.FileName); VerifyPlayerFile(typeof(P06BenchmarkRunner).Assembly.Location);
                VerifyPlayerFile(typeof(NativeBaselineRecorder).Assembly.Location); VerifyPlayerFile(Path.Combine(installation, "NativeBaseline.binding.json"));
                Directory.CreateDirectory(output); outputOwned = true;
                Need(SystemInfo.graphicsDeviceType == GraphicsDeviceType.Direct3D11, "direct3d11_required");
                Need(NativeProcessMemory.TryRead(out startupWorkingSet, out startupPrivateBytes, out startupMemoryError), "native_process_memory_startup_failed");
                frames = new Frame[Capacity];
                try { gc = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Allocated In Frame", 1); } catch { }
                Application.logMessageReceived += OnLog;
                Application.runInBackground = true;
                Workload.WarmupSeconds = 10; Workload.QualityIndex = 1;
                Workload.BeginNativeDiagnostic();
                Need(Workload.Running && string.IsNullOrEmpty(Workload.Error), "workload_begin_failed");
                began = Time.realtimeSinceStartupAsDouble; active = true;
                WriteStatus("WARMUP");
            }
            catch (Exception error) { Fail(error); }
            yield break;
#endif
        }
        private void LateUpdate()
        {
            if (!active || finishing || finished) return;
            try
            {
                double now = Time.realtimeSinceStartupAsDouble;
                Need(now - began < 700, "native_window_timeout");
                if (!warmupImage && now - began >= 4) { Capture("warmup.png"); warmupImage = true; }
                if (measured < 0 && Workload.IsMeasuring)
                { measured = Workload.MeasurementStarted; previous = measured; lastMemory = measured - 1; measurementStartedUtc = DateTime.UtcNow.AddSeconds(measured - now).ToString("O"); WriteStatus("MEASURING"); }
                if (measured < 0) return;
                Need(count < Capacity, "frame_capacity_exceeded");
                FrameTimingManager.CaptureFrameTimings();
                bool available = FrameTimingManager.GetLatestTimings(1, timing) > 0 && timing[0].frameStartTimestamp > 0;
                bool gcAvailable = gc.Valid && gc.Count > 0;
                frames[count++] = new Frame { seconds = now - measured, deltaMs = (now - previous) * 1000, unityFrame = Time.frameCount,
                    tick = Workload.CurrentTick, measuredTicks = Workload.DiagnosticMeasuredTicks, cycle = Workload.CurrentCycle, width = Screen.width, height = Screen.height, quality = Workload.VisualQuality.Index,
                    riders = Workload.Stage.ActiveRiderCount, traffic = Workload.Stage.ActiveTrafficCount, pedestrians = Workload.Stage.ActivePedestrianCount,
                    targetFrameRate = Application.targetFrameRate, vSyncCount = QualitySettings.vSyncCount,
                    focused = Application.isFocused, cpuAvailable = available && timing[0].cpuFrameTime > 0, gpuAvailable = available && timing[0].gpuFrameTime > 0,
                    cpuMs = available ? timing[0].cpuFrameTime : 0, gpuMs = available ? timing[0].gpuFrameTime : 0,
                    timingTimestamp = available ? timing[0].frameStartTimestamp : 0, gcAvailable = gcAvailable, gcBytes = gcAvailable ? gc.LastValue : 0 };
                previous = now;
                if (now - lastMemory >= 1) { SampleMemory(now - measured); lastMemory = now; }
                if (now - lastStatus >= 10) { WriteStatus("MEASURING"); lastStatus = now; }
                if (Workload.Completed) { measurementFinishedUtc = DateTime.UtcNow.ToString("O"); finishing = true; StartCoroutine(Finish()); }
            }
            catch (Exception error) { Fail(error); }
        }
        private void SampleMemory(double seconds)
        {
            var sample = new Memory { seconds = seconds, unityAllocated = Profiler.GetTotalAllocatedMemoryLong(), managed = GC.GetTotalMemory(false), graphicsDriver = Profiler.GetAllocatedMemoryForGraphicsDriver() };
            sample.processAvailable = NativeProcessMemory.TryRead(out sample.workingSet, out sample.privateBytes, out sample.processError);
            if (!sample.processAvailable) memoryReadFailures++;
            memory.Add(sample);
        }
        private IEnumerator Finish()
        {
            // End-of-window camera proof and disk serialization are excluded from timing.
            Workload.RestoreNativeDiagnosticTiming();
            yield return new WaitForEndOfFrame();
            try
            {
                Capture("completed.png");
                var summary = JsonUtility.FromJson<WorkloadSummary>(Workload.LastReceiptJson);
                Need(summary != null && summary.status == "completed" && !summary.editor && summary.measuredSeconds >= 600, "workload_did_not_complete_native_window");
                WriteRaw();
                string workloadPath = Path.Combine(output, "workload.json"); WriteNew(workloadPath, Workload.LastReceiptJson);
                var ordered = frames.Take(count).Select(x => x.deltaMs).OrderBy(x => x).ToArray();
                bool identity = Hash(Path.Combine(installation, "NativeBaseline.build.json")) == expectedBuildHash;
                VerifyPlayerFile(process.MainModule.FileName); VerifyPlayerFile(typeof(P06BenchmarkRunner).Assembly.Location); VerifyPlayerFile(typeof(NativeBaselineRecorder).Assembly.Location);
                VerifyPlayerFile(Path.Combine(installation, "NativeBaseline.binding.json"));
                double elapsed = frames[count - 1].seconds;
                bool consistent = frames.Take(count).All(x => x.width == binding.width && x.height == binding.height && x.quality == binding.quality
                    && x.targetFrameRate == -1 && x.vSyncCount == 0 && x.riders == (binding.stress ? 16 : 8) && (!binding.stress || x.traffic == 12 && x.pedestrians == 6));
                consistent &= frames.Take(count).Where(x => x.focused).Sum(x => x.deltaMs) / (elapsed * 1000) >= .99;
                var result = new Receipt { completed = true, status = "RECORDED_BASELINE", identityStable = identity,
                    frames = count, warnings = warnings, errors = errors, sourceFingerprint = fingerprint, buildReceiptSha256 = expectedBuildHash,
                    startedUtc = measurementStartedUtc, finishedUtc = measurementFinishedUtc,
                    platform = Application.platform.ToString(), unityVersion = Application.unityVersion, graphicsApi = SystemInfo.graphicsDeviceType.ToString(), graphicsDevice = SystemInfo.graphicsDeviceName, operatingSystem = SystemInfo.operatingSystem,
                    measuredSeconds = elapsed, meanFps = count / elapsed, p50Ms = ordered[(int)Math.Ceiling(count * .5) - 1], p95Ms = ordered[(int)Math.Ceiling(count * .95) - 1], maxMs = ordered[count - 1],
                    peakWorkingSet = memory.Where(x => x.processAvailable).Select(x => x.workingSet).DefaultIfEmpty(0).Max(),
                    peakPrivateBytes = memory.Where(x => x.processAvailable).Select(x => x.privateBytes).DefaultIfEmpty(0).Max(),
                    startupWorkingSet = startupWorkingSet, startupPrivateBytes = startupPrivateBytes, memoryReadFailures = memoryReadFailures, startupMemoryError = startupMemoryError,
                    workloadCoveragePassed = consistent && summary.measurementCoverageValid && summary.requiredDensityPresentEverySample && elapsed >= 600
                        && frames[count - 1].measuredTicks / (elapsed * 60) >= .95,
                    targetFrameRate = binding.targetFrameRate, vSyncCount = binding.vSyncCount, binding = binding, captures = images.ToArray(),
                    routeMask = ProductionContent.AvailableRouteMask, bikeMask = ProductionContent.AvailableBikeArtMask, riderMask = ProductionContent.AvailableCharacterArtMask,
                    workloadSha256 = Hash(workloadPath), rawSha256 = Hash(Path.Combine(output, "frames.csv")), memorySha256 = Hash(Path.Combine(output, "memory.csv")) };
                result.timingBudgetPassed = result.meanFps >= 60 && result.p95Ms <= 20;
                var observedTimes = new System.Collections.Generic.HashSet<double>(frames.Take(count).Select(x => x.seconds));
                bool memoryWindow = memory.Count > 0 && memory[0].seconds <= frames[0].seconds + .000001
                    && elapsed - memory[memory.Count - 1].seconds <= 1 + result.maxMs / 1000 + .001
                    && memory.All(x => observedTimes.Contains(x.seconds))
                    && memory.Skip(1).Select((x, i) => x.seconds - memory[i].seconds).All(x => x >= 1 - .000001);
                result.memoryBudgetPassed = memoryWindow && memory.Count >= 590 && memory.All(x => x.processAvailable) && result.peakWorkingSet > 0 && result.peakWorkingSet <= 2L * 1024 * 1024 * 1024;
                WriteNew(Path.Combine(output, "receipt.json"), JsonUtility.ToJson(result, true)); finished = true; active = false;
                Application.Quit(identity && errors == 0 ? 0 : 2);
            }
            catch (Exception error) { Fail(error); }
        }
        private void WriteRaw()
        {
            using (var writer = new StreamWriter(new FileStream(Path.Combine(output, "frames.csv"), FileMode.CreateNew)))
            {
                writer.WriteLine("index,seconds,frame_ms,unity_frame,tick,cycle,measured_ticks,width,height,quality,target_frame_rate,vsync_count,riders,traffic,pedestrians,focused,timing_timestamp,cpu_ms,gpu_ms,gc_bytes");
                for (int i = 0; i < count; i++)
                {
                    var f = frames[i];
                    writer.WriteLine(FormattableString.Invariant($"{i},{f.seconds:R},{f.deltaMs:R},{f.unityFrame},{f.tick},{f.cycle},{f.measuredTicks},{f.width},{f.height},{f.quality},{f.targetFrameRate},{f.vSyncCount},{f.riders},{f.traffic},{f.pedestrians},{(f.focused ? 1 : 0)},{f.timingTimestamp},{(f.cpuAvailable ? f.cpuMs.ToString("R", CultureInfo.InvariantCulture) : "")},{(f.gpuAvailable ? f.gpuMs.ToString("R", CultureInfo.InvariantCulture) : "")},{(f.gcAvailable ? f.gcBytes.ToString(CultureInfo.InvariantCulture) : "")}"));
                }
            }
            using (var writer = new StreamWriter(new FileStream(Path.Combine(output, "memory.csv"), FileMode.CreateNew)))
            {
                writer.WriteLine("seconds,working_set_bytes,private_bytes,process_error,unity_allocated_bytes,managed_bytes,graphics_driver_bytes");
                foreach (var m in memory) writer.WriteLine(FormattableString.Invariant($"{m.seconds:R},{(m.processAvailable ? m.workingSet.ToString(CultureInfo.InvariantCulture) : "")},{(m.processAvailable ? m.privateBytes.ToString(CultureInfo.InvariantCulture) : "")},{m.processError},{m.unityAllocated},{m.managed},{(m.graphicsDriver > 0 ? m.graphicsDriver.ToString(CultureInfo.InvariantCulture) : "")}"));
            }
        }
        private void Capture(string name)
        {
            var target = RenderTexture.GetTemporary(binding.width, binding.height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            var prior = RenderTexture.active; Texture2D pixels = null;
            try
            {
                var request = new UniversalRenderPipeline.SingleCameraRequest { destination = target };
                Need(RenderPipeline.SupportsRenderRequest(Workload.Stage.ViewCamera, request), "native_camera_request_unavailable");
                RenderPipeline.SubmitRenderRequest(Workload.Stage.ViewCamera, request); RenderTexture.active = target;
                pixels = new Texture2D(binding.width, binding.height, TextureFormat.RGBA32, false, false);
                pixels.ReadPixels(new Rect(0, 0, binding.width, binding.height), 0, 0); pixels.Apply(false, false);
                byte[] png = pixels.EncodeToPNG(); Need(png != null && png.Length > 1000, "native_camera_png_missing");
                var colors = pixels.GetPixels32(); var first = colors[0];
                Need(Enumerable.Range(1, (colors.Length - 1) / 31).Any(i => Math.Abs(colors[i * 31].r - first.r) + Math.Abs(colors[i * 31].g - first.g) + Math.Abs(colors[i * 31].b - first.b) > 20), "native_camera_uniform_pixels");
                string path = Path.Combine(output, name); using (var stream = new FileStream(path, FileMode.CreateNew)) stream.Write(png, 0, png.Length);
                images.Add(new Image { path = name, sha256 = Hash(path), bytes = png.Length, width = binding.width, height = binding.height });
            }
            finally { if (pixels != null) Destroy(pixels); RenderTexture.active = prior; RenderTexture.ReleaseTemporary(target); }
        }
        private void VerifyPlayerFile(string path)
        {
            string relative = Path.GetRelativePath(installation, path).Replace('\\', '/');
            var row = build.playerFiles.SingleOrDefault(x => x.path == relative);
            Need(row != null && Hash(path) == row.sha256 && new FileInfo(path).Length == row.bytes, "loaded_player_bytes_changed");
        }
        private void OnLog(string message, string trace, LogType type)
        { if (type == LogType.Warning) warnings++; if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert) errors++; }
        private void Fail(Exception error)
        {
            active = false; finished = true;
            Workload?.RestoreNativeDiagnosticTiming();
            string code = error is InvalidOperationException && error.Message.All(c => char.IsLetterOrDigit(c) || c == '_') ? error.Message : error.GetType().Name;
            if (outputOwned && output != null && Directory.Exists(output) && !File.Exists(Path.Combine(output, "receipt.json")))
                WriteNew(Path.Combine(output, "receipt.json"), JsonUtility.ToJson(new Receipt { status = "FAILED", failureCode = code, sourceFingerprint = fingerprint, frames = count, errors = errors, warnings = warnings,
                    graphicsApi = SystemInfo.graphicsDeviceType.ToString(), startupWorkingSet = startupWorkingSet, startupPrivateBytes = startupPrivateBytes, startupMemoryError = startupMemoryError }, true));
            Debug.LogError("RB_NATIVE_BASELINE_FAILED " + code); Application.Quit(2);
        }
        private void WriteStatus(string status) => File.WriteAllText(Path.Combine(output, "status.json"), JsonUtility.ToJson(new Status { state = status, frames = count, seconds = measured < 0 ? 0 : Time.realtimeSinceStartupAsDouble - measured }));
        [Serializable] private sealed class Status { public string state; public int frames; public double seconds; }
        private static string Argument(string[] args, string key)
        { int index = Array.IndexOf(args, key); if (index < 0) return null; Need(index + 1 < args.Length && Array.LastIndexOf(args, key) == index, "duplicate_or_missing_argument"); return args[index + 1]; }
        private static void NoLinks(string path)
        { for (string value = path; value != null; value = Path.GetDirectoryName(value)) if ((File.Exists(value) || Directory.Exists(value)) && (File.GetAttributes(value) & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("linked_output_rejected"); }
        private static string Hash(string path) { using (var sha = SHA256.Create()) using (var stream = File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
        private static void WriteNew(string path, string text) { using (var writer = new StreamWriter(new FileStream(path, FileMode.CreateNew))) writer.Write(text + "\n"); }
        private static void Need(bool value, string message) { if (!value) throw new InvalidOperationException(message); }
        private void OnDestroy() { Application.logMessageReceived -= OnLog; gc.Dispose(); process?.Dispose(); }
    }
}
