# Multiplayer display-copy templates

This module owns only staged MultiplayerLobbyView/MultiplayerCopy presentation
changes and their canonical templates. Production Assets, application/network
state and the shared Race.uxml are unchanged.

`canonical-source.json` binds the exact three original source files and contains
102 Vietnamese semantic templates with named argument sets and source bindings.
There are 28 server-error message mappings and 24 UXML text/tooltip targets.
`worksheet.tsv` is the canonical worksheet. The subsequent authored ENU, DEU,
ESP, FRA and ITA row files each cover all 102 keys, with exact placeholder sets.
`locales/*.json` bind those 510 translations to the frozen canonical SHA.
`coverage.json` records the current authored coverage; the canonical document's
preparation flags remain the original template-only snapshot. `generate.py` implements
`static partial void AddMultiplayer(Dictionary<string,string[]> rows)` with
values ordered ENU, DEU, ESP, FRA, ITA, VI in UiText.Multiplayer.Generated.cs.
The resulting 612 slots include the unchanged canonical Vietnamese text.

Dynamic room counts, level mismatches, invitation messages, result times and
wallet rows are whole templates. Numeric values retain existing precision at
their call sites. Player/room names, route titles, invitation codes/URLs and
formatted values are opaque arguments. They are never translated, reparsed or
used to choose a localization key.

MultiplayerCopy preserves the exact internal `Máy chủ từ chối: ` discriminator
and the complete ordered server-code switch. Only the mapped display message is
localized. Other raw errors pass to the shared UiText.ClientMessage classifier
at this dedicated presentation boundary; unknown raw messages remain unchanged.
Content status follows the same display-only boundary. No protocol codes,
exception routing, message setters or authority decisions are localized.

MultiplayerLobbyView exposes Locale, accepts optional Initialize(document,
locale=null), and preserves a prior SetLocale choice. Changing locale invalidates
the cached room/browser/result rows and countdown; stored transient errors keep
their key and arguments. User-entered room names, invite codes and lobby intents
are not rewritten. The main module must pass its selected locale to lobby
initialization and to MultiplayerCopy.Error calls outside this view.

`uxml-bindings.json` belongs to the shared Race.uxml owner. Existing names are
retained; currently unnamed text targets have explicit semantic mp-copy names
(eyebrow, create heading, route label, invite hint, and similar roles). Keys and
anchors never encode XML traversal ordinals.
The room-name field value is actual user/server data and is excluded entirely,
including its default `Cùng lên đường`; no initialization or locale-change path
rewrites it. Dynamic labels keep their current
script-controlled keys. No layout/style/typography or concept acceptance changes
are proposed.

Reproduce and validate the staged candidates:

```powershell
python tools/p08/media/global-copy-multiplayer-staging/prepare.py
python tools/p08/media/global-copy-multiplayer-staging/generate.py
python tools/p08/media/global-copy-multiplayer-staging/validate.py
```

The validator checks exact original hashes, key uniqueness, complete named
placeholder sets, preserved routing prefix/server codes and consumed keys, then
compiles the two presentation files against the shared staged UiText core and
installed Unity modules. It also runs 1441 managed checks on the exact six-locale
table, opaque inserted values and raw server-code/error boundaries. These checks
are not independent linguistic review, rendered layout tests or full-game
acceptance. The shared UXML owner still needs to compose the semantic anchors;
all production installation and native UI review remain root-owned.
