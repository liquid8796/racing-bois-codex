# Native music v3: verified streamed ownership and lifecycle

This candidate retains the v1 finite-voice lifecycle and v2 native Pause error
retention, and replaces the wrong downloaded-clip loadType rejection with the
verified download-handler contract. No production source is installed by the
preflight or probe.

## Native evidence for the correction

The frozen actual receipt
`docs/p08/media/native-music-uwr-v2-20260928.json` contains four successful native
UWR observations on Unity 6000.5.7f1: streamAudio true/false for both a short test
OGG and the 416-second production `RB_P08_freight-of-light.ogg`.

All four clips report `DecompressOnLoad`. Only requests with streamAudio true
reject bounded GetData calls with the engine's streamed-samples diagnostic;
the false controls return sample data. Both handler readbacks stay true for
the requested true cases. Clips remain valid after handler disposal.

For the production long song, the measured streaming object is 250696 bytes,
versus 53310897 bytes for the nonstreaming control. Unity allocation readings
also differ. These readings corroborate the current engine's behavior; they
are not a process-memory budget proof. Unity allocations are noisy, and v2
scheduled clip destruction without a separate reclamation barrier between
each transfer. The receipt explicitly claims no lifecycle or budget acceptance.
All four tracked clips were released and listener state restored.

## Runtime contract

`LoadNative` explicitly requests streamAudio, verifies the handler getter before
SendWebRequest and again immediately before GetContent, and accepts only a
nonnull owned clip. `UsesNativeStreamingClip` now means that current clip's
verified request/ownership provenance, including exact `output.clip` identity.
It does not compare AudioClip.loadType or claim a universal allocation guarantee.
Stop clears provenance before abort/disposal. Replacement follows the same path.

The 12 MiB local, in-flight advertised/downloaded and completed-transfer bounds
remain intact. Production never calls GetData or reads downloadHandler.data;
this adapter allocates no full PCM array. Native Pause preserves an existing load
error; Web behavior is unchanged.

## Root handoff

```powershell
python tools/p08/media/native-music-v3-staging/preflight.py
python tools/p08/media/native-music-v3-staging/install.py
# Root only, after review:
python tools/p08/media/native-music-v3-staging/install.py --install
```

The guarded target is only
`Assets/RacingBois/Client/Adapters/P08MusicDirector.cs`, expected current SHA256
`3983232b2a41ca1a0db90bda8875094810dbbc8f7e51c75181881124656c56ec`.
Its original meta must remain exact. After refresh/compile, root rebuilds
`ProbeCompile.csproj` against the actual current Library assemblies and loads
`bin/ProbeCompile/netstandard2.1/RacingBois.NativeMusic.ProbeV3.dll` once.

Invoke public static `Start(newReceiptPath)` on
`RacingBois.NativeMusicChecksV3.NativeMusicProbe` in the preserved quiet Play mode
scene. Use `Snapshot()` to read progress; `Abort()` releases owned resources and
restores listener pause. The probe accepts only a live source matching this
reviewed candidate and uses an independent EditorApplication.update scheduler.

V3 runs 26 actual lifecycle assertions, including pause during load, immediate
error retention, finite end once, same-ID and Resume replay, retained paused
playhead, loop behavior, listener pause before/during playback, gesture
idempotence, stop during load and cleared ownership. It does not rerun the
successful v2 GetData/memory experiment. Source, serializer, fixture and executing
runtime assembly identities are bound before/after. All tracked clips and the
owned GameObject must be released, and listener pause restored for a pass.
Four managed serializer groups and managed compilation are only preflight.

## Invocation error kept separate from native evidence

Root's first reflection call returned a TargetInvocationException although the
native v2 receipt completed successfully; a later explicit retry correctly
rejected the already-existing receipt. The project Editor.log contains the four
streamed GetData diagnostics and the v2 PASS, with no exception stack identifying
the first reflection failure.

Read-only inspection of the direct Unity MCP source shows
`ExecuteCode.InvokeCompiled` invokes a compiled snippet once and unwraps one
TargetInvocationException layer. A snippet's own reflection invocation can leave
another wrapper, explaining the generic error text. The Python execute_code
route uses retry-capable transport helpers, so a transport retry is plausible,
but the available evidence does not prove it happened on that call. Compiler
selection itself does not execute the snippet twice. No Unity MCP source was
modified, and the successful receipt was neither rerun nor overwritten.

For future start calls, root should unwrap all InnerException layers in the
invocation wrapper and inspect Snapshot/receipt existence before attempting any
retry. A tool-level invocation error is not evidence that the native run failed;
the bound receipt and cleanup checks decide that separately.
