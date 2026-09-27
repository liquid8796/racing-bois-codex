# P08 UI audit and concept brief

Date: 2026-09-26. Scope: source inspection only. No layout, runtime assets, Unity state or browser state were modified by this audit. Rendered behavior and performance remain unverified here.

The user requires **new 2D UI concepts before implementing the revised UI**, original production art, appropriate design patterns, readable/clean/maintainable source, room for future features, and visual quality without generic AI styling. The implementation owner generates and inspects the concepts before layout work.

## Existing flows and bindings to preserve

| Screen | Existing interaction / authority | Revised presentation |
|---|---|---|
| Main / practice | Local start; offline practice course, level, bike and character selectors; saved-profile or new-guest connection; settings / career / Cinema | A motorcycle and actual route dominate the backdrop. Flat editorial action rail; a visual route and bike selector with clear offline-practice label. Server endpoint belongs to the expanded connection flow. |
| Garage / shop | Ownership, selected bike, condition, repair, buy and trade use authoritative career read models; confirmation and idempotent retry | Large selected-bike showroom, compact flat vehicle list, comparison values with units, one contextual primary action. Keep selected/owned/locked/insufficient-funds/in-room states explicit. |
| Roster | Eight character definitions, normal/happy/focused portrait indexing, character selection intent; no client mutation | Portrait strip or flat roster grid with one strong selected identity. Use loaded portraits; never substitute an unrelated generated face in the production roster. |
| Campaign | Five route families × five levels, qualification mask and current-level eligibility; practice is separate | Route imagery and readable progress rail. Availability, current eligibility and completed state must remain distinct. |
| Lobby browser / private room | Room creation, course and current profile level; six-character join, copy invite, ready/start/content/level gates, reconnect, official results | Route banner, prominent six-character code, flat members with host/local/ready/held-seat states, fixed action footer. An accurate local RTT can be shown; there is no per-member ping in the current member read model. |
| Race / results | Speed, rank, distance, health, bike condition, weapon, recovery and confirmed events; local results vs persisted server results | Road remains dominant. Rank/progress upper left, vitals lower left, speed lower right. Results sheet clearly says practice or server-confirmed progression. |
| Cinematic gallery / playback | 59 catalog entries, category filter, selection, play, captions, elapsed progress, skip/Escape; director owns presentation only | One dominant scene still / actual 3D scene, flat categorized sequence list, restrained metadata/play; safe-zone caption strip and always-available skip. |
| Account / transactions | Password/recovery, profile registration/login/revoke, one-time recovery output, offline-only save import/export, ledger | Deliberate focused forms, grouped account actions and inline error/pending/success. Avoid putting account recovery in a decorative hero flow. |
| Loading / error / settings | Real content progress/retry, quality, reduced motion, audio and HUD scale | Shared overlay treatment, stable loading geometry, labeled retry, visible keyboard focus; reduced motion preserves meaning. |

The five concept images should be separate 1920×1080 references: main/practice, garage/roster, private lobby, race HUD/results, cinematic gallery. Supporting account/loading/settings states follow the same tokens and component system. Concepts are design references; generated text is redrawn as actual localized UI, and images are not pasted wholesale as interactive screens.

## Direction and component rules

Original motorsport photography/3D rendering, graphite surfaces, warm amber actions, off-white text, restrained cool ambient light, flat composition, large readable type and precise numeric rails. Imagery uses Racing Bois designs. Avoid neon-purple SaaS gradients, pill-heavy navigation, nested cards, generic dashboard bento, arbitrary badge collections and tiny labels. A car/road photograph alone does not establish game-specific UI.

Reuse the packaged Vietnamese-capable font unless a licensed replacement is verified. Body copy should start near 16–18 px at reference resolution; numeric speed/rank can be much larger. Menus target 44 px controls and text contrast ≥4.5:1 measured against actual dark and bright rendered backgrounds. Never communicate readiness, failure or ownership by color alone. Accent amber means an action or selected state; green/red retain semantic meaning.

The skill design-system query returned a marketing "Hero + Features + CTA" and pink enterprise palette; these do not fit the game and were rejected. The narrower `gaming immersive` style query supports real 3D showcase, while its Three.js/parallax implementation advice is irrelevant to Unity. The `keyboard focus modal` query supports visible, unobscured focus. The direction above follows the existing project brief and these applicable UX outcomes, not an imported website template.

## Concrete source findings

| Priority | Finding and source | Required change / reproduction target |
|---|---|---|
| High | `RaceScreen.Content.cs:65–77` sets `ContentBusy = busy`, but displays the content modal for `busy || canRetry`. Failed content with `busy=false, canRetry=true` has a visible modal while the gameplay-input property in `RaceScreen.cs:29` no longer blocks it. No focus transfer/trap is installed for the retry overlay. | Give visible loading/error overlay one explicit ownership state, transfer focus to retry when available and restore focus on close. Deliberately fail a route bundle request; use Tab/Enter/Escape and gameplay keys. Verify no hidden action starts behind the error screen, networking stays alive, and retry retains intent. This is a source risk; not a recorded browser reproduction. |
| Medium | `CareerView.cs:127` clears and recreates the entire body after a completed request. `Account()` creates a new username field without retaining its previous text; `OnDestroy()` only removes the session subscription and clears secrets. | Keep nonsecret account field values, selected item, scroll offset and focus across refresh/errors. Secrets still clear immediately. Reproduce login rejection and a garage refresh while scrolled to a lower row. Do not display success until the server confirms. |
| Medium | `CareerView.cs:35–65` appends a generated root and registers an anonymous callback on the longer-lived `surface`; teardown at line429 does not remove that root, unregister that surface callback or restore disabled siblings. RaceScreen / lobby `Initialize` are likewise not guarded or explicitly unbound. Current bootstrap creates them once per scene, so repeated normal open/close is not a proven leak. | During the redesign, make binding lifetime explicit: one initialization, stored handlers or a binding owner, unsubscribe and remove owned elements on disposal, restore focus/enabled states. Test destroying/recreating just the view while keeping the UIDocument. Do not claim a live leak from this source inspection alone. |
| Medium | `CinematicGalleryView.cs:25,44–83` hardcodes palette, layout and typography inline instead of using shared USS. The other screens already have partially shared tokens. | Move gallery visual styles into the shared UI stylesheet/tokens after concept inspection. Keep the gallery/controller semantic contract and use the same focus/loading/disabled controls. |
| Medium | `Race.uss:60,69` uses a percentage-narrow results sheet and fixed 590 px settings card; `Career.uss:22–26` has nonwrapping fixed action rails; campaign is five min-width route buttons plus level label in a row. `.compact` shrinks some type but does not provide a new layout. | Verify 1280×720, 1366×768, 1920×1080, 2560×1440, ultrawide, 125% browser scale and resize. Allow forms/rows to reflow or scroll without losing the action footer. Source constraints demonstrate risk, not observed clipping. |
| Low | `CinematicGalleryView.cs:168–172` formats two duration strings and updates `progressText` every frame even though displayed seconds change only once per second. | Cache integer seconds / total-duration text; update the progress bar independently. Profile browser allocation before calling this a meaningful performance win. |
| Coverage | Static Vietnamese strings span UXML and views; cinematic authored title/caption text is English. There is no centralized locale binding in these inspected views. | A complete localization state matrix needs keyed copy, catalog title/caption keys, numeric formatting and layout checks. Do not call five-language coverage complete from font glyph support. |

## Architecture preserved and targeted improvements

The project already separates application sessions/ports from Unity presentation. `CareerIntent` carries an intent without client price/balance; `CareerProfileReadModel` and ledger projections are immutable; `CareerSession` owns pending/retry/generation and storage ports. Lobby views use pooled rows and current-state eligibility checks. These are useful existing patterns to retain.

For the revised UI, use a small per-screen presenter or explicit render-state adapter for career selection and content overlays; views render stable read models and send intents. Keep simulation, account and economy authority outside view classes. Use explicit binding ownership and composition, rather than a new global event bus or generic framework. Extract shared tokens and common controls where at least two screens use them. Typed operation IDs could reduce the growing string-switch drift in future work, but replacing the protocol is unnecessary for this visual task.

`ContentRegistry` is a static registry of loaded presentation assets, not simulation/economy state. Its asset lifetime is controlled by the content loader/bootstrap. New UI must not store profile/currency there; a scoped asset provider would be justified if multiple simultaneous stages or independent preview lifetimes are introduced.

## Acceptance checklist after concepts and implementation

- [ ] Concepts are saved with prompts/provider provenance, inspected and mapped to specific implemented screens; runtime art remains original.
- [ ] Main, practice, garage/shop, eight-identity roster, campaign, room browser/private room, account/ledger, HUD/results, loading/error, settings and gallery/playback preserve all working flows.
- [ ] Normal/hover/focus/pressed/disabled/pending/success/error/offline states share tokens and readable labels; no decorative-only data promises.
- [ ] Keyboard Tab/Shift-Tab/arrows/Enter/Escape works with fields, dropdown popups, confirmation, content failure/retry and cinematic skip; focus returns to the source control.
- [ ] Mouse and keyboard remain usable at all listed resolutions; long Vietnamese player/room names and text expansion do not obscure primary actions.
- [ ] Reduced motion disables camera/transition ornament while preserving directional combat and transaction feedback; audio unlock/mute/re-enable stays verified in browser.
- [ ] Rapid open/close/back, preview-return, route replacement, room countdown and online-start interruption leave one valid screen owner and release subscriptions/assets.
- [ ] Actual browser images/video compare against each concept, and rendering/memory/frame costs are measured on a source/build-bound run. Editor compile and binding-name tests do not prove visual quality or usability.
- [ ] Local/practice rewards, guest-session rewards and persisted career rewards are never presented as interchangeable.

## P08 content ledger status at inspection

The current checked-in `docs/p08/content/ContentParityLedger.md` reports **192 partial / 299 pending / 0 accepted rows** and `Full required mapping accepted: FALSE`. These are semantic mapping rows, not independent asset totals. The baseline is five course families/25 metadata variants, 15 SKUs, eight identities/24 portrait states, 72 SFX, 14 unique PCM compositions and 59 unique cinematic references, plus unresolved reference roles. Waveform/native compile/catalog signatures and new UI concepts do not close creative quality, actual runtime playback or content parity. Regenerate the ledger only when source mapping and production QA support a state change.
