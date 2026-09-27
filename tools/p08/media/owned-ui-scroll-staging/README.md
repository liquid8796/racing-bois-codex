# Owned UI scroll coverage follow-up

Run06 passed its native fit/navigation/source-preservation checks, but persistent
ScrollView offsets meant several nominal top and bottom images were identical.
That result remains unchanged. This separate helper fills only that coverage gap:
two areas (Career account and multiplayer browser), two scroll edges, six locales,
and two output sizes produce 48 captures. Menu/settings/waiting-room/results are
not captured again, and production UI behavior/source remains unchanged.

For every locale and area, the driver explicitly assigns the actual native low
scroll offset, waits for layout, then focuses a target already fully contained
by the clipped viewport. It checks containment again after real focus and before
capture. Top targets are Career username and multiplayer room-name TextFields.
For the bottom capture it explicitly assigns the current high offset, waits,
then focuses the real export or join Button. The multiplayer invite heading must
also lie fully inside the viewport. No private callback invocation is used.

Each image receipt records target and viewport bounds, offsets/ranges, actual
focus, output dimensions and responsive classes. Each of the 24 top/bottom pairs
records both image identities. If scrolling is available, both offsets and image
hashes must differ. A zero-range area is explicitly reported, not falsely called
a distinct scroll exercise. Synthetic room/profile values must remain unchanged;
focus and scrolling must emit no gameplay/account command.

The driver preserves the already proven OwnedUiRenderR2 copied-font preparation,
root-scoped Update/Repaint/clear/Render pump, detach barrier, cleanup, and current
source/DLL/text-union binding. Only synthetic local transports are used. It never
changes Screen size, global quality, PlayerPrefs, source fonts, original scenes,
or frozen run06 helpers. Persistent owned font/UI copies remain retained.

`prepare_driver.py` is a one-time source derivation pinned to the frozen R5 source
SHA; it refuses an existing destination. The generated C# is the reviewed helper
source, not a runtime patch. Compile only after root confirms source stability:

```powershell
python tools/p08/media/owned-ui-scroll-staging/preflight.py --proof docs/p08/desktop/compiled-sources-safe-20260928-02.json --union tools/p08/media/global-copy-fit2-amendment/authored-text-union.json
```

Load the unchanged OwnedUiRenderR2 DLL and then
`bin/Debug/netstandard2.1/RacingBois.Tools.OwnedUiScrollDriver.dll`.
Public type: `RacingBois.Tools.NativeUi.OwnedUiScrollDriver`.

```csharp
OwnedUiScrollDriver.Start("20260928-ui-scroll-01",
    "docs/p08/desktop/compiled-sources-safe-20260928-02.json",
    "tools/p08/media/global-copy-fit2-amendment/authored-text-union.json");
```

Inspect `Snapshot()` or the fresh driver receipt; `Abort()` keeps bounded cleanup.
No assembly/source reload is allowed during the run. Native success here covers
the stated scroll/focus views, not physical input devices, full gameplay, concept
fidelity or release acceptance.
