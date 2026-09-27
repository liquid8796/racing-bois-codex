# Native music lifecycle probe v4

This is a probe-only correction. Production remains exactly the reviewed v3
director, SHA256
`eb7ad87bd9e73c47408fd4abac7290312edd697fdecc3944583c11818570cdc7`.
There is no runtime candidate, installer, scene or Assets edit in this stage.

The failed v3 receipt remains unchanged at
`docs/p08/media/native-music-lifecycle-v3-20260928.json`. Its direct UnPause
negative assumed a never-paused source, but public P08 Pause had already run
before clip assignment. The observed native UnPause start invalidated that test
premise; it was not a proven product failure. That assertion is not counted as
passed, and its raw failure is retained.

V4 records direct UnPause behavior on two separately owned fresh AudioSources:
one never paused, one paused before assigning its streamed OGG. Neither has a
required isPlaying truth value. Their observations are separate from the 26
functional product assertions. Each isolated source/clip is stopped and released
before touching the production director. Public lifecycle cases never directly
call Play/Pause/UnPause/Stop on the director's private AudioSource.

The two inapplicable direct-source assertions from v3 are removed from the
product gate and replaced by two actual seek requirements: pending Seek is
applied when a paused load completes, and Seek on the loaded paused clip sets its
requested position. Ready Resume must preserve that position. Existing finite
end, same-ID/Resume replay, paused playhead, loop/listener behavior, gesture
idempotence, error retention, source binding and resource cleanup requirements
remain. Functional expectations are not relaxed.

## Root execution

```powershell
python tools/p08/media/native-music-v4-staging/preflight.py
```

The preflight binds the exact installed production source/meta/assemblies,
unchanged v3 source, preserved failed receipt, short OGG, native Unity references
and all helper sources. Managed compilation and five serializer groups do not
prove playback.

Root alone opens its preserved quiet Play mode scene and loads the new DLL once:

`bin/ProbeCompile/netstandard2.1/RacingBois.NativeMusic.ProbeV4.dll`

Type: `RacingBois.NativeMusicChecksV4.NativeMusicProbe`.
Call `Start("docs/p08/media/native-music-lifecycle-v4-20260928.json")`, then
`Snapshot()` for progress. The receipt must be new. Before retrying any reflected
tool call, inspect the existing receipt/Snapshot and unwrap all InnerException
layers. `Abort()` or leaving Play mode releases owned resources and restores
listener pause. Failure cleanup may report clips still pending Unity's deferred
Destroy; such a receipt cannot pass.

A successful receipt requires 26 functional checks, two separately labeled
direct observations, exact source/assembly/fixture stability, all tracked clips
released, all owned GameObjects gone and listener state restored. It establishes
only these native playback lifecycle behaviors. Audible quality, full cinematic
playback, Web playback and release performance remain separate acceptance work.
