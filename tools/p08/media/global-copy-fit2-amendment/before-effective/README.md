# Current global display-copy generation

`current.json` identifies the reviewed active amendment manifest and its exact
hash. The generator composes keyed amendments over an immutable previous union
and provider modules. The current chain preserves the ENU `BIKE UNDAMAGED`
semantic correction and adds the three observed DEU/ESP/FRA pristine-button
shortenings. Historical locale data, unions, handoffs and native receipts remain
at their original paths; the active module comment points here.

```powershell
python tools/p08/media/global-copy-effective/generate.py
python tools/p08/media/global-copy-effective/generate.py --check
python tools/p08/media/global-copy-effective/generate.py --check-live
python tools/p08/media/global-copy-effective/test_generation.py
```

Generation writes only the active amendment's staging folder. `--check` writes
nothing; `--check-live` also checks the installed generated module. The ordinary
Career generator refuses the old baseline, and the pristine amendment's public
entrypoint delegates here. Their prior tool bytes are preserved in the fit
amendment's `before/` folder. Historical replay functions remain explicit; they
are not the current production generation path.

The current preflight projects select each real production C# file once. Only
the generated Career copy module is overridden by default. Presentation can
explicitly override RaceScreen when reviewing the separate viewport patch:

```powershell
dotnet build tools/p08/media/global-copy-effective/BootstrapPreflight.csproj -p:Flavor=Editor
dotnet build tools/p08/media/global-copy-effective/BootstrapPreflight.csproj -p:Flavor=Windows
dotnet build tools/p08/media/global-copy-effective/BootstrapPreflight.csproj -p:Flavor=Web
```

Pass `-p:RaceScreenCandidate=<absolute-reviewed-candidate.cs>` only when reviewing
that candidate. Pass `-p:CareerCopyCandidate=<absolute-installed-or-reviewed.cs>`
to change that one explicit override. Intermediate/output folders are isolated
by project and flavor; duplicate-source warnings are not suppressed.

The older `global-copy-main-staging/*Preflight.csproj` projects describe the
pre-install authoring revision. They combine its then-new staged files with the
then-live tree and are not a current-source verifier after installation. Their
projects and historical receipts are intentionally preserved.

These commands verify generation and compilation. They do not establish native
glyph coverage, responsive behavior, readable layout or concept acceptance.
