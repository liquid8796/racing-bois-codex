# P08 cinematic and streamed music implementation

New runtime files provide the actual scene director, gallery/captions, bootstrap coordinator and streaming music adapter. No existing race/economy class was edited by this media subtask. The integration owner wires `RaceBootstrap` and the main Cinema button.

## Director and presentation ownership

`CinematicDirector.Initialize(RaceStageView)` uses the existing authored `TrackRibbonView` and its current route materials/scenery. It clones the selected bikes/riders from `ContentRegistry`, the real 12 imported animation clips, and available guardrail/chevron prefabs. It creates no placeholder meshes or replacement physics. Cinematic colliders are disabled. The source prefabs and the user's Club source remain unchanged.

`StartPlayback(CinematicDefinition)` returns false with `LastError` if actor/route assets are unavailable. `IsPlaying`, `Current`, `CurrentBeat` and `ElapsedSeconds` expose presentation state. `Evaluate(seconds)` samples exact beat time, camera position/look/FOV, actor position/yaw/action and clip phase. The director runs in late update so it owns the view while active. `Stop(skipped)` destroys its actors/graphs/props and restores the prior camera and regular-actor renderer visibility. `Completed(definition, skipped)`, `MusicRequested(id)` and `Changed` report cosmetic events only.

Actor slots are hero=0, rival=1, patrol=2, crew=3. The current catalog spans local-stage Z = -4 to 27.6 meters; the existing road maps those local points to its real curvature/height. Showcases inspect 15 different asset designs through 15 explicit shot orders. `Converse`, `Celebrate` and `Inspect` use small procedural additions on the actual idle rig. These are supported presentation actions, not claims of newly authored animation clips. Whether those gestures and transitions look convincing remains a visual acceptance question.

`CinematicGalleryView` adds a modal gallery and skippable caption overlay to the existing UI Toolkit surface. It follows the current graphite/amber/Noto presentation, uses labeled controls at least 44 px high, shows durations, provides a role filter and confines keyboard tab traversal to its controls. Escape and the Skip button stop playback. Underlying UI visibility and prior focus are restored. Reduced motion uses fixed per-shot camera framing and removes gesture oscillation. Source cinematic text is original English; the gallery controls are Vietnamese. This is not full five-language localization acceptance.

`BootstrapCinematicCoordinator.Initialize(stage, document, music, resolveValidatedMusicUrl, canPlay)` composes these views. `ContentRequired` requests an initial route load for a gallery opened before assets exist. `PrepareContentUnload()` stops scene ownership while preserving an open, actor-free gallery/loading message. `StopForGameplay(restoreMusic)` closes optional media; the default restores the prior streamed track and playback position. `HandleBack()` consumes Escape once per frame. `BlocksGameplayInput` allows the bootstrap to pause local stepping and suppress game input while the modal is open. The bootstrap must continue online networking and stop optional films when an online race begins.

The director/coordinator do not start races, apply rewards, buy items, edit accounts, or access player storage. Automatic intro/outcome requests are made by explicit bootstrap hooks, and all sequences remain skippable.

## Music memory and lifecycle

`RacingBois.Client.Adapters.P08MusicDirector` exposes:

```text
Play(id, sameOriginUrl, loop, gain)
UnlockFromUserGesture()
SetMix(enabled, gain), SetMuted(muted), SetDucking(multiplier)
Pause(), Resume(), Stop(), Retry()
CaptureState(), RestoreState(state), Seek(seconds)
Status / Error events; CurrentId / CurrentUrl / CurrentStatus / LastErrorCode
```

`SetDucking` takes a volume multiplier: 1 is unchanged and 0 is silent. Volume inputs reject nonfinite values and clamp to 0..1. A failed same-track request can be retried; audio re-enable retries a previous error once. Cosmetic music failure never blocks the race.

WebGL uses **one HTMLAudioElement**, through `RacingBoisMusic.jslib`, instead of creating a 106 MB decoded Unity `AudioClip` for the longest track. Replacement releases the old source on that element; stop clears it, and disposal removes owned document handlers. Trusted pointer/keyboard activation unlocks pending playback; autoplay rejection is reported as `gesture-required`. Document visibility suspends/resumes the element without overriding an explicit pause. This implementation avoids full music decoding into WebAssembly; actual browser media-buffer memory is still a profiling gate.

The adapter accepts only an absolute same-origin `/Content/` URL whose filename ends in 64 hex characters plus `.ogg`, with no credentials, query or fragment. The JavaScript bridge repeats origin/path checks. Editor fallback permits the local `Build/Content` directory or loopback HTTP(S) content root and retains at most one loading request/owned native clip. No external JavaScript library, cross-origin audio, player storage or credential API is used.

Music is streamed from a hash-named URL. This player does **not** download and hash the entire music response in client memory; publish/package validation must bind those immutable files to their manifest hashes. Media decode/play errors are reported separately. Actor/route bundle verification belongs to the content loader and is not replaced by this music path.

## Verification status

`runtime-compile-preflight.json` records C# compilation against installed Unity 6000.5.7f1 Engine modules and current project assemblies for both `UNITY_EDITOR` and `UNITY_WEBGL` branches. Both preflights passed with no warnings/errors. This is not an actual Unity import, IL2CPP build or Play mode receipt.

`music-bridge-unit-validation.json` contains 14 Node VM contract checks: owned element count, gesture deferral, URL/origin rejection, replacement, bounded mix, pause/resume, visibility, seek, autoplay rejection and disposal. The media/document objects are explicitly test stubs; the receipt does not claim audible browser playback.

`CinematicValidationHarness.EvaluateAll(director, callback)` must be run in Unity Play mode after real content is loaded. It instantiates all 59 sequences and checks 1167 beat samples, imported clip-time bounds, finite transforms/camera, actual renderer/mesh/material references, and object cleanup. It yields between sequences to allow Unity destruction to complete. Use a dedicated director without coordinator listeners for this inspection, so the harness does not request 59 audio streams. The harness has been implemented; its actual Unity result remains pending until the integration owner runs it.

Required live checks remain: representative screenshots and full scene playback, convincing gestures/recovery transitions, subtitle readability at 720p/1080p, gallery focus/back/loading behavior, route-unload/online-start interruption, camera/audio restoration, actual browser music activation/mute/visibility/retry, simultaneous SFX/music mix and measured browser memory. Do not mark these complete from a compilation or stub test.

```powershell
dotnet build tools/p08/media/RuntimeCompile -p:DefineConstants=UNITY_EDITOR
dotnet build tools/p08/media/RuntimeCompile -p:DefineConstants=UNITY_WEBGL
node tools/p08/media/test_music_bridge.mjs
python tools/p08/media/preflight_runtime.py
```

The compile preflight intentionally suppresses CS0436 only because it compiles the new source against existing project assembly snapshots that may already contain an older copy of that source. It does not suppress runtime/asset warnings in Unity.
