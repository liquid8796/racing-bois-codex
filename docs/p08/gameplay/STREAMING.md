# P08 content streaming and runtime composition

Status: implemented and compiled against the installed Unity 6000.5.7f1 managed assemblies for both Editor and Web conditional branches. This is a compile preflight, not an Editor AssetBundle/WebGL runtime receipt. Actual bundle import, visual QA, browser transfer/error/retry and memory measurements remain parent-task acceptance work.

## Manifest contract

`/Content/manifest.json` uses schema 1 and exact `GameplayRules.ContentHash`. It contains `actorsId: "actors"` and a `bundles` array. Every row has `id`, `kind`, `url`, `sha256`, `bytes`, `crc`, `asset`, `courseIndex`.

- `actors`: one AssetBundle whose lowercase `assets/...` asset is `P08ActorContent`.
- `route-0` through `route-4`: one AssetBundle per biome; its lowercase asset is `P08RouteContent` and its `courseIndex` matches the ID.
- `music-*`: an original `.ogg` media resource, with empty `asset` and unused CRC. Its URL ends with its complete 64-hex SHA-256 plus `.ogg`. Music IDs must match the route and cinematic catalogs.

All URLs are relative to the same-origin `/Content/` root. Absolute URLs, cross-origin targets, credentials, traversal, encoded segments, query strings and fragments are rejected. Bundle sizes are bounded at 64 MiB; manifests at 128 KiB. Bundle bytes are checked against exact length and SHA-256, then loaded using Unity's CRC argument. A corrupt or incompatible manifest/bundle cannot enable Local, Ready or Start.

The Web music path uses a single HTMLAudioElement supplied by `P08MusicDirector`; it does not fetch/decode complete scores into WebAssembly. The stream uses same-origin transport and a hash-qualified URL with SHA/size metadata retained for packaging verification. The browser does not compute a full-file SHA before streaming playback. Editor music may decode one track through the media director's native fallback. A music playback error is cosmetic and does not block the race.

The host explicitly serves `.bundle`/`.assetbundle` as `application/octet-stream` and `.ogg` as `audio/ogg`; ordinary ASP.NET static-file range behavior remains available. An offline LAN host must carry every generated Content file beside the Web build.

## Ownership and lifetime

`P08ContentLoader` serializes requests. It retains one common actor bundle and one current route bundle. Before changing route, it calls the composition callback, clears the route registry, waits a frame for deferred scene destruction and unloads the previous route with dependencies. A failed load stops automatic retries; the UI exposes a manual retry. On destruction, pending requests are aborted and any in-flight AssetBundle completion is unloaded.

`ContentRegistry` exposes readonly Bike/Rider lists and Sfx/Voices maps. The serialized ScriptableObject fields are populated only inside bundles; no new pack references belong in Resources or the bootstrap scene. P06 scene references serve the initial loading/menu view only. Starting a race requires the selected P08 content.

`RaceStageView` selects exact authoritative bike/character indices and keeps a maximum 16 rider, 12 traffic and 6 pedestrian pooled views. Reuse requires matching identity. When a bounded pool is full, only an idle mismatched family is replaced. New character materials retain their authored appearance rather than inheriting an unrelated ID tint. Menu/cinematic actors remain separate from race pools.

`TrackRibbonView` rebuilds from `world.Track` when course/level changes. Generated meshes, chunk roots, cached bounds and route references are released between routes. All five themes use the approved concept-led props and materials. The Ridge gallery is widened to keep posts outside the road/shoulder corridor; Coastal water is a visual plane outside authority contacts. Road width, shoulders, curvature and elevation continue to come from shared definitions.

## Scene and UI composition

`RaceBootstrap` gates Local/Ready/Start on loaded content, retains practice choices, loads the matching lobby route, and publishes course/bike/character/content/music/cinematic telemetry. It refreshes career data after persisted results. Old rooms retain their original campaign level; promoted profiles must create an eligible room, with the lobby showing that constraint.

Optional cinematics pause local simulation and suppress regular stage rendering while playing. They stop at multiplayer Countdown/Racing and before route unload. Shop previews return to the career screen; gallery previews retain their gallery flow. The media coordinator preserves gallery state while its first actor/route download runs. Neither presentation nor the music service changes multiplayer authority, rewards or save state.

## Acceptance commands

`tools/p08/verify-gameplay.ps1 -ContentOnly` exercises native manifest rejection and core content tests. Once production masks are promoted, add `-RequireProductionContent` to require all 25 durable campaign qualifications.

Remaining runtime checks: actual bundle CRC success, truncated/SHA-corrupt bundle rejection and retry, no premature Ready, every route/level match between scene and authority, all 15/8 identities in the bounded pools, gallery/showcase return flow, streamed Web audio after a real gesture, and repeated route changes without growing retained meshes/bundles. These cannot be inferred from successful compilation.
