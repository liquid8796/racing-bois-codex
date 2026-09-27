# P07 browser acceptance

Final Web `Build/Web-p07-v4`, runtime source `3cac900`, release **0.7.0**.
Observed 2026-09-22 05:55:05–06:05:48 UTC on the final packaged Windows host at
`https://localhost:7888/`. The [Unity build receipt](unity/build.json),
[package manifest and archive receipt](backend/delivery.json) and
[selected UI/DOM observations](browser-observations.json) bind this result.

Testing used **one physical PC**. Two real Web clients connected through WSS;
neither an Internet-region test nor physical two-machine LAN is claimed.
Certificate validation used ordinary trust. UI actions used the browser tool;
DOM telemetry reads did not inspect browser credentials/storage or modify game
state. Screenshots were inspected inline, not exported as persistent files.

## Final v4 observations

| Flow | Verified behavior |
| --- | --- |
| Startup | P06 scene/art and P07 menu loaded; version 0.7.0 and shared 3,000-tick golden `ED162155D421B3CF` passed |
| Persistent profile | Garage connected to a fresh QA profile with Spark 450, condition 100 and 1,000 credits |
| Real shop transaction | Explicit trade confirmation sold Spark for 2,247 and bought Ember for 2,999; server returned 248 credits and Ember ownership |
| Ledger | Exactly opening +1,000 and one trade −752 appeared; ASCII negative sign and `dd/MM/yyyy HH:mm UTC` were readable |
| Reload | After leaving the WS session and reloading, Garage fetched Ember, condition 100 and 248 credits from the authority |
| Campaign | Only current-level Canyon Run was enabled; other routes showed player-facing development labels; campaign created a private room |
| Private invitation | Room `22R84L` showed a full code and usable link; a second client saw no room in the public list |
| Link behavior | Opening `?room=22R84L` stayed Offline, then the joined server's code field was prefilled; Enter joined without clicking Join |
| Multiplayer | Persistent host and fresh guest readied, counted down and entered the same Racing room with distinct sessions/rider IDs |
| Gameplay | Host cruise/input advanced to at least 460.645 m; a right punch animation was visible. This does not separately establish PvP damage |
| Durable race condition | After both players left, Garage showed Ember condition 49 and credits 248. Repair cost 299 was shown and disabled for insufficient funds |
| Layout | Long shop/confirmation/header/footer at 1280×720 viewport (1280×690 canvas), account/campaign scrolling, and full HUD at 1920×1080 canvas were visually inspected |
| Console and cleanup | Captured warning/error logs were empty for both clients; guest logged out/closed, viewport override reset, main tab kept at menu |

The first race samples showed approximately 9.5/14.0 ms RTT, one/three missing
inputs, and zero late/future/stale-remotes counters. These are sampled local
counters, not zero-loss or WAN performance claims. The guest's final 1080p
sample was a stationary rider while the host had moved. A 193,331,200-byte WASM
heap was observed; GPU and allocation counters were unavailable. The mixed
functional session, rolling timing readout and UI-derived FPS do not replace
an uninterrupted ten-minute performance run or monitor-refresh measurement.

## Earlier candidate and separate API coverage

V1 visual review exposed header/confirmation flex shrink in long lists and a
Unity download-reader warning on chunked career responses. V3 fixed the layout
and API Content-Length; its browser export/import of a signed offline checkpoint
succeeded without changing 248 credits. Those checkpoint UI observations are
explicitly attributed to `2890f29` in the JSON receipt. V4 additionally corrected
the missing monetary-minus glyph, date formatting and internal phase jargon.

The [final real HTTP/WSS probe](career-live-validation.json) ran against the same
packaged source on separate offline/online QA realms: **11/11 groups passed,
46/46 responses had exact positive Content-Length**. It covers account upgrade,
login, recovery, concurrent/idempotent commerce, object access, signed saves,
realm separation and normal acknowledged logout/revocation closes. Passwords
and recovery codes were generated and kept only in probe memory. Browser
account forms were inspected without entering credentials; browser password
entry/recovery and clipboard permission interactions are not claimed.

## Scope still open

Native ARM64 execution, physical LAN with WAN disconnected/cold caches,
cross-network/regional Internet testing, long browser performance runs,
low-end hardware, physical gamepad and human usability/art/audio approval
remain separate gates. P07 adds no new 3D assets and does not fill P08's remaining
track/vehicle art or deploy P09's OCI service.
