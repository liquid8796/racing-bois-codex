using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    public readonly struct GameplayVerificationResult
    {
        public readonly bool Passed;
        public readonly string Hash, ExpectedHash;
        public readonly int Ticks;
        public GameplayVerificationResult(ulong hash)
        { Hash = hash.ToString("X16"); ExpectedHash = GameplayVerification.ExpectedHash.ToString("X16"); Passed = hash == GameplayVerification.ExpectedHash; Ticks = GameplayVerification.ReplayTicks; }
    }

    public readonly struct GameplayVerificationFrame
    {
        public readonly long Tick, DistanceMillimeters;
        public readonly int LateralMillimeters, SpeedMillimetersPerSecond, HeightMillimeters, Health, BikeCondition, EventCount, PedestrianCount;
        public readonly RaceInput Input;
        public readonly RiderMode Mode;
        public readonly string Hash;
        internal GameplayVerificationFrame(GameplayWorld world, RaceInput input, ulong hash)
        {
            var rider = RaceSimulation.FindRider(world, 1); Tick = world.Tick; DistanceMillimeters = rider.DistanceMillimeters;
            LateralMillimeters = rider.LateralMillimeters; SpeedMillimetersPerSecond = rider.SpeedMillimetersPerSecond;
            HeightMillimeters = rider.HeightMillimeters; Health = rider.Health; BikeCondition = rider.BikeCondition;
            EventCount = world.EventCount; PedestrianCount = world.PedestrianCount; Input = input; Mode = rider.Mode; Hash = hash.ToString("X16");
        }
    }

    /// <summary>Bounded startup replay, same integer core in native and Web. Owns an isolated world and touches no live session.</summary>
    public static class GameplayVerification
    {
        public const int ReplayTicks = 3000;
        public const ulong ExpectedHash = 0xFD320D8BD0D9435EUL;

        public static GameplayVerificationResult Run(Action<GameplayVerificationFrame> observer = null)
        {
            var world = RaceSimulation.CreateDefault(1996, 5, 2); RaceSimulation.AddPlayer(world, 1);
            ulong hash = 14695981039346656037UL;
            for (int tick = 0; tick < ReplayTicks; tick++)
            {
                var rider = RaceSimulation.FindRider(world, 1);
                int desiredLane = (int)(world.Tick / 180 % 3 - 1) * 2200;
                int curve = world.Track.CurvatureAt(rider.DistanceMillimeters + rider.SpeedMillimetersPerSecond / 8);
                int drift = (int)((long)rider.SpeedMillimetersPerSecond * curve / 100000);
                int steer = RaceSimulation.Clamp(((desiredLane - rider.LateralMillimeters) * 2 + drift) * 1000 / (1200 + rider.SpeedMillimetersPerSecond / 6), -1000, 1000);
                var input = new RaceInput(1000, world.Tick % 900 > 810 ? 400 : 0, steer,
                    world.Tick % 200 < 40 ? 1 : world.Tick % 200 > 150 ? -1 : 0, world.Tick % 500 < 100);
                RaceSimulation.SetInput(world, 1, input); RaceSimulation.Step(world); hash = Fingerprint(world, hash);
                if (observer != null) observer(new GameplayVerificationFrame(world, input, hash));
            }
            return new GameplayVerificationResult(hash);
        }

        private static ulong Fingerprint(GameplayWorld world, ulong hash)
        {
            Mix(ref hash, world.Tick); Mix(ref hash, world.RandomState); Mix(ref hash, world.PedestrianRandomState); Mix(ref hash, world.FinishedCount); Mix(ref hash, world.TrafficCount); Mix(ref hash, world.PedestrianCount);
            for (int i = 0; i < world.RiderCount; i++)
            {
                var r = world.Riders[i]; Mix(ref hash, r.Id); Mix(ref hash, (int)r.Mode); Mix(ref hash, (int)r.Weapon); Mix(ref hash, r.DistanceMillimeters);
                Mix(ref hash, r.LateralMillimeters); Mix(ref hash, r.HeightMillimeters); Mix(ref hash, r.SpeedMillimetersPerSecond); Mix(ref hash, r.Health);
                Mix(ref hash, r.BikeCondition); Mix(ref hash, r.Endurance); Mix(ref hash, r.Rank); Mix(ref hash, r.FinishTick); Mix(ref hash, r.Reward);
                Mix(ref hash, r.BikeDistanceMillimeters); Mix(ref hash, r.BikeLateralMillimeters);
            }
            for (int i = 0; i < world.TrafficCount; i++)
            { var t = world.Traffic[i]; Mix(ref hash, t.Id); Mix(ref hash, t.DistanceMillimeters); Mix(ref hash, t.LateralMillimeters); Mix(ref hash, t.SpeedMillimetersPerSecond); Mix(ref hash, t.WidthMillimeters); Mix(ref hash, t.LengthMillimeters); Mix(ref hash, t.HeightMillimeters); }
            for (int i = 0; i < world.EventCount; i++)
            { var e = world.Events[i]; Mix(ref hash, e.Id); Mix(ref hash, e.Tick); Mix(ref hash, (int)e.Kind); Mix(ref hash, e.ActorId); Mix(ref hash, e.TargetId); Mix(ref hash, e.Value); }
            for (int i = 0; i < world.PedestrianCount; i++)
            {
                var p = world.Pedestrians[i]; Mix(ref hash, p.Id); Mix(ref hash, p.DistanceMillimeters); Mix(ref hash, p.LateralMillimeters);
                Mix(ref hash, (int)p.Mode); Mix(ref hash, p.ModeAgeTicks); Mix(ref hash, p.WalkingSpeedMillimetersPerSecond); Mix(ref hash, p.FacingSide); Mix(ref hash, p.IsCrossing ? 1 : 0);
            }
            return hash;
        }
        private static void Mix(ref ulong hash, long value) { hash = unchecked((hash ^ (ulong)value) * 1099511628211UL); }
    }
}
