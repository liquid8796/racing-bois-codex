# P08 content delivery

`P08ContentPackBuilder` is the single editor composition point for production
packs. Its asset references live under `Assets/RacingBois/Content/P08`, outside
Resources and the Race scene. The base scene keeps its P06 loading presentation.

1. Run `PrepareRoutes()` after the four new biome prop sets are imported.
2. Run `PrepareActors()` after all 15 bikes, eight riders and 24 portraits exist.
3. Run `Validate()`, `BuildEditor()` for Editor acceptance, then `BuildDesktop()`
   and `P08DesktopBuilder.Build()` from Unity MCP for the primary Windows 10/11
   player. See [desktop delivery](../desktop/README.md).
4. Web delivery is deferred. Its optional build flow uses `BuildWeb()` and copies
   only the manifest's immutable delivery files into the Web build:
   `python tools/p08/content-pack/audit_publish.py --web-root Build/Web-p08 --receipt docs/p08/streaming/web-export.json`.

The Editor build targets Windows64 and writes `Build/Content-editor`. The desktop
build uses `Build/Content-desktop`, copied into the player's
`RacingBois_Data/StreamingAssets/Content`. Native loading resolves that installed
folder through `Application.streamingAssetsPath`; it uses no developer-machine
path. The deferred WebGL build writes `Build/Content`. They have separate
manifests and platform-specific Unity CRCs. Each manifest has schema 1, an explicit
build target, the current shared gameplay content hash, one actor
bundle, five route bundles, and 25 Ogg resources. Bundle and Ogg names carry the
full SHA-256. Exact lengths, SHA and Unity CRC are included in each bundle row.

The actor bundle owns all player bikes/riders, police, traffic, pedestrian, club,
12 shared animation clips, 24 portraits, and the 72 short authored sound cues.
Its audio bank retains six original short P06 utility/ambient cues where the new
library has no replacement. Full music is absent from every serialized audio
bank. Music uses the existing single browser media element and stays outside the
WebAssembly decoded audio heap. The desktop music director loads installed Ogg
resources with the same bounded ownership and validated content allowlist. All
25 compositions/scores ship for offline use. The five default route compositions match the
audio delivery's explicit course associations.

Road furniture, marking materials and shared road textures are explicitly
assigned to the actor bundle. Route bundles reference that common dependency;
the loader keeps it once and swaps only the current route. The build rejects
unexpected dependencies and missing identities, portraits, audio roles or
audited compositions. Every route has six authored props, its own atmosphere,
road/terrain material variants, sky and cosmetic water material.

The Python audit checks exported distribution bytes and only copies into a Web
build directory under this project's `Build` directory. It does not mutate a
server, private user data, database or historical phase package. It retains old
immutable files safely; the manifest defines the current catalog. It does not
claim Unity CRC, browser playback, visual quality or memory acceptance from hashes.

Remaining acceptance is recorded by actual build receipts and runtime tests:
load/CRC success, corrupt/truncated rejection and retry, all identities, route
swaps without growing live meshes, full bundle limits, Web music activation and
offline host delivery. Successful managed compilation alone is not acceptance.
