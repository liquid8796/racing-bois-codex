# P06 delivery

Release `0.6.0`, compiled Unity runtime, Web shell and package source commit
`efce749`, final distribution `Build/Web-p06-v4`.
This is direct Unity release build output from job `build-059204f1d7`; the source
template includes `autoSyncPersistentDataPath: true`. No HTML or Unity binary
postprocessing was applied. `delivery.json` binds the Web files, both package
manifests, archives, source manifest, Unity build receipt and live HTTP/HTTPS
response headers.

The v3 candidate packages remain intact, with all previous top-level evidence
preserved in `v3-before-join-ui-fix/`. The older v2 candidate evidence remains in
`v2-before-auto-sync/`. V4 includes the final join-code Enter handling and invite
code layout fixes. Browser gameplay acceptance is recorded separately.

| Artifact | Size | Verification |
| --- | ---: | --- |
| `Build/Packages/RacingBois-P06-win-x64-efce749.zip` | 69,527,484 bytes | Self-contained native SelfTest PASS; 368 immutable package files; all archive hashes matched |
| `Build/Packages/RacingBois-P06-linux-arm64-efce749.tar.gz` | 66,265,234 bytes | Self-contained ELF64/AArch64; all archive hashes and executable permissions matched; native execution NOT RUN |
| `Build/Web-p06-v4` | 21,530,218 bytes | Exact payload matched both packages; gzip decoded and live HTTP/HTTPS Content-Encoding checked |

Archive SHA256 values:

- Windows: `03486fbefc344d6e0b7f6c4ea9001d5e2209f65c4e1e0c45686fd1889e9a7f74`
- Linux ARM64: `62da73ad276c304a5363b7242d1cdee950d29f035108682d11ad449825ea7964`

## Local demo

The managed demo serves `https://localhost:7778/` and
`http://127.0.0.1:7777/`; protocol v3 uses `/multiplayer`. Both listeners bind
only `127.0.0.1`. Normal OS certificate trust passed without a bypass.
The v4 process has PID `19388`, start time `2026-09-22T02:10:25.4305324Z`;
`_local/server-session.json` records its executable, start time, WebRoot and
private DataRoot. Verify those fields before stopping any managed process.
The previously recorded v3 PID `26832` was absent and both ports were free at
preflight. No existing process was stopped during the v4 launch.

The existing private `_local/p05-main-data` directory was reused. Its realm ID
matches the P05/v3 records and persistent profiles remain enabled. No private realm
files, player data, credentials or Unity debug artifacts enter either archive.
Package creation and launching made no OCI, router, firewall or network-adapter
changes.

## Package use

On Windows, extract the whole ZIP and run `launch-lan.bat`; open the URL printed
by the host or the generated `LAN_JOIN.html`. Detailed LAN/profile/QR operations
remain in the bundled `README-P05.md`; `README-P06.md` describes this release.
`launch-local.bat` stays on loopback. Both launchers use an explicit private data
directory outside `web`. For upgrades, choose one stable data directory with
`launch-lan.ps1 -DataRoot 'D:\RacingBoisData\FriendsLAN'`.

On Linux ARM64, extract the tarball preserving executable permissions and use
`./launch-local.sh` or `./launch-lan.sh`. Both pass an explicit private DataRoot;
override it with `--DataRoot /absolute/private/racing-bois-data` to retain the
same realm between package versions. The Windows QR helper is not included or
claimed for Linux.

## Evidence and scope

`source-comparison.json` compares 95 captured files to the final P05 source
manifest: all existing entries are unchanged; the only new entry is the
presentation benchmark projection.
Git also reports no source changes from P05 evidence commit `94be01e` to
`efce749` under `src/`, `Packages/`, `tools/foundation/` or `tools/p05/`.
P06 therefore does not claim new fixes to P05 network authority, persistence or
contact-transition uncertainty.

Fresh Windows native SelfTest, package integrity, exact Web hashes and six live
gzip header checks passed. Browser gameplay is documented separately by the
main P06 acceptance report. This packaging result does not establish native
ARM64 execution, a cold-cache first launch on two physical LAN machines with
WAN disconnected, or cross-network Internet play. Those gates remain open.

The packaging receipt is in `delivery.json`; component receipts are
`windows-package-verification.json`, `arm-web-audit.json`,
`http-headers.json`, `source-manifest.json`, and `source-comparison.json`.
