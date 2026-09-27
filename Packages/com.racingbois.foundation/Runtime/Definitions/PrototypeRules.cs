namespace RacingBois.Gameplay.Definitions
{
    /// <summary>P02 transport fixture. These are newly authored test rules, NOT recovered Road Rash physics.</summary>
    public static class PrototypeRules
    {
        public const int Version = 1;
        public const string ContentHash = "p02-foundation-v1";
        public const int TickRate = 60;
        public const int SnapshotRate = 20;
        public const int MaxPlayers = 8;
        public const int MaximumSpeedMillimetersPerSecond = 60000;
        public const int AccelerationMillimetersPerSecondSquared = 12000;
        public const int BrakingMillimetersPerSecondSquared = 20000;
        public const int CoastingMillimetersPerSecondSquared = 1500;
        public const int LateralSpeedMillimetersPerSecond = 6000;
        public const int RoadHalfWidthMillimeters = 6000;
        public const int InputTimeoutTicks = 30;
    }
}
