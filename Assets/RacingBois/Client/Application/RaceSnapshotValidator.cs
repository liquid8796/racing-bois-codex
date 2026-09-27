using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

namespace RacingBois.Client.Application
{
    internal static class RaceSnapshotValidator
    {
        public static void Validate(RaceSnapshotMessage snapshot, int localId, int sent, int previousAck)
        {
            Require(snapshot.tick >= 0 && snapshot.ackSequence >= previousAck && snapshot.ackSequence <= sent &&
                snapshot.level >= 0 && snapshot.level <= 4 && snapshot.courseIndex >= 0 && snapshot.courseIndex < CampaignCatalog.RouteCount &&
                snapshot.trackLengthMillimeters == TrackDefinition.ForCourse(snapshot.courseIndex, snapshot.level).LengthMillimeters,
                "Invalid race envelope");
            Require(snapshot.riders != null && snapshot.riders.Length > 0 && snapshot.riders.Length <= RaceProtocol.MaxRiders &&
                snapshot.traffic != null && snapshot.traffic.Length <= RaceProtocol.MaxTraffic &&
                snapshot.pedestrians != null && snapshot.pedestrians.Length <= RaceProtocol.MaxPedestrians &&
                snapshot.events != null && snapshot.events.Length <= RaceProtocol.MaxEvents, "Invalid race collection");
            var ids = new HashSet<int>(); bool found = false;
            foreach (var rider in snapshot.riders)
            {
                Require(rider != null && rider.id > 0 && ids.Add(rider.id), "Invalid rider identity");
                Require(Between(rider.bikeCatalogIndex, 0, BikeCatalog.Count - 1) && Between(rider.characterCatalogIndex, 0, CharacterCatalog.Count - 1), "Unknown content identity");
                Require(rider.kind >= (int)RiderKind.Player && rider.kind <= (int)RiderKind.Police &&
                    rider.mode >= (int)RiderMode.Riding && rider.mode <= (int)RiderMode.Finished &&
                    rider.weapon >= (int)WeaponKind.Fist && rider.weapon <= (int)WeaponKind.Kick &&
                    rider.attackWeapon >= (int)WeaponKind.Fist && rider.attackWeapon <= (int)WeaponKind.Kick, "Unknown race enum");
                Require(rider.kind == (int)RiderKind.Player ? Between(rider.id, 1, 999) :
                    rider.kind == (int)RiderKind.Opponent ? Between(rider.id, 1001, 1999) : rider.id == GameplayRules.PoliceId,
                    "Rider identity does not match actor namespace");
                Require(Distance(rider.distanceMillimeters, snapshot.trackLengthMillimeters) && Distance(rider.bikeDistanceMillimeters, snapshot.trackLengthMillimeters) &&
                    Between(rider.lateralMillimeters, -50000, 50000) && Between(rider.bikeLateralMillimeters, -50000, 50000) &&
                    Between(rider.speedMillimetersPerSecond, 0, BikeHandlingCatalog.GetAt(rider.bikeCatalogIndex).MaximumSpeedMillimetersPerSecond) && Between(rider.heightMillimeters, -1000000, 1000000) &&
                    Between(rider.bikeHeightMillimeters, -1000000, 1000000) && Between(rider.leanMillidegrees, -90000, 90000), "Invalid race position");
                Require(Between(rider.health, 0, GameplayRules.InitialHealth) && Between(rider.bikeCondition, 0, GameplayRules.InitialBikeCondition) &&
                    Between(rider.strength, 0, 1000) && Between(rider.rank, 0, RaceProtocol.MaxRiders) &&
                    (rider.mode == (int)RiderMode.Busted ? rider.reward == -400 * (snapshot.level + 1) : Between(rider.reward, 0, 100000)) &&
                    Between(rider.attackSide, -1, 1) && rider.attackAgeTicks >= 0 && rider.modeAgeTicks >= 0 &&
                    Between(rider.gear, 0, 7) && rider.finishTick >= -1 && rider.finishTick <= snapshot.tick,
                    "Invalid race status");
                if (rider.id == localId) { Require(rider.kind == (int)RiderKind.Player, "Wrong local rider kind"); found = true; }
            }
            Require(found, "Local rider absent");
            foreach (var vehicle in snapshot.traffic)
                Require(vehicle != null && Between(vehicle.id, 3001, 3999) && ids.Add(vehicle.id) && Between(vehicle.kind, 0, 1) &&
                    Distance(vehicle.distanceMillimeters, snapshot.trackLengthMillimeters) && Between(vehicle.lateralMillimeters, -50000, 50000) &&
                    Between(vehicle.speedMillimetersPerSecond, -100000, 100000) && Between(vehicle.halfLengthMillimeters, 1, 15000) &&
                    Between(vehicle.halfWidthMillimeters, 1, 5000) && Between(vehicle.heightMillimeters, 1, 6000), "Invalid traffic");
            foreach (var person in snapshot.pedestrians)
                Require(person != null && Between(person.id, 4001, 4999) && ids.Add(person.id) &&
                    Distance(person.distanceMillimeters, snapshot.trackLengthMillimeters) && Between(person.lateralMillimeters, -50000, 50000) &&
                    person.heightMillimeters == 0 && Between(person.walkingSpeedMillimetersPerSecond, -10000, 10000) &&
                    person.mode >= (int)PedestrianMode.Waiting && person.mode <= (int)PedestrianMode.Stumbled &&
                    person.stateTicks >= 0 && (person.facingSide == -1 || person.facingSide == 1), "Invalid pedestrian");
            long previousEvent = 0;
            foreach (var item in snapshot.events)
            {
                Require(item != null && item.id > previousEvent && item.tick >= 0 && item.tick <= snapshot.tick &&
                    item.kind >= (int)RaceEventKind.Attack && item.kind <= (int)RaceEventKind.PedestrianRecovered &&
                    item.sourceId >= 0 && item.targetId >= 0 && Between(item.value, -1000000, 1000000), "Invalid event");
                previousEvent = item.id;
            }
        }
        // Traffic may remain 140 m behind the rearmost starting rider before despawning.
        private static bool Distance(long value, long length) => value >= -250000 && value <= length + 500000;
        private static bool Between(int value, int min, int max) => value >= min && value <= max;
        private static void Require(bool condition, string reason) { if (!condition) throw new InvalidOperationException(reason); }
    }
}
