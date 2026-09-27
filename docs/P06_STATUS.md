# Racing Bois — P06 production slice

Started 2026-09-21; integration continued 2026-09-22 (Asia/Bangkok).
Release 0.6.0. Implementation, Editor integration, native regressions and local
Web/package delivery are complete. Final human/hardware/network acceptance
gates remain open. This phase upgrades one Canyon Run slice. It does not close
P01 full reverse, P05 physical-network/remote-contact, P08 complete-content or
P09 public-deployment gates.

## Original concept-first art

New motorcycle, rider, canyon and patrol concept sheets were generated and
inspected before their corresponding 3D work. Traffic uses the previously
generated and inspected coupe/van concepts. Exact prompts and real generator
provenance are in [P06 concepts](../ArtSource/Concepts/P06/PROMPTS.md). The built-in
tool does not expose a verifiable model name; no GPT Image 2.5 claim is invented.

The slice uses six P06 hero prefab variants and seven P06 scenery prefabs.
Patrol variants share explicitly identified base geometry/material surfaces;
LODs and variants are not counted as independent original-game content parity.
The original club and pedestrian remain in use.

- [Hero source/QA](p06/hero/ASSETS.md): motorcycle 14,668 triangles at LOD0,
  rider 11,442; three LODs, URP PBR, normalized two-influence Generic skin,
  twelve authored clips, no root-motion authority. All 27 source meshes across
  five geometry exports pass independent topology/UV checks. Unity separately
  samples the imported clips and BakeMesh bounds.
- [Scenery layout](p06/environment/scenery-layout.md): layered sandstone,
  sage/grass, guardrail, chevron and utility pole/cables, static mesh batches,
  LOD and bounded chunk visibility. Road physics remains unchanged. Large-prop
  footprints are rejected against the full route, including another arm of a bend.
- Newly authored stochastic road/gravel/stone PBR maps replace the overly
  regular first material pass. Warm directional light, a restrained URP post
  profile, sky and an original ambient reflection cube provide the shared look.

## Presentation and UI

[UI direction](p06/ui/DIRECTION.md) implements shared graphite/amber styling,
contextual lobby/results states, focus handling, quality tiers, HUD scale,
audio and reduced-motion preferences. Gameplay input is neutral while settings
or an explicit HUD control owns focus; settings do not pause server authority.

[Audio/VFX](p06/audio-vfx/README.md) includes seventeen original clips, layered
engine/gear/tire/gravel/wind, music ducking, UI feedback, dust, sparks and skids.
Fifteen audio sources and bounded particle/trail pools replace unbounded effects.
Audio source checks pass clipping, loop seam and true-peak tests; audible browser
review and final subjective audio approval are separate acceptance items.

The rider animation graph samples authored clips using authoritative state age.
The club attaches to the imported hand bind basis. Pooling reuses nearby riders,
traffic and pedestrians, including interpolation, tint and weapon-state reset.

## Verified integration

- Scene references and imported asset validation passed without related Unity
  console errors/warnings.
- [Actual Play Mode pool smoke](p06/acceptance/README.md): 24 ID generations,
  16 riders, 12 traffic and 6 pedestrians; 34 pooled entries remain 34, with
  1,598 reuses and zero type rebalances. Menu retirement and left-club/Fist/right-
  club reset assertions pass. This is functional evidence, not a performance test.
- Native regressions: 31 gameplay, 32 client, 25 server-domain, 14 race integration
  and 18 foundation checks pass. The 3,000-tick and 20,000-tick golden hashes
  remain `ED162155D421B3CF` and `3F421751C31690CB`.
- [Controlled gameplay video](p06/unity/gameplay-combat-recovery.mp4) and its
  [timeline](p06/unity/gameplay-timeline.json) show real simulation-driven combat,
  falling, running and remounting over 360 frames at 30 fps. Initial positions
  and inputs are a scripted fixture; the MP4 is a silent visual capture, not
  human-play or reference-parity footage.

## Measured Editor performance

Hardware: i7-11800H, RTX 3070 Laptop, Direct3D12. Medium index 1, render scale 1,
1920x1080, 8-second warmup and 60-second measurement. Unity's inherited quality
level label is Ultra, but the recorded P06 runtime tier is Medium.

| Workload | Mean FPS | p95 frame | Worst frame | Dropped simulation ticks |
| --- | ---: | ---: | ---: | ---: |
| Standard, uninterrupted | 59.994 | 17.268 ms | 35.026 ms | 0 |
| Stress: 16 riders + 12 traffic + 6 pedestrians | 60.000 | 17.236 ms | 35.044 ms | 0 |

Both runs have valid coverage, stable resolution/quality and required actor
density. GPU mean is approximately 2.44 ms. The stricter 16.667 ms p95 flag remains
**false**; measured p95 is below the architecture's proposed 20 ms target.
The first standard run included an in-sample MCP call and retained a 1,528 ms
spike; it remains in the [summary](p06/performance/summary.json), alongside the
uninterrupted rerun. Editor-wide allocation/memory counters include Editor and
tools and do not establish Player memory cost or zero allocations.

These one-minute measurements do not replace the proposed ten-minute browser
replay, an iGPU/low-end device run, physical gamepad use or novice-user usability
testing. Final art/audio/feel approval remains a human review of the playable
slice, not an automatic conclusion from topology checks or generated concepts.

The measured runtime was `c1762b8`. Final runtime `efce749` additionally corrects
chevron direction, persistent-data synchronization, Enter-to-join and invite
field clipping. The final runtime was not rebenchmarked in the Editor; final
browser checks are recorded separately below.

## Final Web and local delivery

- [Unity build](p06/unity/build.json): final `efce749`, direct release IL2CPP/gzip
  output `Build/Web-p06-v4`, 21,530,218 bytes, 153.79 seconds, zero build errors
  and warnings. No post-build HTML or binary patching.
- [Browser validation](p06/BROWSER_VALIDATION.md): two real browser clients on
  **one physical PC** entered the same race over WSS; Enter-to-join, invite
  readability, ready/start, movement, successful lobby reload/resume, expired
  lease feedback, HTTP/WS guest connection, local 1080p results/retry and audio
  unlock were observed. Captured warning/error logs were empty. The kick pose
  does not establish PvP damage; this pass does not claim successful race resume.
- [Delivery](p06/backend/DELIVERY.md): Windows self-contained ZIP is 69,527,484
  bytes; native SelfTest, 368 immutable files and archive hashes pass. ARM64
  tarball is 66,265,234 bytes; architecture/archive/permissions pass, native
  execution is not verified. Both contain exactly the final Web payload.
- Local demo: [HTTPS](https://localhost:7778/) or
  [HTTP](http://127.0.0.1:7777/), bound to loopback only. Normal certificate trust,
  gzip and MIME headers passed. Existing private realm/data are retained outside
  the distribution. Physical LAN and public Internet acceptance remain open.

## Preserved user work

The pre-existing modified `ArtSource/Weapons/RB_Club.blend` was backed up and left
unchanged. Existing URP metadata in Race was preserved while integrating P06.
No OCI service, public DNS, firewall or WAN setting was changed.
