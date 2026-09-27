# Native P08 handoff

This is an authoring handoff, not a release acceptance report. Windows 10/11 x64
is primary; Web is deferred and the online backend remains an OCI deployment.

## Preconditions before building

- Finish concept-led geometry/export/import for all 15 bike identities, eight
  riders, 24 portraits, traffic extras and biome props. Run the actual Unity art
  validation. The filesystem snapshot below is explicitly incomplete.
- Finish the scene/UI integration and inspect its runtime presentation. UI must
  follow the newly generated 2D concepts. Do not substitute a successful import
  for visual or gameplay acceptance.
- Keep the installed public config's `contentBaseUrl` empty. Installed assets
  and all 25 Ogg resources must support local/offline play. Backend WSS can be
  configured separately for OCI; it does not change the installed content root.
- Freeze code, scene and settings during the actual player build and distribution
  audit. The source snapshot detects edits during the build and the Python audit
  detects edits made after it.
- Choose a new, empty player output directory. The builder preserves nonempty
  outputs and refuses to combine stale or unrelated files with a new candidate.

## Current filesystem snapshot

On 2026-09-26, during this resumed handoff review:

| Item | Observed status |
| --- | --- |
| Bike prefab roster | 00–05 present; 06–14 absent |
| Rider prefab roster | All eight absent |
| Portrait PNG roster | 0 of 24 present |
| Authored audio distribution | All 97 declared Ogg paths exist: 25 music + 72 SFX |
| Desktop pack manifest | Not built |
| Native player | Not built |

File existence is not creative/visual/runtime QA. Root should recheck the roster
after completing authoring. The pack builder deliberately rejects missing
identities, portraits, functional audio roles or audited delivery inputs.

## Exact Unity MCP method order

After checking Editor readiness and compilation/console errors:

```csharp
RacingBois.Authoring.Editor.P08ArtBuilder.Setup();
RacingBois.Authoring.Editor.P08ArtBuilder.Validate();
```

Run the pack setup after the complete roster is imported:

```csharp
RacingBois.Authoring.Editor.P08ContentPackBuilder.Setup();
RacingBois.Authoring.Editor.P08ContentPackBuilder.Validate();
RacingBois.Authoring.Editor.P08ContentPackBuilder.BuildEditor();
```

Use `BuildEditor` for real Editor route/actor/music acceptance. The Editor loader
uses `Build/Content-editor`. Then build the native distribution through Unity:

```csharp
RacingBois.Authoring.Editor.P08ContentPackBuilder.BuildDesktop();
RacingBois.Authoring.Editor.P08DesktopBuilder.Describe();
RacingBois.Authoring.Editor.P08DesktopBuilder.Prepare();
RacingBois.Authoring.Editor.P08DesktopBuilder.Build();
RacingBois.Authoring.Editor.P08DesktopBuilder.Validate();
```

Run long operations separately and wait for their actual completion. A later
candidate uses a fresh named folder instead of overwriting the current release:

```csharp
RacingBois.Authoring.Editor.P08DesktopBuilder.BuildTo("Build/Desktop-P08-candidate-2");
RacingBois.Authoring.Editor.P08DesktopBuilder.ValidateAt("Build/Desktop-P08-candidate-2");
```

The latest `docs/p08/desktop/build.json` records the exact output path and attempt.
Previous receipts are preserved under `history`. At attempt start the latest
receipt becomes `passed: false`; compilation, preparation, BuildPlayer, source
binding or installed-content failure cannot leave an older success masquerading
as the current attempt.

## Distribution audit and native QA

Supply the exact `GameplayRules.ContentHash` returned by Unity. For the default
candidate, run:

```powershell
python tools/p08/desktop/audit_desktop.py --expected-content-hash '<actual shared hash>' --receipt docs/p08/desktop/distribution-audit.json
```

For a later candidate add `--player-root Build/Desktop-P08-candidate-2`. This
command requires the actual successful Unity build receipt and binds source,
manifest, PE platform, release Mono runtime, config and every installed byte.

Then launch the real player with a log kept **outside** its distribution root,
otherwise the verifier correctly rejects the added diagnostic file. Preserve
the full `RacingBois_Data` and `MonoBleedingEdge` folders beside the executable.
Verify local startup without Internet, all route/identity swaps, music/cinematics,
resize/focus/input/settings/persistence and native performance. Finally verify
LAN using the separate host and OCI WSS using its actual trusted endpoint.

Archive only the accepted player files. Compiler/verifier fixtures, Editor timing
and old browser checks do not substitute for native acceptance or OCI deployment.
