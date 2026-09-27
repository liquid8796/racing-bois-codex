# Desktop authoring and distribution checks

The primary target is Windows 10/11 x64; public server deployment stays on OCI.
See `docs/p08/desktop/README.md` for the native build order and acceptance gates.

Compile the editor wrapper against this workstation's installed Unity API:

```powershell
dotnet build tools/p08/desktop/EditorBuildPreflight.csproj -v minimal
```

Run negative verifier tests without launching a game or touching any database:

```powershell
python -m unittest discover -s tools/p08/desktop -p test_audit_desktop.py -v
```

After a real Unity build, verify the exact player output and corresponding
successful build receipt. Supply the content hash returned by Unity, not a
test hash:

```powershell
python tools/p08/desktop/audit_desktop.py --expected-content-hash '<actual shared hash>' --receipt docs/p08/desktop/distribution-audit.json
```

The default root is the project-owned `Build/Desktop-P08`. A later Unity candidate
uses `P08DesktopBuilder.BuildTo("Build/Desktop-P08-candidate-2")`, then passes
`--player-root Build/Desktop-P08-candidate-2` to this audit. The builder refuses
nonempty output roots and preserves previous files/receipts. The command reads
only the distribution and its build receipt. It does not launch a player,
archive a candidate, inspect player saves, deploy OCI or change firewall rules.
It rejects source masters, research media, database files, secrets/config fields,
diagnostic logs and unregistered StreamingAssets resources.

`RacingBois.runtime.json` is the four-field public LAN configuration example.
The separate `RuntimeCompile.csproj` and config tests cover native adapters.
The audit binds the exact output root, checks current source snapshot freshness,
and rejects failed or incomplete attempts. Editor preflight, fixture tests,
actual build verification and runtime acceptance
are distinct receipts; passing a compile or fixture does not close release QA.
