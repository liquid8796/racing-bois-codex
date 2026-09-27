using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

int passed = 0;
void Check(bool ok, string why) { if (!ok) throw new Exception(why); }
void Test(string name, Action body) { body(); passed++; Console.WriteLine("PASS " + name); }
Test("real refresh binds level advance and consumes once after natural win", () =>
{
    var f = new Fixture(); f.Finish();
    Check(!f.Tracker.TryTake(out _), "Played before ordinary win completed");
    f.Tracker.OutcomeCompleted(f.Match, false);
    Check(f.Tracker.TryTake(out var id) && id == "rb-level-past-the-first-ridge", "Missing actual level transition");
    f.Observe(); Check(!f.Tracker.TryTake(out _), "Duplicate result replay");
});
Test("all four level advances and final completion use actual shared qualification rule", () =>
{
    string[] expected = { "rb-level-past-the-first-ridge", "rb-level-city-rhythm", "rb-level-above-the-weather", "rb-level-a-line-beside-the-sea", "rb-finalwin-the-road-stays-open" };
    for (int level = 0; level < 5; level++)
    {
        var f = new Fixture(level); f.Finish(); f.Tracker.OutcomeCompleted(f.Match, false);
        Check(f.Tracker.TryTake(out var id) && id == expected[level], "Wrong level/final scene");
        Check(CinematicCatalog.Get(id).Role == (level == 4 ? CinematicRole.FinalWin : CinematicRole.Level), "Missing authored scene");
    }
});
Test("transient refresh failure retains retry but never creates a cue until authority returns", () =>
{
    var f = new Fixture(); f.Result = f.CreateResult(); f.Session.Refresh(); string transaction = f.Wire.Last.transactionId;
    f.Wire.Complete(null, true); f.Observe(); f.Tracker.OutcomeCompleted(f.Match, false);
    Check(f.Session.CanRetry && !f.Tracker.TryTake(out _), "Failure created milestone");
    f.Session.Retry(); Check(f.Wire.Last.transactionId == transaction, "Retry lost request identity");
    f.Wire.Complete(f.After()); f.Observe(); Check(f.Tracker.TryTake(out _), "Correlated retry did not recover");
});
Test("skip cancels even when successful profile refresh arrives later", () =>
{
    var f = new Fixture(); f.Tracker.OutcomeCompleted(f.Match, true); f.Finish();
    Check(!f.Tracker.TryTake(out _), "Skipped outcome replayed as milestone");
});
Test("ordinary qualification without a new level keeps regular win", () =>
{
    var f = new Fixture(mask: 0); f.Finish(); f.Tracker.OutcomeCompleted(f.Match, false);
    Check(!f.Tracker.TryTake(out _), "Nonmilestone qualification promoted");
});
Test("missing before-state and already-applied historical ledger never infer an advance", () =>
{
    var f = new Fixture(); f.Tracker.Reset(); f.Finish(); f.Tracker.OutcomeCompleted(f.Match, false);
    Check(!f.Tracker.TryTake(out _), "Post-result profile became before-state");
    f.Tracker.Observe("realm-a", "profile-a", "session-a", f.Room(LobbyPhase.Racing), null);
    f.Observe(); Check(!f.Tracker.TryTake(out _), "Already applied ledger replay");
});
Test("missing exact ledger row fails closed and a later real refresh can supply it", () =>
{
    var f = new Fixture(); var after = f.After(); after.ledger = Array.Empty<CareerLedgerEntry>(); f.Finish(after);
    f.Tracker.OutcomeCompleted(f.Match, false); Check(!f.Tracker.TryTake(out _), "Missing ledger accepted");
    f.Session.Refresh(); f.Wire.Complete(f.After()); f.Observe(); Check(f.Tracker.TryTake(out _), "Fresh ledger recovery failed");
});
Test("wrong ledger reason, duplicated row, reward and balance are rejected", () =>
{
    foreach (Action<CareerResponse> change in new Action<CareerResponse>[] {
        r => r.ledger[0].reason = "legacy_result", r => r.ledger = new[] { r.ledger[0], r.ledger[0] },
        r => r.ledger[0].delta++, r => r.ledger[0].balance++, r => r.ledger[0].bikeId = "not-the-raced-bike" })
    { var f = new Fixture(); var after = f.After(); change(after); f.Finish(after); f.Tracker.OutcomeCompleted(f.Match, false); Check(!f.Tracker.TryTake(out _), "Uncorrelated ledger accepted"); }
});
Test("unpersisted and wrong result identity never borrow a proven cue", () =>
{
    var f = new Fixture(); f.Finish(); f.Tracker.OutcomeCompleted(f.Match, false);
    f.Result = f.CreateResult(persisted: false); f.Observe(); Check(!f.Tracker.TryTake(out _), "Unpersisted result accepted");
    f.Result = new MultiplayerResultReadModel("realm-a/8", f.Match, true, f.CreateResult().Entries.ToArray()); f.Observe();
    Check(!f.Tracker.TryTake(out _), "Wrong result identity accepted");
});
Test("mismatching shared-rule progress, revision gap and non-race operation are rejected", () =>
{
    foreach (Action<CareerResponse> change in new Action<CareerResponse>[] {
        r => r.profile.levelIndex = 2, r => r.profile.revision += 2, r => r.profile.qualificationMask = 1 })
    { var f = new Fixture(); var after = f.After(); change(after); f.Finish(after); f.Tracker.OutcomeCompleted(f.Match, false); Check(!f.Tracker.TryTake(out _), "Unproven transition"); }
    var g = new Fixture(); g.Result = g.CreateResult(); g.Session.Execute(new CareerIntent("import", saveJson: "synthetic-test-save")); g.Wire.Complete(g.After()); g.Observe();
    g.Tracker.OutcomeCompleted(g.Match, false); Check(!g.Tracker.TryTake(out _), "Import response created a race milestone");
});
Test("endpoint switch and stale response cannot cross realms", () =>
{
    var f = new Fixture(); f.Result = f.CreateResult(); f.Session.Refresh(); var old = f.Wire.Callback;
    f.Session.SetEndpoint("wss://other.invalid/multiplayer"); old(f.After(), false); f.Observe(); f.Tracker.OutcomeCompleted(f.Match, false);
    Check(f.Session.Profile == null && !f.Tracker.TryTake(out _), "Stale realm response accepted");
});
Test("logout and login identity replacement invalidate the captured profile", () =>
{
    var f = new Fixture(); f.Session.Execute(new CareerIntent("logout")); f.Wire.Complete(new CareerResponse { ok = true }); f.Observe();
    f.Session.Execute(new CareerIntent("login", username: "new-test-user", password: "synthetic-only-password"));
    var replacement = f.After(); replacement.profile.profileId = "profile-b"; replacement.profileToken = "synthetic-profile-b";
    f.Wire.Complete(replacement); f.Observe(); f.Tracker.OutcomeCompleted(f.Match, false); Check(!f.Tracker.TryTake(out _), "Other profile inherited milestone");
});
Test("new room, explicit cancellation and nonqualifying outcome prevent playback", () =>
{
    var f = new Fixture(); f.Finish(); f.Tracker.OutcomeCompleted(f.Match, false); f.Tracker.CancelCurrent(); Check(!f.Tracker.TryTake(out _), "Cancellation ignored");
    var g = new Fixture(); g.Finish(); g.Tracker.OutcomeCompleted(g.Match, false);
    g.Tracker.Observe("realm-a", "profile-a", "session-a", g.Room(LobbyPhase.Lobby), g.Result); Check(!g.Tracker.TryTake(out _), "Room exit ignored");
    var h = new Fixture(); h.Finish(); h.Result = h.CreateResult(outcome: RaceOutcome.Busted); h.Observe(); h.Tracker.OutcomeCompleted(h.Match, false); Check(!h.Tracker.TryTake(out _), "Busted milestone");
});
Test("real refresh or profile callback between Observe and TryTake invalidates cached proof", () =>
{
    var f = new Fixture(); f.Finish(); f.Tracker.OutcomeCompleted(f.Match, false); f.Session.Refresh();
    Check(f.Session.Busy && !f.Tracker.TryTake(out _), "In-flight refresh reused cached cue");
    f.Wire.Complete(f.After()); f.Observe(); Check(!f.Tracker.TryTake(out _), "Cancelled cue revived after refresh");
    var g = new Fixture(); g.Finish(); g.Tracker.OutcomeCompleted(g.Match, false); g.Session.Refresh(); g.Wire.Complete(null, true);
    Check(!g.Tracker.TryTake(out _), "Failed refresh reused cached cue");
    var h = new Fixture(); h.Finish(); h.Tracker.OutcomeCompleted(h.Match, false); h.Session.Refresh(); h.Wire.Complete(h.After());
    Check(!h.Tracker.TryTake(out _), "New unobserved profile object reused cached cue");
});
Test("leave intent cancels a late career response before the room acknowledgement arrives", () =>
{
    var f = new Fixture(); f.Result = f.CreateResult(); f.Session.Refresh(); f.Tracker.OutcomeCompleted(f.Match, false);
    f.Tracker.CancelCurrent(); // The bootstrap's leave/rematch/disconnect intent helper calls this before sending its existing command.
    f.Wire.Complete(f.After()); f.Observe();
    Check(f.Room(LobbyPhase.Results).Phase == LobbyPhase.Results && !f.Tracker.TryTake(out _), "Late result played before leave acknowledgement");
});
Console.WriteLine($"PASS {passed} authority-correlation groups using real CareerSession callbacks; fixtures are synthetic, not native campaign acceptance.");

sealed class Fixture
{
    public readonly Wire Wire = new(); public readonly Store Store = new(); public readonly CareerSession Session; public readonly CareerMilestoneTracker Tracker;
    public readonly int Level, Mask; public string Match => "realm-a/7"; public MultiplayerResultReadModel Result;
    public Fixture(int level = 0, int mask = 30)
    {
        Level = level; Mask = mask; const string endpoint = "wss://example.invalid/multiplayer";
        Store.Save(endpoint, new ProfileCredential("synthetic-capability", "profile-a", "Rider", "realm-a", 1000));
        Session = new CareerSession(Wire, Store, Store); Session.SetEndpoint(endpoint); Session.Refresh(); Wire.Complete(Before());
        Tracker = new CareerMilestoneTracker(Session); Tracker.Observe("realm-a", "profile-a", "session-a", Room(LobbyPhase.Racing), null);
    }
    public LobbyReadModel Room(LobbyPhase phase) => new("room-a", "AAAAAA", "Synthetic room", "session-a", Match, phase, 1, 1, 0, 8, 0,
        new[] { new LobbyMemberReadModel("session-a", "Rider", 1, true, true, false) }, false, 0, Level);
    public CareerResponse Before() => new() { ok = true, profile = new CareerProfileData { realmId = "realm-a", realmKind = "offline", profileId = "profile-a", displayName = "Rider",
        selectedBikeId = BikeCatalog.StarterBikeId, selectedCharacterId = CharacterCatalog.GetAt(0).Id, credits = 1000, levelIndex = Level, qualificationMask = Mask, revision = 10,
        bikes = new[] { new CareerBikeData { bikeId = BikeCatalog.StarterBikeId, condition = 100 } } }, ledger = Array.Empty<CareerLedgerEntry>() };
    public CareerResponse After()
    {
        var response = Before(); var expected = CampaignRules.ApplyQualification(Level, Mask, false, 0, 1);
        response.profile.levelIndex = expected.LevelIndex; response.profile.qualificationMask = expected.QualificationMask; response.profile.campaignComplete = expected.Completed;
        response.profile.credits = 1600; response.profile.revision = 11;
        response.ledger = new[] { new CareerLedgerEntry { transactionId = "match:7", reason = "race_result", bikeId = BikeCatalog.StarterBikeId, delta = 600, balance = 1600 } };
        return response;
    }
    public MultiplayerResultReadModel CreateResult(bool persisted = true, RaceOutcome outcome = RaceOutcome.Finished) => new(Match, Match, persisted,
        new[] { new MultiplayerResultEntry("session-a", "Rider", 1, outcome, 1, 600, 1600, 100) });
    public void Finish(CareerResponse after = null) { Result = CreateResult(); Session.Refresh(); Wire.Complete(after ?? After()); Observe(); }
    public void Observe() => Tracker.Observe("realm-a", "profile-a", "session-a", Room(Result == null ? LobbyPhase.Racing : LobbyPhase.Results), Result);
}
sealed class Wire : ICareerTransport
{
    public CareerRequest Last; public Action<CareerResponse, bool> Callback;
    public void Send(string endpoint, string bearer, CareerRequest request, Action<CareerResponse, bool> completed) { Last = request; Callback = completed; }
    public void Complete(CareerResponse response, bool transient = false) => Callback(response, transient);
}
sealed class Store : IProfileCredentialStore, IResumeReceiptStore
{
    readonly Dictionary<string, ProfileCredential> credentials = new();
    public ProfileCredential Load(string endpoint) => credentials.TryGetValue(endpoint, out var value) ? value : null;
    public void Save(string endpoint, ProfileCredential value) => credentials[endpoint] = value;
    public void Clear(string endpoint) => credentials.Remove(endpoint);
    ResumeReceipt IResumeReceiptStore.Load(string endpoint) => null;
    void IResumeReceiptStore.Save(string endpoint, ResumeReceipt value) { }
    void IResumeReceiptStore.Clear(string endpoint) { }
}
