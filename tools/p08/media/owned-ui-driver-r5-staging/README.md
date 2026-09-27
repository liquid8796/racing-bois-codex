# Attached UI R5: bounded floating-point comparisons and invite heading

R5 retains the actual copied-font isolation, focus/navigation, target-only clear,
responsive-class checks and 108 captures from R4. Frozen run05 remains FAIL. Its 162
strict Button flags were no greater than 0.000091553 logical units; all were at 1920.
The new policy addresses float32 layout arithmetic without changing UI geometry,
font size or native measured values.

Both raw native widths and their signed difference remain in every row. The
rounding bound is the smaller of:

1. Four float32 ULPs at the largest involved layout-coordinate/width magnitude.
2. One thousandth of one actual output pixel, converted to local logical units.

The coordinate term allows a few rounding steps when layout origins/endpoints,
padding and widths are combined. This is a numeric diagnostic bound, not a font
fit margin. The independent 0.001 output-pixel cap prevents large coordinate
magnitudes from masking clipping. Local-to-panel horizontal scale is read from
the actual element transform; target/root width supplies panel-to-output scale.
Nonfinite, nonpositive or non-axis-aligned geometry fails. Each row records the
scales, ULP, logical/pixel bounds, raw delta and strict comparison alongside the
bounded result. Images remain mandatory visual evidence.

The pure helper is replayed against all 963 samples from the exact hash-bound
failed run05 receipt, including all 162 strict failures. All three large historical
pristine overflows must remain rejected. Separate cap controls at four output
scales reject a 0.002 pixel excess even with million-unit coordinates; exact equality,
known IEEE 754 ULPs and invalid measurements are also checked. These controls do
not rerun Unity or change the original receipt's result.

The specific `mp-copy-invite-heading` Label is measured in all 12 lower-scroll
locale/size captures, in addition to visible single-line Buttons. Its current
text must fit. The exact previously clipped German heading is measured as an
argument in the same native Label at both sizes and must fail even with the tiny
rounding bound; no text is assigned or layout changed for this negative control.
The three historical 1920 pristine negatives remain required; their 1366 versions
remain observations because run05 introduced correct compact styling.

After all 108 captures, global-state and current source/DLL checks run before the
aggregate fit assertions, so a fit failure no longer skips those final checks.
Earlier failures still remain failures and do not fabricate unexecuted evidence.

Root must install the reviewed fit2 Multiplayer module, refresh and provide the
fresh settled source proof before final preflight:

```powershell
python tools/p08/media/owned-ui-driver-r5-staging/preflight.py --proof <fresh-source-proof.json> --union tools/p08/media/global-copy-fit2-amendment/authored-text-union.json
```

Load the unchanged OwnedUiRenderR2 DLL and the fresh
`bin/Debug/netstandard2.1/RacingBois.Tools.AttachedUiDriverR5.dll`. Public type stays
`RacingBois.Tools.NativeUi.AttachedUiDriver`; call `Start(freshRunId,proofPath,unionPath)`
once and use `Snapshot()` or the fresh receipt for progress. No helper/runtime
source changes are allowed during the run. The new result remains separate from
run05 and does not constitute full-game, physical-input, concept or release acceptance.

Frozen initial R5 invocation after root's settled ten-assembly proof:

```csharp
AttachedUiDriver.Start("20260928-ui-render-06",
    "docs/p08/desktop/compiled-sources-safe-20260928-02.json",
    "tools/p08/media/global-copy-fit2-amendment/authored-text-union.json");
```
