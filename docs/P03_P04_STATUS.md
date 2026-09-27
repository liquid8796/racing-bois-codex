# Racing Bois — P03/P04 implementation and acceptance

Updated 2026-09-21. Scope: playable driving/combat graybox on desktop browsers, with original concept-guided assets. P01 remains an incomplete reverse-engineering audit. This implementation preserves verified rules where evidence exists and labels newly authored physical tuning; it does not claim 100% Road Rash parity or final P06 visual quality.

## Implemented

| Area | Current implementation | Evidence |
| --- | --- | --- |
| P03 driving | Original 2.2 km ribbon, 11 sections, curves/grades/shoulders, throttle curve, brake, offroad traction, lean, crest flight/landing, swept collisions | [Driving and replay](p03/driving-and-replay.md), [31 native tests](p03/gameplay-validation.json) |
| Camera and HUD | Chase camera with horizon handling, speed FOV and optional reduced motion; rank, route progress, rider/bike health, state and recovery cues | `RaceStageView`, `RaceScreen`, Unity capture |
| P04 combat | Left/right attacks and kicks, weapon reach, recovered Q8 damage/cooldown/steal gates, stable event IDs | [Combat, AI and rules](p04/combat-ai-rules.md) |
| Recovery | Separate bike and rider positions; fall, detached, physical running, animated remount, wreck/bust/finish | [Controlled capture](p03p04/unity/gameplay-combat-recovery.mp4), [reference observations](p03p04/reference-observations.md) |
| World actors | Five opponent bots, traffic, police braking/chase/bust; bounded pedestrians with waiting/walking/crossing/stumbled recovery | Shared core + maximum actor/soak tests |
| Race rules | Stable finish order, top-three qualification, recovered reward table/fines; temporary local campaign bookkeeping | Native/integration tests; one playable route only |
| Local and server | Immediate offline practice uses the same core as server authority; v2 snapshots/events and input validation | [Backend evidence](p03p04/backend/final-backend-verification.json) |
| Assets | Eight original prefabs, 3 LODs, PBR palettes, simple colliders, identity roots; correct meter scale and +Z/left-right axes | [Asset pack](p03/assets/ASSET_PACK.md), [Unity validation](p03/assets/unity-validation.json) |

## Asset workflow requirement

The user requires a 2D concept before each 3D design. Seven generated references and exact prompts are retained in [ArtSource/Concepts/P03P04](../ArtSource/Concepts/P03P04/PROMPTS.md): the six references used for the original eight-prefab pack, plus the club concept. The subsequent P05 release adds the concept-guided [club prefab](p04/club/ASSET.md), bringing the current pack to nine prefabs. Models were authored/revised through Blender MCP after inspecting the concepts. The original early graybox is archived with its actual chronology. No extracted original-game asset is a runtime asset.

The available built-in image generator does not expose a model selector or confirm the requested name “GPT Image 2.5”; provenance records the actual tool and this limitation. The first club concept attempt was rejected by the generator's safety filter, but the user-requested retry on 2026-09-21 succeeded using the same built-in tool. The club has now been modeled, imported and attached to either hand in gameplay; the earlier rejection remains recorded as history. A dedicated chain prop remains open.

## Verification boundaries

- Shared tick, protocol/application and live WS/WSS checks are separate receipts. Native microbenchmarks do not establish browser render performance.
- The controlled visual capture sets initial rider/traffic positions, then uses the real shared simulation and input intents. It is not human input footage or a matched recreation of the reference video's unknown inputs.
- Reference recovery takes roughly 7–8 seconds in the sampled original sequence. Our recorded scenario has different speed/contact geometry and is documented separately. Similar state order does not prove matching all original timings.
- Rig articulation and synthesized audio are gameplay prototypes. Skin deformation, authored animation clips, final scenery/materials/lighting/audio and final UI art remain P06 work.
- Full original physics/bike SPEC interpretation remains open in P01. One authored route and tested five-course campaign bookkeeping do not constitute five playable routes or complete content parity.
- The follow-up [P05 implementation](P05_STATUS.md) adds prediction/reconciliation, rooms and reconnect. Actual two-machine LAN/WAN proof, remote contact presentation quality and public deployment remain open. No service was deployed on the OCI VM in P03/P04 or this P05 run.

## Final artifact and browser evidence

Runtime `130fa9b`, release Web `Build/Web-p03p04-v2`:11,037,632bytes, zero build errors/warnings. [Browser acceptance](p03p04/BROWSER_VALIDATION.md) verifies visible local/WSS flows, short Q/E/kick inputs, input ACKs, Vietnamese UI,720p/1080p layouts and the native↔WASM3000-tick golden. A browser-discovered short-press bug was fixed in both render-to-tick and server command sampling.

Checks:31gameplay tests,14integration tests,18P02regressions; WS/WSS each8checks with8clients. [Delivery](p03p04/backend/delivery.json) records Windows SelfTest and complete package/Web hashes; ARM64 native execution remains untested for this release.

The sampled1080p window reports3ms p50/4ms p95 and roughly108MB Unity allocated/161MB WASM memory. GPU timing, release per-frame GC and per-tab resident memory are unavailable/unmeasured. These are sampled baselines, not complete hardware/performance acceptance. **P03/P04 implementation is delivered, with fidelity/manual-feel/full-performance acceptance still open as listed above.** No100% original-game parity, final-art or global multiplayer claim is made.
