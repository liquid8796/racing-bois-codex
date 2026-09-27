# P05 browser validation — 2026-09-21

Runtime commit `9873732`, release `0.5.0`, `Build/Web-p05-v1`. The running
Windows package serves the exact gzip payload in [delivery.json](backend/delivery.json).
All browser actions used Computer Use on the real Unity canvas; no state was
injected into Unity, no storage capabilities were read, and no certificate
warning was bypassed. The user had already trusted the localhost development
certificate. Screenshots were inspected inline in the task; the saved PNGs under
`unity/` are separate Editor evidence, not relabeled browser screenshots.

## Actual flows

| Flow | Observed result |
| --- | --- |
| HTTPS startup | Menu, Vietnamese glyphs and version 0.5.0 load. The native/WASM 3,000-tick shared replay passes with `ED162155D421B3CF`. |
| Text input | Mouse click, Ctrl+A and typed text update player and room names without losing focus. |
| Two Web clients | Separate guest clients `QA Alpha` and `QA Bravo` join room `XC3MT8` by its displayed code. Both members appear, ready states synchronize, and only the host has Start. |
| Race start | Both ready, host starts, visible countdown begins at 3, then both clients enter Racing. Two human riders plus five bots give HUD denominator 7 even when interest management sends fewer actor models. |
| WSS actions | Short E input visibly animates a right attack; Shift+E changes the action state. Hold-throttle advances the authoritative rider, with input ACKs. No successful browser PvP hit is claimed from these out-of-range swings; eight-client native transport tests separately prove damage delivery. |
| Reload/resume | Reload Alpha during Falling, then use Connect. Same public session ID, rider 1 and room return. Bike damage remains 92, world advances and recovery completes; no duplicate player is observed. Display-name preference is shared across tabs, while the resume lease stays per tab. |
| Host leaves | Alpha leaves; Bravo stays Connected/Racing in the same room and continues receiving ticks. This proves ongoing dedicated-server simulation; lobby host transfer is separately covered by native tests. |
| Logout | Back to menu reaches Offline/None, empty room/session and zero pending inputs. |
| HTTP/Gzip + WS | New HTTP-origin tab loads all Unity assets, defaults to `ws://127.0.0.1:7777/multiplayer`, connects a saved server profile, creates room `7MXMZ4`, readies and races with five bots. |
| Race results | Normal throttle-only driving eventually wrecks the bike. Server phase becomes Results, HUD shows HONG XE (Vietnamese accents rendered), reward/fund $0 and durable-result confirmation. Return to lobby resets readiness and keeps the same room/profile. Logout then reaches Offline. |
| Layout | 1280×690 game canvas and 1920×1080 canvas display menu/lobby/HUD/results without clipped controls once resize settles. Temporary viewport override was reset. |
| Logs | Captured warning/error lists for both HTTPS clients and the HTTP client are empty. |

The browser's two HTTPS tabs remained active simultaneously without a visibility
override. This does not prove a physical browser tab-suspension scenario;
visibility/reconnect behavior has separate application and native-socket tests.

## Measurements and limitations

Selected DOM telemetry is retained in [browser-observations.json](browser-observations.json).
The two-client loopback sample reports approximately 9–10 ms RTT and 4/5 ms
frame p50/p95. The later 1080p HTTP sample reports 3/4 ms p50/p95, approximately
109.5 MB Unity allocated and 161.1 MB WASM heap. GPU timing and per-frame GC
counters report unavailable; zero in those fields is not a measured zero cost.
Resident browser memory and a hardware-wide 60 fps guarantee were not measured.

The HTTP session's missing-input counter rose from 4 to 187 during the mixed
resize/tab-management/driving run, while late/future remained zero. The exact
cause of that gap was not isolated, so this run is **not zero-loss or continuous
frame-pacing proof**. It did continue to receive snapshots, drive, recover,
finish with a wreck result, return to lobby and log out. Alpha's reload run
likewise reports 2 late and 20 missing inputs after resuming. These observations
are preserved rather than replaced by the cleaner synthetic matrix numbers.

All clients and server ran on one PC. No WAN-off, independent cold-cache LAN,
cross-network Internet, native ARM or public OCI acceptance is claimed.
Remote crash-transition error up to 15.897 m and the slightly exceeded network
budgets remain open in [P05 status](../P05_STATUS.md). Final art and effects are
P06 work. The Results subtitle still repeats the lobby readiness hint; refine
that contextual copy during the UI polish pass.

The user separately reviewed the local LAN helper and confirmed URL/QR clarity.
That manual confirmation is independent of this browser game validation.
