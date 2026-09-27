# P08 Windows 10/11 delivery

Primary release target is the native Windows 10/11 x64 Unity player. Web delivery
is deferred. Multiplayer authority, accounts, inventory, currency and lobby
services remain in the existing backend; the online deployment target remains
the OCI VM. This local packaging workflow does not deploy or reconfigure OCI.

## Build contract

`P08DesktopBuilder` owns native player composition. It uses the installed Unity
6000.5.7f1 Windows64 release **Mono** variation. The installed module inventory
contains the `win64_player_nondevelopment_mono` variation and no Windows release
IL2CPP variation. This is an explicit local build choice; there is no claim that
the player was built with IL2CPP. Direct3D 11 is the graphics compatibility
baseline. The player opens in a resizable borderless window with a 1920×1080
default resolution; display dimensions and actual settings require runtime QA.

The pack builder writes `Build/Content-desktop` for `StandaloneWindows64`. Its
manifest carries the gameplay content hash and platform. The native loader
rejects bundles for WebGL or another gameplay version. The player installs only
the immutable manifest delivery: one actor bundle, five route bundles, all 25
Ogg music resources, and the manifest. Unity verifies exact SHA-256, length and
bundle CRC before copying them to `Assets/StreamingAssets/Content`. The build
includes them at `RacingBois_Data/StreamingAssets/Content`, resolved through
`Application.streamingAssetsPath`; no developer machine path is embedded.

The actor bundle includes the full authored actor/portrait/audio catalog. Music
is stored as compressed Ogg resources and loaded by the native music director.
Offline local play needs neither an Internet content server nor a browser.
Source `.blend`, music WAV masters, original-game research, database files and
private player data are not included. The preparation step rejects unregistered
StreamingAssets files; it only removes obsolete files owned by the previous
content manifest in that exact folder.

## Editor commands

After all P08 prefabs/portraits/audio and scene UI are finalized, root runs these
methods through Unity MCP, checking compile and console state between operations:

1. `P08ContentPackBuilder.Setup()` and `Validate()`.
2. `P08ContentPackBuilder.BuildDesktop()` for release bundles.
3. `P08DesktopBuilder.Describe()` for live module/path evidence.
4. `P08DesktopBuilder.Prepare()` for content/config/settings receipt.
5. `P08DesktopBuilder.Build()` for the actual release player in a fresh default
   output folder. For a later candidate use
   `P08DesktopBuilder.BuildTo("Build/Desktop-P08-candidate-2")`.
6. `P08DesktopBuilder.Validate()` to verify its installed content and Unity CRC;
   a named candidate uses `ValidateAt("Build/Desktop-P08-candidate-2")`.

The output is `Build/Desktop-P08/RacingBois.exe`. Build is deliberately explicit;
it does not silently create missing art, accept incomplete content or package a
fallback scene. Preparation must finish before the source snapshot is frozen.
Build records the source file hashes, aggregate source fingerprint, Unity build
result/size/time/error/warning counts and exact installed player file hashes.
Changing source during the build fails the source-binding gate. Build refuses
nonempty output folders and preserves their files, so stale bundles or unrelated
files cannot enter a reused release folder. A later candidate gets its own
explicit directory under `Build`. The latest build receipt is invalidated at
attempt start and records preparation/build/validation failure honestly; the
previous receipt is retained unchanged under `history` with its SHA in the name.
Receipts under
this directory are created by actual operations, never by changing pass flags.

Then audit distribution bytes with the exact shared content hash returned by
Unity:

```powershell
python tools/p08/desktop/audit_desktop.py --expected-content-hash '<actual shared hash>' --receipt docs/p08/desktop/distribution-audit.json
```

For a named candidate, also pass
`--player-root Build/Desktop-P08-candidate-2`. The audit requires that exact root
to match the build receipt and checks every declared source hash against the
current repository. Run it before making further source changes; later source
edits correctly invalidate source freshness instead of silently accepting the
old build.

This audit validates the x64 PE identities, release Mono bootstrap/runtime,
actual successful Unity receipt, all installed content, the public config and
every player-file SHA. It does not prove launch, visual quality or performance.
Archive creation waits for the final source/content roster and native runtime
acceptance; no provisional archive is presented as the final P08 release.

## LAN and OCI online

`RacingBois_Data/StreamingAssets/RacingBois.runtime.json` is a public installation
config with schema 1 and four fields. The shipped local example uses
`connectionMode: lan`, `ws://127.0.0.1:7777/multiplayer`, and installed content.
Passwords, session tokens, account state and private server configuration never
belong in that file. Existing valid installation settings are preserved during
preparation. Player data stays in the existing per-user storage adapter.
This offline-ready release requires `contentBaseUrl` to remain empty; a remote
content override is rejected by preparation and distribution audit. Configuring
an OCI WSS backend does not move installed local content to an Internet-only root.

For offline LAN, distribute the separate LAN host package to the host PC. Run
the host on TCP 7777; each desktop client enters
`ws://HOST-LAN-IP:7777/multiplayer` and joins using its room code. Localhost is
only suitable when the host runs on the same PC. Browser HTML and QR guidance
from older phases are optional historical web flows, not required for desktop.

For online, `connectionMode: online` requires an explicit WSS endpoint ending
in `/multiplayer` with a trusted certificate. The OCI address previously
provided identifies the deployment VM; it does not prove a deployed P08 service
or a trusted public endpoint. No public endpoint or cross-Internet result is
invented in a package. Native TLS trust, OCI deployment, persistence and real
multi-machine LAN/WAN checks remain separate acceptance gates.

## Proposed desktop budgets

These are targets to measure, **not fresh benchmark results**:

| Check | Proposed release target |
| --- | --- |
| Primary device | Windows 10/11 x64 PC/laptop, DX11, 1920×1080 Medium |
| Sustained frame time | Mean ≥60 FPS; p95 ≤20 ms during a controlled 10-minute race |
| Weak hardware | Separate Low-tier measurement on an integrated-GPU laptop |
| Process memory | Peak working set ≤2 GiB; managed, native and GPU allocations recorded separately |
| Content residency | Shared actors + one current route; route swap stress shows no monotonic live-object/memory growth |
| Loading | Installed cold/warm measurements for actors and each route; all 25 Ogg resources remain available offline |
| Input/audio | Keyboard and real gamepad; focus loss, resize, reduced motion, volume and music transition QA |
| Soak/network | Native long-run stability plus physical LAN without Internet and actual OCI WSS clients |

Earlier P06 Editor measurements and P07 browser receipts are historical evidence.
They are not substituted for P08 native timing or a Windows 10 hardware run.

## Current evidence boundary

The new editor wrapper compiles against the installed Unity assemblies with
zero warnings/errors. Fourteen distribution-contract tests pass, including wrong
platform/version, corrupt/truncated resources, missing offline music, path
escape, unregistered source masters, config userinfo/private fields, x86 PE and
player/source mutation and truncated PE rejection. These fixtures test the verifier and are explicitly
not runtime or visual acceptance. Actual player/build/runtime receipts appear
only after their corresponding operations complete.
