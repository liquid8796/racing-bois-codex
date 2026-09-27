# Second copy-fit amendment: German invite-code heading

Run05's actual lower-scroll screenshots clip the right edge of
`Multiplayer / DEU / multiplayer.browser.invite-heading` at both1920 and1366.
The exact change is `EINEN CODE VON FREUNDEN ERHALTEN?` → `CODE VON FREUNDEN?`.
Only this rendered invitation question changes; layout, fonts, user data,
protocol discriminator and gameplay behavior remain unchanged.

`changes.json` binds both screenshots. `run05-review.json` retains the failed
native result:108captures,963Button samples,162positive width differences, all
at1920 and no larger than0.000091553logical units. Those tiny differences are
consistent with single-precision layout arithmetic, while the visibly clipped
heading is a Label outside that Button-only scan. The original native receipt
remains FAIL. Its early aggregate failure prevented the native final source
assertion; the review separately verifies the frozen preflight inputs afterward.

The generic effective generator starts from the frozen b926 first-fit union and
all four currently installed module snapshots. `before-effective` retains the
prior pointer and shared tooling; `before` retains complete module bases. The
existing ENU semantic correction and DEU/ESP/FRA Career fit amendments remain.
Only a new Multiplayer generated module is emitted. All5550union cells and2364
effective lookups are checked; exactly one cell may differ. Existing248codepoint
font coverage is checked again.

Shared preflight now has explicit Career and Multiplayer candidate overrides,
each replacing exactly one normal compile item. Active changed providers select
their candidate path automatically; unchanged providers use current production
source. Unsupported provider overrides fail instead of validating stale code.
Editor, Windows and Web managed compilations are evidence only, not native fit.

Root validates `python tools/p08/media/global-copy-fit2-amendment/install.py`,
then adds `--install` for a guarded atomic replacement of only the reviewed
Multiplayer C# file. Exact metadata and untouched provider hashes are checked
before and after. Root must refresh/attest current assemblies and run fresh R5
native captures before claiming this heading fits. Frozen earlier artifacts,
including failed run05, are never rewritten.
