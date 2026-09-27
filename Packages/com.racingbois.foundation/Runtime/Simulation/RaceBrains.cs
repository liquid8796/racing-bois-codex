using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Authored bounded lane planning and police pursuit. Legacy aggression thresholds seed attack decisions.</summary>
    internal static class RaceBrains
    {
        internal static RaceInput Decide(GameplayWorld world, RaceRider rider)
        {
            if (!GameplayRules.CanDrive(rider.Mode)) return default;
            RaceRider nearestPlayer = null; long nearestDistance = long.MaxValue;
            for (int i = 0; i < world.RiderCount; i++)
            {
                var candidate = world.Riders[i];
                if (candidate.Kind != RiderKind.Player || GameplayRules.IsTerminal(candidate.Mode)) continue;
                long delta = Math.Abs(candidate.DistanceMillimeters - rider.DistanceMillimeters);
                if (delta < nearestDistance) { nearestPlayer = candidate; nearestDistance = delta; }
            }
            if (rider.Kind == RiderKind.Police && (nearestPlayer == null || nearestPlayer.DistanceMillimeters < 350000 || rider.DistanceMillimeters > world.Track.LengthMillimeters + 50000))
                return new RaceInput(0, 1000, 0);
            rider.AiDecisionTicks--;
            if (rider.AiDecisionTicks <= 0)
            {
                rider.AiDecisionTicks = 24 + rider.Id % 18;
                int targetLane = rider.AiLane;
                if (targetLane == 0) targetLane = rider.Id % 2 == 0 ? -1800 : 1800;
                if (nearestPlayer != null && (rider.Kind == RiderKind.Police || nearestDistance < 22000))
                    targetLane = nearestPlayer.LateralMillimeters + (rider.LateralMillimeters <= nearestPlayer.LateralMillimeters ? -1250 : 1250);
                bool blocked = false;
                long lookAhead = 12000 + rider.SpeedMillimetersPerSecond;
                for (int i = 0; i < world.TrafficCount; i++)
                {
                    var traffic = world.Traffic[i]; long delta = traffic.DistanceMillimeters - rider.DistanceMillimeters;
                    if (delta > -6000 && delta < lookAhead && Math.Abs(traffic.LateralMillimeters - targetLane) < 2200)
                    { blocked = true; targetLane = traffic.LateralMillimeters > 0 ? -3000 : 3000; }
                }
                if (!blocked)
                    for (int i = 0; i < world.RiderCount; i++)
                    {
                        var other = world.Riders[i]; long delta = other.DistanceMillimeters - rider.DistanceMillimeters;
                        if (other != rider && delta > 1500 && delta < 12000 && Math.Abs(other.LateralMillimeters - targetLane) < 1000 && other.SpeedMillimetersPerSecond < rider.SpeedMillimetersPerSecond + 1000)
                            targetLane = other.LateralMillimeters >= 0 ? -1800 : 1800;
                    }
                rider.AiLane = RaceSimulation.Clamp(targetLane, -4800, 4800);
            }
            int curve = world.Track.CurvatureAt(rider.DistanceMillimeters + rider.SpeedMillimetersPerSecond / 5);
            int desiredLateralVelocity = RaceSimulation.Clamp((rider.AiLane - rider.LateralMillimeters) * 2, -6500, 6500);
            int drift = (int)((long)rider.SpeedMillimetersPerSecond * curve / 100000);
            int cornering = BikeHandlingCatalog.GetAt(rider.BikeCatalogIndex).CorneringPermille;
            int steer = RaceSimulation.Clamp((int)((long)(desiredLateralVelocity + drift) * 1000000 / ((1200 + rider.SpeedMillimetersPerSecond / 6) * cornering)), -1000, 1000);
            int throttle = 1000, brake = 0;
            if (rider.Kind == RiderKind.Police && nearestPlayer != null)
            {
                long separation = nearestPlayer.DistanceMillimeters - rider.DistanceMillimeters;
                // Start braking while still behind the target. Braking only after overlap strands a cop far ahead of a stopped rider.
                long availableDistance = Math.Max(0, separation - 1400);
                long targetSpeedSquared = (long)nearestPlayer.SpeedMillimetersPerSecond * nearestPlayer.SpeedMillimetersPerSecond;
                int pursuitSpeed = IntegerSquareRoot(Math.Min(3600000000L, targetSpeedSquared + 24000 * availableDistance));
                if (rider.SpeedMillimetersPerSecond > pursuitSpeed + 250 || separation < 0)
                { throttle = 0; brake = 1000; }
            }
            // Cornering speed budget and near-obstacle emergency braking augment lane selection.
            if (Math.Abs(curve) > 6500 && rider.SpeedMillimetersPerSecond > 46000) { throttle = 450; brake = 140; }
            for (int i = 0; i < world.TrafficCount; i++)
            {
                var traffic = world.Traffic[i]; long distance = traffic.DistanceMillimeters - rider.DistanceMillimeters;
                if (distance > 0 && distance < 10000 && Math.Abs(traffic.LateralMillimeters - rider.LateralMillimeters) < 2100) { throttle = 0; brake = 1000; }
            }
            int attackSide = 0;
            if (rider.Mode == RiderMode.Riding)
            {
                int aggression = world.Level == 0 ? 4 : world.Level == 1 ? 8 : world.Level == 2 ? 25 : world.Level == 3 ? 64 : 256;
                for (int i = 0; i < world.RiderCount; i++)
                {
                    var target = world.Riders[i];
                    if (target == rider || target.Kind == RiderKind.Police || !GameplayRules.CanDrive(target.Mode)) continue;
                    int side = Math.Sign(target.LateralMillimeters - rider.LateralMillimeters);
                    if (CombatRules.InRange(rider, target, side, rider.Weapon) && world.Tick > target.HitUntilTick && (RaceSimulation.NextRandom(world) & 255) < aggression)
                    { attackSide = side; break; }
                }
            }
            return new RaceInput(throttle, brake, steer, attackSide);
        }

        private static int IntegerSquareRoot(long value)
        {
            long low = 0, high = 60001;
            while (low + 1 < high)
            { long middle = (low + high) / 2; if (middle * middle <= value) low = middle; else high = middle; }
            return (int)low;
        }

        internal static void StepTraffic(GameplayWorld world)
        {
            long front = long.MinValue, back = long.MaxValue;
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (rider.Kind != RiderKind.Player || GameplayRules.IsTerminal(rider.Mode)) continue;
                front = Math.Max(front, rider.DistanceMillimeters); back = Math.Min(back, rider.DistanceMillimeters);
            }
            for (int i = world.TrafficCount - 1; i >= 0; i--)
            {
                var traffic = world.Traffic[i]; traffic.PreviousDistance = traffic.DistanceMillimeters;
                traffic.DistanceRemainder += traffic.SpeedMillimetersPerSecond;
                traffic.DistanceMillimeters += traffic.DistanceRemainder / 60; traffic.DistanceRemainder %= 60;
                if (front == long.MinValue || traffic.DistanceMillimeters < back - 140000 || traffic.DistanceMillimeters > world.Track.LengthMillimeters + 150000)
                {
                    traffic.Active = false;
                    world.Traffic[i] = world.Traffic[world.TrafficCount - 1]; world.Traffic[--world.TrafficCount] = traffic;
                }
            }
            if (front == long.MinValue || world.Tick < world.NextTrafficTick || world.TrafficCount >= world.Traffic.Length || front > world.Track.LengthMillimeters - 150000) return;
            world.NextTrafficTick = world.Tick + 240;
            var spawned = world.Traffic[world.TrafficCount++];
            spawned.Id = AllocateTrafficId(world); spawned.Active = true; spawned.Oncoming = (RaceSimulation.NextRandom(world) & 1) == 0;
            bool van = VehicleDimensions.IsVan(spawned.Id);
            spawned.WidthMillimeters = van ? VehicleDimensions.VanWidth : VehicleDimensions.CoupeWidth;
            spawned.LengthMillimeters = van ? VehicleDimensions.VanLength : VehicleDimensions.CoupeLength;
            spawned.HeightMillimeters = van ? VehicleDimensions.VanHeight : VehicleDimensions.CoupeHeight;
            spawned.DistanceMillimeters = front + 180000 + RaceSimulation.NextRandom(world) % 65000;
            spawned.PreviousDistance = spawned.DistanceMillimeters; spawned.LateralMillimeters = spawned.Oncoming ? -3000 : 3000;
            spawned.SpeedMillimetersPerSecond = spawned.Oncoming ? -16000 - RaceSimulation.NextRandom(world) % 7000 : 17000 + RaceSimulation.NextRandom(world) % 9000;
            spawned.DistanceRemainder = 0;
            RaceSimulation.Emit(world, RaceEventKind.TrafficSpawned, spawned.Id, 0, spawned.Oncoming ? 1 : 0);
        }

        private static int AllocateTrafficId(GameplayWorld world)
        {
            while (true)
            {
                int candidate = world.NextTrafficId++;
                if (world.NextTrafficId > 3999) world.NextTrafficId = 3001;
                bool active = false;
                // The final slot is the object currently being spawned and still contains its old recycled ID.
                for (int i = 0; i < world.TrafficCount - 1; i++) if (world.Traffic[i].Id == candidate) { active = true; break; }
                if (!active) return candidate;
            }
        }

        internal static void ResolvePolice(GameplayWorld world)
        {
            var police = RaceSimulation.FindRider(world, GameplayRules.PoliceId);
            if (police == null || !GameplayRules.CanDrive(police.Mode)) return;
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (rider.Kind != RiderKind.Player || GameplayRules.IsTerminal(rider.Mode)) continue;
                bool contact = rider.DistanceMillimeters >= 350000 && Math.Abs(police.DistanceMillimeters - rider.DistanceMillimeters) < 5000
                    && Math.Abs(police.LateralMillimeters - rider.LateralMillimeters) < 2600 && rider.SpeedMillimetersPerSecond < 5500;
                rider.PoliceContactTicks = contact ? rider.PoliceContactTicks + 1 : 0;
                if (rider.PoliceContactTicks < 180) continue;
                rider.Mode = RiderMode.Busted; rider.ModeAgeTicks = 0; rider.SpeedMillimetersPerSecond = 0;
                rider.Reward = -400 * (world.Level + 1); rider.Qualified = false;
                RaceSimulation.Emit(world, RaceEventKind.Busted, police.Id, rider.Id, -rider.Reward);
            }
        }
    }
}
