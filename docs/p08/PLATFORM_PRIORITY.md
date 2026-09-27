# P08 platform priority

User update 2026-09-26: **Windows 10/11 desktop is the primary client; Web follows later.** Online backend and user data remain on OCI. The previously approved real-time skippable cinematics, concept-first art/UI and maintainable architecture remain required.

Current work targets a release Windows x64 Unity player, native networking and installed `StreamingAssets/Content` packs built for `StandaloneWindows64`. Editor content remains under `Build/Content-editor`; desktop export uses `Build/Content-desktop`. Bundle platform/rules/hash/CRC checks reject incompatible content. Public backend URL configuration contains no credential and does not bypass TLS.

Offline practice can start from installed content without an Internet connection or an external web server. Offline LAN still needs an authoritative native host with its own local realm; it does not merge economy with OCI online accounts.

Windows build, actual executable startup, input/focus/fullscreen, native audio, content loading, offline practice and multiplayer are the current acceptance path. Existing Web/Editor reports are retained with their measured scope. New code preflight tests are not an executed desktop build or performance result.

The installed Unity Windows release module currently supports Mono. The desktop build recipe records that choice and DX11 compatibility; no claim of installed Windows IL2CPP support is made without module evidence. Public OCI staging and multi-region/physical-network acceptance remain the infrastructure phase; this update does not imply they have already been deployed.
