# Owned UI rendering and native navigation

Run `20260928-ui-render-04` produced 84 actual UI-only PNGs: six languages,
seven view states and two target-texture sizes. Its 545 native checks pass,
including real panel focus/NavigationSubmit dispatch, account draft/focus
preservation through locale changes and exactly one create/ready/rematch intent
per synthetic submit. No network or physical input device was used.

[Independent verification](20260928-ui-render-04-verification.json) checks every
PNG's hash, dimensions and decoding, its paired layout/preservation receipt and
the original source-file hashes after release. Both copied fonts warmed all 248
authored codepoints. Original font source/meta, member identity/dirty/serialized
state and atlas pixels were verified throughout. Transient document, texture and
preview objects were released; owned font/UI copies remain private and ignored.

**This is not visual-fit, responsive-layout or full-game acceptance.** Root's
actual image review found the DEU pristine-state button text overflowing. Further
review also found overlong ESP/FRA equivalents. A separate copy-fit amendment is
in progress. The review also found that RaceScreen reads global Screen dimensions
for breakpoints: merely changing its offscreen texture to 1366 x 768 does not
prove the compact layout. A separate target-size correction and fresh native
run are required; run04 is retained as the preceding pixel-resolution evidence.

These captures contain no gameplay background, bike or rider render. Original
MainPanel has no explicit PanelTextSettings; the fixture deliberately supplies
owned default/fallback fonts and an owned root font. That dependency isolation
is disclosed and is not proof of original implicit fallback behavior. The actual
locked UI concepts remain unchanged and visually unaccepted.

## Preserved attempts

- `20260928-global-ui-01`: preparation failed because renaming the copied font
  generated a Unity ImportLog object, rejected by strict member validation.
  Original font bytes and native member/atlas state were unchanged. R2 keeps
  the copied font's original name; the allowlist was not relaxed.
- `20260928-global-ui-02`: native ownership/prewarm/closure passed, and root
  inspected an English menu image. The manual run established the required
  owned-panel Update, Repaint and Render order and clean release.
- `20260928-ui-render-03`: four English captures and account focus checks ran,
  then a newly revealed multiplayer field was focused before layout settled.
  The run failed and released cleanly. Its images also retained previous-frame
  pixels because an offscreen panel without a camera did not clear its target.
  These images are rejected for clean-frame visual review.
- `20260928-ui-render-04`: the driver waits real update frames before focus and
  clears only its owned target before each render, restoring RenderTexture.active.
  The source panel settings stay unchanged. The full native event/capture run
  passes; the visual and breakpoint findings above remain open.

Frozen helpers live in `tools/p08/media/owned-ui-render*-staging` and
`owned-ui-driver*-staging`. The source-bound managed preflights are preparation,
while the native receipts identify the DLLs actually executed. Run04 uses the
amended `global-copy-pristine-amendment/authored-text-union.json`, not the older
union shown in the first driver's historical example command.
