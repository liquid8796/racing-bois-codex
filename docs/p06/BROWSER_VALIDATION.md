# P06 final browser validation

Observed 2026-09-22, 02:10:55–02:32:01 UTC. Final release `0.6.0`, compiled
runtime and Web template commit `efce749`, direct Unity output `Build/Web-p06-v4`.
The [build receipt](unity/build.json), [package receipt](backend/delivery.json)
and [selected browser observations](browser-observations.json) describe the same
payload. UI input used the computer-use browser API; telemetry was read from
the public DOM status element without changing game state through JavaScript.

All browser testing used **one physical Windows PC** and the loopback host.
HTTPS used the user's already trusted localhost certificate, with no warning
bypass. Screenshots were inspected inline at gameplay distance. No persistent
browser screenshot file is claimed; the images/video under `unity/` are Unity
captures, not browser captures.

## Final v4 results

| Check | Observation |
| --- | --- |
| HTTPS startup | Scene and Vietnamese UI rendered, version 0.6.0; shared 3,000-tick replay passed with `ED162155D421B3CF` |
| Invite and keyboard join | Alpha created `Đua thử P06`, full code `W3TAUF` was readable; Bravo typed the code and pressed Enter to join without clicking Join |
| Two Web clients over WSS | Both readied, host started, countdown appeared; distinct public sessions and rider IDs entered the same room's Racing phase |
| Input and movement | Alpha's acknowledged inputs advanced; subsequent sample reached 484.847 m with bike health 88; right-kick pose was visually observed |
| Lobby reload/resume | A batched reload → Online → Connect completed in 3,419 ms; room `VEAD68`, public session ID and rider ID were preserved |
| Expired reconnect feedback | Two earlier manual race reload attempts exceeded the 30-second lease and showed expired-seat feedback; they are not recorded as successful race resume |
| HTTP/WS | A separate `127.0.0.1:7777` tab loaded and connected as a guest to the lobby, then logged out; no HTTP race is claimed |
| Local gameplay at 1080p | Real 1920×1080 canvas, Medium, cruise movement, wrecked results, Retry and return to menu worked; retry sample reached 201.965 m at 46.307 m/s |
| Audio lifecycle | Final telemetry reported bank ready, audio unlocked after interaction, mute off and audio events; this is not subjective mix approval |
| Browser warnings/errors | Captured warning/error logs were empty for both HTTPS clients and the HTTP client |
| Cleanup | Secondary clients logged out and closed, temporary viewport override reset, main tab kept at the menu |

The kick observation establishes input/animation, not peer damage: Bravo's
health remained 4096 in the recorded sample. Native combat regressions and the
controlled combat video are separate evidence. This browser pass also does not
close P05's remote-contact visual uncertainty.

Initial race snapshots reported roughly 10–11 ms RTT, three missing inputs per
client, zero late/future inputs and zero stale remotes. These are actual sampled
counters, not a zero-loss or WAN-latency claim. The final 1080p moving sample
reported about 120.76 MB Unity allocated, 5.43 MB managed and a 193.33 MB WASM
heap. Its rolling p50/p95 values were 3/4 ms. These point readings and the UI's
derived FPS do not establish display refresh rate, steady-state performance or
the required ten-minute browser benchmark. GPU timing and allocation counters
were unavailable; zero values in those fields must not be interpreted as zero
GPU cost or zero garbage allocation. Use the separately scoped
[Editor measurements](performance/README.md) for the uninterrupted 60-second runs.

## Earlier candidate observations

Before the final v4 build, the v3 candidate was exercised for Low/Medium/High,
HUD scaling, reduced motion, mute persistence, keyboard focus and settings
Escape handling. Preferences survived reload and were restored to Medium,
100% HUD, audio on and reduced motion off. Its WebAudio context was observed
changing from suspended to running at 48 kHz/stereo after a user gesture.
These are historical candidate observations, not fresh v4 measurements.

That pass exposed two UI defects: Enter inside the join field did not submit,
and the invite field clipped some glyphs. Commit `efce749` fixed both; the final
v4 checks above exercised the corrected paths. The earlier persistent-data
sync warning was fixed in the source Web template, which now enables
`autoSyncPersistentDataPath`; v4 required no post-build HTML patch.

## Acceptance still open

Physical LAN with Internet disconnected and cold browser caches, different
Internet networks, native ARM64 execution, a sustained ten-minute browser
benchmark, low-end/iGPU hardware, physical gamepad operation, novice-user
usability and final human art/audio/feel approval remain open. This slice does
not establish full original-game content parity or public OCI deployment.
