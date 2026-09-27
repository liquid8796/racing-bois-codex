# Racing Bois — P05 implementation and acceptance

Date: 2026-09-21. **P05 implementation, local validation and distributable packages delivered; full acceptance remains open.** Runtime commit `9873732`, release `0.5.0`. The original club was built from the approved 2D concept before the multiplayer work. The remaining gates are physical LAN/WAN tests and remote collision presentation quality, detailed below.

## Confirmed constraints

- The user currently has one physical PC and no public domain for Racing Bois.
- Multiple loopback clients and synthetic delay tests cannot establish two-machine LAN-without-WAN or cross-network Internet acceptance. Those gates remain explicitly open.
- No public deployment, OCI service change, firewall change or WAN disconnection is part of this run.

## Club delivered

Original source, FBX, PBR maps and threeLODs are documented in [club asset](p04/club/ASSET.md). [Unity validation](p04/club/unity-validation.json) confirms0.55m length, identityroot, grip pivot,1080/384/160triangles, oneURP material and onecapsule. Independent geometry and UV intersection audits passed. `WeaponGripView` follows the articulated palm from authoritative equipment state; left/right gameplay captures are in `docs/p04/club/`. Its Unity collider is disabled in gameplay because shared simulation owns hit resolution.

## Multiplayer implementation

- Protocolv3 `/multiplayer`, separate from retained P02/P03 regression endpoint `/ws`.
- Bounded room/create/join/code/ready/countdown/host-transfer lifecycle, eight players perroom, explicit late-join policy.
- Exact target-tick input, full own checkpoint, prediction/reconciliation, bounded nearby actor snapshots and remote presentation sampling.
- Reliable lifecycle/combat/result lane separated from replaceable snapshots; epoch and sequence fencing, resume leases and acknowledged logout.
- Distinct cosmetic preferences, durable server-profile capability and per-tab resume receipt. Explicit freshguest choice prevents silently sharing one player's seat across tabs.
- Realm-scoped profile/results storage with idempotent match outcomes, asynchronous bounded persistence and owner-applied completion.
- Offline self-contained WindowsLAN packaging, private-interface URL/QR helper, data directory kept outside servedWeb files.

The P05 Web build uses native gzip compression so the same payload can load over LAN HTTP and HTTPS. P03's Brotli-only build was not sufficient evidence for ordinary LAN HTTP cold-loading: [Unity's deployment documentation](https://docs.unity3d.com/6000.0/Documentation/Manual/webgl-deploying.html) states that Chrome/Firefox native Brotli support requires HTTPS, while gzip works with either scheme.

Implementation details: [server](p05/backend/IMPLEMENTATION.md), [client prediction](p05/client-prediction.md), [LAN packaging](p05/lan/DELIVERY.md), [browser bridge tests](p05/web-bridge-validation.json).

## Validation and deliverables

- [Source-bound final validation](p05/backend/final-verification.json): 25 server domain, 32 client, 18 foundation and 14 race regression tests pass; 31 gameplay checks retain the shared golden replay. Eight socket impairment scenarios pass. WS and WSS each pass nine checks with eight native player connections plus five bots, including authoritative PvP damage, resume and logout.
- [Browser validation](p05/BROWSER_VALIDATION.md): two actual Web clients on this PC create/join by code, ready, count down and race over trusted WSS. Reload plus Connect resumes the same room, session and rider. The remaining client keeps racing after the original host leaves. HTTP/Gzip and WS are also exercised. This is single-PC evidence.
- [Unity build](p05/unity/build.json): release IL2CPP Web, gzip, 15,069,946 bytes, zero errors and warnings. Build source is runtime commit `9873732`; Unity cleared the dynamic font cache according to its build setting, and browser runtime rendered Vietnamese glyphs successfully. The cleared cache is retained in the subsequent receipt commit.
- [Delivery receipt](p05/backend/delivery.json): Windows self-contained package passes native SelfTest v3 and all 367 immutable-file hashes. ARM64 ELF/archive/permissions and all packaged Web hashes pass static checks; native ARM execution is not claimed. Neither archive contains player data.
- Demo: <https://localhost:7778/>. Windows package: `Build/Packages/RacingBois-P05-win-x64-9873732.zip`; ARM package: `Build/Packages/RacingBois-P05-linux-arm64-9873732.tar.gz`. The running demo binds loopback; the Windows package's `launch-lan.bat` starts the intended LAN host.

Integration fixed focus stealing during text entry, transition to local before logout ACK, stale-epoch reliable replay, low-FPS input batching, discarded session-replacement reasons, persistence retries and synchronous disk I/O on the simulation owner. The server uses elapsed-time scheduling instead of assuming every timer wake equals one 60 Hz tick.

## Open acceptance gates

1. Two physical LAN machines, WAN disconnected, cold browser caches, first host launch and complete race. The user currently has one PC. Dependency bundling, QR decoding and loopback tests do not substitute for this gate.
2. Two clients on different Internet networks, public HTTPS/WSS deployment and native ARM64 execution. No domain was supplied and no OCI deployment occurred.
3. Remote collision presentation: own prediction correction is at most about 0.695 m in the measured 250 ms case and steady relative error at most 1.175 m, but the observer's crash-transition residual reaches **15.897 m** before authoritative collision information arrives. Even loopback has a 3.795 m contact outlier. These are real quality gaps; passing transport tests does not make combat presentation complete.
4. Default eight-human/five-bot payload peaks around 63.3 KB/s download and 15.3 KB/s upload per client, slightly above initial 60/15 KB/s budgets. Full GPU, per-frame GC and browser resident-memory acceptance remain unmeasured; sampled frame timing is only a baseline.

Prioritize remote collision transition presentation and bandwidth tuning before calling P05 fully accepted. P06 remains the phase for final art, effects, audio and comprehensive performance acceptance; the current visual style is an implementation prototype.

## LAN helper review

The root agent's temporaryHTTP-preview launch was rejected by automaticapproval review without a detailedreason; BrowserUse then explicitly blocked the localfile URL. No browser-policy workaround was attempted. The user manually opened `_local/p05-lan-preview/LAN_JOIN.html` and confirmed **URL and QR display clearly**. This is user visual confirmation, separate from the automated QR decode and package dependency tests.
