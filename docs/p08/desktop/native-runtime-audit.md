# Native runtime configuration and transport audit

Windows 10/11 x64 is now the primary player. Online services still target OCI; this audit makes no claim of deployment or live OCI connectivity.

## Installation settings

`DesktopConfiguration` reads only `Application.streamingAssetsPath/RacingBois.runtime.json`, capped at 8 KiB. The schema is 1 with `connectionMode` (`lan` or `online`), `backendWebSocketUrl`, and optional `contentBaseUrl`. These are public installation settings, without credentials or player data. The sample is `tools/p08/desktop/RacingBois.runtime.json`.

The absent-file/default configuration explicitly selects a LAN host at `ws://127.0.0.1:7777/multiplayer`. A server still has to run on that machine; configuration does not imply connectivity. An online installation must supply its real trusted `wss://…/multiplayer` URL. Backend and content origins are independent. Account credentials retain the existing HTTPS-only career transport policy. No certificate bypass has been added.

Installed content defaults to `Application.streamingAssetsPath/Content`; the Unity Editor defaults to `Build/Content-editor`. An optional remote content root must use HTTPS without user information, query, fragment or encoded traversal. The serialized Editor override accepts HTTPS or loopback HTTP only and does not apply to a standalone player. Invalid installation settings produce an explicit menu warning and select the local LAN/default installed-content configuration.

Content manifests are fenced before bundle load by `buildTarget`: `StandaloneWindows64` for native/Editor, `WebGL` for the deferred browser player, as well as the canonical gameplay content hash. Existing SHA-256/CRC, bounded download and relative same-root bundle checks remain enforced. Native music uses the same configured root as the content loader. Canonical file path checks support spaces in installed folders, and reject sibling/outside paths; remote music rejects other origins and escaping URLs.

## Native music memory policy

The native adapter already used `DownloadHandlerAudioClip.streamAudio = true`. Verified against the installed Unity 6000.5.7f1 `UnityEngine.UnityWebRequestAudioModule.xml` and [Unity's streaming API documentation](https://docs.unity3d.com/ja/6000.0/ScriptReference/Networking.DownloadHandlerAudioClip-streamAudio.html), this creates a clip equivalent to `AudioClipLoadType.Streaming`; it supersedes the compressed flag. The audit's 106,496,000-byte value is a hypothetical full stereo float PCM decode, not an observed native allocation.

Native loading retains one source and one owned streaming clip, never copies `downloadHandler.data`, and checks the resulting clip's load type before playback. Installed files are checked before request creation; remote transfers have a 12 MiB compressed-byte cap checked against content length and downloaded bytes each frame. The largest current authored OGG is 5,060,352 bytes. Playback waits for the bounded transfer to complete, avoiding unreliable early-play buffer-rate predictions. New playback/stop cancels the prior request/coroutine and releases its clip. The Web player continues to use its existing single media element.

`UsesNativeStreamingClip`, `LastNativeDownloadedBytes` and the safe `RB_MUSIC_NATIVE_READY Streaming bytes=…` log support packaged-player verification. Unity owns its decoder buffers; this code does not claim a measured fixed decoder memory size. Profiling actual native audio memory, playback/loop quality and rapid song changes remains a player acceptance gate.

## Existing native socket implementation

`BrowserSocketTransport` already contains a native `ClientWebSocket` branch despite its historical name. It keeps the default operating-system TLS validation and uses one receive loop, a serialized send gate and a main-thread callback queue. Messages are capped at 32 KiB, receive backlog at 256, and `Poll()` drains at most 128 callbacks per call. Reconnection replaces the socket; queued callbacks check their socket identity so stale generations cannot update the new session. Explicit close/destroy cancels and disposes the socket. Cancellation and send/receive failures are caught and reported through the queue, with no endpoint/credential logging. The native receive loop now rejects binary frames before protocol dispatch; the multiplayer protocol requires text JSON. No rename or speculative transport rewrite was needed for this platform migration.

`native-transport-tests.json` executes the actual linked native transport source in .NET 10 using an empty test-only `MonoBehaviour` shell and an ephemeral in-process loopback WebSocket fixture. Five checks pass: fragmented Unicode and serialized outgoing text, stale-generation suppression on reconnect, bounded-backlog failure, binary-frame rejection, and remote close/dispose without late callbacks. `native-transport-tests-before-text-guard.json` retains the original failing binary-frame case rather than overwriting its evidence.

This is not packaged-player or Unity Mono/IL2CPP acceptance. The native transport still needs the real player connect/join/reconnect tests, sustained multiplayer load, trusted WSS and physical LAN/WAN acceptance. Browser-specific lifecycle registration remains conditional and is not called by the desktop player.

## Garage and rider inspection

`CareerView` emits bike/character inspection and preview-visibility events separately from its server equipment commands. `RaceBootstrap` caches these cosmetic selections and composes `RaceStageView.SetMenuPreview`; inspection never writes profile/equipment, balances or race state. The stage uses actual `ContentRegistry` prefabs after actor/route readiness, and does not substitute a P06 model for an unavailable indexed P08 selection.

The menu owns one rider/bike visual, independent of race pools. Identity changes disable/release the previous pair and instantiate the selected catalog pair; repeated UI renders or visibility-only changes reuse it. Bike inspection hides the rider; character inspection shows the selected mounted rider. The garage camera places the actor on the right of the flat UI with a gentle five-degree orbit, which stops advancing with reduced motion. Active races ignore preview changes. Closing inspection restores the prior actor, visibility, framing and camera pose/FOV; content switching clears/rebases the preview state. Preview changes are deferred while `CinematicDirector` owns the camera, preserving its capture/restore and renderer lifecycle.

This is implemented presentation behavior with managed compile verification. Model framing, transitions, render quality and repeated rapid inspection still require the actual Unity/player visual and lifecycle checks.

## Evidence and limits

`config-tests.json` contains nine passing pure native tests for installed/Editor roots, explicit LAN defaults, strict public online configuration, music root containment and native-vs-WebGL manifest rejection. `runtime-compile-preflight.json` binds exact source hashes and compiles `UNITY_STANDALONE_WIN`, `UNITY_EDITOR` and the retained `UNITY_WEBGL` branch against installed Unity 6000.5.7f1 modules. All three pass with zero errors/warnings.

These checks do not establish a Unity import, player build, scene/render quality, native audio decode, Windows 10/11 hardware acceptance or live network connectivity. Final player and art acceptance remain separate gates.
