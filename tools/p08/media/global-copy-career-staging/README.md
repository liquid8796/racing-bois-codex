# Career display templates — staged boundary

Current generation uses the explicit reviewed overlay at
`../global-copy-pristine-amendment/current-overlay.json`. Run
`python tools/p08/media/global-copy-pristine-amendment/effective_generate.py --check`
to verify it, or omit `--check` to regenerate its staged module. The historical
inputs, generated module and receipts in this directory remain frozen; the old
`generate.py` entry stops before writing so it cannot undo the ENU pristine-state
amendment. Commands and results below describe the original boundary revision.

This boundary owns only `Assets/RacingBois/Client/Presentation/CareerView.cs`.
Its reviewed source hash is `51ee1179cf071ddc973a671321d5325d4bf57353a84262368a0d6803b500b819`.
No Assets file, protocol operation, name, numeric precision or UI layout is changed
by template preparation. Shared locale selection and `UiText` belong to the main
localization stage.

`canonical-source.json` contains 151 complete VI semantic templates. Five shared
common keys (`done`, `cancel`, `confirm`, `refresh`, `retry`) are referenced but
defined by the main stage. `source-bindings.json` covers all 175 reviewed literal
occurrences / 161 literal fragments as 141 whole-expression sites, including all
30 dynamic or conditional compositions. It records source spans, the complete
original expression, semantic keys and preformatted named-argument expressions.
No global string substitution is used.

Every dynamic sentence is one complete template. Bike-list ownership/availability/
equipped combinations and bike-detail status combinations have complete variants,
allowing translators to order the whole sentence. Prices and stats retain their
existing caller-side format strings. Player/catalog names, usernames, endpoints,
realm values and diagnostic codes are inserted opaquely. `protected-tokens.json`
records proper names, protocol strings and physical units that must remain exact.

`VI.json` and `VI-source.tsv` are the frozen source worksheet. All five target
locales are explicitly authored in `locales/ENU.json`, `DEU.json`, `ESP.json`,
`FRA.json` and `ITA.json`. `UiText.Career.Generated.cs` implements the shared
`AddCareer` hook in ENU/DEU/ESP/FRA/ITA/VI order: 906 explicit cells, no missing
translations and no fallback-filled cells. The shared Application API is:

```csharp
UiText.Get(locale, key);
UiText.Format(locale, key, new UiTextArgument("bike", bike.DisplayName));
```

Named argument values are strings and null values become empty, preserving C#
concatenation. The real shared formatter scans only the template, never inserted
values, and rejects missing, extra or duplicate arguments.

Managed expression equivalence compares all 141 original C# expressions with
their proposed replacements across 2,048 scenarios and four numeric cultures.
It uses the actual shared staged `UiText`/`DisplayLanguage` implementation and a
clearly labeled, nonshipping VI-only test fixture. All 156 Career/common template
variants are exercised: 288,773 assertions pass, including opaque values with
braces and three named-argument rejection controls. This is not native UI,
translation quality, glyph, layout or readability acceptance.

```powershell
python tools/p08/media/global-copy-career-staging/prepare_templates.py
python tools/p08/media/global-copy-career-staging/generate_equivalence_checks.py
dotnet run --project tools/p08/media/global-copy-career-staging/ExpressionEquivalence.csproj -- tools/p08/media/global-copy-career-staging/expression-equivalence.json
```

The original key/template inventory remains frozen in `templates-freeze.json`.
The staged view applies those exact source spans and adds optional initialization
and a pre-initialization-safe SetLocale. Existing tabs/buttons are relabeled;
selection and scroll state remain in the view. Account drafts are retained only
in method-local variables while rebuilding display text. Focus recognition checks
the owning TextField and its internal descendants; generic name-based restoration
is suppressed for those fields to avoid selecting another `unity-text-input`.
Confirmation text is a display-only factory, independent of its unchanged
CareerIntent. Busy requests defer body rebuilding until their normal completion.

Final managed checks use the real generated Career and main tables: 288,773 VI
expression-equivalence assertions, 3,926 exact six-locale lookup/alias/fallback/
opaque-formatting assertions, 15 authored-data negative controls, and a Unity
reference preflight with zero warnings/errors. `coverage.json` and the separate
test receipts state their limited scopes. These checks do not prove native
focus/caret behavior, wrapping, glyph coverage, full UI readability or linguistic
acceptance. Those remain root-owned review work. No Assets files are installed.

Production generation and final checks:

```powershell
python tools/p08/media/global-copy-career-staging/generate.py
python tools/p08/media/global-copy-career-staging/test_generation.py
dotnet run --project tools/p08/media/global-copy-career-staging/ProductionExpressionEquivalence.csproj -- tools/p08/media/global-copy-career-staging/production-expression-equivalence.json
dotnet run --project tools/p08/media/global-copy-career-staging/CopyTests.csproj -- tools/p08/media/global-copy-career-staging tools/p08/media/global-copy-career-staging/copy-tests.json
dotnet build tools/p08/media/global-copy-career-staging/Preflight.csproj
```

`handoff.json` lists only CareerView plus the generated Application copy module
and their metadata. Shared locale/main UI wiring belongs to the lead stage and
must be integrated together; this boundary provides no standalone live installer.
