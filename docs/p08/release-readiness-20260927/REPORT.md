# P08–P10: concrete build handoff and remaining gates

This targeted review supplements the [semantic content audit](../parity-audit-20260927/REPORT.md).
It does not repeat its asset inventory or assign a completion percentage.
The [read-only snapshot](snapshot.json) binds the specific source/evidence files
examined. No Client, shared gameplay, server, running probe, live Editor source,
Unity scene, Blender scene or original asset was modified by this review.

**Subsequent root integration:** root installed the three pinned schema-2 files
and captured actual Unity dependencies without a full player build or promotion.
The [native check](native-dependency-check.json) passes for207 dependencies,
including81 virtual package files, and357 source files. Root's permanent suite
has50 passing tests; the staged suite's51st is the preserved old-verifier
reproduction. The earlier staging-only paragraphs below describe this review's
handoff boundary, not the later live integration. No art acceptance follows from
this successful dependency check.

## Ready-to-review repair

**A real desktop distribution verifier mismatch is fixed in staging.**
`P08DesktopBuilder.SourceSnapshot` includes scene/URP dependencies, while the
current Python `audit_sources` accepts only code and fixed settings. It rejects
a legitimate existing `.asset` before checking its hash. This would block a real
desktop delivery independently of the outstanding art work.

The [candidate](../../../tools/p10/release-contract-staging/README.md) makes Unity
record its exact logical/physical dependency closure, resolves virtual package
paths to narrowly bound PackageCache directories, binds package manifests/lock
and explicit engine resources, and checks the full expected source union.
**51 tests and the managed Unity API compilation pass** in the
[source-bound verification](staged-verification.json). Actual Unity capture/build
remains root's next validation step; the fix is not installed by this task.

## Implementation gaps to close before full desktop delivery

| Priority | Concrete current gap | Required next change and proof |
|---|---|---|
|1|The pack builder still selects fixed legacy `RB_P08_Bike_*`, rider and P06 route/traffic/prop paths. It has no mapping from accepted Golden revision to catalog slot.|After visual approval, bind each semantic slot to its exact accepted prefab/source/concept/QA revision. Keep rejected candidates and masks unchanged. A copied alias alone is not accepted art.|
|1|`P08ActorContent` has one Pedestrian and Club field; no chain/animal/specialized pedestrian catalog. Route content has six generic props per family.|Resolve source semantic roles first, then extend the typed content/view contracts for the actually required original designs. Shared rigs/chassis remain explicit shared dependencies, not multiplied asset counts.|
|1|`P08ContentPackBuilder.ReadAudio` requires files and a stored signal flag, but does not compare SFX Ogg hashes; the music build does compare its hashes.|Verify all 97 current Ogg fingerprints plus audio manifest/audit bindings before importing/building. Snapshot finds zero Ogg mismatches now; this is an enforcement gap, not a claim that current files are corrupt. Listening/mix flags remain unaccepted.|
|1|Pack validation verifies object counts/references, not the parity ledger, finalized concept review or an accepted production mapping.|Make release orchestration require the complete hash-bound ledger and explicit visual/runtime reviews. Keep authoring preview builds distinguishable from release candidates. Never open masks solely because all arrays are populated.|
|2|The pack build receipt binds output entries/dependency names, but not a before/after snapshot of authored bundle inputs and accepted QA revisions.|Capture the exact AssetDatabase input dependency closure, importer settings and acceptance records per pack; compare before/after build and preserve receipts by attempt. Desktop code/settings binding cannot prove that a later accepted prefab was the one used in an older bundle.|
|2|One actor bundle includes all bikes/riders/portraits/SFX; every resource is limited to64 MiB and the loader downloads bytes then calls `LoadFromMemoryAsync`.|Measure actual compressed and resident sizes once accepted content exists. If needed, split catalog/shared assets or implement a desktop-specific file-backed loading strategy with matching manifest/CRC/hash contracts. No measured over-budget result exists yet; do not blindly raise the limit.|
|2|The P05 host publisher requires a WebRoot and audits browser content; foundation defaults resolve a Web build; the P07 release packager requires a Git commit and Web payload.|Create a desktop LAN host recipe with a fresh self-contained win-x64 host, private offline realm outside content, explicit protocol/content identity, native-client instructions and immutable file/archive hashes. Existing Web packages are historical, not a current desktop LAN deliverable.|
|2|Exact reproducibility is broader than current source snapshots: importer `.meta`, assembly definitions, pack authoring inputs and actual Editor/package identity are not all bound by the present desktop recipe.|Record these before claiming reproducible full-content releases. The staged dependency fix closes the demonstrated allowlist/virtual-package mismatch; it does not claim to solve every reproducibility input.|

Primary source callsites: [pack builder](../../../Assets/RacingBois/Editor/P08ContentPackBuilder.cs:61),
[actor contract](../../../Assets/RacingBois/Client/Presentation/P08ActorContent.cs:7),
[route contract](../../../Assets/RacingBois/Client/Presentation/P08RouteContent.cs:6),
[64 MiB limit](../../../Assets/RacingBois/Client/Application/ContentManifestRules.cs:14),
[native loader](../../../Assets/RacingBois/Client/Adapters/P08ContentLoader.cs:147),
[desktop snapshot](../../../Assets/RacingBois/Editor/P08DesktopBuilder.cs:279),
[LAN publisher](../../../tools/p05/publish-lan.ps1:1),
[legacy packager](../../../tools/p07/package-release.py:87).

## What still needs art, rather than another build script

The current builder is missing9 required bike-prefab paths and all24 portrait
paths. These are **fixed-path inputs**, not the number of remaining independent
models. There are491 heterogeneous ledger rows,192 partial and299 pending,
zero accepted;9 stored file bindings are stale. None of the actual P08 content
roots, bundles or full desktop build exists in the checked paths. Current
availability masks are1/1/1; a full catalog would require31/32767/255 **after**
approval, not as a shortcut to making tests run.

Use the semantic audit's unresolved roles: five complete route families/level
variations; finalized vehicle and rider identities/portraits; chain, missing
traffic silhouettes/liveries, specialized pedestrians/props and cow; complete
action/equipment coverage; supporting UI states/localization; and reviewed
audio/cinematic event coverage. Finish matched-view Golden samples first and
avoid multiplying a visibly mismatching template. Source reference semantics
and P01 behavioral gaps remain separate from this content packaging work.

Garage V7 is a useful resolved technical defect: actual native Unity reports
180 meshes,165,812 triangles and **zero degenerate primary UV triangles** in
[its CSV](../golden/garage/v7/native-primary-uv.csv), unlikeV5/V6. Root reports
bake06 complete. This does not accept its workshop geometry/material/framing.
Apex, Ash, Canyon and menu/garage UI also remain visually unaccepted.

## P09/P10 evidence that must not be conflated

- The latest recorded [OCI f post-soak verification](../../p09/releases/f/deployment-after-soak.json)
  is dated2026-09-27 01:01UTC and verifies1,986 deployed files. This review does
  not SSH/revalidate current service state.
- The [30-minute protocol6 WAN run](../../p10/network/20260927T003126Z/run.json)
  passes with unchanged source; its probe records21 cycles,14 planned reconnects
  and2 storms. This is one workstation's synthetic peers, not geographically
  separate players or visual smoothness acceptance.
- The [actual Unity Mono WSS specimen](../../p10/native-wss/turnover-20260927-0727.json)
  passes two short races and identity/slot-preserving resume. It is transport
  evidence, not the finished full-content game's campaign/graphics/input QA.
- The eight-hour run20260927T003037Z still reportsRUNNING in this snapshot.
  All163 recorded source paths match, with no change during this read-only
  review. Elapsed time and partial counters do not imply its finalPASS.
- Physical offline LAN still needs a second PC with WAN disconnected. Windows10,
  lower-tier hardware, a real gamepad, novice usability, sustained actual-player
  frame/memory/audio/route-swap testing and SEA/EU/NA game-client behavior remain
  external or actual-player gates. The user's one current PC does not close them.

No new machine/domain/payment request is needed to do the code/art work above.
An owned branded domain and external alert destination are later operational
decisions; temporary trusted TLS already has recorded evidence. The previously
blocked cleanup remains separate and is not retried here.

## Reproducible next build sequence

1. Review/integrate the staged desktop dependency receipt fix; obtain a real
   Unity dependency-capture/build receipt and run its verifier. Preserve the
   failing old receipt contract as historical proof.
2. Finish original art from locked concepts, semantic mappings and real QA;
   refresh `production-mappings.json`/ledger only with reviewed evidence. Run
   `python tools/p08/content/content_ledger.py --write`, then `--check` and
   `--check --require-complete`. Refreshing hashes is not accepting a row.
3. Bind accepted prefabs/media to pack slots, run `P08ContentPackBuilder.Setup()`
   and `Validate()` via direct Unity MCP, build Editor packs for loading/CRC/
   route-residency checks, then `BuildDesktop()`. Record exact inputs/outputs.
4. Root uses `P08DesktopBuilder.BuildTo("Build/Desktop-P08-candidate-N")` with a
   fresh directory and actual online or LAN config. Audit the actual player
   against its own build receipt/hash, then prepare/run P10 native recorder and
   independent raw verifier. Golden camera builds do not substitute for this.
5. Publish the matching desktop LAN host, verify self-contained cold offline
   start and separate realm, then run physical LAN/target-hardware/player QA.
   Complete the unchanged-source soak and required OCI regional/operations gates.
6. Create immutable player/host archives only from the verified file manifests,
   verify archived bytes and compatibility, and publish current player/operator
   instructions. Keep failed/superseded attempts labelled accurately.

This order preserves the source freeze and separates implementation work from
missing art acceptance and unavailable physical QA evidence. P08, P09 and P10
are not declared complete by this review.
