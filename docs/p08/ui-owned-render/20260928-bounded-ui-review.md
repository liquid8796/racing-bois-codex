# Completed native UI copy, focus and scroll review

The bounded Editor UI scope passes at 1920×1080 and 1366×768 for ENU, DEU, ESP,
FRA, ITA and VI. These are actual attached UI Toolkit panels using isolated copied
fonts and synthetic local profile/lobby state; they are not full gameplay scenes.

| Evidence | Verified outcome |
| --- | --- |
| [Run06 native receipt](20260928-ui-render-06-driver.json) | PASS; 108 captures, 963 Button measurements and 12 invite-heading measurements. Actual compact classes match target sizes. Source binding, global state and transient cleanup pass. |
| [Scroll01 native receipt](20260928-ui-scroll-01-driver.json) | PASS; 48 additional captures and 24 top/bottom pairs. Every focused target lies fully within its clipped viewport; lower invite headings are also contained. No gameplay/account command was emitted. |
| [Independent Scroll01 verification](20260928-ui-scroll-01-review.json) | All 48 PNGs decode, match receipt hashes and dimensions, and contain rendered pixels. All 24 pairs have different offsets and image hashes; offset changes range from 193.359375 to 524.999939 logical units. Final source checks pass and frozen preflight inputs still match. |

Run06 retains raw positive float differences for 162 Button samples. Its reviewed
comparison allows at most four float32 ULPs at the involved coordinate scale,
capped at 0.001 output pixel; the largest actual allowance was about 0.000586
pixel. The five historical negative controls still detect genuine overflows.
Failed run05 remains FAIL and is not relabeled.

Run06's retained scroll positions made some nominal top/bottom images identical.
Scroll01 closes that specific coverage gap with explicit low/high offsets,
containment checks before and after native focus, and distinct pair identities.
The checks require offset differences as well as different image hashes, so a
focus-border change alone cannot establish scrolling.

Actual visual inspection confirms the shortened German invite heading
`CODE VON FREUNDEN?` fits at both sizes. The 1366 German browser top/bottom and
account top/bottom views show the expected distinct content with visible focus.
German lower account controls at both sizes and French/Vietnamese lower account
controls at 1366 remain readable, with no newly confirmed overflow in these
inspected views. The earlier Career pristine labels retain their validated copy
correction. The full PNG inventory and hashes are retained in the independent
verification receipt; its script is
`tools/p08/media/owned-ui-scroll-review/verify.py`.

This completes the stated copied-font UI copy/focus/scroll exercise. Physical
input devices, arbitrary player-name glyph coverage, full gameplay, final 2D/3D
concept fidelity and release acceptance remain separate gates. Original scenes,
source fonts and earlier evidence were preserved.
