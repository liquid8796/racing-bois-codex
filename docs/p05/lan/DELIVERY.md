# P05 offline LAN packaging

The Windows player package has a PowerShell launcher, a private-LAN address
selector, a fully local HTML/SVG QR helper, and a self-contained publish wrapper.
No Unity/Bootstrap/server game logic was changed by this work.

`tools/p05/publish-lan.ps1` requires an explicit final Web build and a fresh
versioned output directory below `Build/`. It reuses the existing foundation
publisher for the native runtime and deployable Web copy, then overlays the P05
launcher, helper, documentation, MIT license and integrity manifest. Previous
packages and live realm data are never overwritten. The preparation checks below
were followed by final publishing on 2026-09-21: Windows and Linux ARM64 packages
contain the exact gzip Web build from runtime commit `9873732`. See the
[delivery receipt](../backend/delivery.json) for archive hashes, complete file
verification and Windows native SelfTest v3. ARM64 execution remains untested.

```powershell
./tools/p05/publish-lan.ps1 -Output 'Build/LanHost/win-x64-p05-<source>' -WebRoot 'Build/Web-p05-<source>'
```

The host command is `--AllowLan true --Port 7777 --WebRoot <package>/web
--DataRoot <package>/data`. The server agent confirmed and implemented DataRoot.
The launcher accepts another persistent data directory explicitly, validates it
outside public `web`, and preserves it across restarts. A later package version
can use the same external DataRoot. Runtime `realm-data` remains recognized by
the verifier because it is the native executable's default when bypassing the
launcher. Neither location may be included in a new package manifest.

The address helper only selects canonical RFC1918 IPv4 on physical active NICs;
virtual/VPN/Docker/WSL/link-local/public addresses are excluded. No adapters,
firewall rules, routing, router settings or global Internet access are changed.
The helper emits no credentials or profile data into QR codes.

## Evidence recorded during preparation

- `helper-tests.json`: 24 passing checks for private-address boundaries, physical
  interface selection, route preference, persistent data path, public-data
  rejection, JSON script-boundary escaping and pinned QR bytes.
- `qr-roundtrip.json`: 16 passing independent encode/decode combinations. The
  exact vendored Nayuki JavaScript encoded four URLs; ZXing-C++ 2.3.0 decoded the
  actual matrices at two pixel scales and two rotations. Node/Python/ZXing are
  development-only QA dependencies and are not shipped to players.
- `package-validator-tests.json`: complete copied-package smoke plus rejection
  of native Brotli over HTTP (including an additional script), an external
  loader/CDN, renamed non-gzip bytes, a corrupt gzip trailer, changed Web bytes,
  missing bundled-runtime contract,
  publishing player data, and overwriting an existing output. Generated private
  state/address pages do not break immutable payload hashes. The fixture uses a
  copied P03/P04 package. Its actual Brotli assets are decoded and recompressed
  into real gzip only under `_local/` to exercise the HTTP-compatible gates;
  original files are preserved. This is explicitly not a final P05 deliverable
  or a production-build compression conversion.
- `p03p04-package-web-audit.json`: the existing P03/P04 package has all four Unity
  entrypoint dependencies bundled, no external CSS/font URL, and matching file
  hashes. Its native self-test passed separately. The refreshed receipt explicitly
  reports `httpCompressionCompatible: false` for its native Brotli payloads.
  This baseline is **not HTTP LAN cold-load proof**.

## HTTP compression gate

The P05 Unity build is now gzip with decompression fallback off. Both P05
publisher preflight and the package verifier call the Web audit with
`-RequireHttpCompatible`. Gzip and uncompressed resources are accepted; native
`.br` and unverified `.unityweb` fallback resources fail closed. Gzip is read
through the local decoder, and the regression corrupts the trailer to confirm
integrity validation instead of trusting extensions.

The [Unity 6 deployment manual](https://docs.unity3d.com/6000.0/Documentation/Manual/webgl-deploying.html)
states gzip works over HTTP and HTTPS, while Chrome/Firefox native Brotli needs
HTTPS. A local dependency manifest and a successful WS handshake do not test
that browser decompression requirement. Final delivery separately checked live
HTTP/HTTPS Content-Encoding and MIME headers; root integration also loaded the
HTTP build in a real browser and joined a WS race. Physical LAN cold-cache testing
with WAN disconnected remains unverified.

## Helper visual review

The helper agent had no available browser for visual review. During root
integration, automatic approval review rejected a temporary HTTP preview-server
launch without a detailed reason, and Browser Use explicitly blocked the local
file URL. No policy workaround was attempted. The user then manually opened
`_local/p05-lan-preview/LAN_JOIN.html` and confirmed that the **URL and QR display
clearly**. This is user visual confirmation, separate from automated QR decoding.

The helper follows the established graphite/amber game direction, uses bundled
JavaScript and system fonts, 17px body text, visible keyboard focus and explicit
text URLs next to high-contrast QR symbols. The UI/UX skill's initial gaming
landing-page recommendation was not a fit; its targeted readable-text contrast
guidance was used instead. No external font recommendation was adopted.

## Third-party provenance

The unmodified browser QR encoder comes from the
[official Nayuki library](https://www.nayuki.io/page/qr-code-generator-library),
with MIT license and exact SHA-256 in `tools/p05/lan/vendor-provenance.json`.
There is no runtime download. Independent QA used the
[official ZXing-C++ Python wrapper](https://github.com/zxing-cpp/zxing-cpp/tree/master/wrappers/python)
only under ignored `_local/` test dependencies.

## Remaining acceptance

Final P05 native/package/browser tests must use the final build. Two clients on
one PC and static checks do not prove first launch on two independent PCs, with
empty browser caches and WAN unavailable while LAN remains connected. That test
is still unverified because only one PC is available. No public-domain, OCI TLS
or worldwide routing acceptance is implied by an offline LAN package.
