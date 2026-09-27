# Career milestone cinematic triggers — staged

The current bootstrap automatically plays ordinary Win/Lose/Wreck/Busted scenes.
It never requests the authored Level or FinalWin scenes. This candidate adds a
cosmetic follow-up to a naturally completed Win only when existing authority
responses prove that the same match advanced the same career. Regular outcomes
remain available when any proof is missing. This changes no rewards, saves,
campaign rules, protocol, server or production content mask.

`CareerMilestoneTracker` takes the real `CareerSession` read models. During a
current Countdown/Racing match it captures a successful, settled pre-match
profile, bound to endpoint, welcome realm/profile, session ID, room, match,
epoch, level and course. It cannot establish a baseline after the match result
or its ledger entry already exists. The new `MultiplayerSession.RealmId` and
`ProfileId` getters expose the validated welcome identity already held privately;
`PlayerId` remains a session ID and is not confused with the career profile ID.

A milestone requires all of the following:

- Results phase and a persisted result whose result ID and match ID equal the
  tracked canonical `<realm>/<positive-number>` match.
- Exactly one local session result, Finished with rank 1–3.
- A later successful career **view** response for the same realm/profile, exactly
  one revision newer, containing exactly one `match:<number>` / `race_result`
  ledger row with the raced bike and matching reward/balance/profile credits.
- Exact equality of all three resulting progress fields with the existing
  `CampaignRules.ApplyQualification` rule. Rank or money alone is not proof.
- A naturally completed ordinary Win, no skip/cancellation, and an unchanged
  successful career snapshot when the cue is finally consumed. New pending
  requests, failures or new unobserved Profile/Ledger objects invalidate a cached
  cue before playback.

The server returns only its latest 40 ledger entries. Missing evidence stays
missing; the client does not guess older transactions. A transient refresh may
recover through the existing CareerSession retry path. The tracker never makes
network requests or supplies a profile target to an authority operation.

Level advances 0→1, 1→2, 2→3 and 3→4 select the authored stable IDs
`rb-level-past-the-first-ridge`, `rb-level-city-rhythm`,
`rb-level-above-the-weather` and `rb-level-a-line-beside-the-sea`. Only an exact
false→true campaign completion selects `rb-finalwin-the-road-stays-open`.
There are five campaign levels; six authored Level vignettes are not six levels.
The other two remain accessible through the gallery. This explicit new-game
selection does not prove the reference game's original cinematic event mapping.

Bootstrap checks existing content readiness and UI state before taking the cue.
Skipping the ordinary Win, opening career/gallery/showcase, unloading content,
returning to gameplay, changing identity/realm/room or leaving the match cancels
the follow-up. Leave/rematch/disconnect/local/reconnect intents cancel immediately,
before any asynchronous room acknowledgement or late profile response. It is
consumed once even if starting the optional scene fails.
Local practice remains unchanged; this scope covers account career in both OCI
online and the separate authoritative offline-LAN realm.

The focused tests use the actual CareerSession request/callback, refresh, retry,
logout/login and endpoint-generation paths with explicitly synthetic authority
responses. Positive progress comes from the real shared CampaignRules function;
negative tests cover missing/duplicate/wrong ledger entries, unrelated operations,
revision gaps, stale results, identity switches, cancellation and consumption-time
freshness. They do not prove an actual earned full campaign or open any masks.

```powershell
dotnet run --project tools/p08/media/milestone-staging/Tests.csproj
dotnet build tools/p08/media/milestone-staging/BootstrapPreflight.csproj -p:DefineConstants=UNITY_STANDALONE_WIN
```

The preflight compiles complete candidate Application and Bootstrap assemblies
with their correct assembly names against the installed native dependencies. No
duplicate-type warning suppression is used. Native import/assembly/source proof,
actual full-content campaign playback and UX review remain root-owned gates.
All production candidates are staged outside Assets until coordinated review and
installation; original line endings and existing script metadata are preserved.

Final reviewed state: 15 real-CareerSession correlation test groups pass; full
candidate Application/Bootstrap preflights pass for Windows, Editor and Web with
zero warnings/errors. Root review added consumption-time proof freshness; p09
review added immediate leave/rematch intent cancellation. `validation.json` binds
the tested sources. `handoff.json` pins the three source candidates and unchanged
or new metadata; `install.py` validates all six rows without writing by default,
and `--install` performs only the coordinated scoped installation. Native and
full campaign playback acceptance remain false.
