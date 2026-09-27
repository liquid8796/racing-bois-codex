# Staged Unity Windows Mono WSS specimen

This folder is outside `Assets`. No component is installed in the game and no live Editor operation has been performed. The runtime and builder compile against the installed Unity6000.5.7f1 managed assemblies; this compilation is **not** a Unity build, Mono/TLS execution or game/render acceptance.

The specimen uses the existing production `BrowserSocketTransport` native `ClientWebSocket` branch, `MultiplayerSession`, `UnityWireCodec` and `UnityMonotonicClock`. It creates a fresh guest/private room, sends normal driving inputs, records real authoritative progress, deliberately suspends/resumes once and verifies the same identity/slot/room. Credentials exist only in memory. Success requires acknowledged room leave and session logout. Report fields are bounded aggregates and sanitized pose samples; no tokens, profile/room identifiers or raw packets are written.

Root owns integration after the protocol6 source freeze and matching OCI deployment:

1. Copy **only** `Runtime` and `Editor` into a new `Assets/RacingBois/Diagnostics/NativeProbe` folder. Keep their asmdefs. Refresh once when the Editor is idle and inspect compilation diagnostics.
2. Call `RacingBois.Diagnostics.NativeProbe.Editor.NativeProbeBuilder.Build("D:/Project/Unity/racing-bois/Build/NativeProbe/<fresh-attempt>")` through the direct Unity tool. It creates its own additive scene, builds a dedicated Windows64 Mono player, restores Editor settings/active scene, and writes `NativeProbe.build.json` plus `NativeProbe.binding.json`. It never closes an unrelated scene.
3. Inspect the successful build receipt, zero errors, source binding and output file hashes. Run `python tools/p10/unity-native-probe-staging/run_native_probe.py --build Build/NativeProbe/<fresh-attempt> --endpoint wss://<configured-host>/multiplayer --seconds 90 --report D:/Project/Unity/racing-bois/docs/p10/native-wss/<fresh-id>.json`. The launcher checks all source/player hashes, uses normal certificate validation and owns only the new process handle. It does not stop any old process.
4. Require runtime `status=PASS`, WindowsPlayer/Mono detection, matching source fingerprint/protocol, at least two actual connections, accepted resumed welcome, authoritative/post-resume progress and cleanup acknowledgments. Preserve failures. This closes the Unity-Mono native-TLS path gap; it does not establish full-game visuals/performance, physical two-machine LAN or an eight-hour stability gate.

The blank scene/camera is a transport specimen, not replacement game content. The probe is opt-in (`--rb-native-probe`) and rejects malformed options, non-WSS addresses and invalid source bindings. No TLS bypass is installed. Only root should install/build/run it; staging scripts must not be copied into `Assets` wholesale.

## Scoped build and launcher hardening

The builder now completes read-only validation before creating output or scenes.
`NativeProbeBuildScope` records a rollback before each actual setting change;
unchanged settings and rejected preflights invoke no setting setters. Owned scene
cleanup and prior active-scene restoration continue even if one setting restore
throws. `editorSettingsChanged`, `editorStateRestored` and bounded restoration
error codes are included in the final receipt; restoration failure cannot leave
`passed=true`. There is no global `AssetDatabase.SaveAssets` call. Only the new
probe scene is explicitly saved.

The launcher now reserves its own launch receipt before spawning, verifies the
source fingerprint/required player files, and rechecks all source/player hashes
plus the build receipt after exit. Runtime protocol, WindowsPlayer/Mono identity
and endpoint must also match. A mid-run file mutation fails the launch receipt
even if the player reports PASS. Timeout/interruption only controls the owned
process handle. Logs remain files and are never printed by the launcher. The
UTF-8 BOM reader spelling is corrected to `utf-8-sig`.

Latest scoped staging verification:
`docs/p10/unity-native-probe-staging/20260926T231911Z/receipt.json`:
managed Unity compilation plus eight option-policy groups, six rollback-journal
lifecycle checks and seven launcher postcheck/ownership checks all pass.
Each test report is fresh in that exact verification directory; an earlier
configuration report is no longer accidentally reused. These are pure/managed
checks, **not a live Unity lifecycle, native process, TLS or rendering result**.
