using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using RacingBois.Client.Adapters;
using UnityEditor;
using UnityEngine;
using UnityEngine.Networking;

namespace RacingBois.NativeMusicChecksV2
{
    /// <summary>Root-run Play mode probe. Uses a real streamed OGG and the installed production component.</summary>
    public static class NativeMusicProbe
    {
        private const string Stage = "tools/p08/media/native-music-v2-staging/";
        private const string FixtureStage = "tools/p08/media/native-music-staging/fixtures/";
        private const string Fixture = "finite-87055f90f631a745db5312e662525cb14c6c72d0e97a80f5c6ca9fb0606c2464.ogg";
        private const string LongFixture = "Assets/RacingBois/Art/P08/Audio/Music/RB_P08_freight-of-light.ogg";
        private static Session active;
        private static string last = "";

        public static string Start(string receiptPath) => StartCore(receiptPath, false);
        public static string StartTransfers(string receiptPath) => StartCore(receiptPath, true);
        private static string StartCore(string receiptPath, bool transfersOnly)
        {
            if (!EditorApplication.isPlaying || EditorApplication.isPaused) throw new InvalidOperationException("A running, unpaused Play mode context is required.");
            if (active != null) throw new InvalidOperationException("A music probe is already running.");
            if (AudioListener.pause) throw new InvalidOperationException("The caller's listener must be unpaused.");
            foreach (var source in Resources.FindObjectsOfTypeAll<AudioSource>())
                if (source.gameObject.scene.IsValid() && source.gameObject.activeInHierarchy && source.isPlaying)
                    throw new InvalidOperationException("An existing AudioSource is playing. Use an otherwise quiet Play mode context.");
            foreach (var music in Resources.FindObjectsOfTypeAll<P08MusicDirector>())
                if (music.gameObject.scene.IsValid() && music.gameObject.activeInHierarchy && music.CurrentId.Length != 0)
                    throw new InvalidOperationException("An existing music request is active, including hidden owners.");
            string root = Path.GetFullPath(".");
            string output = Path.GetFullPath(receiptPath);
            if (!output.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) ||
                output.StartsWith(Path.Combine(root, "Assets") + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || File.Exists(output))
                throw new InvalidOperationException("Use a new receipt file inside the project, outside Assets.");
            for (var parent = new DirectoryInfo(Path.GetDirectoryName(output)); parent != null; parent = parent.Parent)
                if (parent.Exists && (parent.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("Receipt parents must not be links.");
            string live = Path.Combine(root, "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs");
            string staged = Path.Combine(root, transfersOnly ? "tools/p08/media/native-music-staging/" : Stage, "P08MusicDirector.cs");
            if (Hash(live) != Hash(staged)) throw new InvalidOperationException("Installed director does not match the reviewed stage.");
            string fixture = Path.Combine(root, FixtureStage, Fixture);
            if (Hash(fixture) != "87055f90f631a745db5312e662525cb14c6c72d0e97a80f5c6ca9fb0606c2464") throw new InvalidOperationException("Fixture hash mismatch.");
            string longFixture = Path.Combine(root, LongFixture);
            if (Hash(longFixture) != "42fc4ca272d9a1ee2dcff6365216ba8174b930fdcb4b8eb1c0ed0e6669324c23") throw new InvalidOperationException("Production long fixture hash mismatch.");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            active = new Session(root, output, fixture, longFixture, transfersOnly);
            try { active.Begin(); }
            catch { active.Cleanup(); active = null; throw; }
            return "running: " + output;
        }

        public static string Snapshot() => active == null ? last : ProbeReceipt.Serialize(active.Receipt);

        public static void Abort()
        {
            if (active == null) return;
            active.Receipt.failure = "Probe interrupted before completion.";
            active.Abort();
        }

        private static void PlayModeChanged(PlayModeStateChange state)
        { if (state == PlayModeStateChange.ExitingPlayMode) Abort(); }

        private static string Hash(string path)
        { using (var sha = SHA256.Create()) using (var stream = File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }

        private sealed class Session
        {
            public readonly Result Receipt = new Result();
            private readonly string root, outputPath, fixture, longFixture;
            private readonly bool previousListenerPause;
            private readonly double start;
            private GameObject owner;
            private P08MusicDirector director;
            private UnityWebRequest directRequest;
            private readonly HashSet<AudioClip> ownedClips = new HashSet<AudioClip>();
            private readonly HashSet<AudioClip> directClips = new HashSet<AudioClip>();
            private readonly Stack<IEnumerator> routines = new Stack<IEnumerator>();
            private static readonly FieldInfo RequestField = typeof(P08MusicDirector).GetField("request", BindingFlags.Instance | BindingFlags.NonPublic);
            private static readonly FieldInfo LoadingField = typeof(P08MusicDirector).GetField("loading", BindingFlags.Instance | BindingFlags.NonPublic);
            private static readonly FieldInfo GenerationField = typeof(P08MusicDirector).GetField("generation", BindingFlags.Instance | BindingFlags.NonPublic);
            private int ended, playingEvents;
            private string phase = "setup";
            private AudioSource Source => director == null ? null : director.GetComponentInChildren<AudioSource>();

            public Session(string project, string output, string fixturePath, string longFixturePath, bool transfersOnly)
            {
                root = project; outputPath = output; fixture = fixturePath; longFixture = longFixturePath; Receipt.transfersOnly = transfersOnly;
                if (transfersOnly) Receipt.scope = "Direct native UWR streamAudio true/false metadata, bounded GetData and Unity memory observations for short and production-long OGG. No product lifecycle, audible or memory-budget acceptance.";
                previousListenerPause = AudioListener.pause; start = Time.realtimeSinceStartupAsDouble;
                var assembly = typeof(P08MusicDirector).Assembly;
                Receipt.startedUtc = DateTime.UtcNow.ToString("O"); Receipt.unityVersion = UnityEngine.Application.unityVersion;
                Receipt.sourceSha256 = Hash(Path.Combine(root, "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs"));
                Receipt.probeSourceSha256 = Hash(Path.Combine(root, Stage, "NativeMusicProbe.cs"));
                Receipt.serializerSourceSha256 = Hash(Path.Combine(root, Stage, "ProbeReceipt.cs"));
                Receipt.jsonAssemblySha256 = Hash(typeof(Newtonsoft.Json.JsonConvert).Assembly.Location);
                Receipt.audioModuleSha256 = Hash(typeof(AudioClip).Assembly.Location);
                Receipt.runtimeAssemblyPath = assembly.Location; Receipt.runtimeAssemblySha256 = Hash(assembly.Location);
                Receipt.runtimeAssemblyMvid = assembly.ManifestModule.ModuleVersionId.ToString();
                Receipt.probeAssemblySha256 = Hash(typeof(NativeMusicProbe).Assembly.Location); Receipt.fixtureSha256 = Hash(fixture);
                Receipt.longFixtureSha256 = Hash(longFixture);
            }

            public void Begin()
            {
                owner = new GameObject("Native music lifecycle probe " + Guid.NewGuid().ToString("N"));
                owner.hideFlags = HideFlags.HideAndDontSave;
                director = owner.AddComponent<P08MusicDirector>();
                director.ConfigureContentBase(new Uri(Path.GetDirectoryName(fixture) + Path.DirectorySeparatorChar));
                director.Status += OnStatus;
                EditorApplication.playModeStateChanged += PlayModeChanged;
                // The probe scheduler is independent of the director under test. Its Stop/StopCoroutine
                // lifecycle cannot accidentally stop or replace this runner.
                routines.Push(Cases()); EditorApplication.update += Tick;
            }

            private void OnStatus(string state) { if (state == "ended") ended++; if (state == "playing") playingEvents++; Read(); }
            private void Read()
            {
                var source = Source;
                if (source != null && source.clip != null) ownedClips.Add(source.clip);
                var reading = new Reading { phase = phase, status = director.CurrentStatus, lastErrorCode = director.LastErrorCode,
                    elapsed = Time.realtimeSinceStartupAsDouble - start, position = director.PositionSeconds(), samples = source == null || source.clip == null ? 0 : source.timeSamples,
                    isPlaying = source != null && source.isPlaying, explicitPause = director.IsPaused, listenerPause = AudioListener.pause,
                    loop = director.IsLooping, endedEvents = ended, loadState = source == null || source.clip == null ? "none" : source.clip.loadState.ToString(),
                    frame = Time.frameCount, dspTime = AudioSettings.dspTime, timeScale = Time.timeScale, active = director.isActiveAndEnabled && owner.activeInHierarchy };
                try
                {
                    var request = (UnityWebRequest)RequestField.GetValue(director);
                    reading.requestPresent = request != null; reading.loadingHandlePresent = LoadingField.GetValue(director) != null;
                    reading.generation = (int)GenerationField.GetValue(director);
                    if (request != null)
                    {
                        reading.requestDone = request.isDone; reading.requestBytes = request.downloadedBytes; reading.requestResult = request.result.ToString();
                        reading.requestError = request.error ?? ""; reading.requestUrl = request.url; reading.responseCode = request.responseCode;
                    }
                }
                catch (Exception error) { reading.requestObservationError = error.GetType().Name + ": " + error.Message; }
                Receipt.readings.Add(reading);
            }
            private void Check(bool condition, string name)
            {
                Read(); Receipt.checks.Add(new Check { name = name, passed = condition });
                if (!condition) throw new InvalidOperationException(name);
            }
            private IEnumerator Wait(Func<bool> condition, double seconds, string reason)
            {
                double limit = Time.realtimeSinceStartupAsDouble + seconds;
                double nextReading = 0;
                while (!condition())
                {
                    if (Time.realtimeSinceStartupAsDouble >= nextReading) { Read(); nextReading = Time.realtimeSinceStartupAsDouble + .25; }
                    if (director.CurrentStatus == "error" || director.LastErrorCode.Length > 0) throw new InvalidOperationException("Director error: " + director.LastErrorCode);
                    if (Time.realtimeSinceStartupAsDouble > limit) throw new TimeoutException(reason);
                    yield return null;
                }
            }
            private static IEnumerator Delay(double seconds)
            { double until = Time.realtimeSinceStartupAsDouble + seconds; while (Time.realtimeSinceStartupAsDouble < until) yield return null; }
            private bool Playing() => Source != null && Source.isPlaying && Source.timeSamples > 0;
            private bool Ended() => director.CurrentStatus == "ended" && Source != null && !Source.isPlaying;
            private void Play(bool loop = false) => director.Play("native-lifecycle", new Uri(fixture).AbsoluteUri, loop, 0);

            private IEnumerator Transfer(string path, bool stream)
            {
                phase = "direct-uwr-" + (path == fixture ? "short" : "long") + "-" + (stream ? "stream" : "default");
                double began = Time.realtimeSinceStartupAsDouble;
                long allocatedBeforeRequest = UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong();
                directRequest = UnityWebRequestMultimedia.GetAudioClip(new Uri(path).AbsoluteUri, AudioType.OGGVORBIS);
                var handler = (DownloadHandlerAudioClip)directRequest.downloadHandler; handler.streamAudio = stream;
                var reading = new TransferReading { fixtureSha256 = Hash(path), requestedStream = stream,
                    streamBeforeSend = handler.streamAudio, compressedBeforeSend = handler.compressed, unityAllocatedBeforeRequest = allocatedBeforeRequest };
                Receipt.transfers.Add(reading);
                directRequest.timeout = 30; var operation = directRequest.SendWebRequest();
                yield return Wait(() => operation.isDone, 35, "Direct UWR did not finish.");
                reading.elapsedSeconds = Time.realtimeSinceStartupAsDouble - began;
                reading.streamBeforeGet = handler.streamAudio; reading.compressedBeforeGet = handler.compressed;
                reading.result = directRequest.result.ToString(); reading.error = directRequest.error ?? ""; reading.downloadedBytes = directRequest.downloadedBytes;
                AudioClip clip = null;
                if (directRequest.result == UnityWebRequest.Result.Success) clip = DownloadHandlerAudioClip.GetContent(directRequest);
                reading.clipPresentBeforeDispose = clip != null;
                if (clip != null)
                {
                    ownedClips.Add(clip); directClips.Add(clip); reading.loadTypeBeforeDispose = clip.loadType.ToString(); reading.loadStateBeforeDispose = clip.loadState.ToString();
                    reading.length = clip.length; reading.samples = clip.samples; reading.frequency = clip.frequency; reading.channels = clip.channels;
                    reading.memoryBeforeDispose = UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(clip);
                    reading.expectedFloatPcmBytes = (long)clip.samples * clip.channels * sizeof(float);
                    reading.unityAllocatedAfterTransfer = UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong();
                    ReadData(clip, reading, false);
                    reading.memoryAfterGetData = UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(clip);
                }
                directRequest.Dispose(); directRequest = null;
                int frame = Time.frameCount;
                yield return Wait(() => Time.frameCount > frame, 3, "Player frames did not advance after handler disposal.");
                reading.clipPresentAfterDispose = clip != null;
                if (clip != null)
                {
                    reading.loadTypeAfterDispose = clip.loadType.ToString(); reading.loadStateAfterDispose = clip.loadState.ToString();
                    reading.memoryAfterDispose = UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(clip);
                    reading.unityAllocatedAfterDispose = UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong();
                    ReadData(clip, reading, true);
                    UnityEngine.Object.Destroy(clip); directClips.Remove(clip);
                }
            }

            private static void ReadData(AudioClip clip, TransferReading reading, bool afterDispose)
            {
                // Bounded diagnostic only. A refusal is evidence, not an instruction to weaken the streaming gate.
                float[] sample = new float[32]; bool result = false;
                Application.LogCallback capture = (message, stack, type) => reading.getDataLogs.Add(type + ": " + message);
                UnityEngine.Application.logMessageReceived += capture;
                try { result = clip.GetData(sample, 0); }
                catch (Exception error) { reading.getDataLogs.Add(error.GetType().Name + ": " + error.Message); }
                finally { UnityEngine.Application.logMessageReceived -= capture; }
                if (afterDispose) { reading.getDataAfterDispose = result; reading.first32AfterDispose = sample; }
                else { reading.getDataBeforeDispose = result; reading.first32BeforeDispose = sample; }
            }

            private IEnumerator Cases()
            {
                yield return Transfer(fixture, true); yield return Transfer(fixture, false);
                yield return Transfer(longFixture, true); yield return Transfer(longFixture, false);
                yield return Delay(.15);
                if (Receipt.transfersOnly) yield break;
                phase = "immediate-file-error-then-pause";
                string missing = Path.Combine(Path.GetDirectoryName(fixture), "missing-" + new string('0', 64) + ".ogg");
                if (File.Exists(missing)) throw new InvalidOperationException("Negative fixture unexpectedly exists.");
                director.Play("native-missing", new Uri(missing).AbsoluteUri, false, 0);
                bool immediateError = director.CurrentStatus == "error" && director.LastErrorCode == "music-file-unavailable";
                director.Pause();
                Check(immediateError && director.CurrentStatus == "error" && director.LastErrorCode == "music-file-unavailable", "pause-does-not-mask-immediate-load-error");
                director.Stop();
                phase = "pause-during-load";
                Play(); director.Pause();
                yield return Wait(() => director.UsesNativeStreamingClip, 8, "Streamed fixture did not load while paused.");
                Receipt.clipLength = Source.clip.length;
                Check(Receipt.clipLength > 1.1f && Receipt.clipLength < 1.3f, "real-streamed-ogg-duration");
                yield return Delay(Receipt.clipLength + .15);
                Check(director.IsPaused && director.CurrentStatus == "paused" && !Source.isPlaying && ended == 0, "loading-and-never-started-pause-do-not-end");
                phase = "native-unpause-negative-control";
                Source.UnPause(); yield return Delay(.1);
                Check(!Source.isPlaying, "actual-unpause-does-not-start-never-played-source");
                phase = "resume-ready";
                director.Resume(); yield return Wait(Playing, 3, "Resume did not start a freshly loaded clip.");
                Check(director.CurrentStatus == "playing" && !director.IsPaused, "resume-starts-ready-voice");
                yield return Wait(Ended, 4, "Finite clip did not report ended.");
                yield return Delay(.15);
                Check(ended == 1, "finite-end-reported-once");
                phase = "unlock-after-end";
                int playsBefore = playingEvents; director.UnlockFromUserGesture(); yield return Delay(.15);
                Check(!Source.isPlaying && director.CurrentStatus == "ended" && playingEvents == playsBefore && ended == 1, "unrelated-gesture-does-not-replay-ended-voice");
                phase = "native-ended-unpause-negative-control";
                Source.UnPause(); yield return Delay(.1);
                Check(!Source.isPlaying && director.CurrentStatus == "ended", "actual-unpause-does-not-restart-ended-source");

                phase = "same-id-replay";
                AudioClip sameClip = Source.clip; Play();
                yield return Wait(Playing, 3, "Same-ID Play did not restart an ended clip.");
                Check(Source.clip == sameClip && director.CurrentStatus == "playing", "same-id-replays-owned-clip-without-reload");
                yield return Delay(.25);
                int sampleBefore = Source.timeSamples; playsBefore = playingEvents; Play(); director.UnlockFromUserGesture(); director.UnlockFromUserGesture();
                Check(Source.timeSamples >= sampleBefore - 256 && Source.isPlaying && playingEvents == playsBefore, "same-id-and-unlock-do-not-rewind-or-renotify-active-voice");
                yield return Wait(Ended, 4, "Replayed finite clip did not end.");
                Check(ended == 2, "same-id-replay-has-one-new-end");

                phase = "resume-ended";
                director.Resume(); yield return Wait(Playing, 3, "Resume did not restart an ended clip.");
                Check(director.CurrentStatus == "playing", "resume-restarts-ended-voice");
                yield return Delay(.25);
                phase = "ordinary-pause";
                director.Pause(); sampleBefore = Source.timeSamples; int endsBefore = ended;
                yield return Delay(Receipt.clipLength + .15);
                Check(!Source.isPlaying && director.IsPaused && director.CurrentStatus == "paused" && ended == endsBefore, "explicit-pause-does-not-end");
                Check(Math.Abs(Source.timeSamples - sampleBefore) <= 256, "paused-native-playhead-is-retained");
                director.Resume(); yield return Wait(Playing, 3, "Paused source did not resume.");
                Check(Source.timeSamples >= sampleBefore - 256, "unpause-resumes-retained-playhead");
                yield return Wait(Ended, 4, "Resumed finite clip did not end.");
                phase = "pause-after-end";
                director.Pause(); director.Resume(); yield return Wait(Playing, 3, "Pause after end created a phantom resumable voice.");
                Check(director.CurrentStatus == "playing", "pause-after-end-still-restarts");
                director.Seek(Receipt.clipLength - .18);
                yield return Wait(Ended, 4, "Seeked finite clip did not end.");
                Check(director.CurrentStatus == "ended", "seek-near-end-completes");

                phase = "loop";
                Play(true); yield return Wait(Playing, 3, "Loop did not start."); endsBefore = ended;
                yield return Delay(Receipt.clipLength * 2.2);
                Check(Source.isPlaying && Source.loop && director.IsLooping && director.CurrentStatus == "playing" && ended == endsBefore, "loop-survives-multiple-durations-without-end");
                Play(false); yield return Wait(Ended, 4, "Turning loop off did not allow completion.");
                Check(!Source.loop && ended == endsBefore + 1, "same-id-loop-off-eventually-ends");

                phase = "listener-pause-active";
                director.Resume(); yield return Wait(Playing, 3, "Listener fixture did not start."); yield return Delay(.25);
                AudioListener.pause = true; sampleBefore = Source.timeSamples; endsBefore = ended;
                director.Resume();
                yield return Delay(Receipt.clipLength + .15);
                Check(ended == endsBefore && director.CurrentStatus != "ended" && !director.IsPaused, "listener-pause-does-not-false-end");
                Check(Math.Abs(Source.timeSamples - sampleBefore) <= 512, "listener-pause-retains-native-playhead");
                AudioListener.pause = false; yield return Wait(Playing, 3, "Listener unpause did not restore playback.");
                yield return Wait(Ended, 4, "Listener-resumed clip did not end.");
                Check(ended == endsBefore + 1, "listener-unpause-finishes-once");

                phase = "listener-pause-before-load";
                director.Stop(); AudioListener.pause = true; endsBefore = ended; Play();
                yield return Wait(() => director.UsesNativeStreamingClip, 8, "Listener-paused fixture did not load.");
                director.Resume(); yield return Delay(Receipt.clipLength + .15);
                Check(ended == endsBefore && director.CurrentStatus != "ended", "listener-paused-start-does-not-false-end");
                AudioListener.pause = false; yield return Wait(Playing, 3, "Listener-paused start did not begin after unpause.");
                yield return Wait(Ended, 4, "Listener-paused start did not finish.");
                Check(ended == endsBefore + 1, "listener-paused-start-eventually-ends-once");

                phase = "stop-during-load";
                director.Stop(); endsBefore = ended; Play(); director.Stop(); yield return Delay(.3);
                Check(director.CurrentStatus == "stopped" && director.CurrentId.Length == 0 && Source.clip == null && ended == endsBefore, "stop-during-load-does-not-resurrect-or-end");
                Check(Hash(Path.Combine(root, "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs")) == Receipt.sourceSha256, "live-director-source-stable-through-probe");
            }

            private void Tick()
            {
                while (routines.Count > 0)
                {
                    object yielded = null; bool failed = false;
                    try
                    {
                        var next = routines.Peek();
                        if (!next.MoveNext()) { (next as IDisposable)?.Dispose(); routines.Pop(); continue; }
                        yielded = next.Current;
                        if (yielded is IEnumerator child) { routines.Push(child); continue; }
                    }
                    catch (Exception error) { Receipt.failure = error.GetType().Name + ": " + error.Message; failed = true; }
                    if (failed) break;
                    return;
                }
                Finish();
            }

            public void Abort()
            {
                Finish();
            }

            private void Finish()
            {
                try { Cleanup(); }
                catch (Exception error) { Receipt.failure += " Cleanup " + error.GetType().Name + ": " + error.Message; }
                Receipt.sourceSha256After = Hash(Path.Combine(root, "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs"));
                Receipt.probeSourceSha256After = Hash(Path.Combine(root, Stage, "NativeMusicProbe.cs"));
                Receipt.serializerSourceSha256After = Hash(Path.Combine(root, Stage, "ProbeReceipt.cs"));
                Receipt.runtimeAssemblySha256After = Hash(Receipt.runtimeAssemblyPath); Receipt.fixtureSha256After = Hash(fixture);
                Receipt.longFixtureSha256After = Hash(longFixture);
                Receipt.finishedUtc = DateTime.UtcNow.ToString("O"); Receipt.finished = true;
                bool transfersComplete = Receipt.transfers.Count == 4;
                foreach (var transfer in Receipt.transfers) transfersComplete &= transfer.result == "Success" && transfer.clipPresentBeforeDispose && transfer.clipPresentAfterDispose && transfer.downloadedBytes > 0;
                Receipt.passed = Receipt.failure.Length == 0 && transfersComplete && Receipt.checks.Count == (Receipt.transfersOnly ? 0 : 26) && Receipt.listenerPauseRestored && Receipt.ownedObjectsReleased &&
                    Receipt.sourceSha256 == Receipt.sourceSha256After && Receipt.probeSourceSha256 == Receipt.probeSourceSha256After &&
                    Receipt.serializerSourceSha256 == Receipt.serializerSourceSha256After && Receipt.longFixtureSha256 == Receipt.longFixtureSha256After &&
                    Receipt.runtimeAssemblySha256 == Receipt.runtimeAssemblySha256After && Receipt.fixtureSha256 == Receipt.fixtureSha256After;
                Receipt.nativeLifecycleVerified = Receipt.passed && !Receipt.transfersOnly;
                last = ProbeReceipt.Serialize(Receipt); active = null;
                using (var file = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write))
                using (var writer = new StreamWriter(file)) writer.WriteLine(last);
                Debug.Log("RB_NATIVE_MUSIC_PROBE " + (Receipt.passed ? "PASS " : "FAIL ") + outputPath);
            }

            public void Cleanup()
            {
                EditorApplication.playModeStateChanged -= PlayModeChanged;
                EditorApplication.update -= Tick;
                foreach (var iterator in routines) (iterator as IDisposable)?.Dispose(); routines.Clear();
                try
                {
                    try
                    {
                        if (directRequest != null)
                        {
                            try { directRequest.Abort(); }
                            finally { directRequest.Dispose(); directRequest = null; }
                        }
                    }
                    finally
                    {
                        try { foreach (var clip in directClips) if (clip != null) UnityEngine.Object.Destroy(clip); directClips.Clear(); }
                        finally { if (director != null) { director.Status -= OnStatus; director.Stop(); } }
                    }
                }
                finally
                {
                    try { if (owner != null) UnityEngine.Object.DestroyImmediate(owner); }
                    finally
                    {
                        Receipt.loadedClipCount = ownedClips.Count; Receipt.releasedClipCount = 0;
                        foreach (var clip in ownedClips) if (clip == null) Receipt.releasedClipCount++;
                        Receipt.ownedObjectsReleased = owner == null && Receipt.loadedClipCount > 0 && Receipt.releasedClipCount == Receipt.loadedClipCount;
                        AudioListener.pause = previousListenerPause;
                        Receipt.listenerPauseRestored = AudioListener.pause == previousListenerPause;
                    }
                }
            }
        }
    }
}
