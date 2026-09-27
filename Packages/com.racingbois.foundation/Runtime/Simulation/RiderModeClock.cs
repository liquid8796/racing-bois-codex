using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Known driving-state clocks, shared by authority and bounded neighbor forecasts.</summary>
    internal static class RiderModeClock
    {
        internal static void AdvanceDrivingMode(RaceRider rider)
        {
            if (rider.Mode == RiderMode.Hit && rider.ModeAgeTicks >= 12)
            { rider.Mode = RiderMode.Riding; rider.ModeAgeTicks = 0; }
            if (rider.Mode != RiderMode.Attacking) return;
            rider.AttackAgeTicks++;
            if (rider.AttackAgeTicks >= GameplayRules.AttackDurationTicks)
            { rider.Mode = RiderMode.Riding; rider.ModeAgeTicks = 0; rider.AttackSide = 0; }
        }
    }
}
