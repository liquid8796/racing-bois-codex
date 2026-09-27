using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Current combat state only. Never contains future inputs or random state.</summary>
    public readonly struct RiderCombatPredictionContext
    {
        public const int MaximumHitProtectionTicks = 90, MaximumStealProtectionTicks = 300;
        public readonly int Endurance;
        public readonly bool AttackResolved;
        public readonly long HitUntilTick, StealUntilTick;

        public RiderCombatPredictionContext(long tick, int endurance, bool attackResolved, int hitRemaining, int stealRemaining)
        {
            if (tick < 0 || endurance < GameplayRules.InitialEndurance / 2 || endurance > GameplayRules.InitialEndurance ||
                hitRemaining < 0 || hitRemaining > MaximumHitProtectionTicks || stealRemaining < 0 || stealRemaining > MaximumStealProtectionTicks ||
                tick > long.MaxValue - Math.Max(hitRemaining, stealRemaining))
                throw new ArgumentException("Remote combat context is outside authoritative bounds.");
            Endurance = endurance; AttackResolved = attackResolved;
            HitUntilTick = tick + hitRemaining; StealUntilTick = tick + stealRemaining;
        }
        public bool IsValidAt(long tick) => tick >= 0 && Endurance >= GameplayRules.InitialEndurance / 2 && Endurance <= GameplayRules.InitialEndurance &&
            HitUntilTick >= tick && HitUntilTick - tick <= MaximumHitProtectionTicks &&
            StealUntilTick >= tick && StealUntilTick - tick <= MaximumStealProtectionTicks;
    }
}
