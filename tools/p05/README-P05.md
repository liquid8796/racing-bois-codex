# Racing Bois — Windows offline LAN host

This package includes the native server runtime, the complete Unity Web payload,
and a local QR/address helper. Players do not need .NET, Node, Python, a package
manager, a CDN, an account service, or an Internet download on first launch.
Use a desktop browser on a PC/laptop. Keep the host and players connected to the
same wired LAN or Wi-Fi router even when that router has no Internet uplink.

## Start and join

1. Extract the whole package to a writable folder. Do not run it inside a ZIP.
2. Double-click `launch-lan.bat`. Keep its console open while playing.
3. On the host PC, open `http://localhost:7777/`.
4. On another PC on the same LAN, open the private address printed in the host
   console, then create/join a lobby in the game.
5. Open the generated `LAN_JOIN.html` for readable addresses and QR codes.
   `show-lan-addresses.bat` regenerates the page if the LAN address changes.
6. Press Ctrl+C in the host console to stop the host cleanly.

Automatic sharing only lists private IPv4 addresses on active physical network
adapters. VPN, virtual adapters, Docker/WSL, public addresses, loopback and
169.254.x.x link-local addresses are excluded. If no eligible address exists,
localhost remains usable on the host PC, but the helper does not invent a LAN
address or claim that another machine can connect.

The QR generator and its MIT license are included under `lan/`. QR generation
happens in the browser without a network request. The QR contains the displayed
LAN URL, without authentication tokens or player data. It does not make the
server publicly reachable over the Internet.

If the chosen port is already occupied, the launcher exits without stopping
another process. An alternate port can be selected explicitly:

```powershell
./launch-lan.ps1 -Port 7787
```

If Windows Firewall prompts when the host first listens, the PC owner can allow
this application on the intended Private network. The launcher never changes
firewall rules, disables adapters, disconnects a VPN, or alters the router.

## Persistent LAN realm data

The launcher passes an explicit `--DataRoot` to the server. By default it is the
package's `data` directory, separate from the publicly served `web` directory.
Keep this directory across host restarts. It contains the local realm profile
records, hashed profile capabilities and idempotent race-result ledger.

For a stable location shared by successive package versions:

```powershell
./launch-lan.ps1 -DataRoot 'D:\RacingBoisData\FriendsLAN'
```

Stop the host before backing up or moving its data directory. Start the new
package with the same explicit DataRoot to keep that realm. Do not run two host
processes against the same DataRoot. New publishes use a fresh output folder and
never copy, overwrite or distribute existing player data. DataRoot is refused
if it is inside `web`; its JSON files must not become downloadable game assets.

LAN realm profiles are local to that realm. Browser-side identity also depends
on browser storage and origin; clearing browser data or changing IP/port can
affect recognition. These profiles are not global P07 accounts, and LAN rewards
are not silently uploaded or merged into a future online wallet.

## Verify package integrity

```powershell
./verify-package.ps1 -PackageRoot .
```

The verifier checks shipped file hashes, required bundled runtime files, local
Web entrypoint/CSS dependencies and the host's `--SelfTest`. That self-test opens
no listener. `package-manifest.json` excludes only generated `LAN_JOIN.html`,
package verification receipts and the local `data/` or default `realm-data/`
directories. Publishing refuses existing realm data, including `realm.json`
found elsewhere in a candidate package.

The package can be prepared while Internet is available and then carried to an
offline LAN. Preparing a developer build requires the .NET SDK and Unity build;
those tools are not player runtime dependencies. The QR JavaScript is already
vendored, so building or launching does not download it.

## Compression for HTTP LAN

The P05 LAN build uses **gzip**, with Unity decompression fallback disabled.
Unity documents gzip support over both HTTP and HTTPS; Chrome and Firefox native
Brotli support requires HTTPS. Therefore the earlier Brotli build's local files
and WS connectivity do not establish a first HTTP LAN load. See the
[Unity 6 deployment manual](https://docs.unity3d.com/6000.0/Documentation/Manual/webgl-deploying.html).

P05 publishing and package verification always enable `-RequireHttpCompatible`.
They reject entrypoint-linked `.br` resources and unverified `.unityweb`
JavaScript fallback payloads. Gzip files are decoded during the audit, including
their integrity check; renaming a Brotli file to `.gz` is insufficient. The host
must still serve the matching `Content-Encoding: gzip` and content type. Actual
response headers and browser loading require the separate live build tests.

## Acceptance boundary

Static dependency checks, file hashes, native self-tests and multiple clients
on one PC do not prove a cold-cache launch on two separate LAN machines with
the WAN unavailable. That acceptance test remains explicit until performed on
the actual machines. A global network or firewall change is not used to
manufacture such a result. Public OCI routing/TLS and worldwide Internet play
require their separate deployment and connection checks.
