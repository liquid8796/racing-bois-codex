using System;

namespace RacingBois.Gameplay.Definitions
{
    /// <summary>Pure integer quotes. The server owns balances, eligibility, transactions and idempotency.</summary>
    public static class EconomyRules
    {
        public const int Version = 1;
        public const int StartingCredits = 1000;
        public const int MaximumRewardedRank = 14;

        private static readonly int[] rewards = { 1000, 750, 500, 400, 300, 250, 200, 160, 130, 100, 70, 50, 30, 20 };

        public static int TradeInValue(int priceCredits)
        {
            if (priceCredits < 0) throw new ArgumentOutOfRangeException(nameof(priceCredits));
            return priceCredits / 2;
        }

        public static int RepairCost(int priceCredits)
        {
            if (priceCredits < 0) throw new ArgumentOutOfRangeException(nameof(priceCredits));
            return priceCredits / 10;
        }

        public static int BustFine(int levelIndex)
        {
            CampaignCatalog.ValidateLevel(levelIndex);
            return 400 * (levelIndex + 1);
        }

        /// <summary>
        /// Reference prize table for a valid finish. DNF/busted/wrecked settlement must not call this as a finish.
        /// Ranks 15 and 16 are valid Racing Bois finish positions with no reference-table prize.
        /// </summary>
        public static int RewardForRank(int oneBasedRank, int levelIndex)
        {
            CampaignCatalog.ValidateLevel(levelIndex);
            if (oneBasedRank < 1 || oneBasedRank > GameplayRules.MaxRiders)
                throw new ArgumentOutOfRangeException(nameof(oneBasedRank));
            return oneBasedRank > rewards.Length ? 0 : rewards[oneBasedRank - 1] * (levelIndex + 1);
        }
    }
}
