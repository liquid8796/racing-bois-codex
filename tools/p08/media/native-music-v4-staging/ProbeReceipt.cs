using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace RacingBois.NativeMusicChecksV4
{
    public sealed class Check { public string name; public bool passed; }
    public sealed class DirectAudioReading
    {
        public string scope = "Isolated direct engine observation; no expected UnPause truth value and no product lifecycle assertion.", requestResult, requestError, nativeLoadType;
        public bool pauseBeforeClip, streamBeforeSend, streamBeforeGet, playingBeforeUnPause, playingImmediatelyAfter, playingAfterFrame;
        public int samplesBeforeUnPause, samplesImmediatelyAfter, samplesAfterFrame;
        public ulong requestBytes;
    }
    public sealed class Reading
    {
        public string phase, status, lastErrorCode, loadState, nativeLoadType, requestResult = "", requestError = "", requestUrl = "", requestObservationError = "";
        public double elapsed, position, dspTime;
        public float timeScale;
        public int samples, endedEvents, frame, generation;
        public long responseCode;
        public ulong requestBytes;
        public bool isPlaying, explicitPause, listenerPause, loop, active, requestPresent, requestDone, loadingHandlePresent, ownsValidatedStream;
    }
    public sealed class Result
    {
        public int schema = 4;
        public string startedUtc, finishedUtc, unityVersion, sourceSha256, sourceSha256After, probeSourceSha256, probeSourceSha256After;
        public string serializerSourceSha256, serializerSourceSha256After, jsonAssemblySha256, audioModuleSha256;
        public string runtimeAssemblyPath, runtimeAssemblySha256, runtimeAssemblySha256After, runtimeAssemblyMvid, probeAssemblySha256, fixtureSha256, fixtureSha256After;
        public string failure = "", scope = "Actual installed native AudioSource lifecycle and streamed OGG control probe; silent gain 0. No audible mix, music quality, Web playback or full-game acceptance.";
        public bool finished, passed, listenerPauseRestored, ownedObjectsReleased, nativeLifecycleVerified;
        public int loadedClipCount, releasedClipCount;
        public float clipLength;
        public List<Check> checks = new List<Check>();
        public List<Reading> readings = new List<Reading>();
        public List<DirectAudioReading> directObservations = new List<DirectAudioReading>();
    }
    public static class ProbeReceipt
    {
        // CLR serialization deliberately avoids Unity's native JsonUtility registration of dynamic DLL DTO lists.
        public static string Serialize(Result value)
        {
            if (value == null || value.checks == null || value.readings == null || value.directObservations == null) throw new ArgumentException("Incomplete probe receipt.");
            string json = JsonConvert.SerializeObject(value, Formatting.Indented);
            var parsed = JObject.Parse(json);
            if (!(parsed["checks"] is JArray checks) || checks.Count != value.checks.Count ||
                !(parsed["readings"] is JArray readings) || readings.Count != value.readings.Count ||
                !(parsed["directObservations"] is JArray direct) || direct.Count != value.directObservations.Count)
                throw new InvalidOperationException("Probe receipt lost list evidence during serialization.");
            return json;
        }
    }
}
