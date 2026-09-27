# P08 career and lobby UI integration

The career view now has six tabs: Garage, Shop, Riders, Campaign, Transactions and Account. The existing account/recovery/checkpoint workflow remains in its original view code. New controls emit application intents; the server remains the owner of currency, garage, selected character and room state.

## Riders and bike previews

The Riders tab lists the eight `CharacterCatalog` identities. It uses actual loaded `ContentRegistry.Actors.Portraits` sprites when available. An eight-element array supplies normal portraits; a 24-element array uses `characterIndex * 3 + stateIndex`, where states 0/1/2 are normal/happy/focused. The latter enables a cosmetic expression-preview dropdown. Missing/loading portraits show an explicit text identity rather than a fabricated asset image.

Selecting a rider sends `new CareerIntent("character", characterId: character.Id)`. The named argument is deliberate: the constructor's second positional argument is a bike ID. There is no optimistic mutation of the profile. Buttons remain disabled for guest/no-profile, in-room, busy, unavailable and already-selected states; the click handler rechecks these conditions.

Garage and shop rows include `XEM 3D`, which closes the career modal and emits `ShowcaseRequested(bikeIndex)` for the bootstrap coordinator. The owner must reopen the career view after that requested showcase, unless live-race/content transitions take precedence. Direct gallery showcases retain their separate return-to-gallery behavior. `RefreshPresentation()` rerenders portraits after an asynchronous actor-pack load.

Bike labels come from `BikeDefinition.Handling`: the configured speed ceiling is converted from mm/s to km/h; engine and cornering permille values are shown as multipliers relative to Spark 450; braking deceleration is converted from mm/s² to m/s². They are authored game parameters, not road-test results or claims of recovered original-game measurements. Price/ownership and repair/trade rules still use the shared definitions and server profile.

## Campaign and lobby

Campaign text describes five routes across five levels. Route buttons use actual `IsPlayable` availability and current profile level. An unavailable route is visibly unavailable. The view does not unlock a level or promote a room when the profile changes.

The lobby course dropdown enumerates available `CampaignCatalog.Routes`; create-room intents use the selected course instead of a hardcoded course 0. Guest creation targets level 1. Persistent creation targets the current career level.

Ready and Start combine the existing content-ready gate with current room/profile level compatibility. Their click handlers recheck the same current session state. Start additionally requires the host and every member connected/ready.

| Session | Room | Result before other readiness checks |
|---|---|---|
| Saved profile at level 2 | Level 2 | Level-compatible |
| Saved profile promoted to level 2 | Existing level-1 room | Ready/Start disabled; leave and create a room at the current level |
| Guest | Level 1 | Level-compatible |
| Guest | Higher level | Ready/Start disabled; leave and use a level-1 room |

The stale-room hint persists in the room panel and takes priority over the ordinary ready/content-loading hint. No client method modifies `Room.LevelIndex`. The backend still validates eligibility independently.

The UXML edit adds the lobby course field and replaces stale Canyon-only static captions with general Racing Bois/practice labels. Existing practice selectors, content-loading overlay, retry control and Cinema button remain present.

## Verification

Both Editor and WebGL conditional C# preflights compile the actual updated views against the installed Unity references. `ui-binding-validation.json` parses the real UXML, checks 91 unique element names and 46 named view bindings, validates dropdown types, verifies existing P08 overlays remain, and checks the new career style selectors. The six career tabs share available width; row statistics wrap and the rider grid scrolls.

These checks do not prove rendered layout, portrait quality, focus behavior, clicked server transactions or room promotion behavior in the browser. Required live checks: 1280×720 and 1920×1080 career tabs/portraits, all three portrait states, character persistence after reload, shop-preview return, all five lobby course choices, promoted-profile old-room blocking, guest level restrictions, and content loading/retry. Unity refresh and visual testing are reserved for the integration owner while art exports run.
