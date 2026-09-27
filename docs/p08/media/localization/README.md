# Cinematic copy: six locales, native binding verified

The cinematic gallery now displays ENU, DEU, ESP, FRA, ITA or VI copy through stable scene/beat keys. Each locale has 531 explicit keys: 59 titles, 59 synopses, 389 captions and 24 controls/role labels. The original catalog/storyboards, scene timing, audio and asset selections are unchanged. Vietnamese remains the default; Windows accepts `--cinematic-language=FRA` (or another supported code). Unsupported or malformed explicit values fall back to English. This selects cinematic copy only, not the whole game's language.

The source generator rejects incomplete, duplicate, stale or malformed locale data. Display projection checks the current English against its frozen source before using translated text, preventing an old translation from replacing a changed scene field. Runtime locale changes retain the selected scene/category and update current captions, loading/error text and controls.

Independent review corrected malformed culture-tag handling, a pre-initialization locale being overwritten, and several translation ambiguities. All six final locale files are bound by the generated source. Twelve data controls, 6,327 pure runtime assertions and Editor/Windows/Web managed preflights passed with zero warnings/errors.

After installation, actual Unity compilation had no errors. PE/PDB/source checks passed; the live Application, Presentation and Bootstrap module IDs exactly match `compiled-sources.json` (recorded in `live-mvids.json`). The real Gallery/Director classes passed 6,355 checks in an unattached UI tree: 354 localized scene selections, 2,334 caption bindings and 66 category/locale switches, with owned GameObject/preview-scene cleanup. Director read state was supplied synthetically for caption binding; no actor playback or UI input dispatch was claimed.

The first probe failed because an unattached DropdownField does not dispatch ChangeEvent when its index changes: the actual diagnosis recorded index1, zero events and an unchanged59-entry list. The failure and original probe remain preserved. The revised probe explicitly invokes the real list binding after selecting a category and labels its limited scope. It does not label that fixture limitation as a product fix.

Both source TrueType fonts contain all 218 non-whitespace Unicode codepoints used by this copy and its conservative uppercase projection. This is a read-only cmap check; it does not populate or alter the user's SDF assets. Their original source hashes remain unchanged.

Native layout/wrapping, SDF atlas rendering, full playback, readability at target resolutions and speaker review remain open. This patch does not accept complete five-language game parity, art, performance, physical inputs or release readiness.
