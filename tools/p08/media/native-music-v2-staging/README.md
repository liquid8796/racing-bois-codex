# Native music diagnosis v2

The original stage and failed native receipt remain unchanged. The first native
run timed out before an accepted streaming clip appeared. Root independently
reproduced `music-streaming-unavailable` after all 5688 fixture bytes downloaded,
and separately proved `Pause()` overwrote an immediate `music-file-unavailable`
status with `paused` while retaining its error code. The first probe watched only
the status, so it could hide that failure behind a timeout. This is a supported
explanation, not evidence that the first coroutine stopped.

The v1 native `JsonUtility` output also omitted the lists of checks/readings.
V2 uses the installed Unity Newtonsoft CLR library and verifies collection
retention after serialization. Five managed serializer groups cover empty lists,
nested rows, raw numeric values, Unicode/escaped errors, sample arrays/logs and
rejection of null collections. These controls do not establish native playback.

## Changes confined to this new stage

- Independent `EditorApplication.update` runner; it never runs its own coroutine
  on the director being tested.
- Quiet-scene checks include active hidden owners via
  `Resources.FindObjectsOfTypeAll`, filtered to valid runtime scenes.
- Null-clip `timeSamples` reads removed; waits record retained error codes and
  live request/handle/generation/frame/DSP state every 250 ms.
- Four direct UWR observations use streamAudio true/false on both the original
  1.2-second fixture and the actual 416-second production stereo song.
- Each direct transfer records handler flags before send/before content access,
  clip metadata and Unity object/total allocated memory before/after handler
  disposal. Two bounded 32-float `GetData` calls retain their return values, sample
  arrays and synchronous Unity logs. A refusal is diagnostic evidence, not a
  reason to weaken a production guard.
- `P08MusicDirector.cs` contains only an additional native Pause error-retention
  candidate over v1. Web behavior and the loadType streaming guard are unchanged.
  It has not been installed by this stage.

The production long file is read directly, without edits:
`Assets/RacingBois/Art/P08/Audio/Music/RB_P08_freight-of-light.ogg`, SHA256
`42fc4ca272d9a1ee2dcff6365216ba8174b930fdcb4b8eb1c0ed0e6669324c23`.
Its 32 kHz stereo 416-second PCM equivalent is 106496000 float bytes. This
calculated size is not an observed allocation. Unity allocator/object readings
exclude some allocations and include unrelated engine activity; neither they
nor `GetData` alone prove a memory budget or streaming implementation.

## Root-owned next native call

`preflight.py` binds the candidate, probe, serializer, actual DLL references,
fixtures and all managed checks. Load the new DLL only once:

`bin/ProbeCompile/netstandard2.1/RacingBois.NativeMusic.ProbeV2.dll`

Type: `RacingBois.NativeMusicChecksV2.NativeMusicProbe`.

Call `StartTransfers("docs/p08/media/native-music-uwr-v2-20260928.json")`
through reflection while the preserved quiet scene is playing. This requires
the installed v1 director hash and does not require any production installation.
`Snapshot()` returns progress; `Abort()` releases owned requests/clips/objects and
restores listener pause. Exiting Play mode aborts as well. Files must be fresh,
inside the project, outside Assets, with no linked parent directory.

The diagnostic receipt must contain four `transfers` and explicit `checks` and
`readings` arrays. `transfersOnly=true` always means
`nativeLifecycleVerified=false`, even if all four diagnostic transfers succeed.

`Start(newReceiptPath)` is reserved for a later reviewed installation of the v2
Pause candidate. It runs those same direct observations, then 26 lifecycle
checks including immediate file-error retention. The current streaming gate is
expected to reject any clip whose native loadType is not Streaming; this stage
does not bypass it. Root must decide the next runtime change from the actual
direct evidence. No player, Unity call, asset save, source installation or font
mutation is performed by the scripts in this stage.
