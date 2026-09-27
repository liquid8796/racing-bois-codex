# P08 desktop UI implementation

The primary client is native Windows 10/11. The Web implementation remains compile-compatible and is secondary. Backend authority remains on the OCI VM; changing the presentation does not grant the client account, currency or simulation authority.

## Concept provenance and implementation direction

All five concepts in `ArtSource/Concepts/P08/UI` were generated and visually inspected **before these layout edits**. `PROVENANCE.md` records the provider limitation: the built-in tool does not identify an exact GPT Image version. Generated prices, statistics, manufacturer markings, years, slogans and input bindings are not game data. Production text comes from real catalogs/read models; the concept images are not pasted into the functioning UI.

| Inspected concept | Implemented screen and actual content |
|---|---|
| `ui-main-v1.png` | Flat left action rail, prominent selected route/level/bike, offline-practice explanation, progressively expanded server form; the original live 3D stage fills the open scene. |
| `ui-garage-v1.png` | Flat owned/catalog index, retained browse selection, authoritative condition/price/actions, comparison against equipped bike; independent preview events display original indexed 3D actors without equipping them. Eight identities support all 24 loaded portrait states. |
| `ui-lobby-v1.png` | Flat numbered member rows and explicit empty seats, separate six-character invite rail, route/level/privacy from the actual room, fixed ready/start/leave footer. No invented per-player ping. |
| `ui-hud-v1.png` | Position/progress upper left, health/condition lower left, speed lower right; road center stays open. Combat inputs remain Q/E left/right and Shift+Q/E kick. Practice reward text explicitly refers to the local session. |
| `ui-gallery-v1.png` | Flat categorized sequence list, synopsis/duration from the real 59-entry catalog, actual 3D playback, restrained caption safe zone and visible skip. Shared USS replaces inline color/layout duplication. |

Graphite, warm ivory and restrained amber are shared USS tokens. Actions use 44–48 px minimum heights. Ownership, readiness, locks and errors have text labels as well as color. Lists, account actions and campaign rows scroll/wrap at compact widths. The scene remains real 3D; screenshots of concepts are never used as production game screens.

## Architecture and behavior

Existing application sessions and immutable read models retain all economy/network authority. Views render read models and emit `CareerIntent`/lobby actions. The three persistent-document views use a small `UiBindingScope` to own button/value/event subscriptions; disposal unbinds document callbacks, removes owned rows/elements and restores disabled siblings. No new global event bus or UI framework was added.

Loading **and failed-but-retryable content** share explicit modal ownership. Both block gameplay, disable underlying screen containers, move focus to the modal/retry control, consume Tab/Escape and restore the prior focus/enabled state when dismissed by successful loading. Connection updates continue independently. Career responses retain nonsecret username, browse selection and per-tab scroll; passwords/recovery/import text still clear. Gallery time text updates when its displayed second changes, while the progress bar remains continuous.

Native display settings use an isolated `DesktopDisplaySettings` adapter. On Windows players it lists `Screen.resolutions` plus the current window size and the real Unity windowed/borderless/exclusive modes. An explicit Apply issues `Screen.SetResolution`; the UI does not claim monitor support, persistence or measured performance before runtime acceptance. These display APIs are excluded from Editor/Web execution. The settings focus boundary includes these additional controls.

## Verification and remaining native acceptance

`python tools/p08/ui/preflight.py` passed real Roslyn compilation against installed Unity 6000.5.7f1 assemblies for Standalone Windows, Editor and retained Web branches with zero compiler errors/warnings. Actual UXML parsing found 92 unique named elements (the prior 91 plus the selected-menu summary), and all 94 queried name/type bindings passed. Stylesheets and five PNG concept files exist; SHA-256 source bindings are in `desktop-ui-preflight.json`.

This is **source/managed preflight**, not proof of Unity importing USS/UXML, native rendering, human visual quality, keyboard/gamepad behavior or display-mode application. Root must run the final source/build-bound native checks at 1280×720, 1366×768, 1920×1080, 2560×1440 and ultrawide; inspect long player/room names and scaling; deliberately fail/retry a content load; exercise account rejection, repeated view replacement, each preview identity, settings focus including native display controls, actual cinematic caption/skip and reduced motion. Such checks must be recorded as observed results. Concept presence and compiler success do not close the P08 content-parity ledger.
