# OCI release e — protocol 5 remote collision immunity

Release **`p09-20260927-e`** is active on the existing loopback-only
`racing-bois-staging` service at `127.0.0.1:18080`. Public access remains
`https://racing-bois.158.180.59.36.sslip.io/ready` and
`wss://racing-bois.158.180.59.36.sslip.io/multiplayer` with normal certificate
validation. This is staging backend evidence, not completion of P08 art or
Windows client acceptance.

Source SHA256:
`90f38b173fcd7edac01a138d5aee5da1f4a773112f9ddf827e7ab1e045c54544`.
[Package receipt](../../p09-20260927-e-package.json).

The [source delta](source-delta.json) identifies exactly two runtime source
changes from d: `MultiplayerMessages.cs` and `MultiplayerProjection.cs`.
Protocol 5 carries remote collision-immunity state needed by client prediction.
Of 1,253 packaged files, 1,223 are byte-identical to d and 30 changed. No database
migration or economic-state rollback was performed.

Fresh evidence:

- [Installation](installation.json): archive hash and all 1,253 immutable files
  validated before activation.
- [ARM64 tests](arm-validation.json): multiplayer **32**, gameplay **31** and
  persistence **26** cases passed in a separately capped private QA directory.
  The gameplay receipt's 25 source hashes match the e test-source manifest.
- [Activation](activation.json) used the existing deployment lock and scoped
  binary rollback, retaining release d as the previous target. A fresh encrypted
  [backup](backup-before-activation.json) preceded the switch.
- [Upgrade preservation](upgrade-data-check.json): the complete logical realm
  state hash and identity, five pre-existing profiles, 1,240 total credits,
  ten ledger rows and five receipts were exactly equal before and after the
  release switch.
- [Live operations](live-ops.json): **21** trusted HTTPS, account/policy,
  idempotency, restart, backup and isolated restore checks passed. Readiness
  returned after restart in **3.66 seconds**. This intentionally created one
  new QA account and traded its starter bike; that later test-data change is
  separate from the exact pre/post-activation preservation check.
- [Deployment validation](deployment-verification.json): actual running
  executable, source/file hashes, Unix data privacy, resource caps and
  loopback-only listener pass; multiplayer protocol reports **5**.

## Shared-host evidence limitation

Caddy file hashes match exactly, every unrelated previously running service is
still running, and the unrelated HTTPS site returns 200. No Caddy reload/site
edit, firewall mutation, other-project restart or new paid service was invoked.

The [first shared-service postcheck](shared-services-postcheck-first.json)
failed on its raw `iptables-save` digest. That digest includes live chain
packet/byte counters and cannot distinguish counter movement from rule changes.
A [read-only diagnosis](firewall-counter-diagnosis.json) reproduced a
raw IPv4 hash change while the counter-normalized rules stayed identical across
two reads surrounding an ordinary HTTPS GET. The original failure remains
recorded. A normalized **pre-deployment** digest was not captured, so the
[current report](shared-services-postcheck.json) marks that before/after
structural measurement **inconclusive**, rather than fabricating a PASS. The
probe now also records counter-normalized hashes for future baselines.

## Remaining prediction finding

The completed protocol-5 WAN trace contains large equal-target
prediction corrections despite valid snapshots and exact diagnostic replays.
[Read-only observations](correction-observations.json) identify a distinct
pedestrian recovery gap: authority increments Stumbled age and recovers at
180 ticks, while the predictor leaves a non-Walking pedestrian's mode/age
unchanged. A captured authority recovery/re-collision at tick 2814 corresponds
to a 9.135 m Riding-to-Falling correction (9.065 m in the existing presentation
sample). This remains a gameplay-feel failure; a protocol/operations soak PASS
must not be presented as smooth prediction acceptance. Source is unchanged
while the protected runs continue.

## WAN duration evidence

The source-bound **30-minute** e WSS run `20260926T214515Z` completed **PASS**
at 2026-09-26 22:15:29 UTC. [Supervisor](wan-supervisor.json) and
[full run](../../../p10/network/20260926T214515Z/run.json): 1,800.282 seconds,
eight peers, 21 race cycles, 14 planned reconnects, two reconnect storms,
zero invalid snapshots and stable source.

[Measured capacity](capacity.json) uses this run's histogram deltas and private
observer samples: p99 tick **upper bound 1 ms**, one slow tick, zero dropped
catch-up ticks, zero persistence failures and zero automatic service restarts.
Average game cgroup CPU use was **0.155 cores**; maximum sampled cgroup memory
was **86,106,112 bytes**. This measures one room from one Windows Internet
origin, not worldwide gameplay or the eight-room configuration bound.

The final diagnostic observed **16.258 m** maximum equal-target prediction
correction with zero replay mismatches. [Its immutable episode](maximum-correction-episode.json)
and the earlier pedestrian example are retained; prediction smoothness remains
**unaccepted** despite the protocol/operations PASS.

[The end-of-soak deployment](deployment-after-soak.json) still verifies all
release files and the active protocol-5 process. [Shared-host checks](shared-services-after-soak.json)
confirm unchanged Caddy hashes, the unrelated HTTPS site's 200 response and
all earlier unrelated services still running. Counter-normalized firewall
rules stayed identical from the post-deployment diagnosis through soak end;
the missing pre-deployment normalized baseline remains explicitly unknown.

[Final scope summary](release-verification-summary.json). No d/c measurements
were renamed as e evidence, and no further deployment was made by this subtask.

The protected local eight-hour run `20260926T213110Z` and its supervisor/server/
probe PIDs **33776 / 20968 / 15344** were left untouched. No production, probe,
shared gameplay or Client.Application source was edited by this deployment.
The four earlier policy-blocked plaintext recovery artifacts under
`_local/p09-recovery` were neither deleted nor moved, and no alternate cleanup
route was attempted. No Jarvis MCP or Unity/Blender mutation was used here.
