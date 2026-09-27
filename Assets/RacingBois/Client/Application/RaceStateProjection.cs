using System;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    internal static class RaceStateProjection
    {
        public static RaceRiderReadModel Rider(RaceRider rider) => new RaceRiderReadModel(rider.Id, rider.Kind,
            rider.Mode, rider.Weapon, rider.AttackWeapon, rider.DistanceMillimeters / 1000f, rider.LateralMillimeters / 1000f,
            rider.SpeedMillimetersPerSecond / 1000f, rider.HeightMillimeters / 1000f, rider.LeanMillidegrees / 1000f,
            rider.BikeDistanceMillimeters / 1000f, rider.BikeLateralMillimeters / 1000f, rider.BikeHeightMillimeters / 1000f,
            rider.Health, GameplayRules.InitialHealth, rider.BikeCondition, GameplayRules.InitialBikeCondition,
            rider.Strength, rider.Rank, rider.FinishTick, rider.Reward, rider.Qualified, rider.AttackSide,
            rider.AttackAgeTicks, rider.ModeAgeTicks, rider.Gear, rider.BikeCatalogIndex, rider.CharacterCatalogIndex);

        public static RaceRiderReadModel Rider(RaceEntitySnapshot rider) => new RaceRiderReadModel(rider.id,
            (RiderKind)rider.kind, (RiderMode)rider.mode, (WeaponKind)rider.weapon, (WeaponKind)rider.attackWeapon,
            rider.distanceMillimeters / 1000f, rider.lateralMillimeters / 1000f, rider.speedMillimetersPerSecond / 1000f,
            rider.heightMillimeters / 1000f, rider.leanMillidegrees / 1000f,
            rider.bikeDistanceMillimeters / 1000f, rider.bikeLateralMillimeters / 1000f, rider.bikeHeightMillimeters / 1000f,
            rider.health, GameplayRules.InitialHealth, rider.bikeCondition, GameplayRules.InitialBikeCondition,
            rider.strength, rider.rank, rider.finishTick, rider.reward, rider.qualified,
            rider.attackSide, rider.attackAgeTicks, rider.modeAgeTicks, rider.gear, rider.bikeCatalogIndex, rider.characterCatalogIndex);

        public static RaceWorldReadModel World(GameplayWorld world, int ack, RaceEventReadModel[] events)
        {
            var riders = new RaceRiderReadModel[world.RiderCount];
            for (int i = 0; i < riders.Length; i++) riders[i] = Rider(world.Riders[i]);
            var traffic = new RaceTrafficReadModel[world.TrafficCount];
            for (int i = 0; i < traffic.Length; i++)
            {
                var item = world.Traffic[i];
                traffic[i] = new RaceTrafficReadModel(item.Id, item.Oncoming ? 1 : 0, item.DistanceMillimeters / 1000f,
                    item.LateralMillimeters / 1000f, (item.Oncoming ? -Math.Abs(item.SpeedMillimetersPerSecond) : Math.Abs(item.SpeedMillimetersPerSecond)) / 1000f,
                    item.LengthMillimeters / 2000f, item.WidthMillimeters / 2000f, item.HeightMillimeters / 1000f);
            }
            var pedestrians = new RacePedestrianReadModel[world.PedestrianCount];
            for (int i = 0; i < pedestrians.Length; i++)
            {
                var item = world.Pedestrians[i];
                pedestrians[i] = new RacePedestrianReadModel(item.Id, item.DistanceMillimeters / 1000f,
                    item.LateralMillimeters / 1000f, item.HeightMillimeters / 1000f, item.WalkingSpeedMillimetersPerSecond / 1000f,
                    item.Mode, item.ModeAgeTicks, item.FacingSide, item.IsCrossing);
            }
            return new RaceWorldReadModel(world.Tick, ack, world.Track.LengthMillimeters / 1000f,
                world.Level, riders, traffic, events, pedestrians, world.CourseIndex);
        }

        public static RaceWorldReadModel World(RaceSnapshotMessage snapshot)
        {
            var riders = new RaceRiderReadModel[snapshot.riders.Length];
            for (int i = 0; i < riders.Length; i++) riders[i] = Rider(snapshot.riders[i]);
            var traffic = new RaceTrafficReadModel[snapshot.traffic.Length];
            for (int i = 0; i < traffic.Length; i++)
            {
                var item = snapshot.traffic[i];
                traffic[i] = new RaceTrafficReadModel(item.id, item.kind, item.distanceMillimeters / 1000f,
                    item.lateralMillimeters / 1000f, (item.kind == 1 ? -Math.Abs(item.speedMillimetersPerSecond) : Math.Abs(item.speedMillimetersPerSecond)) / 1000f,
                    item.halfLengthMillimeters / 1000f, item.halfWidthMillimeters / 1000f, item.heightMillimeters / 1000f);
            }
            var events = new RaceEventReadModel[snapshot.events.Length];
            for (int i = 0; i < events.Length; i++)
            {
                var item = snapshot.events[i];
                events[i] = new RaceEventReadModel(item.id, item.tick, (RaceEventKind)item.kind, item.sourceId, item.targetId, item.value);
            }
            var pedestrians = new RacePedestrianReadModel[snapshot.pedestrians.Length];
            for (int i = 0; i < pedestrians.Length; i++)
            {
                var item = snapshot.pedestrians[i];
                pedestrians[i] = new RacePedestrianReadModel(item.id, item.distanceMillimeters / 1000f,
                    item.lateralMillimeters / 1000f, item.heightMillimeters / 1000f, item.walkingSpeedMillimetersPerSecond / 1000f,
                    (PedestrianMode)item.mode, item.stateTicks, item.facingSide, item.isCrossing);
            }
            return new RaceWorldReadModel(snapshot.tick, snapshot.ackSequence, snapshot.trackLengthMillimeters / 1000f,
                snapshot.level, riders, traffic, events, pedestrians, snapshot.courseIndex);
        }
    }
}
