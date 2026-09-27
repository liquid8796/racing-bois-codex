using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using RacingBois.Client.Adapters;
using UnityEditor;
using UnityEngine;

namespace RacingBois.NativeMusicChecks
{
    /// <summary>Root-run Play mode probe. Uses a real streamed OGG and the installed production component.</summary>
    public static class NativeMusicProbe
    {
        private const string Stage = "tools/p08/media/native-music-staging/";
        private const string Fixture = "finite-87055f90f631a745db5312e662525cb14c6c72d0e97a80f5c6ca9fb0606c2464.ogg";
        private static Session active;
        private static string last = "";

        public static string Start(string receiptPath)
        {
            if (!EditorApplication.isPlaying || EditorApplication.isPaused) throw new InvalidOperationException("A running, unpaused Play mode context is required.");
            if (active != null) throw new InvalidOperationException("A music probe is already running.");
            if (AudioListener.pause) throw new InvalidOperationException("The caller's listener must be unpaused.");
            foreach (var source in UnityEngine.Object.FindObjectsByType<AudioSource>())
                if (source.isPlaying) throw new InvalidOperationException("An existing AudioSource is playing. Use an otherwise quiet Play mode context.");
            foreach (var music in UnityEngine.Object.FindObjectsByType<P08MusicDirector>())
                if (music.CurrentId.Length != 0) throw new InvalidOperationException("An existing music request is active.");
            string root = Path.GetFullPath(".");
            string output = Path.GetFullPath(receiptPath);
            if (!output.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) ||
                output.StartsWith(Path.Combine(root, "Assets") + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || File.Exists(output))
                throw new InvalidOperationException("Use a new receipt file inside the project, outside Assets.");
            for (var parent = new DirectoryInfo(Path.GetDirectoryName(output)); parent != null; parent = parent.Parent)
                if (parent.Exists && (parent.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("Receipt parents must not be links.");
            string live = Path.Combine(root, "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs");
            string staged = Path.Combine(root, Stage, "P08MusicDirector.cs");
            if (Hash(live) != Hash(staged)) throw new InvalidOperationException("Installed director does not match the reviewed stage.");
            string fixture = Path.Combine(root, Stage, "fixtures", Fixture);
            if (Hash(fixture) != "87055f90f631a745db5312e662525cb14c6c72d0e97a80f5c6ca9fb0606c2464") throw new InvalidOperationException("Fixture hash mismatch.");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            active = new Session(root, output, fixture);
            try { active.Begin(); }
            catch { active.Cleanup(); active = null; throw; }
            return "running: " + output;
        }

        public static string Snapshot() => active == null ? last : JsonUtility.ToJson(active.Receipt, true);

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

        [Serializable] public sealed class Check { public string name; public bool passed; }
        [Serializable] public sealed class Reading
        {
            public string phase, status, loadState;
            public double elapsed, position;
            public int samples, endedEvents;
            public bool isPlaying, explicitPause, listenerPause, loop;
        }
        [Serializable] public sealed class Result
        {
            public int schema = 1;
            public string startedUtc, finishedUtc, unityVersion, sourceSha256, sourceSha256After, probeSourceSha256, probeSourceSha256After;
            public string runtimeAssemblyPath, runtimeAssemblySha256, runtimeAssemblySha256After, runtimeAssemblyMvid, probeAssemblySha256, fixtureSha256, fixtureSha256After;
            public string failure = "", scope = "Actual installed native AudioSource lifecycle and streamed OGG control probe; silent gain 0. No audible mix, music quality, Web playback or full-game acceptance.";
            public bool finished, passed, listenerPauseRestored, ownedObjectsReleased;
            public int loadedClipCount, releasedClipCount;
            public float clipLength;
            public List<Check> checks = new List<Check>();
            public List<Reading> readings = new List<Reading>();
        }

        private sealed class Session
        {
            public readonly Result Receipt = new Result();
            private readonly string root, outputPath, fixture;
            private readonly bool previousListenerPause;
            private readonly double start;
            private GameObject owner;
            private P08MusicDirector director;
            private readonly HashSet<AudioClip> ownedClips = new HashSet<AudioClip>();
            private int ended, playingEvents;
            private string phase = "setup";
            private AudioSource Source => director == null ? null : director.GetComponentInChildren<AudioSource>();

            public Session(string project, string output, string fixturePath)
            {
                root = project; outputPath = output; fixture = fixturePath;
                previousListenerPause = AudioListener.pause; start = Time.realtimeSinceStartupAsDouble;
                var assembly = typeof(P08MusicDirector).Assembly;
                Receipt.startedUtc = DateTime.UtcNow.ToString("O"); Receipt.unityVersion = UnityEngine.Application.unityVersion;
                Receipt.sourceSha256 = Hash(Path.Combine(root, "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs"));
                Receipt.probeSourceSha256 = Hash(Path.Combine(root, Stage, "NativeMusicProbe.cs"));
                Receipt.runtimeAssemblyPath = assembly.Location; Receipt.runtimeAssemblySha256 = Hash(assembly.Location);
                Receipt.runtimeAssemblyMvid = assembly.ManifestModule.ModuleVersionId.ToString();
                Receipt.probeAssemblySha256 = Hash(typeof(NativeMusicProbe).Assembly.Location); Receipt.fixtureSha256 = Hash(fixture);
            }

            public void Begin()
            {
                owner = new GameObject("Native music lifecycle probe " + Guid.NewGuid().ToString("N"));
                owner.hideFlags = HideFlags.HideAndDontSave;
                director = owner.AddComponent<P08MusicDirector>();
                director.ConfigureContentBase(new Uri(Path.GetDirectoryName(fixture) + Path.DirectorySeparatorChar));
                director.Status += OnStatus;
                EditorApplication.playModeStateChanged += PlayModeChanged;
                director.StartCoroutine(Execute());
            }

            private void OnStatus(string state) { if (state == "ended") ended++; if (state == "playing") playingEvents++; Read(); }
            private void Read()
            {
                var source = Source;
                if (source != null && source.clip != null) ownedClips.Add(source.clip);
                Receipt.readings.Add(new Reading { phase = phase, status = director.CurrentStatus,
                    elapsed = Time.realtimeSinceStartupAsDouble - start, position = director.PositionSeconds(), samples = source == null ? 0 : source.timeSamples,
                    isPlaying = source != null && source.isPlaying, explicitPause = director.IsPaused, listenerPause = AudioListener.pause,
                    loop = director.IsLooping, endedEvents = ended, loadState = source == null || source.clip == null ? "none" : source.clip.loadState.ToString() });
            }
            private void Check(bool condition, string name)
            {
                Read(); Receipt.checks.Add(new Check { name = name, passed = condition });
                if (!condition) throw new InvalidOperationException(name);
            }
            private IEnumerator Wait(Func<bool> condition, double seconds, string reason)
            {
                double limit = Time.realtimeSinceStartupAsDouble + seconds;
                while (!condition())
                {
                    if (director.CurrentStatus == "error") throw new InvalidOperationException("Director error: " + director.LastErrorCode);
                    if (Time.realtimeSinceStartupAsDouble > limit) throw new TimeoutException(reason);
                    yield return null;
                }
            }
            private static IEnumerator Delay(double seconds)
            { double until = Time.realtimeSinceStartupAsDouble + seconds; while (Time.realtimeSinceStartupAsDouble < until) yield return null; }
            private bool Playing() => Source != null && Source.isPlaying && Source.timeSamples > 0;
            private bool Ended() => director.CurrentStatus == "ended" && Source != null && !Source.isPlaying;
            private void Play(bool loop = false) => director.Play("native-lifecycle", new Uri(fixture).AbsoluteUri, loop, 0);

            private IEnumerator Cases()
            {
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

            private IEnumerator Execute()
            {
                // Flatten owned subroutines so timeouts and assertions are recorded, not swallowed by Unity's coroutine scheduler.
                var stack = new Stack<IEnumerator>(); stack.Push(Cases());
                while (stack.Count > 0)
                {
                    object yielded = null; bool failed = false;
                    try
                    {
                        var next = stack.Peek();
                        if (!next.MoveNext()) { (next as IDisposable)?.Dispose(); stack.Pop(); continue; }
                        yielded = next.Current;
                        if (yielded is IEnumerator child) { stack.Push(child); continue; }
                    }
                    catch (Exception error) { Receipt.failure = error.GetType().Name + ": " + error.Message; failed = true; }
                    if (failed) break;
                    yield return yielded;
                }
                foreach (var iterator in stack) (iterator as IDisposable)?.Dispose();
                Finish();
            }

            public void Abort()
            {
                if (director != null) director.StopAllCoroutines();
                Finish();
            }

            private void Finish()
            {
                try { Cleanup(); }
                catch (Exception error) { Receipt.failure += " Cleanup " + error.GetType().Name + ": " + error.Message; }
                Receipt.sourceSha256After = Hash(Path.Combine(root, "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs"));
                Receipt.probeSourceSha256After = Hash(Path.Combine(root, Stage, "NativeMusicProbe.cs"));
                Receipt.runtimeAssemblySha256After = Hash(Receipt.runtimeAssemblyPath); Receipt.fixtureSha256After = Hash(fixture);
                Receipt.finishedUtc = DateTime.UtcNow.ToString("O"); Receipt.finished = true;
                Receipt.passed = Receipt.failure.Length == 0 && Receipt.checks.Count == 25 && Receipt.listenerPauseRestored && Receipt.ownedObjectsReleased &&
                    Receipt.sourceSha256 == Receipt.sourceSha256After && Receipt.probeSourceSha256 == Receipt.probeSourceSha256After &&
                    Receipt.runtimeAssemblySha256 == Receipt.runtimeAssemblySha256After && Receipt.fixtureSha256 == Receipt.fixtureSha256After;
                last = JsonUtility.ToJson(Receipt, true); active = null;
                using (var file = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write))
                using (var writer = new StreamWriter(file)) writer.WriteLine(last);
                Debug.Log("RB_NATIVE_MUSIC_PROBE " + (Receipt.passed ? "PASS " : "FAIL ") + outputPath);
            }

            public void Cleanup()
            {
                EditorApplication.playModeStateChanged -= PlayModeChanged;
                try
                {
                    if (director != null) { director.Status -= OnStatus; director.Stop(); }
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
