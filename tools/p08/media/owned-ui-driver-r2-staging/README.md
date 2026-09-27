# Attached six-locale UI render driver — R2

R2 preserves the failed run03 receipt/captures and adds a real four-update
layout barrier before focusing a newly revealed target. Failures include the
target name, type, bounds, display/visibility/opacity and enabled state. It also
clears only the owned target texture immediately before each Render, restoring
RenderTexture.active afterward. The copied source panel's clearColor setting is
unchanged. This replaces the missing scene-camera clear in an offscreen UI-only
fixture; run03 images with accumulated old text are not clean-frame evidence.

This separate helper consumes the frozen, native-proven OwnedUiRenderR2 fixture.
It does not change production source or the base fixture. It references actual
installed view/application/protocol assemblies and reuses the synthetic transport
fixtures from the independent unattached UI contracts. No real network, credentials
or gameplay authority is involved.

The driver loads the actual RaceScreen, CareerView and MultiplayerLobbyView on
the owned copied-font UIDocument. It pumps only that panel in root-verified order:
`Update(); Repaint(new UnityEngine.Event { type = EventType.Repaint }); Render();`.
It never calls global UIElementsRuntimeUtility methods. Event is not IDisposable.

For each of ENU/DEU/ESP/FRA/ITA/VI at 1920×1080 and 1366×768, it captures:

- menu and settings;
- career garage and account;
- multiplayer browser, waiting room and official synthetic results.

That is 84 actual PNGs with paired base-fixture source/font/layout receipts.
No 3D bike thumbnails or gameplay backdrop is synthesized; these are UI-only
captures, so art/concept acceptance remains separate. Missing/clear/unlaid-out
targets fail instead of creating a fabricated capture.

Controls use the real panel focus controller and NavigationSubmit event route,
not private Clickable.Invoke or direct view callbacks. They require one create,
ready and rematch intent per submit. Settings/career tabs open/close by submit.
The account case checks internal TextField-child focus and opaque password/name
draft retention across locale repaint. Locale changes must preserve selected
quality/player data and emit no gameplay/preference commands.

CareerSession is not IDisposable. Cleanup invalidates only this synthetic
session's callback generation, clears its private wire callback/store/profile,
and lets CareerView.OnDestroy detach Changed when the owned GameObject is
released. MultiplayerSession is disposed. The driver detaches the document,
waits four editor updates without resetting the detach barrier, then releases
owned transient objects. Persistent copied fonts/UI assets remain retained.

## Root invocation

First dispose any manual attached fixture so the editor is quiet. After final
source/DLL attestation:

```powershell
python tools/p08/media/owned-ui-driver-r2-staging/preflight.py
```

Load `RacingBois.Tools.OwnedUiRenderR2.dll` and then
`bin/Debug/netstandard2.1/RacingBois.Tools.AttachedUiDriverR2.dll` once.
Public type: `RacingBois.Tools.NativeUi.AttachedUiDriver`.

```csharp
AttachedUiDriver.Start(
    "20260928-ui-render-04",
    "docs/p08/media/global-copy-pristine-r2-compiled-sources-20260928.json",
    "tools/p08/media/global-copy-pristine-amendment/authored-text-union.json");
```

Use reflection if the calling dynamic wrapper has not registered the helper
reference. `Start` returns immediately; poll `Snapshot()` or inspect the fresh
`docs/p08/ui-owned-render/<runId>-driver.json` receipt. `Abort()` starts bounded
detach/release cleanup. Unwrap all InnerException layers and inspect progress
before retrying an invocation. Do not reload/recompile during the native run.

The helper checks the independent expected MVID/source/DLL proof and all 5550
authored text cells before creating UI, then binds input hashes through completion.
Global quality/display/PlayerPrefs must remain unchanged. Native success requires
the complete capture count and cleanup. Human visual inspection, physical input
devices, arbitrary usernames, full gameplay and release acceptance remain open.
