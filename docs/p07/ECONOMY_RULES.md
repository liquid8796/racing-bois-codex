# P07 — Catalog, economy and campaign rules

Date: 2026-09-22. Shared implementation: [Definitions](../../Packages/com.racingbois.foundation/Runtime/Definitions). This document records the reference evidence separately from Racing Bois decisions. It does not claim full original-game parity or completion of P08 content.

## What the reference establishes

| Rule | Evidence and confidence | Remaining limit |
|---|---|---|
| 15 bike SKUs and their integer prices | Static instructions/data at `0x468fc0`; exact SPEC ID/index/name mapping in [economy_tables.json](../reverse-engineering/logic/economy_tables.json) and [LOGIC_AUDIT.md](../reverse-engineering/logic/LOGIC_AUDIT.md) | A SKU does not establish a separate 3D mesh. Original names and assets are research references. |
| Trade credit is `floor(currentBikePrice / 2)` | Purchase handler `0x42161c..0x421694`; buying the currently selected bike is rejected at `0x421606` | Original shop owns one current bike; a multi-bike garage is a Racing Bois extension. |
| Repair is `floor(currentBikePrice / 10)` | Handler `0x4214f9..0x42150e` in mode 2 | The fixed price is not a recovered proportional-per-damage repair formula. |
| Busted fine is `400 * (levelIndex + 1)` | Handler `0x421528..0x421537`, zero-based level 0–4 | Original insufficient funds reset the profile. Racing Bois must state its own recovery/debt policy; it must not silently delete a modern account. |
| Prize base for ranks 1–14 is `[1000,750,500,400,300,250,200,160,130,100,70,50,30,20]`, multiplied by level 1–5 | Static table `0x46ab48` and reward arithmetic `0x421365..0x42137a` | The original caller's eligibility after every race outcome is not fully traced. A table does not prove all result paths award money. |
| Offline top-three qualification, five route bits, five levels | P01 native-byte fixtures follow outcome → UI → qualification-mask chain; 28 threshold, 60 course-bit and 35 progression cases in [LOGIC_P01.md](../p01/logic/LOGIC_P01.md) | Original network mode uses a different first-place threshold. Full natural campaign/menu execution remains open. |
| Qualification mask must equal `0x1f` before level advance | `0x41f6d0..0x41f70a` plus native-byte fixtures | Invalid extra bits are not a valid completed campaign. |
| Fifteen SPEC records contain differing engine/gear parameters | [bike-component-bench.json](../p01/logic/bike-component-bench.json), original byte execution for all 15 records | The isolated bench excludes complete dispatcher ordering, slopes, traction, nitro, collision and actual speed-unit calibration. It does not establish production-ready per-bike km/h or acceleration values. |

No extracted model, texture, audio, portrait or executable data is a runtime dependency of this P07 catalog. The regression test reads the existing research price table only to verify numerical provenance.

## Racing Bois decisions in this phase

- New SQLite profiles start with **1,000 credits** and a free **Spark 450** (`rb-spark-450`, index 0). This is a new onboarding choice, not a recovered universal starting profile. Existing migrated balances must retain their prior value; the starter grant must not run again on session refresh or migration retry.
- New original product names and stable string IDs are used. The reference price schedule is retained as an explicit initial balance choice. Prices are integer credits without fractional rounding or real-money value.
- All 15 commerce entries currently use **one P06 motorcycle model and the existing shared handling profile**. The 58,000 mm/s value is the shared simulation speed cap, not a measured terminal speed for a particular SKU. More expensive entries have no implemented performance advantage in P07. The UI must disclose shared art/handling; P08 adds and validates distinct designs and tuning.
- There are **five logical levels and five route slots**, but only **Canyon Run** has playable P06 content. The other four routes remain unavailable until P08. They must not point at Canyon Run while pretending to be new roads. It is therefore impossible to complete the full 25-slot campaign in the delivered P07 content set; the rules/storage path can be exercised independently with fixtures.
- Top-three qualification is the shared Racing Bois campaign rule. A valid finish receives the rank-table prize independently of whether it qualified. Ranks 15 and 16 receive zero because the reference table has only 14 prize entries. Busted, wrecked, abandoned, timed-out and other non-finish outcomes are not valid inputs to `RewardForRank`.
- New quotes and progression calculations are pure definitions. The server owns purchase eligibility, authoritative match results, balance/debt constraints, bike ownership/condition, selected bike, realm separation and transaction IDs. A client quote is for display; it cannot authorize a debit or grant.
- The pure progression function does not provide idempotency. Before applying it, the transaction owner must verify a unique result ID, the match's captured level/course, participant identity and valid terminal outcome. Replaying a prior level's course after a level rollover must not qualify that course again in the new level.
- Fine underflow, account recovery and replay/transaction policy belong to the persistence implementation and its tests. The shared layer calculates the exact fine but does not clamp balances, invent debt, reset a profile or choose which repair must be paid automatically.

## Catalog and prices

The index column preserves the reference table order, making numerical comparison explicit. It is not an art-count claim.

| Index | Stable ID | Racing Bois name | Price | Trade credit | Fixed repair |
|---:|---|---|---:|---:|---:|
| 0 | `rb-spark-450` | Spark 450 | 4,495 | 2,247 | 449 |
| 1 | `rb-kestrel` | Kestrel | 3,249 | 1,624 | 324 |
| 2 | `rb-rift-250` | Rift 250 | 3,497 | 1,748 | 349 |
| 3 | `rb-jackal` | Jackal | 5,489 | 2,744 | 548 |
| 4 | `rb-ember` | Ember | 2,999 | 1,499 | 299 |
| 5 | `rb-apex` | Apex | 29,998 | 14,999 | 2,999 |
| 6 | `rb-corvus` | Corvus | 18,999 | 9,499 | 1,899 |
| 7 | `rb-viper` | Viper | 40,000 | 20,000 | 4,000 |
| 8 | `rb-rift-750n` | Rift 750 N | 21,789 | 10,894 | 2,178 |
| 9 | `rb-specter` | Specter | 34,888 | 17,444 | 3,488 |
| 10 | `rb-nightjar` | Nightjar | 13,796 | 6,898 | 1,379 |
| 11 | `rb-cinder-10` | Cinder 10 | 16,875 | 8,437 | 1,687 |
| 12 | `rb-rift-750` | Rift 750 | 11,988 | 5,994 | 1,198 |
| 13 | `rb-odyssey` | Odyssey | 9,199 | 4,599 | 919 |
| 14 | `rb-havoc` | Havoc | 6,994 | 3,497 | 699 |

All entries resolve to art ID `RB_P06_Motorcycle`. `HasDistinctArt` is true only for index 0, the entry that owns that existing production art; it is false for the other 14. `HandlingProfileId` refers to the current shared `GameplayRules.ContentHash`. New art must follow the user's **2D concept → Blender MCP → Unity MCP → production checklist** requirement; this task creates no new 3D asset.

| Course index | Stable route ID | Display name | P07 availability |
|---:|---|---|---|
| 0 | `rb-canyon-run` | Canyon Run | Playable, existing 2.2 km slice |
| 1 | `rb-neon-district` | Neon District | Locked: P08 content |
| 2 | `rb-ridge-pass` | Ridge Pass | Locked: P08 content |
| 3 | `rb-coastal-line` | Coastal Line | Locked: P08 content |
| 4 | `rb-orchard-road` | Orchard Road | Locked: P08 content |

These route names are original planning IDs. They do not claim the original game's course geometry, distances or level variants have already been recreated.

## API and state invariants

The new files reside in `Packages/com.racingbois.foundation/Runtime/Definitions` and are compiled into the existing `RacingBois.Gameplay.Definitions` assembly for both Unity and .NET. They use no Unity, filesystem, network or database API. Collection views are immutable; definitions expose read-only properties. IDs compare ordinally and are case-sensitive. Unknown IDs never silently select the starter bike.

| API | Responsibility |
|---|---|
| `BikeCatalog.All`, `Get(id)`, `GetAt(index)`, `TryGet(id, out definition)` | Immutable 15-entry identity, pricing and content-readiness catalog |
| `EconomyRules.TradeInValue(price)`, `RepairCost(price)` | Nonnegative integer quotes; rejects negative prices |
| `EconomyRules.BustFine(levelIndex)`, `RewardForRank(rank, levelIndex)` | Strict level 0–4 and rank 1–16 validation; no silent clamping into a payable result |
| `CampaignCatalog.Routes`, `GetRoute(index)`, `TryGetRoute(id, out definition)`, `IsPlayableRoute(index)` | Complete logical route inventory plus explicit availability |
| `CampaignRules.ApplyQualification(level, mask, completed, course, rank)` | Pure finish-to-next-progress calculation; returns `CampaignProgress` |
| `CampaignRules.ValidateProgress(level, mask, completed)` | Reject invalid bits and unsettled completion combinations in persisted input |

A settled active progress state has level 0–4, mask 0–30 and `Completed=false`. When the fifth distinct course qualifies at levels 0–3, the result is the next level with mask 0. The final result is level 4, mask 31, `Completed=true`, which stays unchanged on subsequent valid finishes. Negative masks, extra bits, completed states with missing bits and intermediate levels carrying mask 31 are rejected. Migration must explicitly normalize any older valid representation before calling this stricter settled-state API.

Route availability is checked by the server's application boundary before a match starts. `ApplyQualification` deliberately supports every logical course for deterministic rule tests and future P08 content; it does not itself permit starting an unavailable race.

## Validation and remaining integration work

Run from the repository root:

```powershell
dotnet run --project src/Tests/RacingBois.EconomyRules.Tests/RacingBois.EconomyRules.Tests.csproj -c Release -- docs/p07/economy-rules-validation.json
```

[The source-bound receipt](economy-rules-validation.json) records 11 passing scenario groups: all 15 reference prices/trade/repair values, stable immutable catalog IDs, honest art/handling availability, integer boundaries, all 70 reference reward combinations, invalid inputs, all 25 logical qualification steps, repeated-course stability, top-three boundary, corrupt progress rejection and unavailable routes. These are native .NET pure-rule tests, not Unity/browser, database concurrency or full original-campaign runtime evidence.

Integration must additionally prove atomic purchase/trade/repair, duplicate/reordered results, concurrent purchases, restart/recovery, migration retries, ownership checks, realm separation and unavailable-route rejection. Those checks belong to the P07 persistence/application evidence; this document does not mark them passed solely from the pure-rule suite.
