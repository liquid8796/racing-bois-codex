# Global display copy — main/shared staged integration

The four coordinated modules contain **394 semantic keys in six languages**:
107 main/shared keys here, 151 Career keys, 102 multiplayer keys and 34 scoped
client/content messages. Cinematic copy remains its separate 531-key catalog.
The counts describe authored data coverage, not visual/linguistic acceptance or
proof that every possible game state has been exercised.

All production edits remain outside Assets until root completes the preceding
native music/milestone/Canyon checkpoint and coordinates installation. The
bootstrap candidate is deliberately based on the frozen milestone candidate,
recorded in `bootstrap-composition.json`; it must not overwrite an intervening
live bootstrap change. Existing source metadata and unchanged newline bytes are
preserved when the final installer is prepared.

## Selection and data boundaries

`DisplayLanguage.FromArguments` recognizes `--language=ENU|DEU|ESP|FRA|ITA|VI` and
the established short/culture aliases. No option preserves Vietnamese. Invalid,
blank, malformed or duplicate explicit options fall back to English. No locale
picker/control or layout was added. The existing `--cinematic-language` remains
an explicit cinematic-only override; otherwise cinematic copy uses `--language`.
No thread/global culture, file config schema, account, server or protocol changes
are made by language selection.

`UiText` owns private display tables and strict named templates. Each argument is
a preformatted string; null values preserve original concatenation semantics as
empty text. Formatting reads placeholders only from the trusted template and
appends argument values verbatim. Player/room/bike/route names, brace-containing
values, addresses, error codes, currency amounts and typed account fields cannot
be recursively interpreted as translation keys/templates.

The source VI text, explicit line breaks and existing numeric precision/format
calls are preserved. Main's canonical source and exact original expression
bindings are frozen by SHA256 before translating its other locales. Each authored
locale is complete; generation refuses missing/extra keys, stale source hashes,
blank/corrupt values, changed placeholder multiplicity, braces, hard line breaks,
currency markers or HUD bounds. English is an authored fallback, not a blank-row
substitute. German/Italian throttle-hold labels describe fixed throttle, not a
target-speed cruise controller.

`UiText.ClientMessage` is used only at the dedicated client-owned error/status
display boundaries. Root's module recognizes exact known VI messages and the
five exact catalog route-loading strings. Unknown data is returned unchanged.
The multiplayer `Máy chủ từ chối: ` prefix and ordered raw error-code routing
remain byte-for-byte intact. Bootstrap's three client messages retain their raw
VI identity and are translated only on display, including subsequent repaint.

## View behavior

The shared UXML differs only by 27 semantic name anchors for previously unnamed
labels (17 main, 10 multiplayer). Its 160-node hierarchy, classes, source text,
default field values and ordering are unchanged. In particular, default and user
player/room names are not translated.

Main and practice preserve numeric choices and suppress quality callbacks while
relabeling dropdown values. A locale change invalidates label caches, retains
focus and event/tick history, and repaints only a currently active cached race
view. Content status/errors retain raw canonical input for display translation.
Native display copy preserves selected mode/resolution and the previous requested
display values; changing locale never calls Screen.SetResolution. The actual Apply
button retains its existing behavior.

Career preserves account drafts, selection/scroll/focus and exact pending
CareerIntent objects while refreshing copy. Its password/recovery/export focus
restoration recognizes the owning field's internal text-input child and suppresses
the competing generic name restore during that refresh. Multiplayer retains field
data and relabels static chrome plus cached rows/countdown.

## Managed verification and native handoff

```powershell
python tools/p08/media/global-copy-main-staging/generate.py
python tools/p08/media/global-copy-main-staging/test_data.py
dotnet run --project tools/p08/media/global-copy-main-staging/CoreTests.csproj
dotnet build tools/p08/media/global-copy-main-staging/BootstrapPreflight.csproj -p:DefineConstants=UNITY_STANDALONE_WIN
```

The composed preflight builds full candidate Application, Presentation and
Bootstrap assemblies with their real assembly names. No duplicate-type warning
suppression is used. Windows/Editor/Web managed builds passed with zero warnings
and errors before final review. Main's 14 data controls and 1,420
source/template/fallback/opaque-value/VI-result-across-four-cultures/UXML-structure
controls passed initially; the final composed six-locale lookup pass covers all
394 keys and brings this suite to **3,142 controls**. Other modules retain their own independent receipts; historical
cinematic and native phase records are not rewritten.

Root's next native checks must use installed/source-attested assemblies and
owned fixtures. Besides exact six-locale bindings, verify:

- Relabeling does not emit preference/quality/commerce/network intents or apply a
  display change; selected choices and current focus remain stable.
- Old MP race tick 600/event 200 → menu → language change → new race tick 0/event
  1 still resets event history. Locale repaint itself must not replay old events.
- Main idle/menu repaint does not resurrect an old race/recovery/results panel.
- Career text-input descendants, dirty account drafts and an open confirmation
  retain their owner, values and exact pending command. Busy requests remain intact.
- Multiplayer names/join code, current filter/state and protocol error mapping
  retain their semantics. Unknown messages/data remain unchanged.

Unattached trees can check bindings/state without font layout; they do not prove
input event dispatch, glyph rendering, wrapping or readability. Actual target
resolution captures and human language review remain required. No visual masks,
authority, campaign rules, audio/voice content or full-game acceptance are changed.

The final `handoff.json` pins 16 reviewed production files plus their metadata
(32 rows). `python tools/p08/media/global-copy-main-staging/install.py` validates
the full set without writes. Root alone uses `--install` with coordinated Editor
refresh, then independently source-attests and performs native checks. The live
bootstrap baseline is the exact published milestone revision; only its reviewed
combined candidate hash was added to the client generator's approved source list.
The client 905-control proof was refreshed against the final shared core with its
earlier receipt preserved. Career's separate `regeneration-v2.json` records the
strict installed-source allowance/source stamps; generated text bytes did not
change and historical input bytes are retained.
