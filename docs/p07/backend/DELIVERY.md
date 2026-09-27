# Racing Bois 0.7.0 — P07 delivery

Verified on 2026-09-22. Machine-readable receipt: [delivery.json](delivery.json). The final local demo is [https://localhost:7888/](https://localhost:7888/), with LAN-compatible HTTP at [http://127.0.0.1:7887/](http://127.0.0.1:7887/).

## Exact build and recipe

| Item | Verified value |
|---|---|
| Runtime and compiled Unity source | `3cac900effe46a0eec8cd75f4251083f94cdb44c` |
| Packaging recipe commit | `d5a4e93878d284a27f94a004b76a60bc8a78ec63` |
| Unity output | `Build/Web-p07-v4` |
| Unity job | `build-a6b0ca6607` |
| Release build duration | 164.7720438 seconds |
| Unity errors / warnings | 0 / 0 |
| Complete deployed Web payload | **21,592,410 bytes**, gzip release output |
| Recipe SHA-256 | `e45a30e5a383b50b73be3d0b2eeb7c67eb605a2f38b4a40baaa47308c3707b8f` |
| Unity build receipt SHA-256 | `03008ebb19b2205c3c46258883580d44f4d33e484c8b44eb6317c79bcd45084e` |

[The Unity receipt](../unity/build.json) records a direct build, with no HTML or binary postprocessing. The packaging recipe changed after the runtime build to support isolated loopback endpoints and correct a filename guard that mistook `Microsoft.Data.Sqlite.dll` for a private database. The verifier checks committed-input equality and records current file hashes; an independent [Git blob audit](source-commit-byte-check.json) additionally matched all 206 listed inputs byte-for-byte to Git at `3cac900`. The recipe commit and script hash are recorded separately. A recipe-only change is not presented as a new Unity/native runtime build.

The guard correction was checked with [18 synthetic path cases](private-data-guard-validation.json): required SQLite assemblies/libraries are allowed; private databases, WAL/SHM/journal files, realm backups, keys and data directories remain rejected. Actual published packages were inspected independently during final archive verification.

## Final artifacts

| Runtime | Archive | Bytes | Files listed in payload manifest |
|---|---|---:|---:|
| Windows x64 | [RacingBois-P07-win-x64-3cac900.zip](../../../Build/Packages/RacingBois-P07-win-x64-3cac900.zip) | **70,845,697** | 378 |
| Linux ARM64 | [RacingBois-P07-linux-arm64-3cac900.tar.gz](../../../Build/Packages/RacingBois-P07-linux-arm64-3cac900.tar.gz) | **67,233,694** | 362 |

SHA-256 values:

```text
Windows ZIP
0153e0c12b28628e6be45f87feac522650487f644fc949d9f5a04796787972f2

Linux ARM64 tar.gz
67e980b4d848ad3a6923ff9a113ab36bc89a812044fbd8c602a014964c24cb14
```

Published directories are `Build/LanHost/win-x64-p07-3cac900` and `Build/LanHost/linux-arm64-p07-3cac900`. Each has a complete `package-manifest.json`; the manifest itself is separately hashed in the delivery receipt. Every archived file was reread and matched to its package source; ZIP integrity and duplicate/path inventories passed. The ARM host and shell launchers have executable permission bits in the tar archive.

Both packages contain the exact selected Web files and a self-contained native runtime. No private realm data, database/WAL, account credential, signing key, local certificate or machine-specific join page is bundled. Earlier `2890f29` candidate directories remain available as development artifacts and were not relabeled as this final release.

## Runtime checks

The packaged Windows executable ran its own native SelfTest successfully, including shared gameplay/protocol checks and a real **SQLite in-memory rollback** through bundled `e_sqlite3.dll`. Its runtime reports x64 and `.NET 10.0.9`. The Windows executable and native SQLite DLL have x64 PE headers.

The ARM host, `libe_sqlite3.so`, `libcoreclr.so` and `libhostfxr.so` have ELF64 little-endian AArch64 headers. The ARM runtime is self-contained and its archive/permissions are verified. **No native ARM or OCI execution was performed.**

Six live requests checked the compressed data, framework and WASM files through both HTTP and HTTPS. MIME, gzip encoding, exact content length and SHA-256 of the actual downloaded compressed bytes all matched the final Web payload. HTTPS used normal OS certificate validation, without a bypass or custom trust callback.

[The final career live probe](../career-live-validation.json) passed **11 of 11 scenario groups** with **46 HTTP requests** and **46 exact positive Content-Length headers**, including:

- Persistent-profile creation through real WSS and exact starter balance/inventory.
- Strict request schema, duplicate-field and origin rejection; HTTPS required for account credentials.
- Insufficient purchase/pristine repair rejection, concurrent duplicate trade, transaction conflict and ownership isolation.
- Registration/login/recovery without regranting money; one-time recovery rotation and revocation of old sessions.
- Signed offline save import, replay/tamper/foreign-profile rejection and online realm import denial.
- Explicit normal `logout` and `profile_revoked` WebSocket close frames. A broken connection alone was not accepted as success.

The probe created generated QA identities. Its receipt contains public IDs and outcomes; passwords, bearer tokens, recovery codes and exported save envelopes were not logged or written. Current checkout hashes in that receipt are paired with this delivery's executable/source provenance, rather than treated as proof of the running binary on their own.

## Isolated local hosts

| Realm | HTTP / HTTPS | PID at delivery | Private data root |
|---|---|---:|---|
| Offline release QA | `7887` / `7888` | 5276 | `_local/p07-release-offline` |
| Online-policy release QA | `7987` / `7988` | 23564 | `_local/p07-release-online` |

Both run the same final packaged Windows executable and serve its `web` directory, bound to loopback only. The online-policy host is a local test of online authority rules, **not a public Internet deployment**. Process/session metadata is stored under `_local`; no private data is copied into the release archives.

These are newly created, isolated QA realms. Existing P07 preview processes and `_local/p07-main-data` / `_local/p07-online-tests` were left unchanged. They were not replaced, migrated or relabeled as the final QA realms. P05 data was not modified. No firewall, certificate-trust, OCI or public network configuration was changed.

The demo uses explicit port overrides; extracted package launchers retain their documented default port and private adjacent `data` directory. See [README-P07.md](../../../tools/p07/README-P07.md) for offline LAN, account HTTPS and backup/restore instructions.

## Limits

This receipt establishes package integrity, Windows native SQLite operation, loopback HTTP/WSS career behavior and strict offline/online policy isolation. It does not establish physical two-PC LAN with WAN disabled, public Internet access, regional latency/capacity, native ARM behavior, long browser soak or final human usability/performance approval. Browser visual/gameplay observations are recorded separately by the P07 acceptance work.

P07 commerce has 15 SKU definitions sharing the P06 motorcycle model and handling. Only Canyon Run is currently playable; four other route environments and distinct bike art/tuning remain P08 content. Package byte size is not a claim that full original-game content parity has been reached.
