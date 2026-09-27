# OCI release d — mailbox concurrency repair

Release **`p09-20260927-d`** is deployed to the existing isolated Racing Bois staging service. The public endpoint remains `wss://racing-bois.158.180.59.36.sslip.io/multiplayer`, with trusted HTTPS readiness at `https://racing-bois.158.180.59.36.sslip.io/ready`. Caddy, DNS, firewall and other projects were not changed.

Backend source SHA-256: **`16787112e2104972c9f46c2b74c50504b0a26c2c4d8b1e5ebd97faa6e99da823`**. [Package receipt](../../p09-20260927-d-package.json).

The only runtime source change from c is `PeerMailbox.cs`, SHA-256 `1e231c52e99febd2f06354ae6d9a807de41db3d9510ebe86b3498e70a2b1a16e`. An extra semaphore notification no longer makes an empty, open mailbox look closed. This prevents the reproduced healthy-socket termination; explicit closure behavior is preserved. [Diagnosis and before/after proof](../../../p10/MAILBOX_DIAGNOSIS.md).

[The delta audit](source-delta.json) confirms 1,249 of 1,253 packaged files are byte-identical to c. The changed artifacts are the host DLL/PDB and the multiplayer test DLL/PDB that links the repaired mailbox. Gameplay, persistence, definitions and protocol source remain identical; their c receipts are preserved as historical unchanged-code evidence, not described as new d test runs.

Fresh d evidence:

- [ARM64 verification](arm-validation.json): the deterministic real-thread mailbox race passes on the OCI ARM VM; 32 multiplayer checks pass; native host/protocol/SQLite smoke passes.
- [Upgrade state check](upgrade-data-check.json): the complete logical realm state hash, identity, four pre-existing QA profiles, 992 credits total, ledger and receipts were identical before/after activation.
- [Live operations](live-ops.json): 21 trusted public HTTPS/account/policy/restart/backup/restore checks pass on d. Restart readiness was restored in 3.72 seconds. A separate restored d server accepted the preserved account and balance.
- [Deployment verification](deployment-verification.json): all 1,253 release file hashes, root ownership/write restrictions, private data modes, loopback-only listener and resource limits pass.
- [Shared service postcheck](shared-services-postcheck.json): the prior unrelated HTTPS site still returns 200; no Caddy/firewall mutation occurred.

[The fresh d 90-second WAN check passed](wan-90s.json): ten malformed cases rejected, eight real WSS peers, one reconnect, 92.46 seconds elapsed and stable source. Its [full receipt](../../../p10/network/20260926T190006Z/run.json) is separate from the failed first attempt.

The source-bound 30-minute d WAN soak completed **PASS** at 2026-09-26 19:33:13UTC. [Supervisor receipt](wan-supervisor.json) and [capacity measurements](capacity.json) bind the deployed process/files/source and the actual eight-peer run: 1,800.304seconds, 22racecycles, 14plannedreconnects and two storms. This passes its protocol/operations checks, not visual prediction smoothness. The separate correction diagnosis later reproduced a real missing-remote-immunity prediction defect; a corrected protocol release and fresh client verification are required. The earlier c PASS remains historical evidence.

The first d WAN attempt, [20260926T185612Z](../../../p10/network/20260926T185612Z/run.json), failed with `TaskCanceledException` after 15.6 seconds: three malformed handshake cases had passed and no gameplay clients had started. Its report cannot distinguish which connect/send/receive stage timed out, so the cause is **not established**. A separate [three-trial duplicate-kind diagnostic](duplicate-handshake-diagnosis.json), preserving the same 12-second deadline and ordinary TLS trust, rejected all three trials with Close frames in 0.878–0.990 seconds. The original failure remains FAIL; no timeout or admission rule was weakened. A fresh full run follows at unchanged d runtime source.

The existing local eight-hour P10 processes were not stopped, restarted or repurposed. No Jarvis MCP or paid tools were used. The four blocked-cleanup plaintext artifacts under `_local/p09-recovery` remain untouched and private; [their recorded status](../../cleanup-status.json) still applies.

Operator handoff: inspect `wan-supervisor.json` for `PASS`/`FAIL`, then read its `networkReceipt` and `capacityReceipt`. Launcher metadata/logs are under ignored `_local/p09/d-supervisor`; the top-level supervisor PID is recorded in `launch.json`. Do not edit server/shared or linked diagnostic-harness source while the WAN/local eight-hour tests run. The supervisor owns only its newly launched WAN test/observer children and never stops the existing local eight-hour processes or the deployed game service.
