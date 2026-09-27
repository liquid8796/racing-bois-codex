# P06 production slice work plan

Started 2026-09-21 from runtime P05 `9873732`, evidence `94be01e`.
Scope: one fully playable Canyon Run slice, original art, presentation and UI;
no content-volume completion claim and no public deployment.

1. Generate and inspect fresh 2D concepts before any new/revised 3D design.
   Keep exact prompts, real provider metadata, source and import mapping.
2. Motorcycle and rider: refined silhouettes/materials, clean pivots, LODs,
   authored animation assets and hand/wheel contracts. Keep core authority unchanged.
3. Canyon: eroded rock, vegetation, road materials and roadside props, bounded
   scene population, warm daylight, atmospheric depth and quality tiers.
4. Presentation: pooled dust/sparks/skid, layered original audio with mix control,
   readable animated UI and accessible keyboard/gamepad focus/settings.
5. Integrate through Unity MCP, validate assets and animation, capture actual
   gameplay, benchmark/stress scenes and render/runtime metrics.
6. Release Web build and same-PC browser/local multiplayer regression. Record
   remaining human usability, hardware or physical-network gates explicitly.

The user confirmed concept-first again for P06. Built-in ImageGen does not expose
an explicit model selector; do not label it GPT Image 2.5 without provider proof.
No extracted original-game content enters the build. Existing P05 remote-contact
presentation and bandwidth limitations remain tracked in `docs/P05_STATUS.md`.

Preflight: modified `RB_Club.blend` and `Race.unity` existed before this work.
Both were copied to `_local/p06-preflight` before integration. The scene changes
add URP camera/light metadata and will be preserved in the P06 scene configuration.
The existing club source is not rewritten for P06.
