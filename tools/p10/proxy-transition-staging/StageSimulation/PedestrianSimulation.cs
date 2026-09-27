using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Original bounded pedestrian behavior. The video proves pedestrians, not these spawn and collision tunings.</summary>
    internal static class PedestrianSimulation
    {
        internal static void Step(GameplayWorld world)
        {
            long front = long.MinValue, back = long.MaxValue;
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (rider.Kind != RiderKind.Player || GameplayRules.IsTerminal(rider.Mode)) continue;
                front = Math.Max(front, rider.DistanceMillimeters); back = Math.Min(back, rider.DistanceMillimeters);
            }
            for (int i = world.PedestrianCount - 1; i >= 0; i--)
            {
                var pedestrian = world.Pedestrians[i]; pedestrian.PreviousDistance = pedestrian.DistanceMillimeters;
                pedestrian.PreviousLateral = pedestrian.LateralMillimeters; pedestrian.ModeAgeTicks++;
                if (front == long.MinValue || pedestrian.DistanceMillimeters < back - 120000 || pedestrian.DistanceMillimeters > world.Track.LengthMillimeters + 30000)
                { world.Pedestrians[i] = world.Pedestrians[world.PedestrianCount - 1]; world.Pedestrians[--world.PedestrianCount] = pedestrian; continue; }
                var ended = PedestrianMotion.AdvanceKnownState(pedestrian, world.Track.RoadHalfWidthMillimeters + 1200);
                if (ended == PedestrianWalkEnd.Recovered) RaceSimulation.Emit(world, RaceEventKind.PedestrianRecovered, pedestrian.Id, 0, 0);
                if (ended == PedestrianWalkEnd.Crossing) pedestrian.WaitTicks = 180 + NextRandom(world) % 180;
                else if (ended == PedestrianWalkEnd.AlongRoad) pedestrian.WaitTicks = 120 + NextRandom(world) % 180;
            }
            if (front == long.MinValue || world.Tick < world.NextPedestrianTick || world.PedestrianCount >= GameplayRules.MaxPedestrians || front > world.Track.LengthMillimeters - 220000) return;
            world.NextPedestrianTick = world.Tick + 300;
            var spawned = world.Pedestrians[world.PedestrianCount++];
            spawned.Id = AllocatePedestrianId(world); spawned.DistanceMillimeters = front + 150000 + NextRandom(world) % 70000;
            spawned.PreviousDistance = spawned.DistanceMillimeters; spawned.HeightMillimeters = 0;
            spawned.IsCrossing = spawned.Id % 3 == 0;
            int startSide = (NextRandom(world) & 1) == 0 ? -1 : 1;
            spawned.LateralMillimeters = startSide * (world.Track.RoadHalfWidthMillimeters + 1200);
            spawned.PreviousLateral = spawned.LateralMillimeters;
            spawned.FacingSide = spawned.IsCrossing ? -startSide : ((NextRandom(world) & 1) == 0 ? -1 : 1);
            spawned.DesiredWalkingSpeed = 1200 + NextRandom(world) % 401;
            spawned.Mode = PedestrianMode.Waiting; spawned.ModeAgeTicks = 0; spawned.MotionRemainder = 0;
            spawned.WaitTicks = spawned.IsCrossing ? 60 : 60 + NextRandom(world) % 180; spawned.WalkingSpeedMillimetersPerSecond = 0;
            RaceSimulation.Emit(world, RaceEventKind.PedestrianSpawned, spawned.Id, 0, spawned.IsCrossing ? 1 : 0);
        }

        private static int AllocatePedestrianId(GameplayWorld world)
        {
            while (true)
            {
                int candidate = world.NextPedestrianId++;
                if (world.NextPedestrianId > 4999) world.NextPedestrianId = 4001;
                bool active = false;
                for (int i = 0; i < world.PedestrianCount - 1; i++) if (world.Pedestrians[i].Id == candidate) { active = true; break; }
                if (!active) return candidate;
            }
        }

        internal static void Stumble(GameplayWorld world, RacePedestrian pedestrian, int riderId, int speed)
        {
            if (pedestrian.Mode == PedestrianMode.Stumbled) return;
            pedestrian.Mode = PedestrianMode.Stumbled; pedestrian.ModeAgeTicks = 0; pedestrian.WalkingSpeedMillimetersPerSecond = 0;
            RaceSimulation.Emit(world, RaceEventKind.PedestrianStumbled, riderId, pedestrian.Id, speed);
        }

        private static int NextRandom(GameplayWorld world)
        { world.PedestrianRandomState = unchecked(world.PedestrianRandomState * 214013u + 2531011u); return (int)((world.PedestrianRandomState >> 16) & 0x7fff); }
    }
}
