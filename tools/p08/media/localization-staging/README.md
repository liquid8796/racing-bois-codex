# Cinematic display-copy localization

This patch supplies original authored display translations for ENU (English),
DEU (German), ESP (Spanish), FRA (French), ITA (Italian) and VI (Vietnamese).
The frozen inventory has 531 keys: 59 titles, 59 synopses, 389 captions and 24
gallery/control/role messages. Repeated English text is authored once in each
488-row worksheet, then expanded to explicit scene/beat keys. Bike and rider
names retain their authored identity. These are translations of Racing Bois
storyboards, not extracted dialogue from reference videos.

The original `CinematicCatalog.cs`, storyboards, direction generator, cameras,
durations, actors, audio, masks and concepts remain unchanged. Display keys use
the exact scene ID plus `title`, `synopsis` or `beat/<authored index>`. Source
English and complete storyboard bytes are hash-bound. The generator rejects
missing/extra/duplicate keys, blank strings, stale sources and malformed or lost
format arguments. Production copy does not fill gaps with placeholders. Runtime
uses English for unsupported locale requests and only uses a translated scene
field if its frozen English still equals the catalog field; changed catalog
text therefore cannot silently inherit an obsolete translation.

No game-wide language selector exists in the current client. The gallery keeps
its existing Vietnamese default. Windows users can select this surface only:

```text
RacingBois.exe --cinematic-language=DEU
```

Supported canonical values are `ENU`, `DEU`, `ESP`, `FRA`, `ITA`, `VI`; common
two-letter/culture tags are normalized (for example `fr-CA` → `FRA`). The option
uses the explicit equals form. Missing option preserves VI. A blank, malformed,
unsupported or duplicate explicit option selects ENU. Other UI and voice are
unaffected. Web uses VI until a future locale selector calls the existing public
`CinematicGalleryView.SetLocale` integration point. SetLocale updates current
titles/captions/controls while retaining the selected category and scene. A
pre-initialization choice is retained unless Initialize receives an explicit
locale override. Culture suffixes accept an optional four-letter script and
optional two-letter or three-digit region; malformed tags fall back to ENU.

Localized controls include role filters, buttons, scene/shot counts, loading and
failure messages. Numeric time display remains minutes:seconds. The director
now exposes stable error codes so the coordinator can choose display copy
without translating exception names. Diagnostic `LastError` remains available.

The five production C# sources are staged here while native build work completes;
the source catalog is never hand-edited. New generated copy belongs to the
Application assembly, while existing Gallery/Director/Coordinator changes stay
in their current assemblies. There is no new package, network request, model
service, paid API, player-data authority or layout/control hierarchy.

Generation and focused verification:

```powershell
python tools/p08/media/localization-staging/author_locale.py VI tools/p08/media/localization-staging/VI.tsv
python tools/p08/media/localization-staging/generate.py
python tools/p08/media/localization-staging/test_generation.py
dotnet run --project tools/p08/media/localization-staging/CopyTests.csproj
dotnet build tools/p08/media/localization-staging/Preflight.csproj -p:DefineConstants=UNITY_EDITOR
dotnet build tools/p08/media/localization-staging/Preflight.csproj -p:DefineConstants=UNITY_WEBGL
```

Other authored worksheets are `ESP.rows.tsv`, `FRA.rows.tsv`, `DEU.rows.tsv` and
`ITA.tsv`. `author_locale.py` checks that the frozen inventory still matches
current English before expanding rows; it cannot silently rebind old text to a
changed source. `prepare_source.py` is only for deliberate source-inventory
updates followed by translation review, not normal generation.

Managed coverage/fallback controls are not native rendering or linguistic
acceptance. Actual UI text wrapping, glyph availability, caption readability at
target resolutions, full playback and review by speakers remain open. Required
DEU/ENU/ESP/FRA/ITA parity covers the whole game; this patch localizes only the
cinematic surface. Other UI, content, voice and all visual gates remain open.

Final staged managed validation is bound in `validation.json`: 12 data controls,
6,327 exact lookup/projection/fallback assertions and Editor/Windows/Web
preflights with zero warnings/errors. Independent review prompted stricter
culture-tag validation, preservation of a pre-initialization language choice,
and three VI/ITA wording corrections. These checks verify wiring/data contracts,
not translation quality scores.

`handoff.json` freezes exactly five production source files and their metadata.
`python tools/p08/media/localization-staging/install.py` is read-only validation;
the same command with `--install` performs the coordinated installation only
after all original/candidate hashes pass. Existing metadata is preserved.

`NativeCopyProbe.body.cs` is an optional root-owned native binding check after
installation. Its exact default-tool wrapper is compiled in
`checks/NativeCopyProbe.cs` by `ProbeCompile.csproj`. It creates an owned preview
scene and an unattached UIDocument (`panelSettings == null`, `panel == null`),
checks six locales, all 59 list/detail selections, all 389 caption bindings,
category/scene retention, keyed errors and English fallback, and destroys its
owned objects/scene in finally. The caption checks deliberately set only the
owned director's read state by reflection; they do not start playback, instantiate
actors, assign a panel, invoke font APIs, render, save assets or prove readability.
Its returned scope flags explicitly distinguish this from actual playback.
