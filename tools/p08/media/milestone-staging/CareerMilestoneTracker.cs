using System;
using System.Collections.Generic;
using System.Globalization;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Client.Application
{
    /// <summary>Optional presentation from correlated authority read models. Never grants or persists progress.</summary>
    public sealed class CareerMilestoneTracker
    {
        private readonly CareerSession career;
        private CareerProfileReadModel before;
        private CareerProfileReadModel proofProfile;
        private IReadOnlyList<CareerLedgerReadModel> proofLedger;
        private string realm = "", profile = "", player = "", roomId = "", match = "", ledgerId = "", endpoint = "";
        private int epoch, level, course;
        private bool cancelled, outcomeCompleted, consumed;
        private string pendingScene = "";
        public string PendingSceneId => pendingScene;
        public string TrackedMatchId => match;

        public CareerMilestoneTracker(CareerSession session) { career = session ?? throw new ArgumentNullException(nameof(session)); }

        public void Reset()
        {
            before = proofProfile = null; proofLedger = null; realm = profile = player = roomId = match = ledgerId = endpoint = pendingScene = "";
            epoch = level = course = 0; cancelled = outcomeCompleted = consumed = false;
        }
        public void CancelCurrent() { cancelled = true; pendingScene = ""; proofProfile = null; proofLedger = null; }
        public void OutcomeCompleted(string resultId, bool skipped)
        {
            if (resultId != match || match.Length == 0) return;
            if (skipped) CancelCurrent(); else outcomeCompleted = true;
        }
        public bool TryTake(out string sceneId)
        {
            sceneId = "";
            if (cancelled || consumed || !outcomeCompleted || pendingScene.Length == 0) return false;
            // A later callback/intent can invalidate the observed proof before presentation consumes it.
            if (career.Busy || career.ErrorCode.Length > 0 || career.Notice != "view" || career.Endpoint != endpoint ||
                !ReferenceEquals(career.Profile, proofProfile) || !ReferenceEquals(career.Ledger, proofLedger))
            { CancelCurrent(); return false; }
            consumed = true; sceneId = pendingScene; pendingScene = ""; return true;
        }

        public void Observe(string welcomeRealm, string welcomeProfile, string sessionId, LobbyReadModel room, MultiplayerResultReadModel result)
        {
            if (room == null || string.IsNullOrEmpty(welcomeRealm) || string.IsNullOrEmpty(welcomeProfile) || string.IsNullOrEmpty(sessionId) ||
                room.Phase == LobbyPhase.Lobby || room.Phase == LobbyPhase.Closing)
            { Reset(); return; }
            bool same = realm == welcomeRealm && profile == welcomeProfile && player == sessionId && roomId == room.RoomId &&
                match == room.MatchId && epoch == room.RaceEpoch && endpoint == career.Endpoint && level == room.LevelIndex && course == room.CourseIndex;
            if (!same)
            {
                string transaction;
                if (!TryTransaction(welcomeRealm, room.MatchId, out transaction)) { Reset(); return; }
                Reset(); realm = welcomeRealm; profile = welcomeProfile; player = sessionId; roomId = room.RoomId;
                match = room.MatchId; epoch = room.RaceEpoch; endpoint = career.Endpoint; level = room.LevelIndex; course = room.CourseIndex; ledgerId = transaction;
            }
            if (cancelled || consumed) return;
            pendingScene = ""; // A cue is available only while this observation still proves every input.
            proofProfile = null; proofLedger = null;
            var current = career.Profile;
            if (current == null || current.RealmId != realm || current.ProfileId != profile)
            { if (before != null) CancelCurrent(); return; }
            if (!ValidProgress(current)) { CancelCurrent(); return; }
            if (before == null)
            {
                // Never establish a before-state from a persisted result or a post-match profile.
                if (room.Phase != LobbyPhase.Countdown && room.Phase != LobbyPhase.Racing) return;
                if (result != null && result.MatchId == match || career.Busy || career.ErrorCode.Length > 0 || career.Notice != "view" ||
                    current.LevelIndex != level || current.CampaignComplete || current.Revision < 0 || HasLedger(ledgerId)) return;
                before = current;
                return;
            }
            if (current.Revision < before.Revision || current.Revision > before.Revision + 1 ||
                (current.Revision == before.Revision && !SameProgress(before, current)))
            { CancelCurrent(); return; }
            if (room.Phase != LobbyPhase.Results || result == null || !result.Persisted || result.ResultId != match || result.MatchId != match ||
                career.Busy || career.ErrorCode.Length > 0 || career.Notice != "view" || ReferenceEquals(current, before)) return;
            if (current.Revision != before.Revision + 1) return;
            MultiplayerResultEntry own = null;
            foreach (var row in result.Entries) if (row.PlayerId == player) { if (own != null) { CancelCurrent(); return; } own = row; }
            if (own == null || own.Outcome != RaceOutcome.Finished || own.Rank < 1 || own.Rank > CampaignCatalog.QualifyingRank)
            { CancelCurrent(); return; }
            CareerLedgerReadModel matchRow = null;
            foreach (var row in career.Ledger) if (row.TransactionId == ledgerId)
            { if (matchRow != null) { CancelCurrent(); return; } matchRow = row; }
            if (matchRow == null) return; // A truncated/stale ledger is not enough evidence.
            if (matchRow.Reason != "race_result" || matchRow.BikeId != before.SelectedBikeId || matchRow.Delta != own.Reward || matchRow.Balance != own.Credits ||
                current.Credits != own.Credits || before.Credits + (long)matchRow.Delta != current.Credits)
            { CancelCurrent(); return; }
            var expected = CampaignRules.ApplyQualification(before.LevelIndex, before.QualificationMask, before.CampaignComplete, course, own.Rank);
            if (current.LevelIndex != expected.LevelIndex || current.QualificationMask != expected.QualificationMask || current.CampaignComplete != expected.Completed)
            { CancelCurrent(); return; }
            proofProfile = current; proofLedger = career.Ledger;
            if (!before.CampaignComplete && current.CampaignComplete)
                pendingScene = "rb-finalwin-the-road-stays-open";
            else if (current.LevelIndex == before.LevelIndex + 1)
            {
                // Four level advances, not six levels. Remaining authored Level vignettes stay available in the gallery.
                switch (current.LevelIndex)
                {
                    case 1: pendingScene = "rb-level-past-the-first-ridge"; break;
                    case 2: pendingScene = "rb-level-city-rhythm"; break;
                    case 3: pendingScene = "rb-level-above-the-weather"; break;
                    case 4: pendingScene = "rb-level-a-line-beside-the-sea"; break;
                }
            }
        }
        private bool HasLedger(string id) { foreach (var row in career.Ledger) if (row.TransactionId == id) return true; return false; }
        private static bool SameProgress(CareerProfileReadModel a, CareerProfileReadModel b)
            => a.LevelIndex == b.LevelIndex && a.QualificationMask == b.QualificationMask && a.CampaignComplete == b.CampaignComplete;
        private static bool ValidProgress(CareerProfileReadModel value)
        {
            try { CampaignRules.ValidateProgress(value.LevelIndex, value.QualificationMask, value.CampaignComplete); return true; }
            catch (ArgumentException) { return false; }
        }
        private static bool TryTransaction(string realmId, string matchId, out string transaction)
        {
            transaction = ""; string prefix = realmId + "/";
            if (matchId == null || !matchId.StartsWith(prefix, StringComparison.Ordinal)) return false;
            string number = matchId.Substring(prefix.Length);
            if (!long.TryParse(number, NumberStyles.None, CultureInfo.InvariantCulture, out long parsed) || parsed <= 0 || parsed.ToString(CultureInfo.InvariantCulture) != number) return false;
            transaction = "match:" + number; return true;
        }
    }
}
