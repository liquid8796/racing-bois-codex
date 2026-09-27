using System;
using System.Collections;
using System.IO;
using System.Runtime.InteropServices;
using RacingBois.Client.Application;
using UnityEngine;
using UnityEngine.Networking;

namespace RacingBois.Client.Adapters
{
    /// <summary>One same-origin streamed song. Music is cosmetic and never gates simulation.</summary>
    [DisallowMultipleComponent]
    public sealed class P08MusicDirector : MonoBehaviour
    {
        public const ulong MaximumNativeMusicBytes = 12UL * 1024 * 1024;
        public readonly struct PlaybackState
        {
            public readonly string Id, Url;
            public readonly bool Loop, Paused;
            public readonly float Gain;
            public readonly double Position;
            public PlaybackState(string id, string url, bool loop, bool paused, float gain, double position)
            { Id = id; Url = url; Loop = loop; Paused = paused; Gain = gain; Position = position; }
        }

        [Serializable] private sealed class StreamEvent { public string state = "", code = "", id = ""; }
        public event Action<string> Status;
        public event Action<string> Error;
        public string CurrentId { get; private set; } = "";
        public string CurrentUrl { get; private set; } = "";
        public string CurrentStatus { get; private set; } = "stopped";
        public string LastErrorCode { get; private set; } = "";
        public bool IsPaused => paused;
        public bool IsLooping => loop;
        public float Gain => gain;
        public long LastNativeDownloadedBytes { get; private set; }
        public bool UsesNativeStreamingClip
        {
            get
            {
#if !UNITY_WEBGL || UNITY_EDITOR
                return ownedClip != null && ownedClip.loadType == AudioClipLoadType.Streaming;
#else
                return false;
#endif
            }
        }
        private bool initialized, enabledMix = true, paused, loop, disposed;
        private float gain = .18f, mixGain = 1, ducking = 1;
        private double pendingSeek;
#if !UNITY_WEBGL || UNITY_EDITOR
        private bool unlocked;
        private AudioSource output;
        private AudioClip ownedClip;
        private UnityWebRequest request;
        private Coroutine loading;
        private int generation;
        private Uri contentBase;
#else
        [DllImport("__Internal")] private static extern void RB_MusicInitialize(string receiver);
        [DllImport("__Internal")] private static extern int RB_MusicPlay(string id,string url,int loop,float gain);
        [DllImport("__Internal")] private static extern void RB_MusicMix(int muted,float gain);
        [DllImport("__Internal")] private static extern void RB_MusicPause(int paused);
        [DllImport("__Internal")] private static extern void RB_MusicUnlock();
        [DllImport("__Internal")] private static extern void RB_MusicStop();
        [DllImport("__Internal")] private static extern void RB_MusicDispose(string receiver);
        [DllImport("__Internal")] private static extern double RB_MusicPosition();
        [DllImport("__Internal")] private static extern void RB_MusicSeek(double seconds);
#endif

        public void Play(string id, string sameOriginUrl, bool shouldLoop, float requestedGain)
            => PlayCore(id, sameOriginUrl, shouldLoop, requestedGain, false);
        public void ConfigureContentBase(Uri root)
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            if (CurrentId.Length > 0) throw new InvalidOperationException("Music root cannot change during playback.");
            contentBase = root ?? throw new ArgumentNullException(nameof(root));
#endif
        }
        private void PlayCore(string id, string sameOriginUrl, bool shouldLoop, float requestedGain, bool forceReload)
        {
            string validUrl;
#if UNITY_WEBGL && !UNITY_EDITOR
            bool valid = TryValidateUrl(sameOriginUrl, out validUrl);
#else
            if (contentBase == null) contentBase = DesktopConfiguration.ContentBase();
            bool valid = DesktopMusicUrlRules.TryValidate(sameOriginUrl, contentBase, out validUrl);
#endif
            if (!ValidId(id) || !valid) { Fail("music-url-rejected"); return; }
            EnsureInitialized();
            if (!forceReload && CurrentId == id && CurrentUrl == validUrl && CurrentStatus != "error") { loop = shouldLoop; gain = Volume(requestedGain); ApplyMix(); Resume(); return; }
            Stop(); CurrentId = id; CurrentUrl = validUrl; loop = shouldLoop; gain = Volume(requestedGain); paused = false; pendingSeek = 0;
            Report("loading");
#if UNITY_WEBGL && !UNITY_EDITOR
            if (RB_MusicPlay(id,validUrl,loop?1:0,EffectiveGain())==0) Fail("music-url-rejected");
            ApplyMix();
#else
            int token = ++generation; loading = StartCoroutine(LoadNative(validUrl, token));
#endif
        }

        public void UnlockFromUserGesture()
        {
            EnsureInitialized();
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_MusicUnlock();
#else
            unlocked = true;
            if (!paused && output != null && output.clip != null && !output.isPlaying) output.Play();
#endif
        }
        public void SetMix(bool enabled, float volume) { bool reenabled = !enabledMix && enabled; enabledMix = enabled; mixGain = Volume(volume); ApplyMix(); if (reenabled && CurrentStatus == "error") Retry(); }
        public void SetMuted(bool muted) { enabledMix = !muted; ApplyMix(); }
        public void SetDucking(float multiplier) { ducking = Volume(multiplier); ApplyMix(); }
        public void Retry() { if (CurrentId.Length > 0 && CurrentUrl.Length > 0) PlayCore(CurrentId, CurrentUrl, loop, gain, true); }
        public void Pause()
        {
            paused = true;
#if UNITY_WEBGL && !UNITY_EDITOR
            if(initialized)RB_MusicPause(1);
#else
            if (output != null) output.Pause();
#endif
            if (CurrentId.Length > 0) Report("paused");
        }
        public void Resume()
        {
            paused = false;
#if UNITY_WEBGL && !UNITY_EDITOR
            if(initialized)RB_MusicPause(0);
#else
            if (output != null && output.clip != null && unlocked) { output.UnPause(); Report("playing"); }
#endif
        }
        public PlaybackState CaptureState() => new PlaybackState(CurrentId, CurrentUrl, loop, paused, gain, PositionSeconds());
        public void RestoreState(PlaybackState state)
        {
            if (string.IsNullOrEmpty(state.Id)) { Stop(); return; }
            Play(state.Id, state.Url, state.Loop, state.Gain); Seek(state.Position); if (state.Paused) Pause();
        }
        public void Seek(double seconds)
        {
            pendingSeek = double.IsNaN(seconds) || double.IsInfinity(seconds) ? 0 : Math.Max(0, seconds);
#if UNITY_WEBGL && !UNITY_EDITOR
            if(initialized)RB_MusicSeek(pendingSeek);
#else
            if (output != null && output.clip != null) output.time = Mathf.Min((float)pendingSeek, Mathf.Max(0, output.clip.length - .01f));
#endif
        }
        public double PositionSeconds()
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            return initialized?RB_MusicPosition():0;
#else
            return output != null && output.clip != null ? output.time : 0;
#endif
        }
        public void Stop()
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            if(initialized)RB_MusicStop();
#else
            generation++;
            if (request != null) { request.Abort(); request.Dispose(); request = null; }
            if (loading != null) { StopCoroutine(loading); loading = null; }
            if (output != null) { output.Stop(); output.clip = null; }
            if (ownedClip != null) { Destroy(ownedClip); ownedClip = null; }
#endif
            CurrentId = ""; CurrentUrl = ""; paused = false; pendingSeek = 0; Report("stopped");
        }
        private void EnsureInitialized()
        {
            if (initialized || disposed) return;
            initialized = true;
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_MusicInitialize(gameObject.name);
#else
            var child = new GameObject("P08 streamed music"); child.transform.SetParent(transform, false);
            output = child.AddComponent<AudioSource>(); output.playOnAwake = false; output.spatialBlend = 0; output.priority = 180; output.dopplerLevel = 0; unlocked = true;
#endif
        }
        private static float Volume(float value) => float.IsNaN(value) || float.IsInfinity(value) ? 0 : Mathf.Clamp01(value);
        private float EffectiveGain() => Volume(gain * mixGain * ducking);
        private void ApplyMix()
        {
            if (!initialized) return;
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_MusicMix(enabledMix?0:1,EffectiveGain());
#else
            if (output != null) { output.mute = !enabledMix; output.volume = EffectiveGain(); output.loop = loop; }
#endif
        }
        [UnityEngine.Scripting.Preserve]
        public void OnStreamEvent(string json)
        {
            if (string.IsNullOrEmpty(json) || json.Length > 512) return;
            StreamEvent value;
            try { value = JsonUtility.FromJson<StreamEvent>(json); } catch (ArgumentException) { return; }
            if (value == null || value.id != CurrentId) return;
            if (value.state == "error") Fail(string.IsNullOrEmpty(value.code) ? "music-playback-failed" : value.code);
            else if (value.state == "playing" || value.state == "paused" || value.state == "ended" || value.state == "gesture-required" || value.state == "buffering") Report(value.state);
        }
        private void Report(string state) { CurrentStatus = state; if (state == "playing" || state == "loading" || state == "stopped") LastErrorCode = ""; Status?.Invoke(state); }
        private void Fail(string code) { LastErrorCode = code; Report("error"); Error?.Invoke(code); }
        private static bool ValidId(string id)
        {
            if (string.IsNullOrEmpty(id) || id.Length > 64) return false;
            foreach (char c in id) if (!(c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '-')) return false;
            return true;
        }
        public static bool TryValidateUrl(string value, out string normalized)
        {
            normalized = "";
#if UNITY_WEBGL && !UNITY_EDITOR
            if (string.IsNullOrEmpty(value) || value.Length > 2048 || value.Contains("%") || !Uri.TryCreate(value, UriKind.Absolute, out var uri) ||
                !string.IsNullOrEmpty(uri.UserInfo) || !string.IsNullOrEmpty(uri.Query) || !string.IsNullOrEmpty(uri.Fragment)) return false;
            string file = Path.GetFileName(uri.LocalPath);
            if (!file.EndsWith(".ogg", StringComparison.OrdinalIgnoreCase) || file.Length < 68) return false;
            string hash = file.Substring(file.Length - 68, 64);
            foreach (char c in hash) if (!Uri.IsHexDigit(c)) return false;
            if(!Uri.TryCreate(UnityEngine.Application.absoluteURL,UriKind.Absolute,out var page)||uri.Scheme!=page.Scheme||uri.Authority!=page.Authority||
                !uri.AbsolutePath.StartsWith("/Content/",StringComparison.Ordinal))return false;
            normalized = uri.AbsoluteUri; return true;
#else
            try { return DesktopMusicUrlRules.TryValidate(value, DesktopConfiguration.ContentBase(), out normalized); }
            catch (ArgumentException) { return false; }
            catch (IOException) { return false; }
#endif
        }
#if !UNITY_WEBGL || UNITY_EDITOR
        private IEnumerator LoadNative(string url, int token)
        {
            // Installed files are bounded before Unity allocates a download handler. Remote transfers are checked every frame.
            if (new Uri(url).IsFile)
            {
                long localBytes;
                try { localBytes = new FileInfo(new Uri(url).LocalPath).Length; }
                catch (Exception error) when (error is IOException || error is UnauthorizedAccessException) { loading = null; Fail("music-file-unavailable"); yield break; }
                if (localBytes <= 0 || (ulong)localBytes > MaximumNativeMusicBytes) { loading = null; Fail("music-size-rejected"); yield break; }
            }
            var local = UnityWebRequestMultimedia.GetAudioClip(url, AudioType.OGGVORBIS); request = local;
            // Unity creates a Streaming clip here, not a full-float PCM clip. Never access downloadHandler.data.
            ((DownloadHandlerAudioClip)local.downloadHandler).streamAudio = true;
            local.timeout = 30; var operation = local.SendWebRequest();
            bool oversized = false;
            while (!operation.isDone)
            {
                string advertised = local.GetResponseHeader("Content-Length");
                if (local.downloadedBytes > MaximumNativeMusicBytes || ulong.TryParse(advertised, out var length) && length > MaximumNativeMusicBytes)
                { oversized = true; local.Abort(); break; }
                yield return null;
            }
            if (token != generation) { local.Dispose(); yield break; }
            request = null;
            if (oversized || local.downloadedBytes > MaximumNativeMusicBytes) { local.Dispose(); loading = null; Fail("music-size-rejected"); yield break; }
            if (local.result != UnityWebRequest.Result.Success) { local.Dispose(); loading = null; Fail("music-download-failed"); yield break; }
            LastNativeDownloadedBytes = (long)local.downloadedBytes;
            AudioClip clip;
            try { clip = DownloadHandlerAudioClip.GetContent(local); } catch (Exception) { local.Dispose(); loading = null; Fail("music-decode-failed"); yield break; }
            local.Dispose(); loading = null;
            if (clip == null) { Fail("music-decode-failed"); yield break; }
            if (clip.loadType != AudioClipLoadType.Streaming) { Destroy(clip); Fail("music-streaming-unavailable"); yield break; }
            ownedClip = clip; output.clip = clip; output.loop = loop; ApplyMix(); Seek(pendingSeek);
            Debug.Log("RB_MUSIC_NATIVE_READY Streaming bytes=" + LastNativeDownloadedBytes);
            if (!paused && unlocked) { output.Play(); Report("playing"); }
        }
#endif
        private void OnDestroy()
        {
            Stop(); disposed = true;
#if UNITY_WEBGL && !UNITY_EDITOR
            if(initialized)RB_MusicDispose(gameObject.name);
#endif
            Status = null; Error = null;
        }
    }
}
