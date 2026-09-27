# Opt-in Windows player observer

The `DesktopAcceptanceRecorder` observes the actual Windows player with `RaceBootstrap`, UI, input, audio and rendering running normally. It does not alter input, start a race, change graphics settings, force focus, restart a level or quit the player. It is inactive unless the process receives exactly one `--rb-qa-config` argument, and it is excluded from Editor and Web runtime branches.

## Prepare after the actual accepted native build

```powershell
python tools/p10/prepare-player-qa.py --player-root Build/Desktop-P08 --screenshots
```

The preparation tool first runs the existing P08 full installation/source audit. It then writes a unique `docs/p10/player/<run-id>/config.json`, preserves the exact audited `build-receipt.json`, and writes `launch.json`. The config's output is a fresh `runtime` directory outside the immutable installation. Preparation fails when the real build/manifest/player file hashes or current source differ. No mock or missing build can prepare a native acceptance run. Reading the installation during this audit can warm the operating system file cache: this procedure is **not a cold-disk loading benchmark**.

Launch the exact executable and argument array in `launch.json` through the normal authorized player/Unity workflow. The argument array includes an external `-logFile` path. This document does not authorize OS UI automation. Use direct Unity MCP/purpose-built in-game operations or actual player input. The recorder leaves the user in control.

The runtime verifies the supplied build receipt SHA, source fingerprint, actual executable, actual loaded Bootstrap assembly, installed content manifest and successful Windows build identity before recording. An invalid config logs only a stable rejection marker and exception type. Existing output files are preserved; no recorder output can be written inside the installation or through an existing symlink/junction parent.

## Measurement and limits

1. Enter a normal playable race with loaded production content before the default 300-second wait deadline.
2. The recorder waits for ten seconds of continuously loaded live race warmup, then records every Unity `LateUpdate` interval for at least 600 real seconds.
3. Menus, cinematic frames, stalls, resizing, lost focus and interrupted input remain in that fixed time window. They are not removed to improve statistics. A bounded preallocated 180,000-frame buffer prevents silent truncation or unbounded allocation.
4. Raw intervals and content/tick/quality/window/UI/focus state are stored in `raw-frames.csv`. Process/Unity/managed/graphics-driver memory is sampled once per second; graphics-driver allocation is not dedicated GPU residency. CPU/GPU timings may lag or repeat; their native timestamp is retained. Missing counters remain blank, with availability counts in the receipt.
5. Optional three screenshots are requested near the beginning, middle and end; their overhead remains in measured intervals. Final receipt binds actual PNG and CSV bytes. No screenshot implies visual/concept acceptance by itself.

The recorder's narrow performance PASS requires:

- A complete 600-second window, at least 95% loaded live-race coverage and 80% moving-rider coverage (over 1 m/s) to prevent an idle menu or parked-bike benchmark from passing as driving.
- At least 99% foreground focus, real mounted UI and Medium/1920×1080 coverage; at least 95% coverage with a checkpoint that advanced within the preceding 0.25 seconds. The latter accounts for the real 20 Hz read-model projection.
- Observed mean at least 60 FPS, p95 frame time at most 20 ms, sampled peak working set at most 2 GiB, zero runtime warnings/errors, and unchanged bound player/manifest/build identities.

No unavailable GPU/GC counter is invented as zero. A timing PASS still cannot close an unmeasured dedicated GPU-memory or external hardware profiling gate. Observer memory, memory sampling and periodic small status-file writes are included in the measurements. The recorder never relabels an interrupted or insufficient-coverage run as complete.

## Independent raw verification

After `runtime/receipt.json` exists:

```powershell
python tools/p10/verify-player-qa.py --run-directory docs/p10/player/ACTUAL-RUN-ID
```

This re-audits current installation/source bytes and independently derives frame count, full elapsed time, FPS, quantiles, counter availability and coverage from the actual CSV. It rejects dropped/repeated frame indices, inconsistent intervals, tampered files, incomplete runs and summaries that differ from the raw data. It does not trust a boolean `passed` as sufficient evidence. Existing verification receipts are preserved.

The 9 configuration policy tests and 8 raw-evidence negative tests are verifier tests only. Three managed branches compile against the installed Unity 6000.5.7f1 references; this is not evidence of an actual 600-second player run. The recorder is ready for root's real player acceptance after art/content/build completion. It does not establish exact concept fidelity, physical gamepad actions, full campaign, two-machine offline LAN, public-region latency or whole-release completion.
