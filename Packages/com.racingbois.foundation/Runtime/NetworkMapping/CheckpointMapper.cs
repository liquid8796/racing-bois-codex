using System;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.NetworkMapping
{
    /// <summary>One conversion used by server and client; neither the simulation nor protocol depends on the other.</summary>
    public static class CheckpointMapper
    {
        public static OwnPredictionState CaptureDto(RaceRider rider, long tick) => ToDto(RiderCheckpoints.Capture(rider, tick));
        public static OwnPredictionState ToDto(RiderCheckpoint checkpoint)
        {
            var d = checkpoint.Data;
            return new OwnPredictionState
            {
                tick = d.Tick, rider = new RaceEntitySnapshot
                {
                    id = d.Id, bikeCatalogIndex = d.BikeCatalogIndex, characterCatalogIndex = d.CharacterCatalogIndex, kind = (int)d.Kind, mode = (int)d.Mode, weapon = (int)d.Weapon, attackWeapon = (int)d.AttackWeapon,
                    distanceMillimeters = d.DistanceMillimeters, bikeDistanceMillimeters = d.BikeDistanceMillimeters, finishTick = d.FinishTick,
                    lateralMillimeters = d.LateralMillimeters, bikeLateralMillimeters = d.BikeLateralMillimeters,
                    heightMillimeters = d.HeightMillimeters, bikeHeightMillimeters = d.BikeHeightMillimeters,
                    speedMillimetersPerSecond = d.SpeedMillimetersPerSecond, leanMillidegrees = d.LeanMillidegrees,
                    health = d.Health, bikeCondition = d.BikeCondition, strength = d.Strength, rank = d.Rank, reward = d.Reward,
                    attackSide = d.AttackSide, attackAgeTicks = d.AttackAgeTicks, modeAgeTicks = d.ModeAgeTicks, gear = d.Gear, qualified = d.Qualified
                },
                endurance = d.Endurance, distanceRemainder = d.DistanceRemainder, lateralRemainder = d.LateralRemainder,
                speedRemainder = d.SpeedRemainder, verticalRemainder = d.VerticalRemainder, verticalSpeed = d.VerticalSpeed,
                steeringPermille = d.SteeringPermille, bikeSpeed = d.BikeSpeed, recoveryTicks = d.RecoveryTicks, policeContactTicks = d.PoliceContactTicks,
                lastInputTick = d.LastInputTick, nextAttackTick = d.NextAttackTick, collisionUntilTick = d.CollisionUntilTick,
                hitUntilTick = d.HitUntilTick, stealUntilTick = d.StealUntilTick, attackResolved = d.AttackResolved,
                appliedInput = new InputValues { throttlePermille = d.Input.ThrottlePermille, brakePermille = d.Input.BrakePermille,
                    steerPermille = d.Input.SteerPermille, attackSide = d.Input.AttackSide, kick = d.Input.Kick }
            };
        }
        public static RiderCheckpoint ToCheckpoint(OwnPredictionState state)
        {
            Validate(state); var r = state.rider;
            return new RiderCheckpoint(new RiderCheckpointData
            {
                Tick = state.tick, Id = r.id, BikeCatalogIndex = r.bikeCatalogIndex, CharacterCatalogIndex = r.characterCatalogIndex, Kind = (RiderKind)r.kind, Mode = (RiderMode)r.mode,
                Weapon = (WeaponKind)r.weapon, AttackWeapon = (WeaponKind)r.attackWeapon,
                DistanceMillimeters = r.distanceMillimeters, BikeDistanceMillimeters = r.bikeDistanceMillimeters, FinishTick = r.finishTick,
                LateralMillimeters = r.lateralMillimeters, BikeLateralMillimeters = r.bikeLateralMillimeters,
                HeightMillimeters = r.heightMillimeters, BikeHeightMillimeters = r.bikeHeightMillimeters,
                SpeedMillimetersPerSecond = r.speedMillimetersPerSecond, LeanMillidegrees = r.leanMillidegrees,
                Health = r.health, BikeCondition = r.bikeCondition, Strength = r.strength, Rank = r.rank, Reward = r.reward,
                AttackSide = r.attackSide, AttackAgeTicks = r.attackAgeTicks, ModeAgeTicks = r.modeAgeTicks, Gear = r.gear, Qualified = r.qualified,
                Endurance = state.endurance, DistanceRemainder = state.distanceRemainder, LateralRemainder = state.lateralRemainder,
                SpeedRemainder = state.speedRemainder, VerticalRemainder = state.verticalRemainder, VerticalSpeed = state.verticalSpeed,
                SteeringPermille = state.steeringPermille, BikeSpeed = state.bikeSpeed, RecoveryTicks = state.recoveryTicks, PoliceContactTicks = state.policeContactTicks,
                LastInputTick = state.lastInputTick, NextAttackTick = state.nextAttackTick, CollisionUntilTick = state.collisionUntilTick,
                HitUntilTick = state.hitUntilTick, StealUntilTick = state.stealUntilTick, AttackResolved = state.attackResolved,
                Input = ToInput(state.appliedInput)
            });
        }
        public static RaceInput ToInput(InputValues input)
        {
            ValidateInput(input); return new RaceInput(input.throttlePermille, input.brakePermille, input.steerPermille, input.attackSide, input.kick);
        }
        public static void ValidateInput(InputValues input)
        {
            Require(input != null && Between(input.throttlePermille, 0, 1000) && Between(input.brakePermille, 0, 1000) &&
                Between(input.steerPermille, -1000, 1000) && Between(input.attackSide, -1, 1));
        }
        public static void Validate(OwnPredictionState s)
        {
            Require(s != null && s.rider != null && s.tick >= 0 && s.tick < int.MaxValue); var r = s.rider;
            Require(Between(r.id, 1, 999) && r.kind == (int)RiderKind.Player && Between(r.mode, 0, (int)RiderMode.Finished) &&
                Between(r.bikeCatalogIndex, 0, BikeCatalog.Count - 1) && Between(r.characterCatalogIndex, 0, CharacterCatalog.Count - 1) && Between(r.weapon, 0, 3) && Between(r.attackWeapon, 0, 3));
            long end = TrackDefinition.MaximumLengthMillimeters + 500000;
            Require(Between(r.distanceMillimeters, -250000, end) && Between(r.bikeDistanceMillimeters, -250000, end) &&
                Between(r.lateralMillimeters, -50000, 50000) && Between(r.bikeLateralMillimeters, -50000, 50000) &&
                Between(r.heightMillimeters, 0, 1000000) && Between(r.bikeHeightMillimeters, 0, 1000000) &&
                Between(r.speedMillimetersPerSecond, 0, BikeHandlingCatalog.GetAt(r.bikeCatalogIndex).MaximumSpeedMillimetersPerSecond) && Between(r.leanMillidegrees, -90000, 90000));
            Require(Between(r.health, 0, GameplayRules.InitialHealth) && Between(r.bikeCondition, 0, 100) && Between(r.strength, 0, 1000) &&
                Between(s.endurance, 0, 1000) && Between(r.rank, 0, 16) && Between(r.gear, 0, 7) && Between(r.attackSide, -1, 1) &&
                Between(r.attackAgeTicks, 0, GameplayRules.AttackDurationTicks) && Between(r.modeAgeTicks, 0, s.tick + 1) && Between(r.finishTick, -1, s.tick));
            Require(r.mode == (int)RiderMode.Busted ? Between(r.reward, -2000, 0) : Between(r.reward, 0, 100000));
            Require(Between(s.distanceRemainder, -59, 59) && Between(s.lateralRemainder, -59, 59) && Between(s.speedRemainder, -59, 59) &&
                Between(s.verticalRemainder, -59, 59) && Between(s.verticalSpeed, -1000000, 1000000) && Between(s.steeringPermille, -1000, 1000) &&
                Between(s.bikeSpeed, 0, 100000) && Between(s.recoveryTicks, 0, 1202) && Between(s.policeContactTicks, 0, int.MaxValue));
            Require(Between(s.lastInputTick, 0, s.tick) && Between(s.nextAttackTick, 0, s.tick + 120) &&
                Between(s.collisionUntilTick, 0, s.tick + 120) && Between(s.hitUntilTick, -1, s.tick + 120) && Between(s.stealUntilTick, -1, s.tick + 300));
            ValidateInput(s.appliedInput);
        }
        private static bool Between(long value, long min, long max) => value >= min && value <= max;
        private static void Require(bool valid) { if (!valid) throw new ArgumentException("Invalid authoritative rider checkpoint."); }
    }
}
