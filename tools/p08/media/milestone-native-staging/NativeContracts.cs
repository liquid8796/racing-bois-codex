using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

namespace RacingBois.Tools.NativeMilestones
{
    public static class NativeMilestoneContracts
    {
        internal static readonly List<Fixture> OwnedFixtures = new List<Fixture>();
        private static bool running;
        [Serializable] public sealed class Group { public string name; public bool passed; public string error = ""; }
        [Serializable] public sealed class AssemblyIdentity { public string name, mvid, path, sha256; }
        [Serializable] public sealed class Receipt
        {
            public int schema = 1, passedGroups, disposedFixtures;
            public string scope = "native-Mono-career-correlation-contracts", unityVersion, platform, failure = "";
            public bool passed, isEditor, isMono, cleanupPassed, actualNetwork = false, uiPlayback = false, fullCampaignAccepted = false;
            public List<Group> groups = new List<Group>();
            public List<AssemblyIdentity> assemblies = new List<AssemblyIdentity>();
        }
        public static string Run(string expectedApplicationMvid, string expectedProtocolMvid, string expectedDefinitionsMvid)
        {
            if (running) throw new InvalidOperationException("Native milestone harness is already running");
            running = true;
            var receipt = new Receipt { unityVersion = UnityEngine.Application.unityVersion, platform = UnityEngine.Application.platform.ToString(),
                isEditor = UnityEngine.Application.isEditor, isMono = Type.GetType("Mono.Runtime") != null };
            try
            {
                RequireIdentity(typeof(CareerSession).Assembly, expectedApplicationMvid, receipt);
                RequireIdentity(typeof(CareerResponse).Assembly, expectedProtocolMvid, receipt);
                RequireIdentity(typeof(CampaignRules).Assembly, expectedDefinitionsMvid, receipt);
                receipt.assemblies.Add(Identity(typeof(RacingBois.Client.Adapters.UnityWireCodec).Assembly));
                receipt.assemblies.Add(Identity(typeof(NativeMilestoneContracts).Assembly));
                if (!receipt.isMono) throw new InvalidOperationException("This scope requires actual Unity Mono");
                foreach (var type in typeof(NativeMilestoneContracts).Assembly.GetTypes())
                    if ((type.Namespace ?? "").StartsWith("RacingBois.Client", StringComparison.Ordinal) || type.Namespace == "RacingBois.Protocol" || type.Namespace == "RacingBois.Gameplay.Definitions")
                        throw new InvalidOperationException("A production type was copied into the helper assembly");
                typeof(CareerSession).Assembly.GetType("RacingBois.Client.Application.CareerMilestoneTracker", true);
int passed = 0;
void Check(bool ok, string why) { if (!ok) throw new Exception(why); }
void Test(string name, Action body)
            {
                try { body(); passed++; receipt.groups.Add(new Group { name = name, passed = true }); }
                catch (Exception error) { receipt.groups.Add(new Group { name = name, passed = false, error = error.ToString() }); }
            }
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
    f.Result = f.CreateResult(resultId: "realm-a/8"); f.Observe();
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
receipt.passedGroups = passed; receipt.passed = passed == 15 && receipt.groups.Count == 15;


            }
            catch (Exception error) { receipt.passed = false; receipt.failure = error.ToString(); }
            finally
            {
                receipt.cleanupPassed = true;
                receipt.disposedFixtures = OwnedFixtures.Count;
                foreach (var fixture in OwnedFixtures)
                {
                    try { fixture.Dispose(); }
                    catch (Exception error) { receipt.passed = false; receipt.cleanupPassed = false; receipt.failure += " Cleanup: " + error; }
                }
                OwnedFixtures.Clear(); running = false;
            }
            // CLR serialization avoids native JsonUtility registration for dynamic helper DTO lists.
            string json = Newtonsoft.Json.JsonConvert.SerializeObject(receipt, Newtonsoft.Json.Formatting.Indented);
            var parsed = Newtonsoft.Json.Linq.JObject.Parse(json);
            if (!(parsed["groups"] is Newtonsoft.Json.Linq.JArray groups) || groups.Count != receipt.groups.Count ||
                !(parsed["assemblies"] is Newtonsoft.Json.Linq.JArray assemblies) || assemblies.Count != receipt.assemblies.Count)
                throw new InvalidOperationException("Native milestone receipt lost evidence lists");
            return json;
        }
        private static void RequireIdentity(Assembly assembly, string expected, Receipt receipt)
        {
            if (!Guid.TryParse(expected, out var parsed) || parsed != assembly.ManifestModule.ModuleVersionId)
                throw new InvalidOperationException("Live assembly MVID mismatch: " + assembly.GetName().Name);
            receipt.assemblies.Add(Identity(assembly));
        }
        private static AssemblyIdentity Identity(Assembly assembly)
        {
            string path = assembly.Location;
            string hash = "";
            if (!string.IsNullOrEmpty(path) && File.Exists(path))
                using (var sha = SHA256.Create()) hash = BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
            return new AssemblyIdentity { name = assembly.GetName().Name, mvid = assembly.ManifestModule.ModuleVersionId.ToString("D"), path = path, sha256 = hash };
        }
    }
}
