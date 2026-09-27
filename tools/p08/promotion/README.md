# Golden production binding

This path can bind an **already visually accepted** Golden prefab into an existing
P08 semantic slot without passing it through the old single-material art builder.
No current candidate is accepted, and this change creates no production manifest,
acceptance record, asset replacement or availability-mask change.

`GoldenProductionBindings.Load()` returns the actual accepted prefab asset
reference. It does not copy a prefab, rename children, replace materials, change
LOD groups, substitute rigs/clips, or call `P08ArtBuilder.Setup`. The normal full
roster, portrait, audio and route validation still runs. This is a binding path,
not completion of P08, gameplay/contact acceptance or permission to ship.

## Existing contracts retained

The gate reads the existing schema-1 Golden descriptor and explicit native import
receipt. `GoldenSampleBuilder.ValidatePromotionSource` reuses `ReadDescriptor`,
`InputSnapshot`, the source fingerprint and the existing full native
`ValidateAsset` implementation. It verifies a **named immutable import receipt**;
`import-latest.json` is not implicitly selected. A new compiler/source revision
requires a fresh successful import before promotion.

The content ledger keeps its existing `qa_state`, source/provenance/QA and
semantic mapping contract. A successful promotion integrity check does not
automatically mark any ledger row accepted. The visual record below is additional
evidence, not a replacement for production QA or the content ledger.

## Explicit mapping and review

The optional production file is
`docs/p08/promotion/production-bindings.json`. Its absence preserves legacy
prefab selection, but an existing actor/route containing a Golden prefab is
rejected without its active binding. Removing a binding cannot leave an unchecked
Golden actor in a pack.

The schema-1 root has a `bindings` array. Each binding requires:

| Field | Meaning |
| --- | --- |
| `semanticName` | Exact existing catalog or route-prop slot, e.g. `RB_P08_Bike_05`. |
| `assetId`, `kind` | Exact Golden descriptor identity and `bike`, `rider` or `environment`. |
| `descriptor` | `{path, sha256}` for the exact descriptor. |
| `nativeImport` | `{path, sha256}` for its successful source-bound native import. |
| `prefab` | `{path, sha256}` for `Assets/RacingBois/Golden/Generated/Prefabs/<assetId>.prefab`. |
| `acceptance` | `{path, sha256}` for a separately authored, explicit visual review record. |

Bike/rider kinds only map to their 15/8 catalog slots. Environment bindings only
map to the exact existing route-prop and road-furniture allowlist. Police,
pedestrians, traffic and weapons need their own typed promotion contract before
this path supports them; an environment cannot occupy those actor slots.

The acceptance record requires schema 1; exact `assetId` **and** `semanticName`;
`status: "accepted"`; `visualAccepted: true`; a named `reviewer`; `reviewedUtc` in
round-trip UTC format; the same `descriptor`, `nativeImport`, `prefab` and locked
`concept` file references; a substantive hash-bound Markdown `review`; an explicit
empty `remainingDifferences` array; and corresponding `comparisons`. These values
must record a completed real review. No command creates or fills an accepted
record, and changing booleans does not establish visual fidelity.

Actors require `quarter`, `front`, `side`, `rear`, `gameplay`, and `detail`
comparisons. Static environments require `gameplay` and `detail`. Each comparison
binds a native `capture` receipt and names `view`, exact `conceptView`,
`framingReview` and `lightingReview`. Its `criteria` array must review each of
`silhouette`, `proportions`, `geometry`, `component-placement`, `materials`,
`color`, and `details` exactly once, with a concrete nonblank `observation` and
`result: "match"`. Omitted views/dimensions, known differences, duplicate image
pixels, stale files, a concept substituted for a render, or mismatched identities
are rejected. These are evidence-integrity checks; software cannot verify the
truth of a reviewer's visual judgment.

Preserve the exact approved concept bytes and every previous candidate. Resolve
contradictory reference views before authoring or accepting replacements. Never
use an image-similarity score or these contract tests as a claim of 100% fidelity.

## Native capture and pack use

Root exclusively owns Unity operation. After a fresh import/compiled-source
audit, instantiate the exact generated prefab in an idle Editor review scene,
then call `GoldenProductionCapture.Capture` with the descriptor, asset ID, pinned
import receipt, actual subject, camera, required view, corresponding concept-view
description and a new PNG path under `docs/p08/promotion/captures/`.

The method makes an actual URP camera render request, rejects uniform pixels,
and writes a PNG plus `.capture.json` binding the exact descriptor/import/prefab,
concept, pixels, dimensions, UTC time and native camera/subject metadata. It
refuses overwrite. The capture gate checks that an enabled subject renderer lies
in the camera frustum and culling mask; this is not proof that every part is
unoccluded, so the reviewer must inspect the actual image.

This first capture contract supports **the unchanged authored rest state**.
World translation/rotation for framing are allowed at unit scale. It rejects
descendant transform/visibility/layer changes, added/removed objects/components,
other prefab property overrides, material property blocks, changed mesh/material
references, rig root/bone/expression changes, and changed LOD membership. An
animated/posed capture needs a future explicit source-clip/time contract; do not
relax this gate or accept modified scene geometry as the production prefab.
Animation deformation/contact acceptance remains a separate requirement.

The capture rejects `forceRenderingOff` suppression. It renders a fresh temporary
instance of the validated prefab at the same world pose and explicitly forces
LOD0 on that owned instance, recording `lodPolicy: "fresh-instance-lod0"`. The
original is hidden only during the render, then its active state is restored and
the temporary instance is destroyed in `finally`. No unknown forced-LOD state on
the original instance is overwritten or guessed. These captures compare the
highest-detail authored geometry; native LOD transition review remains separate.

`GoldenProductionBindings.Load` also decodes the actual PNG through Unity and
validates typed camera/subject metadata. The standalone CLI performs file/header
and review-integrity checks only; it does not run native Unity decoding or prefab
validation.

P08 pack preparation resolves accepted mappings before legacy paths. Validation
checks exact assigned prefab references and repeats the original full-roster
requirements. Content build verifies the gate again after building, requires the
same manifest hash (including absent/present state), and records that manifest
identity in its build receipt. The manifest recursively binds acceptance,
capture, descriptor, import, source and prefab evidence.
Shared guardrail/chevron/utility-pole bundle roots come from the validated actual
route references, including accepted replacements. All five routes must share
those same objects, so their dependencies stay assigned to the shared actor pack.

## Verification

```powershell
dotnet run --project tools/p08/promotion/GateTests.csproj
dotnet build tools/p08/promotion/Preflight.csproj --nologo -v:minimal
dotnet run --project tools/p08/promotion/GateTests.csproj --no-restore
dotnet run --project tools/p08/promotion/GateTests.csproj -- --manifest docs/p08/promotion/production-bindings.json
```

The final command intentionally fails while no accepted production manifest
exists. Positive test controls live only in disposable temporary directories,
use synthetic identities/bytes, and are explicitly labelled as contract fixtures.
They are never copied into production evidence. Tests cover unaccepted and stale
records, missing/mismatching review dimensions, material/rig/LOD byte changes,
slot/kind substitutions, removed manifests and immutable binding behavior. Native
capture/import/prefab preservation and actual visual quality require Unity work
and are not established by the managed tests or compilation.

Verified on 2026-09-27: 40 managed contract controls pass; the Editor preflight
compiles against the installed Unity 6000.5.7f1 assemblies with zero warnings and
errors. Per-project `obj`/`bin` paths keep the net10.0 gate runner and
netstandard2.1 Editor preflight independent; running preflight between two
`--no-restore` gate runs succeeds. Root independently executed the actual Unity
orphan-binding negative control: `GoldenProductionBindings.Load().ValidateBound`
for `RB_P08_Bike_05` and the current Apex R4 prefab throws
`Golden prefab has no active accepted binding`. No positive real-asset acceptance,
native capture, shared-pack build or animation/visual gate is implied.
