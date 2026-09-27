# Native finite-music lifecycle candidate

This stage fixes a concrete Windows/Editor defect: a finite streamed song never
reported `ended`, and repeating its ID or resuming after completion called
`UnPause()` on a stopped source, leaving it silent. Pausing while the song loaded
also left a ready clip that `UnPause()` could not start.

The native adapter now keeps one voice state and observes actual `isPlaying`
before detecting completion. Loading, explicit pause, loop, listener pause and
unloaded clips cannot count as finite completion. Ready/ended voices use `Play`;
paused voices use `UnPause`. Repeated requests for an active voice preserve its
playhead. Native unlock is idempotent, starts only a ready pending voice and does
not restart an ended song or emit repeated playing events. Web branches and the
JavaScript bridge retain their existing behavior.

Unity documents that [UnPause does not start a stopped or never-played source](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/AudioSource.UnPause.html),
[isPlaying is false during explicit pause](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/AudioSource-isPlaying.html),
and [listener pause suspends audio and starts new requests paused](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/AudioListener-pause.html).
Those semantics inform the guards; the native probe must still verify them in the
installed Unity 6000.5.7f1 runtime.

## Handoff

Production source before this stage is SHA256
`cdd8b9bcbede475f594d672adee7e55130ab71eea2e88744d66d009abf2c2db5`;
its existing meta is
`bed57dec813e2e651b2e22516ee194be26cbcaa763aa63ef7e7c3278a7341ffe`.
Only `P08MusicDirector.cs` is a production target. Nothing in this stage installs
it automatically, launches Unity or launches a player.

```powershell
python tools/p08/media/native-music-staging/preflight.py
python tools/p08/media/native-music-staging/install.py
# Root only, after review:
python tools/p08/media/native-music-staging/install.py --install
```

`validation.json` binds all compiler inputs before/after, the probe DLL, and the
Editor/Windows/WebGL compilation results. Managed compilation is not native
playback acceptance. The probe has no simulated AudioSource implementation.

## Root-owned native verification

After installing and refreshing the director, root preserves the current clean
scene setup and opens an owned minimal quiet Play mode scene with Camera/Light.
No RaceBootstrap, UIDocument, fonts, test scene asset or probe component asset is
needed. The probe refuses an active music request or existing playing source.

Rebuild the probe against the refreshed project assemblies:

```powershell
dotnet build tools/p08/media/native-music-staging/ProbeCompile.csproj --nologo -v:minimal
```

Load only `bin/ProbeCompile/netstandard2.1/RacingBois.NativeMusic.Probe.dll` into
the running editor, and invoke:

```csharp
RacingBois.NativeMusicChecks.NativeMusicProbe.Start(
    "docs/p08/media/native-music-lifecycle-20260928.json");
```

With a tool that compiles a standalone method body, use reflection to load that
absolute DLL path and call the public static `Start` method. The probe starts a
coroutine on its owned production director and returns immediately. Call
`Snapshot()` to retrieve progress/results. `Abort()` restores listener pause and
releases owned objects if root must interrupt; exiting Play mode also aborts.
Do not reload the probe assembly repeatedly within the same AppDomain.

The probe runs 25 assertions using a real 1.2-second, 48 kHz mono Vorbis stream
loaded through the public music URL path, with gain zero. It directly confirms
the native negative `UnPause` controls, pause during loading, first resume, finite
completion, same-ID replay, resumed replay, explicit pause/playhead preservation,
pause after end, seek to end, multiple loops, loop-off completion, listener pause
both before and during playback, stop during loading, and gesture idempotence.
It records actual positions, sample offsets, `isPlaying`, load states, status
events, runtime assembly SHA/MVID and source/fixture hashes before/after.

Every encountered streamed clip is tracked. A successful receipt requires the
owned GameObject and all tracked clips to be Unity-null after normal stop, plus
the original `AudioListener.pause` value restored. Failure cleanup uses the
director's normal deferred `Destroy` for clips; an interrupted receipt may
therefore record clips pending Unity destruction and must not be marked passed.
No generic scene object or asset cleanup runs. The final successful path waits
after Stop before checking release. Root restores its preserved scene setup
after the probe and verifies source/scene hashes independently.

Fixture SHA256:
`87055f90f631a745db5312e662525cb14c6c72d0e97a80f5c6ca9fb0606c2464`.
It is a locally generated 440 Hz sine, 5688 bytes, created with installed free
FFmpeg (`sine=frequency=440:sample_rate=48000:duration=1.2`, `libvorbis -q:a 2`,
metadata stripped and bitexact flags). It is a test signal, not production music.

Neither the probe nor this patch establishes audible quality, simultaneous
SFX/music mixing, full cinematic playback, memory acceptance or Web playback.
