# Garage v2 implementation handoff — 2026-09-27

Status: source/layout candidate. **Not visually accepted; 100% concept fidelity is not established.**

## Locked visual specification

- `ArtSource/Concepts/P08/Golden/UI/garage-v2.png`
- SHA256 `65b237da2f4a13b554de13d5a70ec2c3aed995e9cba5c95af6601ca7d0201ef5`
- Inspected together with `garage-v2-review.md` before implementation.
- The fixture shown in the concept owns Spark 450 and Apex, selects Apex, and has 100% condition.
- The Spark thumbnail must be rendered from the approved P06 original Spark design; the large Apex and its thumbnail must come from the approved Golden Apex model. Crops of either concept are not runtime assets.

## Source implementation

`CareerView.cs` and `Career.uss` now give garage its own inventory rail, large selected-bike title, authoritative condition bar, short explanation and lower-right equip/repair rail. The header spans the entire viewport with the wordmark, six tabs and XONG. Idle garage hides the unrelated profile summary/server footer; pending requests, errors and meaningful operation notices remain visible.

Shop retains its actual design-stat comparisons, prices, trade and purchase flow. Characters, campaign, ledger and account keep their own layouts and behavior. The prototype's two-bike fixture is never substituted for a real profile.

Garage inspection changes only the preview request. Equip emits an intent and waits for the session's server response. Art availability, room/guest restrictions, condition and repair credits still gate the actual buttons. Header/body feedback and modal keyboard ownership retain the content-overlay priority guards. The `career-is-open` surface class hides only underlying main/header/footer/HUD/results/room visuals; it does not hide the content-loading overlay.

`CareerView.SetBikeThumbnails(IReadOnlyList<Sprite>)` accepts catalog-indexed, genuinely rendered images. A serialized array also supports authoring. Empty thumbnail slots carry `thumbnail-pending`; no surrogate bike or baked UI image is substituted. Production actor-pack binding is still pending.

## Editor-only fixture

`RacingBois.Authoring.Editor.GaragePrototypeFixture.Open(document, renderedThumbnails, previewRequested)` creates a disposable `CareerView` against the live UIDocument. It uses a real `CareerSession` with in-memory credentials and a transport that accepts only `view`; all mutating requests are rejected. The endpoint is the reserved `.invalid` host and no network client exists in the fixture. It does not change production masks, player saves or accounts.

Call from idle Play mode with no open career view, room, race or content-loading overlay. Supply genuine thumbnail sprites and an `Action<int>` for the real 3D preview. `GaragePrototypeFixture.Close()` disposes the fixture and restores normal focus/visibility; exiting Play mode also cleans it up. This fixture is **only a visual/presentation aid**, not live backend or account acceptance.

## Verification performed

- `python tools/p08/ui/preflight.py`: Standalone Windows, Editor and retained Web source branches compile; 93 unique UXML names and 95 typed named bindings pass. Receipt: `desktop-ui-preflight.json`.
- `dotnet build tools/p08/ui/GarageFixtureCompile.csproj --nologo -v:minimal`: actual Editor-only fixture source compiles against installed Unity 6000.5.7f1 assemblies, zero errors/warnings.
- Scoped `git diff --check`: passed.
- Protected `ArtSource/Weapons/RB_Club.blend` remains at the required SHA256.
- No Unity/Blender calls were made by this implementation worker; no runtime/render result is implied by compilation.

## Remaining acceptance gates

1. Import the USS and scripts in real Unity and inspect Console warnings/errors.
2. Inspect the actual rendered layout at the prototype aspect ratio and compare header, fonts, row geometry, selected-state border, condition fill, spacings and bottom actions directly to the locked reference. The current Noto-based wordmark and typography remain candidates until that comparison passes.
3. Supply and visually accept the real Apex, Spark, workshop scene, camera, lighting and two rendered thumbnail sprites. The scene/model/image gap alone prevents 100% fidelity acceptance.
4. Verify mouse and keyboard inspection, tab navigation, close/focus restoration and the higher-priority content overlay. Verify long inventory scrolling and other tabs at supported desktop sizes.
5. Verify live server responses for equip/repair/shop/account separately; the immutable visual fixture proves none of those external workflows.

Do not mark these pending gates passed from source existence, compilation, fixture data or numerical image-similarity scores.
