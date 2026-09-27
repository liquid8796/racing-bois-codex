using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Fixed-capacity trusted snapshot proxies. The caller owns filling these; prediction copies before mutation.</summary>
    public sealed class PredictionNeighbors
    {
        public const int MaximumAgeTicks = 30;
        public readonly RaceRider[] Riders = new RaceRider[GameplayRules.MaxRiders - 1];
        public readonly RaceTraffic[] Traffic = new RaceTraffic[GameplayRules.MaxTraffic];
        public readonly RacePedestrian[] Pedestrians = new RacePedestrian[GameplayRules.MaxPedestrians];
        public readonly int[] LateralVelocity = new int[GameplayRules.MaxRiders - 1];
        public readonly int[] VerticalVelocity = new int[GameplayRules.MaxRiders - 1];
        public readonly int[] Acceleration = new int[GameplayRules.MaxRiders - 1];
        public int RiderCount, TrafficCount, PedestrianCount;
        public PredictionNeighbors()
        {
            for (int i = 0; i < Riders.Length; i++) Riders[i] = new RaceRider();
            for (int i = 0; i < Traffic.Length; i++) Traffic[i] = new RaceTraffic();
            for (int i = 0; i < Pedestrians.Length; i++) Pedestrians[i] = new RacePedestrian();
        }
    }
}
