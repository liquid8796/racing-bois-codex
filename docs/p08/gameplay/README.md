# P08 gameplay/content implementation

Status: shared core, server and client Application implementation validated locally. Production availability stays gated until matching content has passed the Unity audit.

## Runtime contract

- `TrackDefinition.ForCourse(courseIndex, levelIndex)` is the single immutable course source for authority, local simulation, prediction and `RaceWorldReadModel.Track`.
- `RaceWorldReadModel.CourseIndex` accompanies `Level`; the client rejects a multiplayer snapshot whose course or level differs from its reliable lobby configuration.
- `RaceRiderReadModel.BikeCatalogIndex` and `CharacterCatalogIndex` survive authority snapshots, exact own checkpoints, prediction neighbors and remote interpolation. Numeric multiplayer rider rows are 26 values; P07 rows had 24.
- `RaceSession.StartLocal(seed, botCount, level, courseIndex, bikeCatalogIndex, characterCatalogIndex)` retains its choice on restart. Optional arguments preserve existing callers.
- The 15 stable P07 commerce SKU IDs and original price/trade/repair schedule remain. Their P08 integer handling profiles change speed cap, acceleration, braking, steering response, cornering and offroad response. Spark's player coefficients match the previous player defaults.
- Character cosmetics are Ash, Juno, Mako, Rook, Sol, Vale, Echo and Kai (`rb-ash` through `rb-kai`). They do not alter health, strength, collision or rewards.
- Production art IDs: `RB_P08_Bike_00`â€“`14` and `RB_P08_Rider_00`â€“`07`. A reused Spark source is an explicit alias, not an extra unique mesh.
- `ProductionContent` uses compile-time masks. Do not promote these masks merely because catalog rows or route data exist. The parent task owns promotion after prefab/scene content evidence.

## Compatibility and migration

The multiplayer protocol is 4; legacy race protocol is 3; simulation rules are 3. Both handshake directions bind `GameplayRules.ContentHash`, a cached canonical FNV-1a digest of all 25 course definitions, handling/commerce/art identities and production availability masks. It is compatibility identity, not a cryptographic signature; changing a mask changes the digest automatically. A P07 peer cannot silently join the new simulation. Invalid bike/character indices are rejected before committing client authoritative state.

The realm document remains version 2 and SQLite schema remains version 1. P08 adds `CareerProgress.SelectedCharacterId` with a default of `rb-ash`; a missing P07 JSON field loads deterministically without rewriting credits, inventory, receipt fingerprints, applied match ranges or grants. Explicit malformed character IDs fail validation rather than resetting data.

A `CareerIntent("character", characterId: id)` selects an existing cosmetic. The server applies the same profile-busy and transaction-id fencing used by commerce. Character commands increment profile revision but never modify wallet entries. Existing commerce transaction fingerprints are preserved byte-for-byte; only new character commands add their cosmetic ID to the fingerprint.

Signed local exports are version 2. Original signed P07 version 1 exports still import with the default cosmetic, subject to the existing realm/profile/revision/generation/signature/ledger checks. A local import cannot replay online grants or rewind settled money. No private user database is used by the tests.

## Verification

`src/Tests/RacingBois.P08Content.Tests` writes `content-tests.json` including SHA-256 for the shared runtime, client Application and server sources. It covers 25 route geometries, 15 measured acceleration/braking responses, 375 route/level/bike prediction combinations, malformed IDs, real SQLite P07-compatible JSON migration, replay fences and 25 authoritative qualifications.

This suite does not prove visual quality, live sockets, Unity Web parity, asset completeness, global networking or physical-device performance. The full P05/P07 regression suites are retained; phase-specific assumptions about unavailable routes and shared P06 art must be updated to the new production gates, not deleted.

## Intentional golden replay change

P08 keeps Canyon level 0 geometry and Spark player coefficients, but level 2 has a distinct route variant and NPCs use their own catalog tuning. The seeded replay changes intentionally:

| Replay | P06/P07 preserved baseline | P08 |
|---|---|---|
| Startup 3,000 ticks | `ED162155D421B3CF` | `FD320D8BD0D9435E` |
| Full 20,000 ticks | `3F421751C31690CB` | `BA1786522D59B2D7` |

The first pre-update golden failure is retained separately as `golden-change-before-update.json`. The current `gameplay-validation.json` is the post-review PASS receipt. Two independently seeded full runs agree on every tick. Browser/IL2CPP acceptance must also report the new startup golden; native success alone does not prove cross-runtime parity.

The controlled route-completion fixture finishes every one of the 25 variants using the starter bike with live traffic/pedestrians, zero competitor riders and police pressure disabled. This isolates route drivability and is not a human difficulty or campaign-balance playtest. The complete SQLite 25-qualification group activates only when all five production route gates are open; `pendingProductionGate` explicitly reports the interim limitation.

Rerun after production promotion:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/p08/verify-gameplay.ps1 -ContentOnly -RequireProductionContent
```

Omit `-ContentOnly` for all native regression suites. Reports use P08 paths, preserving earlier phase receipts. Test fixtures write only isolated `_local` directories and do not open an existing user realm or modify running servers.
