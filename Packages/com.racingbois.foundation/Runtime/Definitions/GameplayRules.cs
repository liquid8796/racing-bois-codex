namespace RacingBois.Gameplay.Definitions
{
    public enum RiderMode { Riding, Attacking, Hit, Airborne, Falling, Detached, Running, Remounting, Wrecked, Busted, Finished }
    public enum RiderKind { Player, Opponent, Police }
    public enum WeaponKind { Fist, Club, Chain, Kick }
    public enum PedestrianMode { Waiting, Walking, Stumbled }
    public enum RaceEventKind { Attack, Hit, WeaponStolen, Crash, Landed, Remounted, Wrecked, Busted, Finished, TrafficSpawned, PedestrianSpawned, PedestrianStumbled, PedestrianRecovered }

    /// <summary>New physical units and tuning. Legacy integer combat math is retained where verified; this is not full parity.</summary>
    public static class GameplayRules
    {
        public const int Version = 3;
        public static readonly string ContentHash = ContentFingerprint.Compute();
        public const int TickRate = 60;
        public const int MaxPlayers = 8;
        public const int MaxRiders = 16;
        public const int MaxTraffic = 12;
        public const int MaxPedestrians = 6;
        public const int PedestrianRadiusMillimeters = 300;
        public const int PedestrianHeightMillimeters = 1800;
        public const int MaxEventsPerTick = 64;
        public const int MaximumSpeedMillimetersPerSecond = 58000;
        public const int InitialHealth = 4096;
        public const int InitialBikeCondition = 100;
        public const int InitialEndurance = 1000;
        public const int AttackDurationTicks = 24;
        public const int AttackImpactTick = 8;
        public const int RemountDurationTicks = 60;
        public const int RunSpeedMillimetersPerSecond = 4500;
        public const int PlayerIdMinimum = 1;
        public const int BotIdMinimum = 1001;
        public const int PoliceId = 2001;
        public static bool CanDrive(RiderMode mode) => mode == RiderMode.Riding || mode == RiderMode.Attacking || mode == RiderMode.Hit || mode == RiderMode.Airborne;
        public static bool IsTerminal(RiderMode mode) => mode == RiderMode.Wrecked || mode == RiderMode.Busted || mode == RiderMode.Finished;
        public static int HitCooldownTicks(int level) => 6 * (5 - (level < 0 ? 0 : level > 4 ? 4 : level));
    }
}
