# Output-size correction

RaceScreen previously derived responsive breakpoints from global Screen dimensions
even when its UIDocument rendered into a smaller target texture. The owned review
could therefore produce a 1366 x 768 PNG while retaining the 1920 layout.

The candidate retains the initialized document and reads its current target-texture
dimensions when present. Ordinary desktop documents still use Screen dimensions.
Update and GeometryChanged share the same output-size lookup; breakpoint values,
race-state classes and input behavior remain unchanged. The exact prior source is
retained. This candidate also removes two whitespace-only lines and normalizes the
prior mixed line endings to CRLF; these formatting differences have no behavior.

The Windows Presentation and composed Editor Application/Presentation/Bootstrap
preflights passed without warnings or errors. Native run05 then observed all 108
expected compact/narrow states: Screen stayed 1920 x 1080 while the 1366 target
correctly activated compact styling. Run05 remains failed for its separate exact
float-comparison premise. Run06 passes the corrected native measurement checks.

Both runs retain actual PNGs, source/assembly identities and original-font checks
under `docs/p08/ui-owned-render`. Their separate scroll-position coverage caveat
is recorded there; this change is not full-game or concept-fidelity acceptance.
