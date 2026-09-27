# P10 — native release verification

Updated 2026-09-27 (Asia/Bangkok). **P10 is in progress, not release accepted.** Windows 10/11 x64 is primary; Web remains deferred. OCI owns the online realm and an independent local host owns offline LAN. Jarvis MCP is prohibited, including delegated work.

## Evidence established in this work

| Evidence | Result and scope |
| --- | --- |
| [Native regression](regression/20260926T184121Z/receipt.json) | 214 groups in 13 real suites PASS; source stable during that run. Production content gate remains closed. Includes shared gameplay, client application, lobby/reconnect, real SQLite economy/reward concurrency/migrations/crash recovery, native socket adapter, desktop config, proxy policy and the deterministic mailbox concurrency regression. |
| [Strict protocol corpus](fuzz/20260926T1759-unicode-range-final.json) | 315 structural/schema cases, 20,000 seeded frames and 50,000 adversarial integer input attempts PASS. Valid Vietnamese/supplementary Unicode is preserved. Every range attempt is rejected specifically as `input_range`. A valid mutation may remain schema valid; acceptance count is reported honestly. |
| [Live local networking](network/20260926T175043Z/run.json) | Eight actual .NET socket clients, 90 seconds, ten malformed-frame cases, real race progress and identity/slot-preserving reconnect PASS at the prior mailbox revision. Server/probe binaries and sources are hash-bound; the later concurrency fix requires the new long run. |
| [Live HTTPS/WSS career](career/20260926T184132Z/run.json) | Eleven checks PASS after the mailbox fix, no skipped online checks, on separate loopback offline/online realms using ordinary certificate validation. Real register/login/recovery/revocation, origin/schema/ownership policy and idempotent economy operations. |
| [Local hardware inventory](hardware/local-inventory.json) | Windows 11 Pro build 26200, i7-11800H, RTX 3070 Laptop GPU, approximately 64 GiB RAM. Inventory only; no player performance inferred. WMI AdapterRAM is not a reliable measurement above 4 GiB. |
| [Long local soak](network/20260926T175547Z/run.json) | **FAIL** at485seconds: `start_timeout` after5rematches and3deliberate resumes. No invalid snapshots, persistence failures or dropped server ticks were reported, but several unexpected reconnects occurred. The cause is under diagnosis; the 8-hour gate is open. A separate trace candidate preserves gameplay/timeout behavior and records sanitized command/epoch/member/readiness details. |
| [Native observer verifier](recorder/20260926T181957Z/receipt.json) | Nine configuration tests, eight negative raw-evidence tests and three managed compilation branches PASS. Actual Windows player run pending. |

A real mailbox concurrency defect was subsequently reproduced and fixed; see [diagnosis and before/after proof](MAILBOX_DIAGNOSIS.md). The replacement eight-hour run started at2026-09-26 18:43UTC but was **intentionally superseded at20:50UTC**, before eight hours, after an independent trace reproduced a different prediction defect. Its [supersession record](network/20260926T184316Z/intentional-supersession.json) identifies the verified task-owned probe that was stopped and its supervisor-owned server cleanup. The raw supervisor records process termination as FAIL; it is preserved, not relabelled PASS. The initial failure had no detailed trace, so the mailbox race is not claimed as its sole proven cause.

The new outlier trace proved a missing remote remount-immunity timer: the authoritative neighbor remained collision-immune, while the local proxy treated it as vulnerable. This produced a phantom predicted wreck and a presentation change exceeding ten metres. Offline replay replacing only the observed immunity matched the later authoritative-rebased checkpoint exactly. The minimal validated wire/projection fix and regression are in progress; the eight-hour test must restart from a new frozen source afterward. The existing d WAN protocol PASS does not accept this visual defect.

The first attempted 8-hour run was intentionally superseded within its first few minutes when P09's private-metrics policy required a public-readiness probe option. Its original reports and [explicit interruption reason](network/20260926T175241Z/intentional-supersession.json) are retained. It is not a gameplay failure or an 8-hour success.

Every result establishes only its stated scope. Subsequent source changes can invalidate the current-release applicability of a prior report even when it passed at its original source snapshot. A build log, file count, screenshot, or passing fixture is not a substitute for the separate player and visual gates below.

## Defect found and corrected

Seeded mutations found that `JsonDocument` may defer malformed UTF-8 decoding until `JsonElement.GetString()` or a property-name read, throwing `InvalidOperationException` outside the protocol's expected `JsonException` rejection path. The [original failing fixture](fuzz/20260926T1750-repro.json) contains only generated test bytes, with no credentials. `WireJson.ReadDocument` now validates strict UTF-8 and escaped Unicode scalar pairs at the protocol boundary; both wire parsers use it. Invalid text is rejected as `JsonException`. The regression corpus includes the exact original bytes and both unpaired surrogate directions. Normal Vietnamese and valid supplementary Unicode remain supported.

## Repeatable commands

Run from `D:\Project\Unity\racing-bois`. Each invocation creates a new timestamped receipt; no existing result is overwritten. The private fixture data and logs stay under `_local/p10`.

```powershell
python tools/p10/run-regression.py
dotnet run --project tools/p10/ProtocolFuzz -c Release -- docs/p10/fuzz/NEW-RUN.json
python tools/p10/run-career.py
python tools/p10/run-network.py --seconds 90 --peers 8 --fuzz
python tools/p10/run-network.py --seconds 28800 --peers 8 --fuzz
```

The network supervisor publishes exact copies of the server and probe, checks source stability, binds a new loopback port and new private offline realm, records each published file hash, samples owned process memory and stops only its own process handles at the end. It does not enumerate/terminate existing servers or change certificate trust, firewall or OCI. Probe credentials exist only in process memory. The fresh HTTPS career supervisor similarly owns two independent realms and uses the already trusted localhost certificate.

For the explicitly deployed OCI staging endpoint, P09 owns launch timing and captures private health metrics through SSH. The probe accepts public readiness without requiring infrastructure data exposure:

```powershell
python tools/p10/run-network.py --endpoint wss://racing-bois.158.180.59.36.sslip.io/multiplayer --health-url https://racing-bois.158.180.59.36.sslip.io/ready --seconds 90 --peers 8 --fuzz
```

`--health-url` is limited to `/ready` or `/multiplayer/health` on the same origin. TLS remains ordinary OS validation. Public readiness checks protocol/content identity and actual race checkpoint progression; unavailable private tick/persistence counters remain null in the report. Private counters are supplied only by P09's separate evidence. One room of synthetic peers from one client network is not a regional capacity or two-human multiplayer claim.

## Mandatory outstanding release gates

| Gate | Required evidence; current disposition |
| --- | --- |
| Complete content | All required rows in the parity ledger mapped and independently accepted by semantic category; current production masks are still closed. |
| Exact concept fidelity | Frozen concept version/hash and comparable actual render views for every UI/3D asset; all recorded mismatches resolved. No numerical similarity score or mesh PASS can establish 100% fidelity. |
| Real Windows build | Actual successful Unity Windows64 build, source and file receipts, installed content audit, native player launch. Root owns Unity/build operations. |
| Player correctness | Native campaign from new profile through every route/level; roster selection, cutscenes, music/SFX, commerce, results and restart persistence. Full 25-route qualification test must run after genuine production acceptance opens the mask. |
| Desktop UX/input | Mouse, keyboard, real gamepad and remapping; focus/Back, pending/error states, UI scaling, windowed/borderless/fullscreen, resize, focus loss and suspend/resume. Actual player operations and captures required. |
| Frame pacing/memory | Actual Medium 1080p 10-minute race: mean at least 60 FPS and p95 frame time at most 20 ms; managed/native/GPU memory, GC and route swap residency. Proposed process budget 2 GiB must be measured, not assumed. |
| Hardware coverage | Both Windows 10 and 11; reference laptop and weaker integrated-GPU system. Current inventory covers one Windows 11 laptop only. |
| Physical LAN | At least two physical PCs on LAN with WAN disconnected, installed content/cold start, complete race and reconnect. User currently has one PC; synthetic clients do not close this gate. |
| OCI operations | Current source-bound public TLS/WSS, private DB, real restore/rollback/failure drills and capacity measurement. See P09 receipts rather than assuming from VM specifications. |
| Geographic connectivity | Actual clients/agents in SEA, EU and NA with measured latency and match behavior. One-region deployment is not universally low latency. |
| Soak | 8–24 hours completed with unchanged source and final PASS, bounded memory/queues and repeated race/reconnect cycles. The current run is pending. Native socket soak does not replace Unity player graphics/audio soak. |
| Release packaging | Reproducible immutable source/content snapshot, native player and separate LAN host manifests, verified archive bytes, version/content/protocol compatibility and final user/operator documentation. No accepted native release archive exists yet. |

## Native player acceptance procedure

Use the actual [P08 desktop build workflow](../p08/desktop/README.md) and its verifier. Build into a new output directory only after production content and reference-fidelity review. Root must operate Unity through direct Unity MCP and purpose-built in-game harnesses; no OS UI automation workaround is authorized.

The new [native player observer and independent raw verifier](NATIVE_RECORDER.md) prepare this acceptance without driving the player or replacing its gameplay/UI. It is opt-in, binds actual player/build/content identities, and retains every frame in a 600-second observation. Policy and verifier fixtures are tested; an actual player run remains pending.

Bind capture/performance reports to the actual player executable, content manifest, build receipt and final source fingerprint. Record Windows build, GPU/driver, quality tier, resolution, input devices, graphics API and whether captures are cold or warm. Separate raw observed frame samples from summary percentiles. A screenshot must show the corresponding concept camera/layout view, and gameplay captures must show live interaction, not a pasted reference image.

The independent LAN host must use a private data directory outside the public content root, preserve realm kind, and never import offline balances into the online authority. Include account recovery/save-migration and native disconnect/resume paths in the final operator/user instructions. Publish only after all required gates pass; changing the release scope requires an explicit product decision rather than silently dropping a gate.

## Repository state note

Live `git log` in this checkout reports an unborn `master` branch, with project trees untracked. Historical commit IDs from prior notes are not accepted as current build identities. This work preserved the Git state; published/tested binaries are bound to actual source/file hashes instead. The protected user edit `ArtSource/Weapons/RB_Club.blend` is outside this task's edits and cleanup.
