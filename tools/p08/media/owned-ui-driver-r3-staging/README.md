# Attached UI driver R3: output breakpoints and action fit

This fresh diagnostic revision retains R2's copied-font preservation, panel-only
pump, per-frame target clear, real layout barriers, focus and NavigationSubmit
checks. It does not modify frozen R1/R2 helpers or run03/run04 evidence. Run04's
1366 PNGs establish target pixel dimensions, not the intended compact breakpoint:
the old RaceScreen read the editor Screen dimensions even for an offscreen panel.

R3 requires the reviewed target-texture-aware RaceScreen and the current effective
copy-fit union. Every capture records actual Screen dimensions, target dimensions,
logical surface bounds and actual/expected compact and narrow classes. Neither
class is set by the driver. The 1920 and 1366 cases exercise non-compact and compact
outputs; neither is claimed to exercise the narrow=true branch.

Each displayed single-line Button is measured using native TextElement.MeasureTextSize
with unconstrained width, against its own contentRect in the same logical units.
Disabled actions are included. Hidden ancestors and wholly clipped scroll content
are excluded. The receipt retains all measured widths, content widths, overflow,
text, enabled state and isElided; overflow does not stop remaining captures, but
fails the final fit check. Measurements supplement actual PNG review and cannot
establish concept fidelity or arbitrary user-name coverage.

Six negative controls measure the exact historically overflowing DEU/ESP/FRA
pristine strings in the same actual button and require that they exceed its
content width at both sizes. This does not assign those strings or mutate any
element; it checks that native measurement detects the observed pre-fix defect.

The original seven viewports plus the scrolled Career account bottom and multiplayer
Create/Join actions produce 108 PNGs (nine viewports, six locales, two resolutions).
Scroll changes use each actual ScrollView's current range; no hierarchy, layout,
font size or authored source is changed. The empty UI-only background remains
explicit and must not be interpreted as a complete gameplay screenshot.

Root must finish live installation and source attestation before the final compile:

```powershell
python tools/p08/media/owned-ui-driver-r3-staging/preflight.py --proof <fresh-proof.json> --union <effective-union.json>
```

Load the unchanged OwnedUiRenderR2 DLL and then the new
`bin/Debug/netstandard2.1/RacingBois.Tools.AttachedUiDriverR3.dll`. Public type:
`RacingBois.Tools.NativeUi.AttachedUiDriver`. Invoke
`Start(freshRunId, freshProofPath, effectiveUnionPath)` once, then inspect `Snapshot()`
and the fresh driver receipt. `Abort()` retains bounded detach/release cleanup.
Do not retry a reflective invocation before inspecting progress and all nested
exceptions. Do not recompile or reload while a native run is active.

The initial frozen R3 handoff uses the settled installed sources attested by
`docs/p08/media/global-copy-fit-viewport-compiled-sources-20260928.json` and union
`tools/p08/media/global-copy-fit-amendment/authored-text-union.json`:

```csharp
AttachedUiDriver.Start("20260928-ui-render-05",
    "docs/p08/media/global-copy-fit-viewport-compiled-sources-20260928.json",
    "tools/p08/media/global-copy-fit-amendment/authored-text-union.json");
```
