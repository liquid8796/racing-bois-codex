# Localized fit and actual target-size verification

The production patch fixes three overlong pristine-state labels (DEU, ESP, FRA)
and one German Multiplayer invite heading while retaining the ENU undamaged-state
correction. It also makes RaceScreen read its UIDocument target-texture dimensions
for offscreen responsive layout; ordinary desktop UI still reads Screen.

[Run06](20260928-ui-render-06-driver.json) passes 1,976 native checks and produces
108 actual PNGs. All 963 single-line Button measurements and 12 invite-heading
measurements fit. All 108 observations confirm the expected compact/narrow classes
for the actual 1920 x 1080 and 1366 x 768 targets, while global Screen remains
1920 x 1080. The fresh source/assembly checks reach completion, original global
settings stay unchanged and transient render objects are released.

[Independent file verification](20260928-ui-render-06-verification.json) checks
the PNG bytes, decoding, paired layout/font receipts, fit/breakpoint observations
and current original UI/font file hashes. Separate installed native contracts
also pass all 5,743 checks against the final effective 5,550-cell union in
`../media/global-copy-fit2-native-contracts-20260928.json`.

Run05 remains **FAIL**. Its strict float comparison flagged 162 widths whose
largest excess was 0.000091553 logical units; no Button was confirmed visibly
clipped. R5 records the raw/strict results and permits only four float32 ULPs,
capped at 0.001 actual output pixel. Historical visibly overflowing strings remain
strong negative controls. This is numerical comparison precision, not a visual
fidelity allowance or a reinterpretation of the old failed run.

The new lower-scroll views exposed the German heading defect and verify its
correction at both sizes. However, scroll offsets persisted between locale cases:
12 top/bottom pairs in run06 are byte-identical. Its 108 captures therefore do
not establish 108 distinct scroll viewports. A separate bounded 48-image follow-up
will explicitly reset top/bottom positions and require focused targets inside the
clipped viewport. Other valid run06 fit/navigation observations remain recorded.

No gameplay backdrop or bike/rider art is present in these isolated UI images.
Full-game, physical-input and locked-concept acceptance remain false.
