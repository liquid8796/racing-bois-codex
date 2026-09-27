# Native music lifecycle probe v5

Probe only: production remains the reviewed v3 director, SHA256
`eb7ad87bd9e73c47408fd4abac7290312edd697fdecc3944583c11818570cdc7`.
No runtime source, installer, scene, audio setting or Assets edit is included.

The v4 failed receipt is preserved. Its source-Pause sample advanced from 32864
immediately after Pause to 33888 after the hold: exactly 1024 samples. Root's
separate actual device observation records a 1024-sample DSP block, four blocks
and 48000 Hz output/clip rates. Finite end, replay, idempotent unlock and pending
seek had already passed before that assertion failed. This observation supports
asynchronous mixer settlement; it does not justify unlimited drift or a fixed
1024-sample tolerance.

Unity's [GetDSPBufferSize documentation](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/AudioSettings.GetDSPBufferSize.html)
defines the mixer ring as bufferLength times numBuffers sample frames. V5 reads
the actual configuration and computes:

- queue seconds = bufferLength × bufferCount / outputSampleRate;
- allowed source advance = ceiling(queue seconds × clipSampleRate × pitch).

All inputs must be positive and finite, and the bound must fit the native
playhead range. Clip positions use per-channel sample frames, so channel count
does not multiply that position bound. The device configuration is observed at
start/end and throughout both pause phases. It is never modified.

For explicit source Pause, each observed initial-to-settled sample stays within
the calculated ring window. After waiting that window, the playhead must remain
exactly unchanged over one full clip duration. Resume must start at or after
that settled position. The receipt records initial/settled/minimum/maximum
samples, rates/pitch, calculated bounds, phase times and DSP clock readings.

V4 did not reach listener pause, so V5 does not infer a listener allowance from
the source-Pause observation. It records the same initial/settlement/long-hold
telemetry but requires zero listener-pause advance and zero settled drift. A
different actual result remains a failure for investigation.

The other v4 requirements remain: two separately owned direct-UnPause
observations (no expected truth value), public-only product lifecycle calls,
pending/loaded-paused seeks, finite completion, same-ID/Resume replay, loop,
gesture idempotence, native load-error retention and exact resource release.
V5 has 28 functional checks, including separately stated settlement and
long-hold checks. Old failed assertions are not recast as passes.

## Root execution

After the root-owned milestone compilation has settled:

```powershell
python tools/p08/media/native-music-v5-staging/preflight.py
```

Load only the new
`bin/ProbeCompile/netstandard2.1/RacingBois.NativeMusic.ProbeV5.dll`, type
`RacingBois.NativeMusicChecksV5.NativeMusicProbe`. In root's preserved quiet
Play mode scene call
`Start("docs/p08/media/native-music-lifecycle-v5-20260928.json")` once, then
`Snapshot()` for progress. Inspect Snapshot/file existence before retrying a
tool-level invocation, and unwrap InnerException chains. `Abort()` or leaving
Play mode restores listener state and releases owned objects/requests/clips.
The final successful path waits for deferred clip destruction before acceptance.

Managed serializer/sample-rate conversion checks are preflight only. Native
success still requires all 28 checks, both direct observations, both pause
windows, stable device/source/assembly/fixture identities and full cleanup.
Audible quality, full cinematic playback, Web playback and performance budgets
are outside this receipt.
