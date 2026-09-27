using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
using RacingBois.Protocol;

namespace RacingBois.Client.Application
{
    internal static class PredictionNeighborBuilder
    {
        public static void Fill(PredictionNeighbors target, RaceWorldReadModel current, RaceWorldReadModel previous, int ownId, IReadOnlyDictionary<int, long> collisionUntilByRider, IReadOnlyDictionary<int, PedestrianPredictionContext> pedestrianContexts, IReadOnlyDictionary<int, RiderCombatPredictionContext> riderCombatContexts)
        {
            if (collisionUntilByRider == null) throw new ArgumentNullException(nameof(collisionUntilByRider));
            foreach (var rider in current.Riders)
                if (rider.Id != ownId && (!collisionUntilByRider.TryGetValue(rider.Id, out long until) || until < current.Tick || until - current.Tick > MultiplayerProtocol.MaximumCollisionProtectionTicks))
                    throw new ArgumentException("Remote collision protection is missing or outside snapshot bounds.");
            if (riderCombatContexts == null) throw new ArgumentNullException(nameof(riderCombatContexts));
            foreach (var rider in current.Riders)
                if (rider.Id != ownId && (!riderCombatContexts.TryGetValue(rider.Id, out var combat) || !combat.IsValidAt(current.Tick)))
                    throw new ArgumentException("Remote combat context is missing or invalid.");
            if (pedestrianContexts == null) throw new ArgumentNullException(nameof(pedestrianContexts));
            foreach (var pedestrian in current.Pedestrians)
                if (!pedestrianContexts.TryGetValue(pedestrian.Id, out var context) || !context.IsValid)
                    throw new ArgumentException("Pedestrian prediction context is missing or invalid.");
            target.RiderCount = target.TrafficCount = target.PedestrianCount = 0;
            long gap = previous == null ? 0 : current.Tick - previous.Tick;
            foreach (var r in current.Riders)
            {
                if (r.Id == ownId) continue;
                int index = target.RiderCount++; var proxy = target.Riders[index]; var combat = riderCombatContexts[r.Id];
                // Clear all previous speculative internal state by restoring a fresh value checkpoint.
                RiderCheckpoints.Restore(proxy, new RiderCheckpoint(new RiderCheckpointData
                {
                    Tick = current.Tick, Id = r.Id, BikeCatalogIndex = r.BikeCatalogIndex, CharacterCatalogIndex = r.CharacterCatalogIndex, Kind = r.Kind, Mode = r.Mode, Weapon = r.Weapon, AttackWeapon = r.AttackWeapon,
                    DistanceMillimeters = Mm(r.LongitudinalMeters), LateralMillimeters = Mm(r.LateralMeters), HeightMillimeters = Mm(r.HeightMeters),
                    BikeDistanceMillimeters = Mm(r.BikeLongitudinalMeters), BikeLateralMillimeters = Mm(r.BikeLateralMeters), BikeHeightMillimeters = Mm(r.BikeHeightMeters),
                    SpeedMillimetersPerSecond = Mm(r.SpeedMetersPerSecond), LeanMillidegrees = Mm(r.LeanDegrees),
                    Health = r.Health, BikeCondition = r.BikeCondition, Strength = r.Strength, Endurance = combat.Endurance, AttackResolved = combat.AttackResolved,
                    Rank = r.Rank, Reward = r.Reward, FinishTick = r.FinishTick, Qualified = r.Qualified, AttackSide = r.AttackSide,
                    AttackAgeTicks = r.AttackAgeTicks, ModeAgeTicks = r.ModeAgeTicks, Gear = r.Gear, HitUntilTick = combat.HitUntilTick, StealUntilTick = combat.StealUntilTick,
                    CollisionUntilTick = collisionUntilByRider[r.Id]
                }));
                target.LateralVelocity[index] = target.VerticalVelocity[index] = target.Acceleration[index] = 0;
                if (gap <= 0) continue;
                var before = RemoteMotionSampler.Find(previous.Riders, r.Id);
                if (before.Id != r.Id || before.Mode != r.Mode) continue;
                target.LateralVelocity[index] = Clamp(Mm(r.LateralMeters - before.LateralMeters) * 60 / (int)gap, -12000, 12000);
                target.VerticalVelocity[index] = Clamp(Mm(r.HeightMeters - before.HeightMeters) * 60 / (int)gap, -20000, 20000);
                target.Acceleration[index] = Clamp(Mm(r.SpeedMetersPerSecond - before.SpeedMetersPerSecond) * 60 / (int)gap, -30000, 15000);
            }
            foreach (var t in current.Traffic)
            {
                var proxy = target.Traffic[target.TrafficCount++]; bool van = VehicleDimensions.IsVan(t.Id);
                proxy.Id = t.Id; proxy.Active = true; proxy.DistanceMillimeters = Mm(t.LongitudinalMeters); proxy.LateralMillimeters = Mm(t.LateralMeters);
                proxy.SpeedMillimetersPerSecond = Mm(t.SpeedMetersPerSecond); proxy.Oncoming = t.Oncoming;
                proxy.WidthMillimeters = van ? VehicleDimensions.VanWidth : VehicleDimensions.CoupeWidth;
                proxy.LengthMillimeters = van ? VehicleDimensions.VanLength : VehicleDimensions.CoupeLength;
                proxy.HeightMillimeters = van ? VehicleDimensions.VanHeight : VehicleDimensions.CoupeHeight;
            }
            foreach (var p in current.Pedestrians)
            {
                var proxy = target.Pedestrians[target.PedestrianCount++]; proxy.Id = p.Id;
                proxy.DistanceMillimeters = Mm(p.LongitudinalMeters); proxy.LateralMillimeters = Mm(p.LateralMeters); proxy.HeightMillimeters = Mm(p.HeightMeters);
                proxy.WalkingSpeedMillimetersPerSecond = Mm(p.WalkingSpeedMetersPerSecond); proxy.Mode = p.Mode; proxy.ModeAgeTicks = p.StateTicks;
                proxy.IsCrossing = p.IsCrossing; proxy.FacingSide = p.FacingSide;
                PedestrianCheckpoints.RestorePredictionContext(proxy, pedestrianContexts[p.Id]);
            }
        }
        private static int Mm(float value) => (int)Math.Round(value * 1000, MidpointRounding.AwayFromZero);
        private static int Clamp(int value, int min, int max) => Math.Max(min, Math.Min(max, value));
    }
}
