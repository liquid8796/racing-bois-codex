Racing Bois - Windows x64 native offline LAN host candidate

This package contains the server and its .NET/SQLite runtime. It needs no
installed .NET SDK/runtime, browser game build, CDN, cloud account or Internet
download after extraction. Each PC still needs the separate compatible Windows
player with all required content installed. This is an engineering candidate;
full game art, runtime, hardware and physical multi-PC acceptance remain open.

1. Extract the complete archive. Do not add player saves to the package.
2. Run launch-native-lan.bat on the host PC. Keep its window open.
3. In each installed Windows client, select LAN and enter
   ws://HOST-LAN-IP:7777/multiplayer, using the host's private IPv4 LAN address.
   A client on the host PC can use ws://127.0.0.1:7777/multiplayer.
4. If Windows asks about this executable, allow only the trusted private LAN.
   The launcher does not change firewall, router, certificate or network settings.
5. Press Ctrl+C in the host window to stop it.

Optional PowerShell arguments:
  -LocalOnly                 Bind only this PC for local testing.
  -Port 7780                 Use another unoccupied port; update clients too.
  -DataRoot D:\PrivateRealm  Select a dedicated private offline realm directory.
  -PlanOnly                  Verify all package files and print the launch plan.
  -VerifyOnly                Verify all immutable package files without launch.

The default persistent data directory is
%LOCALAPPDATA%\RacingBois\OfflineLan\default. It is outside the package/public
directory. Keep the complete directory for backups while the host is stopped.
Test restoration in a different private directory before replacing any live
realm. Do not combine different realms or import offline balances into OCI.
Online account/player/resource authority remains on the separate OCI service.

Keep the candidate receipt and archive SHA256 for transfer verification. The
launcher checks every manifested file and refuses extra/missing/changed files.
The package protocolVersion/contentHash must match the separate Windows client.
Neither this package nor its local smoke report proves two physical PCs work
with WAN disconnected. Run that acceptance separately before release.

The public directory intentionally contains only an explanatory text file.
Native clients use their own installed content; no Unity Web build is required.
