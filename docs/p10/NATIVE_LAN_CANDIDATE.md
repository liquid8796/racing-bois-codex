# Native Windows LAN host candidate

The latest verified package is
`Build/LanHost/native-win-x64-20260927T161958Z`, with its
[source-bound receipt](native-lan/20260927T161958Z/receipt.json). It uses the current
production server unchanged and bundles the Windows x64 .NET/ASP.NET/SQLite
runtime. There is no Unity Web build prerequisite. Each Windows client still
needs its separate installed native player and content.

The locally retained immutable ZIP is
`Build/Packages/RacingBois-NativeLan-20260927T161958Z.zip`: 112,981,068 bytes,
361 entries, SHA256
`e38decb99a8a78798331098f6d22027a478ceb5c0500c9e349be5e039420cbfd`.
Every archive member was streamed back and checked against the source file's
size/hash. Build outputs remain local ignored artifacts; this is not a publicly
published or release-accepted game package.

## Actual local evidence

- [Native executable selftest](native-lan/20260927T161958Z/native-selftest.json):
  X64, bundled .NET 10.0.9, real SQLite in-memory rollback and shared protocol/
  gameplay smoke passed while DOTNET_ROOT pointed to an absent directory.
- [Native persistence smoke](native-lan/20260927T161958Z/native-smoke.json):
  two actual owned host launches, loopback HTTP/WS, protocol 6 and gameplay hash
  `p08-C655ECB89DF77CFD`; 12 checks passed. An anonymous persistent offline profile
  was created through the real multiplayer handshake. A durable equip command
  completed, the exact owned process was abruptly terminated, and a second host
  opened the same private SQLite realm. Realm identity, profile, credits, inventory
  and ledger matched afterward; repeating the transaction remained idempotent.
  The database URL returned 404. Both owned hosts stopped; no unrelated process
  was enumerated or terminated.
- [Forced supervisor exit](native-lan/20260927T161958Z/forced-stop.json): a third
  owned host was attached to a Windows Job Object with kill-on-close enabled.
  The publisher opened that exact child handle, forcibly terminated its probe,
  and verified the child handle signalled exit. This tests cleanup even when a
  probe cannot run its `finally` block; no process-name or broad PID cleanup is used.
- [PowerShell 5.1 package verification](native-lan/20260927T161958Z/powershell51-verify.txt)
  and [side-effect-free launch plan](native-lan/20260927T161958Z/powershell51-plan.txt)
  passed on the real package. The private plan directory was not created.
- [Launcher regression](native-lan/launcher-tests-20260927T1616/receipt.json):
  11 real PowerShell 5.1/7 fixture tests passed, including actual symlink rejection,
  tampered/unregistered/missing payload, path escape/alias, online realm, external
  runtime and in-package data rejection. These fixtures do not launch a host.

The private test realm and host logs are retained under `_local/p10/native-lan`.
Raw profile capabilities stayed in the probe's memory and were not written to
the public reports. No firewall, certificate trust, OCI or other realm was changed.
This did not disconnect WAN and is not physical two-PC LAN acceptance.

## Use and rebuild

The package's `README.txt` and `launch-native-lan.bat` provide the user workflow.
The PowerShell launcher verifies the exact file manifest before launch, fixes
realm kind to `offline` and keeps data outside the immutable package/public root.
Its default data location is `%LOCALAPPDATA%\RacingBois\OfflineLan\default`;
`-DataRoot` selects a different private realm. `-LocalOnly` confines the listener
to loopback. Normal launch binds LAN and prints the native WS endpoint; it does
not change firewall rules. Online accounts/resources remain authoritative on OCI.

```powershell
python tools/p10/native-lan/publish.py
python -m unittest discover -s tools/p10 -p test_native_lan_launcher.py -v
```

Each publish invocation creates new versioned output/evidence/private directories
and refuses collisions. It verifies the source snapshot before/after actual native
execution and archive production. A later source edit does not retroactively bind
the current package to the new source; publish and validate a new candidate.

## Preserved failed attempts

`20260927T161104Z` failed because the initial smoke selected `freshGuest=true`,
which intentionally creates a temporary nonpersistent guest without a profile
capability. The corrected smoke uses the production first-use anonymous persistent
profile path. This was a harness misunderstanding, not a demonstrated server bug.

`20260927T161213Z` passed the actual native restart smoke but failed the package
launcher in this PowerShell 5.1 environment because `Get-FileHash` was unavailable.
The launcher now hashes with the built-in .NET SHA256 API. Neither earlier attempt
was relabelled PASS or overwritten.

The successful `20260927T161314Z` and `20260927T161920Z` candidates remain preserved
at their original source bindings. The latest candidate adds the demonstrated
forced-probe cleanup and explicitly binds both imported PE-audit tool sources.

Final release still requires accepted P08 visuals/content, the real Windows game
package, full native gameplay/input/audio/performance/hardware gates, two physical
LAN PCs with WAN disconnected and separate geographic game-client evidence.
