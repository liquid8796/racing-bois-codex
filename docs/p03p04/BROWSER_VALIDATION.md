# P03/P04 browser acceptance — 2026-09-21

Final runtime `130fa9b`, Web artifact `Build/Web-p03p04-v2`, served by the self-contained package at `https://localhost:7778/`. [Build receipt](unity/build.json): release IL2CPP, 11,037,632 compressed deployable bytes, zero errors/warnings. [Delivery receipt](backend/delivery.json) binds the exact five Web files, server binaries and Windows/ARM64 archives.

## Verified in the actual browser

The new game was loaded and interacted with through CUA in the Codex in-app browser. Screenshots were inspected at 1280×720 and 1920×1080 canvas sizes. The viewport override was reset at the end and the tab retained on the menu.

- Local practice starts without a socket connection. Cruise produces movement; a corner departure triggered real crash/recovery. Restart and returning to the menu clear cruise.
- A browser-discovered defect lost short Q/E presses between60Hz ticks. The final client buffers `wasPressedThisFrame` through the next simulation step, and authority retains nonzero attack intent even if neutral input arrives before that tick. The final Web build visibly responds to quick E, Shift+Q and WSS Q presses with the corresponding side/pose.
- The visible WSS panel connects using the user's previously trusted localhost certificate. Received authority snapshots advanced, accepted inputs were acknowledged, and distance reached461.838m in the sampled online run. Brake cancelled cruise visibly. No certificate bypass was used.
- The startup3000-tick shared gameplay replay returned **ED162155D421B3CF**, matching the native golden. This replay includes pedestrians/traffic/events and is isolated from the user's actual race.
- Final Console warning/error queries returned empty arrays. Vietnamese text, keyboard focus indication, menu, HUD and network panel were visible without missing materials or references.

## Measured baseline and limits

Exact samples are in [browser-validation.json](browser-validation.json); [hardware](hardware.json) identifies an i7-11800H, RTX3070 Laptop GPU and64GB host. The sampled rolling360-frame windows reported p50≈3ms, p95≈4ms, CPU frame time3.445–3.555ms, Unity allocated107.8–108.4MB, managed5.6–6.3MB, and WASM linear memory161.1MB. World population reached7riders/12traffic/6pedestrians; not all were simultaneously visible.

These are warm samples from one uncapped in-app browser, not a continuous stress benchmark, a monitor refresh measurement or a guarantee for all laptops. The browser did not provide GPU frame time or release per-frame GC counters. Per-tab resident process memory was not measured. Zero telemetry placeholders for unavailable counters are not zero-cost results. Native zero-allocation core tests do not establish zero client allocations.

Gamepad/manual held-steering feel, the broader quality-tier/hardware matrix, continuous stress captures and final P06 art budgets remain open. Actual two-machine LAN with WAN disconnected and cross-network Internet testing remain P05 gates.

The [controlled Unity capture](unity/gameplay-combat-recovery.mp4) is a separate artifact. It shows real simulation-driven combat/recovery with controlled initial placement; its exported30fps is not browser performance evidence. Its [comparison summary](unity/visual-capture-summary.json) and [original observations](reference-observations.md) explicitly record different recovery duration and conditions.
