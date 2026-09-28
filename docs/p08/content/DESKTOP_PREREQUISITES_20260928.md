# Full P08 desktop content prerequisites

The current desktop preflight is correctly blocked by missing production content.
Creating `Actors.asset` alone cannot resolve it. The existing full-catalog contract
requires 15 bike prefabs, eight rider prefabs, 24 portrait states, five route
assets and their real dependencies before it can build the six Unity bundles.
Availability masks remain **1/1/1**; they do not relax those bundle validators.

This read-only audit is recorded in
[desktop-prerequisites-20260928-01.json](desktop-prerequisites-20260928-01.json).
It hashes actual files and declared inputs; it does not import assets or claim
native/visual acceptance. Root's live `P08DesktopBuilder.Prepare()` stopped at
`Assets/RacingBois/Content/P08/Actors.asset` after the safe builder compiled.

| Required input | Current disk evidence | Work still required |
| --- | --- | --- |
| `Actors.asset`, `Library.asset`, `AudioBank.asset`, `Route-0.asset` … `Route-4.asset` | Entire `Assets/RacingBois/Content/P08` directory is absent; all eight assets missing. | Compose these only after their complete real inputs and acceptance requirements are satisfied. |
| Bikes 00–05 | Six legacy P08 prefabs exist. Slot00 explicitly aliases `RB_P06_Motorcycle`; slots01–05 reference their legacy FBX/BikesA atlas. | Existence is not approved Golden/reference fidelity. Preserve declared legacy identity; do not label aliases as new distinct art. |
| Bikes 06–12: Corvus, Viper, Rift 750 N, Specter, Nightjar, Cinder 10, Rift 750 | Seven `.blend`/FBX/concept exports exist and their declared hashes match; production prefabs are missing. BikesB and BikesC `.mat` assets are missing, though all four maps for each exist. | Review the actual source/reference versions and native geometry/material/LOD output before a scoped import/promotion. Export receipts are not visual approval. |
| Bikes 13–14: Odyssey, Havoc | Concepts exist; no canonical production `.blend`, FBX, manifest entries or prefabs. | Original concept-matched models, material/LOD delivery and native review. |
| Eight riders: Ash, Juno, Mako, Rook, Sol, Vale, Echo, Kai | Eight concept PNGs exist. All canonical `RB_P08_Rider_00` … `_07` models and prefabs are absent. Golden Ash candidates are separate unaccepted assets. | Eight actual authored deliveries with compatible rig/clips, skin/LOD/contact/expression review. Do not duplicate Ash or the P06 rider to fill slots. |
| Portraits | `Art/P08/Portraits` is empty: all 24 exact PNG paths are missing. | Three real states per rider: neutral, happy, focused. Existing recipe code is not a rendered delivery. |
| Route props | All 24 P08 city/ridge/coast/orchard prop prefabs exist; required Canyon P06 props and shared guardrail/chevron/pole also exist. | Current reference/geometry review, exact native bindings and route composition remain required. Resolve the Ridge provenance mismatch below first. |
| Route surfaces/atmosphere | P06 asphalt/gravel/roadside and paint/yellow materials exist. `Materials/P08/Routes` is absent. | Five route material/sky/atmosphere sets and five route assets, retaining exact shared furniture dependencies; then actual route/variant checks. |
| Shared auxiliary actors/clips | Existing police bike/rider, coupe, van, pedestrian and Club prefabs exist. P06 rider FBX exists and its importer metadata declares all 12 required clip names. | Native clip loading and actual runtime pose/contact checks are still separate. This disk audit does not approve those legacy visuals. |
| Audio/media | All 97 delivery OGGs match hashes; audio-manifest/audit hashes also match. There are 25 music tracks/scores and 72 SFX, including 47 reaction cues. | Bind the real 25 effect/47 reaction clips into the generated library/bank; keep full music streamed. Signal/hash checks do not establish all semantic/listening acceptance. |
| Desktop distribution | `Build/Content-desktop`, `Build/Content-editor` and project `StreamingAssets/Content` are absent. | After content validation, build one actors bundle + five route bundles + 25 hashed OGGs, validate their manifest/CRC/dependency closure, then build the full player. |

The art manifest currently declares `passed=false` and
`exported-awaiting-independent-source-and-Unity-QA`. Its 36 entries comprise 12
bikes and 24 environment props; it has no rider or extra-traffic entries. The
pack's optional `TrafficExtras` array therefore currently resolves to zero; that
is not evidence that the broader traffic semantic-parity work is complete.

**Ridge source identity must be reconciled.** Of 108 declared concept/source/FBX
hash references, 12 mismatch across RidgeFir, RidgeGalleryArch, RidgeGranite,
RidgeSnowPole, RidgeStoneWall and RidgeTimberHut. These represent one changed
shared `.blend` and six changed FBX files. The exact expected/actual hashes are
in the snapshot. No hashes or historical receipts were silently rewritten.

**Golden candidates cannot be used as an unreviewed shortcut.** There are 27
Golden prefab files on disk, but no
`docs/p08/promotion/production-bindings.json`. The binding gate requires an
explicit accepted review tied to the semantic slot, exact descriptor/reference,
source-bound native import and unchanged prefab. Actor acceptance requires six
corresponding views; environment acceptance requires gameplay/detail views. Each
must explicitly review silhouette, proportions, geometry, placement, materials,
color and details with no unresolved differences. Missing acceptance, changed
source, contradictory import receipts or an unbound Golden prefab remain rejected.
The current semantic ledger is still 491 rows: 192 partial, 299 pending and zero
accepted. A file count or successful import does not change that status.

The current route contract consumes six **individual prop slots**, shared road
furniture and materials through `TrackRibbonView.ApplyContent`. The promotion
gate likewise enumerates those prop slots; it has no full-route/environment-root
binding for the assembled Golden Canyon prefab. That candidate cannot simply be
assigned to a rock slot. Its eventual production integration needs an explicit
reviewed modular/route mapping and native gameplay-view validation, in addition
to its own art acceptance.

The preparation path now checks the entire shared pack before any `Upsert` or
portrait/audio importer change. `Setup()`, `PrepareRoutes()` and `PrepareActors()`
all reject the current 41 missing prefab/portrait inputs without creating route
assets. Global `SaveAssets` has been replaced by saves of the exact generated
route/material or actor/library/bank paths. Dirty input dependencies/importers
and existing output drafts are rejected, while unrelated drafts are preserved.
[Native verification](PREPARATION_SAFETY_20260928.md) covers 25 checks; successful
full production composition is still unverified because those inputs are absent.

The next content work is therefore the missing/reviewed roster and portraits,
Ridge provenance reconciliation and reference-matched route/actor acceptance,
followed by scoped content composition and actual bundle/player validation.
No placeholders, mask changes or acceptance shortcuts were introduced.

The startup-smoke draft is paused under
`tools/p08/desktop/startup-smoke-staging`; it has not been installed, compiled or
run and is not a substitute for these prerequisites. The separate 600-second
foreground acceptance remains deferred and unchanged. Protected Club source
still hashes to `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`.
