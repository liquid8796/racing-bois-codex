using System;

namespace RacingBois.Simulation
{
    /// <summary>Local provisional campaign bookkeeping. Never an online wallet or an account authority.</summary>
    public sealed class LocalCampaignProgress
    {
        public int Level { get; private set; }
        public int QualifiedCourseMask { get; private set; }
        public int Credits { get; private set; }
        public bool Completed { get; private set; }
        public long LastAppliedRunId { get; private set; } = -1;

        /// <summary>Run IDs are monotonically assigned by the local session, never supplied by a remote player.</summary>
        public bool TryApplyResult(long runId, int courseIndex, int oneBasedRank, bool busted = false)
        {
            if (runId < 0 || runId <= LastAppliedRunId || courseIndex < 0 || courseIndex >= 5 || Completed
                || (!busted && (oneBasedRank < 1 || oneBasedRank > 14))) return false;
            LastAppliedRunId = runId;
            if (busted) { Credits = Math.Max(0, Credits - 400 * (Level + 1)); return true; }
            Credits += RaceSimulation.RewardForRank(oneBasedRank, Level);
            if (oneBasedRank <= 3) QualifiedCourseMask |= 1 << courseIndex;
            if (QualifiedCourseMask == 0x1f)
            {
                if (Level == 4) Completed = true;
                else { Level++; QualifiedCourseMask = 0; }
            }
            return true;
        }
    }
}
