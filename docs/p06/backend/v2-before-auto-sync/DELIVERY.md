# P06 delivery

Release `0.6.0`, runtime commit `6a8ce24`, final Web build `Build/Web-p06-v2`.
`delivery.json` binds the Web files, both package manifests, archives and live
HTTP/HTTPS response headers. P06 v1 is superseded and was not published.

| Artifact | Size | Verification |
| --- | ---: | --- |
| `Build/Packages/RacingBois-P06-win-x64-6a8ce24.zip` | 69,528,848 bytes | Self-contained native SelfTest PASS; 368 immutable package files; all archive hashes matched |
| `Build/Packages/RacingBois-P06-linux-arm64-6a8ce24.tar.gz` | 66,268,229 bytes | Self-contained ELF64/AArch64; all archive hashes and executable permissions matched; native execution NOT RUN |
| `Build/Web-p06-v2` | 21,532,738 bytes | Exact payload matched both packages; gzip decoded and live HTTP/HTTPS Content-Encoding checked |

Archive SHA256 values:

- Windows: `aafa3d9dabddeee7eef6582a54f1a9253c6cec53243f6afc96da934fdff47e59`
- Linux ARM64: `dfb8216445c67ff6bdc61982808d43b6fd4094840c0028512838e2552b2c359d`

## Local demo

The managed demo serves `https://localhost:7778/` and
`http://127.0.0.1:7777/`; protocol v3 uses `/multiplayer`. Both listeners bind
only `127.0.0.1`. Normal OS certificate trust passed without a bypass.
The new process is recorded in `_local/server-session.json`; use that record's
executable and start time to verify ownership before stopping it. The previous
P05 process was already absent at preflight; no unrelated process was stopped.

The existing private `_local/p05-main-data` directory was reused. Its realm ID
matches the P05 record and persistent profiles remain enabled. No private realm
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

`source-comparison.json` compares the captured files to P05: all existing entries
are unchanged; the only new entry is the presentation benchmark projection.
Git also reports no source changes from P05 evidence commit `94be01e` to
`6a8ce24` under `src/`, `Packages/`, `tools/foundation/` or `tools/p05/`.
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
