using System;

namespace RacingBois.Gameplay.Definitions
{
    public readonly struct CampaignProgress
    {
        public int LevelIndex { get; }
        public int QualificationMask { get; }
        public bool Completed { get; }

        internal CampaignProgress(int levelIndex, int qualificationMask, bool completed)
        {
            LevelIndex = levelIndex;
            QualificationMask = qualificationMask;
            Completed = completed;
        }
    }

    public static class CampaignRules
    {
        /// <summary>
        /// Advance after an authority-validated finish. Match IDs, replay protection, route availability and
        /// the match's captured level are checked by the transaction owner before calling this pure rule.
        /// </summary>
        public static CampaignProgress ApplyQualification(int levelIndex, int qualificationMask, bool completed,
            int courseIndex, int oneBasedRank)
        {
            ValidateProgress(levelIndex, qualificationMask, completed);
            CampaignCatalog.GetRoute(courseIndex);
            if (oneBasedRank < 1 || oneBasedRank > GameplayRules.MaxRiders)
                throw new ArgumentOutOfRangeException(nameof(oneBasedRank));
            if (completed || oneBasedRank > CampaignCatalog.QualifyingRank)
                return new CampaignProgress(levelIndex, qualificationMask, completed);

            int mask = qualificationMask | (1 << courseIndex);
            if (mask != CampaignCatalog.CompleteQualificationMask)
                return new CampaignProgress(levelIndex, mask, false);
            if (levelIndex == CampaignCatalog.LevelCount - 1)
                return new CampaignProgress(levelIndex, mask, true);
            return new CampaignProgress(levelIndex + 1, 0, false);
        }

        public static void ValidateProgress(int levelIndex, int qualificationMask, bool completed)
        {
            CampaignCatalog.ValidateLevel(levelIndex);
            if (qualificationMask < 0 || (qualificationMask & ~CampaignCatalog.CompleteQualificationMask) != 0)
                throw new ArgumentOutOfRangeException(nameof(qualificationMask));
            bool finalMask = qualificationMask == CampaignCatalog.CompleteQualificationMask;
            if (completed != (levelIndex == CampaignCatalog.LevelCount - 1 && finalMask) ||
                (finalMask && !completed))
                throw new ArgumentException("Campaign state is not a settled level/mask/completion combination.");
        }
    }
}
