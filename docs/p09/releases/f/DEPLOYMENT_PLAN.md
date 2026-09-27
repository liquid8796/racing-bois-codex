# Release f — immutable package, activated staging backend

`p09-20260927-f` is now the **active protocol6 staging backend**. Root authorized activation after the [30-minute local protocol/operations run](../../../p10/network/20260926T230400Z/run.json) completed PASS. [Installation](installation.json) verifies the uploaded hashes and1,986files; [ARM validation](arm-validation.json) passes all148groups. A [fresh encrypted backup](backup-before-activation.json) preceded the [scoped activation](activation.json), which retained e as the previous release. [Exact postchecks](activation-postcheck.json) and [actual-process/file validation](deployment-verification.json) pass: logical realm state preserved, protocol6 running from f, loopback listener, unchanged Caddy/counter-normalized firewall, prior unrelated services running and unrelated site200. Only the Racing Bois service was restarted. No Caddy/firewall edit or player-data rollback occurred. Recorded prediction/presentation outliers remain unaccepted; this staging activation does not close P08 visuals, full Windows client acceptance or an8-hour gate.

Package identity:

- Archive `Build/OciStaging/p09-20260927-f.tar.gz`,46,829,359bytes, SHA256 `3eeae66746ba7de5293a3d76b833eb0c930dc3f09bd4388d3e08da2bf9d68ca9`.
- Runtime source SHA256 `194d60c159d8978a8520d17df1c900cae09e2614d4b1f620c89b9a5bbcf54c24`.
- Test source SHA256 `f6b89fb632c793ae0446d129da302f195b88780799117f7c80061853b65babd6`.
- QA fixtures `Build/OciStaging/p09-20260927-f-arm-fixtures.tar.gz`, SHA256 `14801052aea2ba8fab8446f5000228dbb303c4b11575c0b7ec74711e49693d10`.
- [Local verification](local-verification.json) verifies all1,986 packaged files, all source/fixture hashes and7ELF64AArch64 entry points. It is not ARM runtime execution.

[Exact delta from e](source-delta.json) contains10runtime source changes: protocol/version, server projection, shared pedestrian transition/context, shared mode clock/combat context, deterministic combat factoring, predictor/contact ordering and driving-clock factoring. Authoritative gameplay rules/content hash and3k/20k goldens are unchanged. No schema migration is introduced. Protocol5 clients must be replaced by protocol6 clients; they are explicitly rejected rather than silently interpreting new row layouts.

The e test-source manifest did not include Client.Application. Added App inventory rows in the f manifest are improved coverage, not proof that every App file changed. The reviewed30-file patch and `docs/p10/proxy-transition-staging/applied-source-freeze.json` define the actual client/shared/test delta.

## Root-owned deployment sequence (steps1–5 completed; native/WAN/8-hour follow-up remains)

1. Re-verify package/fixture SHA and live source freeze. Capture a fresh read-only shared-host baseline, including **counter-normalized** IPv4/IPv6 firewall hashes, Caddy file hashes, unrelated running services/site status, active binary/source/protocol, logical realm state and room count. Require expected `aarch64`, active e and no active room before the switch. An earlier preflight is evidence of its own instant, not an activation-time guarantee.
2. Upload only these immutable archives and reviewed ops into a new private `/tmp/racing-bois-p09.<random>` directory through the existing authorized SSH route. Validate hashes remotely and prepare a new `/srv/racing-bois/releases/p09-20260927-f` with the existing scoped installer. Do not replace e/current during this step.
3. The existing installer chmods its original four entry points only. Explicitly make the three **new test** apphosts executable inside this exact release: `tests/prediction/RacingBois.Prediction.Tests`, `tests/prediction-projection/RacingBois.PredictionProjection.Tests`, `tests/p05-client/RacingBois.P05Client.Tests`. Do not change modes broadly outside the new release.
4. Extract the hashed fixtures into a fresh0700private QA directory owned by `racing-bois-staging`; fixture paths preserve repository-relative source/JSON names used by test receipts. Run the following native binaries under the existing capped transient QA service convention (`CPUQuota=75%`, `MemoryMax=768M`, bounded runtime), with that QA directory as cwd. Each report must match this release/test-source manifest and contain actual nonzero passing cases:

| Relative binary | Report argument | Expected groups |
| --- | --- | --- |
| `tests/multiplayer/RacingBois.Multiplayer.Integration.Tests` | absolute JSON path |32|
| `tests/gameplay/RacingBois.Gameplay.Tests` | absolute JSON path |31|
| `tests/persistence/RacingBois.Persistence.Tests` | `--report <absolute JSON path>` |26|
| `tests/prediction/RacingBois.Prediction.Tests` | absolute JSON path |13|
| `tests/prediction-projection/RacingBois.PredictionProjection.Tests` | absolute JSON path |10|
| `tests/p05-client/RacingBois.P05Client.Tests` | absolute JSON path |36|

5. After all148ARM groups and the local short stress gate pass, root takes a fresh encrypted backup and captures an immediate logical realm baseline/no-active-room check. Activate with the existing deployment lock and scoped rollback script, retaining e. Verify loopback-only listener127.0.0.1:18080, actual process executable/release hashes, protocol6, expected service caps and exact pre/post logical realm preservation. No economic-state rollback is part of a binary rollback.
6. Run trusted external HTTPS/WSS checks and the Unity Mono WSS specimen against the existing public endpoint. The native specimen uses the real production client transport/session and no TLS bypass. Then run source-bound WAN stress and the separately scheduled8-hour test. Preserve every interrupted/failing receipt. Compare fresh counter-normalized firewall/service/Caddy baselines; do not treat live packet-counter changes as firewall edits.

Existing endpoints remain `https://racing-bois.158.180.59.36.sslip.io/ready` and `wss://racing-bois.158.180.59.36.sslip.io/multiplayer`. There is no requested public-port, domain, TLS-policy or unrelated service change in this release.
