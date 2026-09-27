using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    internal static class DrivingDynamics
    {
        internal static void Step(GameplayWorld world, RaceRider rider)
        {
            rider.ModeAgeTicks++;
            if (GameplayRules.IsTerminal(rider.Mode))
            {
                if (rider.Mode == RiderMode.Wrecked && (rider.HeightMillimeters > 0 || rider.BikeHeightMillimeters > 0))
                { rider.VerticalSpeed -= 164; rider.HeightMillimeters = Math.Max(0, rider.HeightMillimeters + rider.VerticalSpeed / 60); rider.BikeHeightMillimeters = Math.Max(0, rider.BikeHeightMillimeters + rider.VerticalSpeed / 60); }
                return;
            }
            if (!GameplayRules.CanDrive(rider.Mode)) { Recover(world, rider); return; }
            RiderModeClock.AdvanceDrivingMode(rider);

            RaceInput input = rider.Input;
            var handling = BikeHandlingCatalog.GetAt(rider.BikeCatalogIndex);
            rider.SteeringPermille = RaceSimulation.Approach(rider.SteeringPermille, input.SteerPermille, handling.SteeringResponse);
            int speed = rider.SpeedMillimetersPerSecond;
            int grade = world.Track.GradeAt(rider.DistanceMillimeters);
            int curve = world.Track.CurvatureAt(rider.DistanceMillimeters);
            bool offroad = Math.Abs(rider.LateralMillimeters) > world.Track.RoadHalfWidthMillimeters;
            int maximumSpeed = handling.MaximumSpeedMillimetersPerSecond;
            int engine = (2500 + (maximumSpeed - Math.Min(speed, maximumSpeed)) * 8500 / maximumSpeed) * input.ThrottlePermille / 1000;
            engine = engine * handling.EnginePermille / 1000;
            int drag = 350 + (int)((long)speed * speed / 3500000) + Math.Abs(rider.SteeringPermille) * speed / 50000;
            if (offroad) { engine = engine * handling.OffroadEnginePermille / 1000; drag += 3000; if (speed > 34000) drag += 4500; }
            int acceleration = engine - input.BrakePermille * handling.BrakeDeceleration / 1000 - drag - grade * 9810 / 1000;
            if (rider.Mode == RiderMode.Airborne) acceleration = -350;
            rider.SpeedRemainder += acceleration;
            rider.SpeedMillimetersPerSecond = RaceSimulation.Clamp(speed + rider.SpeedRemainder / 60, 0, maximumSpeed);
            rider.SpeedRemainder %= 60;
            rider.DistanceRemainder += rider.SpeedMillimetersPerSecond;
            rider.DistanceMillimeters += rider.DistanceRemainder / 60; rider.DistanceRemainder %= 60;

            int control = rider.Mode == RiderMode.Hit ? 550 : rider.Mode == RiderMode.Airborne ? 200 : offroad ? 550 : 1000;
            int lateralVelocity = (int)((long)rider.SteeringPermille * (1200 + rider.SpeedMillimetersPerSecond / 6) / 1000) * control / 1000;
            lateralVelocity = lateralVelocity * handling.CorneringPermille / 1000;
            int bendDrift = (int)((long)rider.SpeedMillimetersPerSecond * curve / 100000);
            rider.LateralRemainder += lateralVelocity - bendDrift;
            rider.LateralMillimeters += rider.LateralRemainder / 60; rider.LateralRemainder %= 60;
            int maxLateral = world.Track.RoadHalfWidthMillimeters + world.Track.ShoulderWidthMillimeters + 800;
            if (Math.Abs(rider.LateralMillimeters) > maxLateral)
            {
                rider.LateralMillimeters = RaceSimulation.Clamp(rider.LateralMillimeters, -maxLateral, maxLateral);
                if (rider.SpeedMillimetersPerSecond > 17000) Crash(world, rider, 350, 12);
                else rider.SpeedMillimetersPerSecond = rider.SpeedMillimetersPerSecond * 9 / 10;
            }
            if (!GameplayRules.CanDrive(rider.Mode)) return;

            int newGrade = world.Track.GradeAt(rider.DistanceMillimeters);
            if (rider.Mode != RiderMode.Airborne && grade - newGrade >= 60 && speed > 32000)
            {
                rider.Mode = RiderMode.Airborne; rider.ModeAgeTicks = 0; rider.HeightMillimeters = 10;
                rider.VerticalSpeed = speed * grade / 1000;
            }
            if (rider.Mode == RiderMode.Airborne)
            {
                rider.VerticalSpeed -= 164;
                rider.VerticalRemainder += rider.VerticalSpeed - newGrade * rider.SpeedMillimetersPerSecond / 1000;
                rider.HeightMillimeters += rider.VerticalRemainder / 60; rider.VerticalRemainder %= 60;
                if (rider.HeightMillimeters <= 0)
                {
                    int impact = Math.Abs(rider.VerticalSpeed - newGrade * rider.SpeedMillimetersPerSecond / 1000);
                    rider.HeightMillimeters = 0; rider.VerticalSpeed = 0; rider.VerticalRemainder = 0;
                    rider.Mode = RiderMode.Riding; rider.ModeAgeTicks = 0;
                    RaceSimulation.Emit(world, RaceEventKind.Landed, rider.Id, 0, impact);
                    if (impact > 10500) Crash(world, rider, 500, 18);
                }
            }
            int targetLean = -rider.SteeringPermille * 38 + curve * 2;
            rider.LeanMillidegrees = RaceSimulation.Approach(rider.LeanMillidegrees, RaceSimulation.Clamp(targetLean, -48000, 48000), 3200);
            if (rider.Gear < 6 && rider.SpeedMillimetersPerSecond > rider.Gear * 9300 + 1000) rider.Gear++;
            else if (rider.Gear > 1 && rider.SpeedMillimetersPerSecond < (rider.Gear - 1) * 9300 - 2000) rider.Gear--;
            rider.BikeDistanceMillimeters = rider.DistanceMillimeters; rider.BikeLateralMillimeters = rider.LateralMillimeters;
            rider.BikeHeightMillimeters = rider.HeightMillimeters;
        }

        internal static void Crash(GameplayWorld world, RaceRider rider, int healthDamage, int bikeDamage)
        {
            if (!GameplayRules.CanDrive(rider.Mode)) return;
            rider.Health = Math.Max(0, rider.Health - healthDamage); rider.BikeCondition = Math.Max(0, rider.BikeCondition - bikeDamage);
            rider.BikeDistanceMillimeters = rider.DistanceMillimeters; rider.BikeLateralMillimeters = rider.LateralMillimeters;
            rider.BikeHeightMillimeters = rider.HeightMillimeters; rider.BikeSpeed = rider.SpeedMillimetersPerSecond * 3 / 4;
            rider.SpeedMillimetersPerSecond /= 3; rider.LeanMillidegrees = 75000;
            rider.AttackSide = 0; rider.ModeAgeTicks = 0; rider.RecoveryTicks = 0;
            if (rider.BikeCondition == 0)
            { rider.Mode = RiderMode.Wrecked; rider.SpeedMillimetersPerSecond = 0; RaceSimulation.Emit(world, RaceEventKind.Wrecked, rider.Id, 0, 0); }
            else { rider.Mode = RiderMode.Falling; RaceSimulation.Emit(world, RaceEventKind.Crash, rider.Id, 0, healthDamage); }
        }

        private static void Recover(GameplayWorld world, RaceRider rider)
        {
            rider.RecoveryTicks++;
            if (rider.Mode == RiderMode.Falling)
            {
                rider.VerticalSpeed -= 164;
                rider.HeightMillimeters = Math.Max(0, rider.HeightMillimeters + (rider.VerticalSpeed - world.Track.GradeAt(rider.DistanceMillimeters) * rider.SpeedMillimetersPerSecond / 1000) / 60);
                rider.BikeHeightMillimeters = Math.Max(0, rider.BikeHeightMillimeters + (rider.VerticalSpeed - world.Track.GradeAt(rider.BikeDistanceMillimeters) * rider.BikeSpeed / 1000) / 60);
                rider.DistanceMillimeters += rider.SpeedMillimetersPerSecond / 60;
                rider.BikeDistanceMillimeters += rider.BikeSpeed / 60;
                rider.SpeedMillimetersPerSecond = Math.Max(0, rider.SpeedMillimetersPerSecond - 500);
                rider.BikeSpeed = Math.Max(0, rider.BikeSpeed - 700);
                rider.BikeLateralMillimeters = RaceSimulation.Approach(rider.BikeLateralMillimeters,
                    rider.LateralMillimeters + (rider.LateralMillimeters >= 0 ? 900 : -900), 25);
                if (rider.ModeAgeTicks >= 42 && rider.HeightMillimeters == 0 && rider.BikeHeightMillimeters == 0)
                { rider.Mode = RiderMode.Detached; rider.ModeAgeTicks = 0; rider.SpeedMillimetersPerSecond = 0; rider.BikeSpeed = 0; }
            }
            else if (rider.Mode == RiderMode.Detached && rider.ModeAgeTicks >= 18) { rider.Mode = RiderMode.Running; rider.ModeAgeTicks = 0; }
            else if (rider.Mode == RiderMode.Running)
            {
                long longitudinal = rider.BikeDistanceMillimeters - rider.DistanceMillimeters;
                int lateral = rider.BikeLateralMillimeters - rider.LateralMillimeters;
                long total = Math.Abs(longitudinal) + Math.Abs(lateral);
                int step = GameplayRules.RunSpeedMillimetersPerSecond / 60;
                if (total <= step)
                {
                    rider.DistanceMillimeters = rider.BikeDistanceMillimeters; rider.LateralMillimeters = rider.BikeLateralMillimeters;
                    rider.Mode = RiderMode.Remounting; rider.ModeAgeTicks = 0;
                }
                else
                {
                    int longitudinalStep = (int)(Math.Abs(longitudinal) * step / total);
                    rider.DistanceMillimeters += Math.Sign(longitudinal) * longitudinalStep;
                    rider.LateralMillimeters += Math.Sign(lateral) * (step - longitudinalStep);
                }
            }
            else if (rider.Mode == RiderMode.Remounting && rider.ModeAgeTicks >= GameplayRules.RemountDurationTicks)
            {
                if (rider.BikeCondition <= 0) { rider.Mode = RiderMode.Wrecked; RaceSimulation.Emit(world, RaceEventKind.Wrecked, rider.Id, 0, 0); }
                else
                {
                    rider.Mode = RiderMode.Riding; rider.ModeAgeTicks = 0; rider.SpeedMillimetersPerSecond = 0; rider.LeanMillidegrees = 0;
                    rider.Health = GameplayRules.InitialHealth; rider.Endurance = GameplayRules.InitialEndurance;
                    rider.CollisionUntilTick = world.Tick + 90; rider.HitUntilTick = world.Tick + 90;
                    RaceSimulation.Emit(world, RaceEventKind.Remounted, rider.Id, 0, rider.RecoveryTicks);
                }
            }
            // Never teleport on timeout. A corrupt/unreachable recovery terminates clearly instead of trapping the race.
            if (rider.RecoveryTicks > 1200 && !GameplayRules.CanDrive(rider.Mode))
            { rider.Mode = RiderMode.Wrecked; rider.ModeAgeTicks = 0; RaceSimulation.Emit(world, RaceEventKind.Wrecked, rider.Id, 0, 1200); }
        }

        internal static void ResolveContacts(GameplayWorld world, int onlyRiderId = 0)
        {
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (onlyRiderId != 0 && rider.Id != onlyRiderId) continue;
                if (!GameplayRules.CanDrive(rider.Mode) || world.Tick <= rider.CollisionUntilTick) continue;
                for (int j = 0; j < world.TrafficCount; j++)
                {
                    var traffic = world.Traffic[j];
                    int time;
                    int verticalCenter = (traffic.HeightMillimeters - VehicleDimensions.MotorcycleHeight) / 2;
                    int previousHeight = rider.PreviousHeight + world.Track.HeightMillimetersAt(rider.PreviousDistance) - world.Track.HeightMillimetersAt(traffic.PreviousDistance);
                    int currentHeight = rider.HeightMillimeters + world.Track.HeightMillimetersAt(rider.DistanceMillimeters) - world.Track.HeightMillimetersAt(traffic.DistanceMillimeters);
                    if (!Sweep(rider.PreviousDistance - traffic.PreviousDistance, rider.DistanceMillimeters - traffic.DistanceMillimeters,
                        rider.PreviousLateral - traffic.LateralMillimeters, rider.LateralMillimeters - traffic.LateralMillimeters,
                        previousHeight - verticalCenter, currentHeight - verticalCenter,
                        traffic.LengthMillimeters / 2 + VehicleDimensions.MotorcycleHalfLength,
                        traffic.WidthMillimeters / 2 + VehicleDimensions.MotorcycleHalfWidth,
                        (traffic.HeightMillimeters + VehicleDimensions.MotorcycleHeight) / 2, out time)) continue;
                    int relativeSpeed = Math.Abs(rider.SpeedMillimetersPerSecond - traffic.SpeedMillimetersPerSecond);
                    rider.DistanceMillimeters = rider.PreviousDistance + (rider.DistanceMillimeters - rider.PreviousDistance) * time / 65536;
                    if (relativeSpeed > 9500) Crash(world, rider, 700, 15 + relativeSpeed / 3000);
                    else { rider.SpeedMillimetersPerSecond = Math.Max(0, traffic.SpeedMillimetersPerSecond - 2000); rider.CollisionUntilTick = world.Tick + 20; }
                    break;
                }
                if (!GameplayRules.CanDrive(rider.Mode)) continue;
                for (int j = 0; j < world.PedestrianCount; j++)
                {
                    var pedestrian = world.Pedestrians[j];
                    if (pedestrian.Mode == PedestrianMode.Stumbled) continue;
                    int center = (GameplayRules.PedestrianHeightMillimeters - VehicleDimensions.MotorcycleHeight) / 2;
                    int previousHeight = rider.PreviousHeight + world.Track.HeightMillimetersAt(rider.PreviousDistance) - world.Track.HeightMillimetersAt(pedestrian.PreviousDistance);
                    int currentHeight = rider.HeightMillimeters + world.Track.HeightMillimetersAt(rider.DistanceMillimeters) - world.Track.HeightMillimetersAt(pedestrian.DistanceMillimeters);
                    int time;
                    if (!Sweep(rider.PreviousDistance - pedestrian.PreviousDistance, rider.DistanceMillimeters - pedestrian.DistanceMillimeters,
                        rider.PreviousLateral - pedestrian.PreviousLateral, rider.LateralMillimeters - pedestrian.LateralMillimeters,
                        previousHeight - center, currentHeight - center,
                        GameplayRules.PedestrianRadiusMillimeters + VehicleDimensions.MotorcycleHalfLength,
                        GameplayRules.PedestrianRadiusMillimeters + VehicleDimensions.MotorcycleHalfWidth,
                        (GameplayRules.PedestrianHeightMillimeters + VehicleDimensions.MotorcycleHeight) / 2, out time)) continue;
                    int pedestrianVelocity = pedestrian.IsCrossing ? 0 : pedestrian.WalkingSpeedMillimetersPerSecond;
                    int impact = Math.Abs(rider.SpeedMillimetersPerSecond - pedestrianVelocity);
                    rider.DistanceMillimeters = rider.PreviousDistance + (rider.DistanceMillimeters - rider.PreviousDistance) * time / 65536;
                    rider.LateralMillimeters = rider.PreviousLateral + (rider.LateralMillimeters - rider.PreviousLateral) * time / 65536;
                    PedestrianSimulation.Stumble(world, pedestrian, rider.Id, impact);
                    if (impact > 12000) Crash(world, rider, 350, 8);
                    else
                    {
                        rider.SpeedMillimetersPerSecond = 0; rider.Mode = RiderMode.Hit; rider.ModeAgeTicks = 0;
                        rider.Health = Math.Max(0, rider.Health - impact / 100); rider.CollisionUntilTick = world.Tick + 45;
                        rider.BikeDistanceMillimeters = rider.DistanceMillimeters; rider.BikeLateralMillimeters = rider.LateralMillimeters;
                        if (rider.Health == 0) Crash(world, rider, 0, 0);
                    }
                    break;
                }
                if (!GameplayRules.CanDrive(rider.Mode)) continue;
                for (int j = i + 1; j < world.RiderCount; j++)
                {
                    var other = world.Riders[j];
                    if (!GameplayRules.CanDrive(other.Mode) || world.Tick <= other.CollisionUntilTick) continue;
                    int time;
                    int previousHeight = rider.PreviousHeight - other.PreviousHeight + world.Track.HeightMillimetersAt(rider.PreviousDistance) - world.Track.HeightMillimetersAt(other.PreviousDistance);
                    int currentHeight = rider.HeightMillimeters - other.HeightMillimeters + world.Track.HeightMillimetersAt(rider.DistanceMillimeters) - world.Track.HeightMillimetersAt(other.DistanceMillimeters);
                    if (!Sweep(rider.PreviousDistance - other.PreviousDistance, rider.DistanceMillimeters - other.DistanceMillimeters,
                        rider.PreviousLateral - other.PreviousLateral, rider.LateralMillimeters - other.LateralMillimeters,
                        previousHeight, currentHeight, VehicleDimensions.MotorcycleHalfLength * 2,
                        VehicleDimensions.MotorcycleHalfWidth * 2, VehicleDimensions.MotorcycleHeight, out time)) continue;
                    int relativeSpeed = Math.Abs(rider.SpeedMillimetersPerSecond - other.SpeedMillimetersPerSecond);
                    if (relativeSpeed > 17000)
                    {
                        rider.DistanceMillimeters = rider.PreviousDistance + (rider.DistanceMillimeters - rider.PreviousDistance) * time / 65536;
                        other.DistanceMillimeters = other.PreviousDistance + (other.DistanceMillimeters - other.PreviousDistance) * time / 65536;
                        Crash(world, rider, 500, 16); Crash(world, other, 500, 16);
                        break;
                    }
                    else
                    {
                        int side = rider.LateralMillimeters <= other.LateralMillimeters ? -1 : 1;
                        rider.LateralMillimeters += side * 90; other.LateralMillimeters -= side * 90;
                        rider.SpeedMillimetersPerSecond = Math.Max(0, rider.SpeedMillimetersPerSecond - 1200);
                        other.SpeedMillimetersPerSecond = Math.Max(0, other.SpeedMillimetersPerSecond - 1200);
                        rider.CollisionUntilTick = other.CollisionUntilTick = world.Tick + 12;
                    }
                }
            }
        }

        /// <summary>Relative swept AABB, integer Q16 slab interval; touching bounds is contact.</summary>
        private static bool Sweep(long s0, long s1, long d0, long d1, long h0, long h1, int halfLength, int halfWidth, int halfHeight, out int time)
        {
            long enter = 0, exit = 65536;
            bool hit = Slab(s0, s1, halfLength, ref enter, ref exit) && Slab(d0, d1, halfWidth, ref enter, ref exit)
                && Slab(h0, h1, halfHeight, ref enter, ref exit);
            time = (int)enter; return hit;
        }
        private static bool Slab(long origin, long end, int half, ref long enter, ref long exit)
        {
            long delta = end - origin;
            if (delta == 0) return origin >= -half && origin <= half;
            long a = (-half - origin) * 65536 / delta, b = (half - origin) * 65536 / delta;
            if (a > b) { long swap = a; a = b; b = swap; }
            enter = Math.Max(enter, a); exit = Math.Min(exit, b);
            return enter <= exit && exit >= 0 && enter <= 65536;
        }
    }
}
