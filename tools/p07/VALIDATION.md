# P07 live verification and packaging

Run commands from the repository root. These tools use generated QA identities and loopback hosts. They do not contact OCI or change certificate trust/firewall settings.

## HTTP and WebSocket career probe

Start isolated P07 offline and online hosts using different private data roots. Suggested ports are offline HTTP/HTTPS `7877/7878` and online `7977/7978`. The localhost development certificate must already be trusted through the normal OS mechanism.

```powershell
dotnet run --project src/Tests/RacingBois.Career.LiveProbe/RacingBois.Career.LiveProbe.csproj -c Release -- https://localhost:7878/ http://127.0.0.1:7877/ docs/p07/career-live-validation.json https://localhost:7978/ http://127.0.0.1:7977/
```

The two online URLs are optional; omitting them explicitly records the online realm test as skipped. All supplied URLs must be loopback base URLs without credentials, paths, queries or fragments.

The probe creates disposable persistent profiles through real WSS, then exercises HTTP view/commerce, concurrent duplicate trade, object access, strict schema/origin checks, HTTPS enforcement for credentials, registration/login/recovery, signed offline save validation and session revocation. It requires both the accepted goodbye command and a normal `logout` close frame. Revocation requires the explicit normal `profile_revoked` close frame; an arbitrary broken connection is not accepted as proof. Standard OS TLS validation stays enabled.

Only generated public profile IDs, pass/fail outcomes and source hashes go into the receipt. Tokens, passwords, recovery codes and save envelopes stay in process memory and are never printed or written. The QA profiles remain in the isolated host data root; the probe does not delete user data. Wait for the endpoint rate-limit window before repeating the complete run, or use a fresh isolated host as appropriate. A probe build alone is not evidence that its live scenarios passed.

## Fresh release archives

Commit the actual P07 runtime/build source. Publish both runtimes from that commit with the complete Unity Web output:

```powershell
./tools/p07/publish.ps1 -WebRoot D:\Project\Unity\racing-bois\Build\Web-p07-final -ReleaseId COMMIT -Runtime win-x64
./tools/p07/publish.ps1 -WebRoot D:\Project\Unity\racing-bois\Build\Web-p07-final -ReleaseId COMMIT -Runtime linux-arm64
```

Replace `COMMIT` with the actual current Git hash. The corresponding fresh directories must be `Build/LanHost/win-x64-p07-COMMIT` and `Build/LanHost/linux-arm64-p07-COMMIT`.

Start the final packaged Windows executable on a free loopback HTTP/HTTPS pair, serving its own `web` directory, with a separate private `_local/p07-*` data root. Record its verified `pid`, absolute `exe`, UTC `startTimeUtc`, absolute `webRoot`, absolute `dataRoot`, `httpUrl` and `httpsUrl` in `_local/p07-server-session.json`. URLs must be credential-free loopback base URLs with explicit ports. This is process metadata only; it must contain no credential. The packaging utility validates the running process identity and exact HTTP/HTTPS gzip payload hashes against the selected Web build. An independent host can use `7887/7888` without replacing preview processes; an online QA host can use `7987/7988` with a different data root.

```powershell
python tools/p07/package-release.py --commit COMMIT --web-root Build/Web-p07-final
```

The utility reruns the packaged Windows native SelfTest and requires `sqliteNativeRollback=true`, verifies Windows x64 and ARM64 SQLite native libraries, rejects private database/key/data paths, produces complete package manifests and fresh ZIP/tar archives, then rereads every archived file hash. ARM host/launcher executable bits are checked. Receipts are written to `docs/p07/backend/delivery.json` only after successful verification.

Existing archives are never overwritten. An existing `delivery.json` must first be preserved explicitly before another release is packaged. Runtime/build inputs must be committed and unchanged from the selected package commit; the user's unrelated Blender edits are outside the source check. The verifier itself and this validation document may be newer, with separate recipe commit/hash evidence; no other runtime/build input difference is accepted. The Unity build receipt must match the selected runtime commit, output path and payload bytes. The script does not launch a server, create player-data copies or reuse the old P06 process/data record.

Native ARM execution, physical two-PC offline LAN, public Internet connectivity and browser UI/gameplay require their own evidence. Archive validation and Windows SQLite smoke do not establish those gates.
