#if UNITY_STANDALONE_WIN && !UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Profiling;
using Process = System.Diagnostics.Process;
using GameApplication = UnityEngine.Application;

namespace RacingBois.Client.Bootstrap
{
    /// <summary>Opt-in observation of the actual native game. Never injects input or changes game settings.</summary>
    [DisallowMultipleComponent]
    public sealed class DesktopAcceptanceRecorder : MonoBehaviour
    {
        private const int FrameCapacity = 180000;
        private RaceBootstrap bootstrap;
        private Func<bool> online, cinematic, blocked;
        private Func<int> quality;
        private DesktopAcceptanceConfiguration config;
        private Frame[] frames;
        private FrameTiming[] timings = new FrameTiming[1];
        private ProfilerRecorder gcRecorder;
        private Process process;
        private readonly List<FileIdentity> screenshots = new List<FileIdentity>(3);
        private readonly List<Diagnostic> diagnostics = new List<Diagnostic>(32);
        private Receipt receipt;
        private int count, screenshotCount, warnings, errors, statusWrites;
        private double waitingSince, warmupSince = -1, measuringSince = -1, previousFrame, lastStatus, lastMemory, lastCheckpointAdvance;
        private double raceSeconds, movingSeconds, focusedSeconds, expectedDisplaySeconds, uiSeconds, advancingTickSeconds;
        private long lastTick = -1, processWorkingSet, processPrivateBytes, allocatedBytes, managedBytes, graphicsDriverBytes;
        private long maxWorkingSet, maxPrivateBytes, maxAllocatedBytes, maxManagedBytes, maxGraphicsDriverBytes;
        private bool memoryAvailable, running, finishing, finished, disposed;

        public static void TryAttach(RaceBootstrap owner, Func<bool> onlineMode, Func<int> qualityIndex, Func<bool> cinematicPlaying, Func<bool> inputBlocked)
        {
            string[] arguments = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(arguments, "--rb-qa-config");
            if (index < 0) return;
            DesktopAcceptanceRecorder recorder = null;
            try
            {
                if (index + 1 >= arguments.Length || Array.LastIndexOf(arguments, "--rb-qa-config") != index)
                    throw new ArgumentException("One explicit QA config path is required.");
                string path = arguments[index + 1];
                if (!Path.IsPathFullyQualified(path) || !File.Exists(path) || new FileInfo(path).Length > 16384)
                    throw new ArgumentException("Invalid bounded QA config.");
                var configuration = JsonUtility.FromJson<DesktopAcceptanceConfiguration>(File.ReadAllText(path));
                if (configuration == null) throw new ArgumentException("QA config is empty.");
                string installation = Path.GetFullPath(Path.Combine(GameApplication.dataPath, ".."));
                configuration.Validate(installation);
                recorder = owner.gameObject.AddComponent<DesktopAcceptanceRecorder>();
                recorder.Initialize(owner, configuration, onlineMode, qualityIndex, cinematicPlaying, inputBlocked, installation);
            }
            catch (Exception error)
            {
                // Never log a supplied config, raw exception path/body, account or credential.
                Debug.LogError("RB_DESKTOP_QA_CONFIG_REJECTED " + error.GetType().Name);
                if (recorder != null) Destroy(recorder);
            }
        }

        private void Initialize(RaceBootstrap owner, DesktopAcceptanceConfiguration configuration, Func<bool> onlineMode,
            Func<int> qualityIndex, Func<bool> cinematicPlaying, Func<bool> inputBlocked, string installation)
        {
            config = configuration; bootstrap = owner; online = onlineMode; quality = qualityIndex; cinematic = cinematicPlaying; blocked = inputBlocked;
            process = Process.GetCurrentProcess();
            string executable = process.MainModule.FileName;
            string assembly = typeof(RaceBootstrap).Assembly.Location;
            string manifest = Path.Combine(GameApplication.streamingAssetsPath, "Content", "manifest.json");
            if (Hash(config.buildReceiptPath) != config.buildReceiptSha256 || Hash(executable) != config.executableSha256 ||
                Hash(assembly) != config.bootstrapSha256 || Hash(manifest) != config.manifestSha256)
                throw new InvalidDataException("Native QA build identities differ.");
            var build = JsonUtility.FromJson<BuildIdentity>(File.ReadAllText(config.buildReceiptPath));
            if (build == null || build.schema != 1 || !build.passed || !build.sourceBindingPassed || build.result != "Succeeded" ||
                build.target != "StandaloneWindows64" || build.sourceFingerprint != config.sourceFingerprint ||
                build.manifestSha256 != config.manifestSha256 || build.contentHash != GameplayRules.ContentHash)
                throw new InvalidDataException("A matching actual successful native build is required.");
            Directory.CreateDirectory(config.outputDirectory);
            frames = new Frame[FrameCapacity]; // One bounded allocation before warmup, included in process memory.
            try { gcRecorder = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Allocated In Frame", 1); }
            catch (Exception) { gcRecorder = default; }
            receipt = new Receipt
            {
                runId = config.runId, startedUtc = DateTime.UtcNow.ToString("O"), status = "WAITING_FOR_RACE", requestedSeconds = config.durationSeconds,
                warmupSeconds = config.warmupSeconds, buildAttemptId = build.attemptId, buildReceiptSha256 = config.buildReceiptSha256,
                sourceFingerprint = config.sourceFingerprint, executableSha256 = config.executableSha256, bootstrapSha256 = config.bootstrapSha256,
                manifestSha256 = config.manifestSha256, contentHash = GameplayRules.ContentHash, unityBuildGuid = GameApplication.buildGUID,
                unityVersion = GameApplication.unityVersion, productVersion = GameApplication.version, operatingSystem = SystemInfo.operatingSystem,
                processor = SystemInfo.processorType, graphicsDevice = SystemInfo.graphicsDeviceName, graphicsApi = SystemInfo.graphicsDeviceType.ToString(),
                systemMemoryMiB = SystemInfo.systemMemorySize, graphicsMemoryMiB = SystemInfo.graphicsMemorySize,
                keyboardPresent = Keyboard.current != null, gamepadPresent = Gamepad.current != null,
                targetFrameRate = GameApplication.targetFrameRate, vSyncCount = QualitySettings.vSyncCount,
                frameCapacity = FrameCapacity, source = "Actual native RaceBootstrap and UI; observer adds no gameplay input and changes no settings."
            };
            GameApplication.logMessageReceived += OnDiagnostic;
            waitingSince = previousFrame = Time.realtimeSinceStartupAsDouble; running = true;
            WriteStatus(receipt.status);
        }

        private void LateUpdate()
        {
            if (!running || finished || finishing) return;
            try { Observe(); }
            catch (Exception error) { Finish("FAIL", "recorder_" + error.GetType().Name); }
        }

        private void Observe()
        {
            double now = Time.realtimeSinceStartupAsDouble, delta = now - previousFrame; previousFrame = now;
            bool isOnline = online();
            var world = isOnline ? bootstrap.Multiplayer.LatestWorld : bootstrap.Session.LatestWorld;
            var rider = isOnline ? bootstrap.Multiplayer.LocalRider : bootstrap.Session.LocalRider;
            bool scenePlaying = world != null && !cinematic() && !GameplayRules.IsTerminal(rider.Mode) &&
                (isOnline ? bootstrap.Multiplayer.Room != null && bootstrap.Multiplayer.Room.Phase == LobbyPhase.Racing : bootstrap.Session.Status == SessionStatus.Connected && bootstrap.Session.Mode == RaceSessionMode.Local);
            bool ready = world != null && bootstrap.ContentLoader != null && bootstrap.ContentLoader.IsReady(world.CourseIndex);
            bool liveRace = scenePlaying && ready;
            if (measuringSince < 0)
            {
                if (now - waitingSince >= config.raceWaitTimeoutSeconds) { Finish("FAIL", "no_loaded_live_race_before_deadline"); return; }
                if (!liveRace) warmupSince = -1;
                else if (warmupSince < 0) { warmupSince = now; WriteStatus("WARMUP"); }
                if (warmupSince < 0 || now - warmupSince < config.warmupSeconds) return;
                measuringSince = now; previousFrame = lastCheckpointAdvance = now; lastTick = world.Tick; receipt.initialTick = lastTick; SampleMemory(); WriteStatus("MEASURING"); return;
            }
            if (count >= frames.Length) { Finish("FAIL", "raw_frame_capacity_exceeded"); return; }
            if (delta <= 0 || double.IsNaN(delta) || double.IsInfinity(delta)) { Finish("FAIL", "invalid_monotonic_frame_interval"); return; }
            bool memorySample = now - lastMemory >= 1;
            if (memorySample) { SampleMemory(); lastMemory = now; }
            bool timing = FrameTimingManager.GetLatestTimings(1, timings) > 0;
            bool gcAvailable = gcRecorder.Valid && gcRecorder.Count > 0;
            bool uiPresent = bootstrap.Document != null && bootstrap.Document.enabled && bootstrap.Document.rootVisualElement != null && bootstrap.Document.rootVisualElement.panel != null;
            int qualityIndex = quality(); long tick = world == null ? -1 : world.Tick;
            bool expectedDisplay = Screen.width == 1920 && Screen.height == 1080 && qualityIndex == 1;
            bool requestScreenshot = config.captureScreenshots && screenshotCount < 3 &&
                (screenshotCount == 0 || screenshotCount == 1 && now - measuringSince >= 300 || screenshotCount == 2 && now - measuringSince >= 599);
            frames[count++] = new Frame
            {
                seconds = now - measuringSince, frameMilliseconds = delta * 1000, unityFrame = Time.frameCount,
                online = isOnline, liveRace = liveRace, contentReady = ready, contentLoading = bootstrap.ContentLoader != null && bootstrap.ContentLoader.Busy,
                inputBlocked = blocked(), uiPresent = uiPresent, focused = GameApplication.isFocused, cinematic = cinematic(),
                width = Screen.width, height = Screen.height, screenMode = (int)Screen.fullScreenMode, quality = qualityIndex,
                tick = tick, course = world == null ? -1 : world.CourseIndex, level = world == null ? -1 : world.Level,
                bike = rider.BikeCatalogIndex, character = rider.CharacterCatalogIndex, distanceMeters = rider.LongitudinalMeters, speedMetersPerSecond = rider.SpeedMetersPerSecond,
                peers = world == null ? 0 : world.Riders.Count, traffic = world == null ? 0 : world.Traffic.Count, pedestrians = world == null ? 0 : world.Pedestrians.Count,
                cpuAvailable = timing && timings[0].cpuFrameTime > 0, gpuAvailable = timing && timings[0].gpuFrameTime > 0,
                timingTimestamp = timing ? timings[0].frameStartTimestamp : 0, cpuMilliseconds = timing ? timings[0].cpuFrameTime : 0, gpuMilliseconds = timing ? timings[0].gpuFrameTime : 0,
                gcAvailable = gcAvailable, gcBytes = gcAvailable ? gcRecorder.LastValue : 0, memorySample = memorySample, processMemoryAvailable = memoryAvailable,
                workingSetBytes = processWorkingSet, privateBytes = processPrivateBytes, unityAllocatedBytes = allocatedBytes,
                managedBytes = managedBytes, graphicsDriverBytes = graphicsDriverBytes, screenshotRequested = requestScreenshot
            };
            if (liveRace) raceSeconds += delta;
            if (liveRace && rider.SpeedMetersPerSecond > 1) movingSeconds += delta;
            if (GameApplication.isFocused) focusedSeconds += delta;
            if (expectedDisplay) expectedDisplaySeconds += delta;
            if (uiPresent) uiSeconds += delta;
            if (liveRace && tick > lastTick) lastCheckpointAdvance = now;
            if (liveRace && now - lastCheckpointAdvance <= .25) advancingTickSeconds += delta;
            lastTick = tick;
            if (requestScreenshot)
            {
                string name = "frame-" + (++screenshotCount).ToString("D2", CultureInfo.InvariantCulture) + ".png";
                screenshots.Add(new FileIdentity { path = name }); ScreenCapture.CaptureScreenshot(Path.Combine(config.outputDirectory, name));
            }
            if (now - lastStatus >= 30) { lastStatus = now; WriteStatus("MEASURING"); }
            if (now - measuringSince >= config.durationSeconds) { finishing = true; StartCoroutine(CompleteAfterScreenshots()); }
        }

        private IEnumerator CompleteAfterScreenshots()
        {
            double deadline = Time.realtimeSinceStartupAsDouble + 5;
            while (screenshots.Exists(file => !File.Exists(Path.Combine(config.outputDirectory, file.path))) && Time.realtimeSinceStartupAsDouble < deadline)
                yield return null;
            Finish("RECORDED", "");
        }

        private void SampleMemory()
        {
            allocatedBytes = Profiler.GetTotalAllocatedMemoryLong(); managedBytes = GC.GetTotalMemory(false);
            graphicsDriverBytes = Profiler.GetAllocatedMemoryForGraphicsDriver();
            try { process.Refresh(); processWorkingSet = process.WorkingSet64; processPrivateBytes = process.PrivateMemorySize64; memoryAvailable = true; }
            catch (Exception) { memoryAvailable = false; processWorkingSet = processPrivateBytes = 0; }
            maxWorkingSet = Math.Max(maxWorkingSet, processWorkingSet); maxPrivateBytes = Math.Max(maxPrivateBytes, processPrivateBytes);
            maxAllocatedBytes = Math.Max(maxAllocatedBytes, allocatedBytes); maxManagedBytes = Math.Max(maxManagedBytes, managedBytes); maxGraphicsDriverBytes = Math.Max(maxGraphicsDriverBytes, graphicsDriverBytes);
        }

        private void Finish(string status, string error)
        {
            if (finished || receipt == null) return;
            finished = true; running = false;
            GameApplication.logMessageReceived -= OnDiagnostic;
            receipt.completedUtc = DateTime.UtcNow.ToString("O"); receipt.frames = count; receipt.failureCode = error;
            receipt.measuredSeconds = count > 0 ? frames[count - 1].seconds : 0;
            receipt.raceCoverage = Ratio(raceSeconds); receipt.movingCoverage = Ratio(movingSeconds); receipt.focusCoverage = Ratio(focusedSeconds);
            receipt.expectedDisplayCoverage = Ratio(expectedDisplaySeconds); receipt.uiCoverage = Ratio(uiSeconds); receipt.advancingTickCoverage = Ratio(advancingTickSeconds);
            receipt.warnings = warnings; receipt.errors = errors; receipt.diagnostics = diagnostics.ToArray(); receipt.statusWrites = statusWrites + 1;
            receipt.maxWorkingSetBytes = maxWorkingSet; receipt.maxPrivateBytes = maxPrivateBytes; receipt.maxUnityAllocatedBytes = maxAllocatedBytes;
            receipt.maxManagedBytes = maxManagedBytes; receipt.maxGraphicsDriverAllocatedBytes = maxGraphicsDriverBytes;
            if (count > 0)
            {
                var durations = new double[count];
                for (int i = 0; i < count; i++) { durations[i] = frames[i].frameMilliseconds; if (frames[i].cpuAvailable) receipt.cpuTimingFrames++; if (frames[i].gpuAvailable) receipt.gpuTimingFrames++; if (frames[i].gcAvailable) receipt.gcFrames++; }
                Array.Sort(durations); receipt.meanFps = count / receipt.measuredSeconds;
                receipt.frameP50Ms = durations[(int)Math.Ceiling(count * .50) - 1]; receipt.frameP95Ms = durations[(int)Math.Ceiling(count * .95) - 1];
                receipt.frameP99Ms = durations[(int)Math.Ceiling(count * .99) - 1]; receipt.frameMaximumMs = durations[count - 1];
            }
            receipt.coveragePassed = receipt.measuredSeconds >= 600 && count >= 600 && receipt.raceCoverage >= .95 && receipt.movingCoverage >= .80 && receipt.focusCoverage >= .99 && receipt.expectedDisplayCoverage >= .99 && receipt.uiCoverage >= .99 && receipt.advancingTickCoverage >= .95;
            receipt.timingBudgetPassed = receipt.meanFps >= 60 && receipt.frameP95Ms <= 20;
            receipt.memoryBudgetPassed = memoryAvailable && maxWorkingSet > 0 && maxWorkingSet <= 2L * 1024 * 1024 * 1024;
            try
            {
                string csv = Path.Combine(config.outputDirectory, "raw-frames.csv"); WriteFrames(csv);
                receipt.rawFrames = Identify(csv, "raw-frames.csv");
                foreach (var file in screenshots)
                {
                    string path = Path.Combine(config.outputDirectory, file.path);
                    if (File.Exists(path)) { var actual = Identify(path, file.path); file.bytes = actual.bytes; file.sha256 = actual.sha256; }
                    else { receipt.failureCode = "screenshot_not_written"; status = "FAIL"; }
                }
                receipt.screenshots = screenshots.ToArray();
                bool sameBuild = Hash(process.MainModule.FileName) == config.executableSha256 && Hash(typeof(RaceBootstrap).Assembly.Location) == config.bootstrapSha256 &&
                    Hash(Path.Combine(GameApplication.streamingAssetsPath, "Content", "manifest.json")) == config.manifestSha256 && Hash(config.buildReceiptPath) == config.buildReceiptSha256;
                receipt.identityStable = sameBuild;
                receipt.passed = status == "RECORDED" && sameBuild && receipt.coveragePassed && receipt.timingBudgetPassed && receipt.memoryBudgetPassed && warnings == 0 && errors == 0;
                receipt.status = receipt.passed ? "PASS" : status == "INTERRUPTED" ? status : "FAIL";
                File.WriteAllText(Path.Combine(config.outputDirectory, "receipt.json"), JsonUtility.ToJson(receipt, true), new UTF8Encoding(false));
                WriteStatus(receipt.status);
            }
            catch (Exception writeError) { Debug.LogError("RB_DESKTOP_QA_WRITE_FAILED " + writeError.GetType().Name); }
            finally { DisposeResources(); }
        }

        private void WriteFrames(string path)
        {
            using (var output = new StreamWriter(path, false, new UTF8Encoding(false), 65536))
            {
                output.WriteLine("seconds,unity_frame,frame_ms,online,live_race,content_ready,content_loading,input_blocked,ui_present,focused,cinematic,width,height,screen_mode,quality,tick,course,level,bike,character,distance_m,speed_m_s,peers,traffic,pedestrians,timing_timestamp,cpu_ms,gpu_ms,gc_bytes,memory_sample,working_set_bytes,private_bytes,unity_allocated_bytes,managed_bytes,graphics_driver_bytes,screenshot_requested");
                var row = new StringBuilder(640);
                for (int i = 0; i < count; i++)
                {
                    var f = frames[i]; row.Clear();
                    row.Append(FormattableString.Invariant($"{f.seconds:R},{f.unityFrame},{f.frameMilliseconds:R},{Bit(f.online)},{Bit(f.liveRace)},{Bit(f.contentReady)},{Bit(f.contentLoading)},{Bit(f.inputBlocked)},{Bit(f.uiPresent)},{Bit(f.focused)},{Bit(f.cinematic)},{f.width},{f.height},{f.screenMode},{f.quality},{f.tick},{f.course},{f.level},{f.bike},{f.character},{f.distanceMeters:R},{f.speedMetersPerSecond:R},{f.peers},{f.traffic},{f.pedestrians},{f.timingTimestamp},"));
                    row.Append(f.cpuAvailable ? f.cpuMilliseconds.ToString("R", CultureInfo.InvariantCulture) : "").Append(',');
                    row.Append(f.gpuAvailable ? f.gpuMilliseconds.ToString("R", CultureInfo.InvariantCulture) : "").Append(',');
                    row.Append(f.gcAvailable ? f.gcBytes.ToString(CultureInfo.InvariantCulture) : "").Append(',').Append(Bit(f.memorySample)).Append(',');
                    row.Append(f.memorySample && f.processMemoryAvailable ? f.workingSetBytes.ToString(CultureInfo.InvariantCulture) : "").Append(',');
                    row.Append(f.memorySample && f.processMemoryAvailable ? f.privateBytes.ToString(CultureInfo.InvariantCulture) : "").Append(',');
                    row.Append(f.memorySample ? f.unityAllocatedBytes.ToString(CultureInfo.InvariantCulture) : "").Append(',');
                    row.Append(f.memorySample ? f.managedBytes.ToString(CultureInfo.InvariantCulture) : "").Append(',');
                    row.Append(f.memorySample && f.graphicsDriverBytes > 0 ? f.graphicsDriverBytes.ToString(CultureInfo.InvariantCulture) : "").Append(',').Append(Bit(f.screenshotRequested));
                    output.WriteLine(row.ToString());
                }
            }
        }

        private void WriteStatus(string status)
        {
            statusWrites++;
            File.WriteAllText(Path.Combine(config.outputDirectory, "status.json"), JsonUtility.ToJson(new Status
            { runId = config.runId, status = status, utc = DateTime.UtcNow.ToString("O"), frames = count, measuredSeconds = count > 0 ? frames[count - 1].seconds : 0, warnings = warnings, errors = errors }), new UTF8Encoding(false));
        }
        private void OnDiagnostic(string message, string trace, LogType type)
        {
            if (type == LogType.Warning) warnings++;
            else if (type == LogType.Error || type == LogType.Assert || type == LogType.Exception) errors++;
            else return;
            if (diagnostics.Count < 32) diagnostics.Add(new Diagnostic { type = type.ToString(), messageSha256 = HashBytes(Encoding.UTF8.GetBytes(message ?? "")) });
        }
        private double Ratio(double seconds) => receipt.measuredSeconds > 0 ? seconds / receipt.measuredSeconds : 0;
        private void OnApplicationQuit() { if (!finished) Finish("INTERRUPTED", "player_quit_before_completion"); }
        private void OnDestroy() { if (!finished) Finish("INTERRUPTED", "bootstrap_destroyed_before_completion"); DisposeResources(); }
        private void DisposeResources() { if (disposed) return; disposed = true; if (gcRecorder.Valid) gcRecorder.Dispose(); process?.Dispose(); }
        private static int Bit(bool value) => value ? 1 : 0;
        private static string Hash(string path) { using (var input = File.OpenRead(path)) using (var hash = SHA256.Create()) return Hex(hash.ComputeHash(input)); }
        private static string HashBytes(byte[] bytes) { using (var hash = SHA256.Create()) return Hex(hash.ComputeHash(bytes)); }
        private static string Hex(byte[] bytes) => BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant();
        private static FileIdentity Identify(string path, string relative) => new FileIdentity { path = relative, bytes = new FileInfo(path).Length, sha256 = Hash(path) };

        private struct Frame
        {
            public double seconds, frameMilliseconds, cpuMilliseconds, gpuMilliseconds;
            public int unityFrame, width, height, screenMode, quality, course, level, bike, character, peers, traffic, pedestrians;
            public long tick, gcBytes, workingSetBytes, privateBytes, unityAllocatedBytes, managedBytes, graphicsDriverBytes;
            public ulong timingTimestamp; public float distanceMeters, speedMetersPerSecond;
            public bool online, liveRace, contentReady, contentLoading, inputBlocked, uiPresent, focused, cinematic, cpuAvailable, gpuAvailable, gcAvailable, memorySample, processMemoryAvailable, screenshotRequested;
        }
        [Serializable] private sealed class BuildIdentity { public int schema = 0; public bool passed = false, sourceBindingPassed = false; public string result = "", target = "", sourceFingerprint = "", manifestSha256 = "", contentHash = "", attemptId = ""; }
        [Serializable] private sealed class Status { public string runId, status, utc; public int frames, warnings, errors; public double measuredSeconds; }
        [Serializable] private sealed class FileIdentity { public string path, sha256; public long bytes; }
        [Serializable] private sealed class Diagnostic { public string type, messageSha256; }
        [Serializable] private sealed class Receipt
        {
            public int schema = 1; public bool passed, identityStable, coveragePassed, timingBudgetPassed, memoryBudgetPassed, keyboardPresent, gamepadPresent;
            public string runId, status, failureCode, startedUtc, completedUtc, source, buildAttemptId, buildReceiptSha256, sourceFingerprint, executableSha256, bootstrapSha256, manifestSha256, contentHash, unityBuildGuid;
            public string unityVersion, productVersion, operatingSystem, processor, graphicsDevice, graphicsApi;
            public int systemMemoryMiB, graphicsMemoryMiB, requestedSeconds, warmupSeconds, frames, frameCapacity, targetFrameRate, vSyncCount, warnings, errors, statusWrites, cpuTimingFrames, gpuTimingFrames, gcFrames;
            public double measuredSeconds, meanFps, frameP50Ms, frameP95Ms, frameP99Ms, frameMaximumMs, raceCoverage, movingCoverage, focusCoverage, expectedDisplayCoverage, uiCoverage, advancingTickCoverage;
            public long initialTick, maxWorkingSetBytes, maxPrivateBytes, maxUnityAllocatedBytes, maxManagedBytes, maxGraphicsDriverAllocatedBytes;
            public FileIdentity rawFrames; public FileIdentity[] screenshots; public Diagnostic[] diagnostics;
            public string scope = "Actual native 600-second full-game observer. PASS covers only recorded timing/coverage/memory/diagnostic gates, not visual fidelity, input correctness, physical LAN, campaign completeness or release approval.";
            public string sampling = "Raw wall-clock intervals are retained without dropped/outlier filtering. CPU/GPU FrameTiming values can lag and repeat; timing_timestamp identifies the supplied sample. Missing counters are blank in CSV. Process/Unity/managed/driver memory is sampled once per second. Driver allocation is not dedicated GPU residency. Advancing-tick coverage means a live race with a checkpoint advance in the preceding0.25seconds, accounting for20Hz projections. Observer buffer and periodic status writes are included in measurements.";
        }
    }
}
#endif
