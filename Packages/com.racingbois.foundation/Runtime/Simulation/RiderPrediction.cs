using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Value-only checkpoint construction data. No mutable reference survives the immutable checkpoint copy.</summary>
    public struct RiderCheckpointData
    {
        public long Tick, DistanceMillimeters, BikeDistanceMillimeters, FinishTick;
        public int Id, BikeCatalogIndex, CharacterCatalogIndex; public RiderKind Kind; public RiderMode Mode; public WeaponKind Weapon, AttackWeapon;
        public int LateralMillimeters, BikeLateralMillimeters, HeightMillimeters, BikeHeightMillimeters;
        public int SpeedMillimetersPerSecond, LeanMillidegrees, Health, BikeCondition, Strength, Endurance;
        public int Rank, Reward, AttackSide, AttackAgeTicks, ModeAgeTicks, Gear;
        public bool Qualified, AttackResolved;
        public long HitUntilTick, StealUntilTick, LastInputTick, NextAttackTick, CollisionUntilTick;
        public int DistanceRemainder, LateralRemainder, SpeedRemainder, VerticalRemainder;
        public int VerticalSpeed, SteeringPermille, BikeSpeed, RecoveryTicks, PoliceContactTicks;
        public RaceInput Input;
    }
    public readonly struct RiderCheckpoint
    {
        private readonly RiderCheckpointData data;
        public RiderCheckpointData Data => data;
        public long Tick => data.Tick;
        public RiderCheckpoint(RiderCheckpointData data) { this.data = data; }
    }
    public static class RiderCheckpoints
    {
        public static RiderCheckpoint Capture(RaceRider r, long tick)
        {
            if (r == null) throw new ArgumentNullException(nameof(r));
            return new RiderCheckpoint(new RiderCheckpointData
            {
                Tick = tick, Id = r.Id, BikeCatalogIndex = r.BikeCatalogIndex, CharacterCatalogIndex = r.CharacterCatalogIndex, Kind = r.Kind, Mode = r.Mode, Weapon = r.Weapon, AttackWeapon = r.AttackWeapon,
                DistanceMillimeters = r.DistanceMillimeters, BikeDistanceMillimeters = r.BikeDistanceMillimeters, FinishTick = r.FinishTick,
                LateralMillimeters = r.LateralMillimeters, BikeLateralMillimeters = r.BikeLateralMillimeters,
                HeightMillimeters = r.HeightMillimeters, BikeHeightMillimeters = r.BikeHeightMillimeters,
                SpeedMillimetersPerSecond = r.SpeedMillimetersPerSecond, LeanMillidegrees = r.LeanMillidegrees,
                Health = r.Health, BikeCondition = r.BikeCondition, Strength = r.Strength, Endurance = r.Endurance,
                Rank = r.Rank, Reward = r.Reward, AttackSide = r.AttackSide, AttackAgeTicks = r.AttackAgeTicks, ModeAgeTicks = r.ModeAgeTicks,
                Gear = r.Gear, Qualified = r.Qualified, AttackResolved = r.AttackResolved,
                HitUntilTick = r.HitUntilTick, StealUntilTick = r.StealUntilTick, LastInputTick = r.LastInputTick,
                NextAttackTick = r.NextAttackTick, CollisionUntilTick = r.CollisionUntilTick,
                DistanceRemainder = r.DistanceRemainder, LateralRemainder = r.LateralRemainder, SpeedRemainder = r.SpeedRemainder,
                VerticalRemainder = r.VerticalRemainder, VerticalSpeed = r.VerticalSpeed, SteeringPermille = r.SteeringPermille,
                BikeSpeed = r.BikeSpeed, RecoveryTicks = r.RecoveryTicks, PoliceContactTicks = r.PoliceContactTicks, Input = r.Input
            });
        }
        public static void Restore(RaceRider r, RiderCheckpoint checkpoint)
        {
            if (r == null) throw new ArgumentNullException(nameof(r)); var d = checkpoint.Data;
            r.Id = d.Id; r.BikeCatalogIndex = d.BikeCatalogIndex; r.CharacterCatalogIndex = d.CharacterCatalogIndex; r.Kind = d.Kind; r.Mode = d.Mode; r.Weapon = d.Weapon; r.AttackWeapon = d.AttackWeapon;
            r.DistanceMillimeters = d.DistanceMillimeters; r.BikeDistanceMillimeters = d.BikeDistanceMillimeters; r.FinishTick = d.FinishTick;
            r.LateralMillimeters = d.LateralMillimeters; r.BikeLateralMillimeters = d.BikeLateralMillimeters;
            r.HeightMillimeters = d.HeightMillimeters; r.BikeHeightMillimeters = d.BikeHeightMillimeters;
            r.SpeedMillimetersPerSecond = d.SpeedMillimetersPerSecond; r.LeanMillidegrees = d.LeanMillidegrees;
            r.Health = d.Health; r.BikeCondition = d.BikeCondition; r.Strength = d.Strength; r.Endurance = d.Endurance;
            r.Rank = d.Rank; r.Reward = d.Reward; r.AttackSide = d.AttackSide; r.AttackAgeTicks = d.AttackAgeTicks;
            r.ModeAgeTicks = d.ModeAgeTicks; r.Gear = d.Gear; r.Qualified = d.Qualified; r.AttackResolved = d.AttackResolved;
            r.HitUntilTick = d.HitUntilTick; r.StealUntilTick = d.StealUntilTick; r.LastInputTick = d.LastInputTick;
            r.NextAttackTick = d.NextAttackTick; r.CollisionUntilTick = d.CollisionUntilTick;
            r.DistanceRemainder = d.DistanceRemainder; r.LateralRemainder = d.LateralRemainder; r.SpeedRemainder = d.SpeedRemainder;
            r.VerticalRemainder = d.VerticalRemainder; r.VerticalSpeed = d.VerticalSpeed; r.SteeringPermille = d.SteeringPermille;
            r.BikeSpeed = d.BikeSpeed; r.RecoveryTicks = d.RecoveryTicks; r.PoliceContactTicks = d.PoliceContactTicks; r.Input = d.Input;
            SetPrevious(r);
        }
        internal static void SetPrevious(RaceRider r)
        {
            r.PreviousDistance = r.DistanceMillimeters; r.PreviousLateral = r.LateralMillimeters; r.PreviousHeight = r.HeightMillimeters;
            r.PreviousBikeDistance = r.BikeDistanceMillimeters; r.PreviousBikeLateral = r.BikeLateralMillimeters;
        }
    }
    /// <summary>Isolated own locomotion/contact-pose prediction; no events, damage claims, finish or rewards are published.</summary>
    public sealed class RiderPredictor
    {
        private readonly GameplayWorld sandbox;
        private readonly RaceRider rider = new RaceRider();
        private readonly RaceRider[] proxyRiders = new RaceRider[GameplayRules.MaxRiders - 1];
        private readonly bool[] proxyMotionTransitionCreated = new bool[GameplayRules.MaxRiders - 1];
        private PredictionNeighbors neighbors;
        private long baseTick;
        private readonly int[] proxyVerticalVelocity = new int[GameplayRules.MaxRiders - 1];
        public RiderCheckpoint Checkpoint => RiderCheckpoints.Capture(rider, sandbox.Tick);
        public RiderPredictor(int level, int courseIndex = 0)
        {
            sandbox = new GameplayWorld(0, level, courseIndex); sandbox.Riders[0] = rider;
            for (int i = 0; i < proxyRiders.Length; i++) proxyRiders[i] = new RaceRider();
        }
        public void SetNeighbors(PredictionNeighbors value)
        {
            if (value != null && (value.RiderCount < 0 || value.RiderCount > value.Riders.Length || value.TrafficCount < 0 ||
                value.TrafficCount > value.Traffic.Length || value.PedestrianCount < 0 || value.PedestrianCount > value.Pedestrians.Length))
                throw new ArgumentException("Prediction proxy count exceeds capacity.");
            neighbors = value;
        }
        public void Restore(RiderCheckpoint checkpoint)
        {
            if (checkpoint.Data.Kind != RiderKind.Player || checkpoint.Tick < 0) throw new ArgumentException("Prediction requires a player checkpoint.");
            RiderCheckpoints.Restore(rider, checkpoint); sandbox.Tick = baseTick = checkpoint.Tick; sandbox.EventCount = 0;
            sandbox.Riders[0] = rider; sandbox.RiderCount = 1; sandbox.TrafficCount = sandbox.PedestrianCount = 0;
            if (neighbors == null) return;
            for (int i = 0; i < neighbors.RiderCount; i++)
            {
                RiderCheckpoints.Restore(proxyRiders[i], RiderCheckpoints.Capture(neighbors.Riders[i], checkpoint.Tick));
                proxyVerticalVelocity[i] = neighbors.VerticalVelocity[i]; proxyMotionTransitionCreated[i] = false; sandbox.Riders[sandbox.RiderCount++] = proxyRiders[i];
            }
            // Authority visits riders in ascending ID order. Earlier pairs can
            // apply protection before a later rider's traffic/pedestrian pass.
            // Keep stable proxy references for kinematics; sort this bounded
            // contact roster once on restore without allocating per tick.
            for (int i = 1; i < sandbox.RiderCount; i++)
            {
                var value = sandbox.Riders[i]; int at = i;
                while (at > 0 && sandbox.Riders[at - 1].Id > value.Id)
                { sandbox.Riders[at] = sandbox.Riders[at - 1]; at--; }
                sandbox.Riders[at] = value;
            }
            for (int i = 0; i < neighbors.TrafficCount; i++)
            {
                var a = neighbors.Traffic[i]; var b = sandbox.Traffic[i];
                b.Id = a.Id; b.DistanceMillimeters = b.PreviousDistance = a.DistanceMillimeters; b.LateralMillimeters = a.LateralMillimeters;
                b.SpeedMillimetersPerSecond = a.SpeedMillimetersPerSecond; b.WidthMillimeters = a.WidthMillimeters;
                b.LengthMillimeters = a.LengthMillimeters; b.HeightMillimeters = a.HeightMillimeters; b.Oncoming = a.Oncoming;
                b.DistanceRemainder = 0; b.Active = true; sandbox.TrafficCount++;
            }
            for (int i = 0; i < neighbors.PedestrianCount; i++)
            {
                var a = neighbors.Pedestrians[i]; var b = sandbox.Pedestrians[i];
                b.Id = a.Id; b.DistanceMillimeters = b.PreviousDistance = a.DistanceMillimeters;
                b.LateralMillimeters = b.PreviousLateral = a.LateralMillimeters; b.HeightMillimeters = a.HeightMillimeters;
                b.Mode = a.Mode; b.ModeAgeTicks = a.ModeAgeTicks; b.FacingSide = a.FacingSide; b.IsCrossing = a.IsCrossing;
                b.WalkingSpeedMillimetersPerSecond = a.WalkingSpeedMillimetersPerSecond;
                b.WaitTicks = a.WaitTicks; b.DesiredWalkingSpeed = a.DesiredWalkingSpeed; b.MotionRemainder = a.MotionRemainder; sandbox.PedestrianCount++;
            }
        }
        public RiderCheckpoint Advance(long targetTick, RaceInput input)
        {
            if (targetTick != sandbox.Tick + 1) throw new InvalidOperationException("Prediction must advance exactly one tick.");
            RiderCheckpoints.SetPrevious(rider); rider.Input = input; rider.LastInputTick = sandbox.Tick;
            sandbox.Tick = targetTick; sandbox.EventCount = 0; DrivingDynamics.Step(sandbox, rider);
            AdvanceNeighbors(); DrivingDynamics.ResolveContacts(sandbox);
            CombatResolver.ForecastKnownAttacks(sandbox, rider.Id);
            if (neighbors != null && sandbox.Tick - baseTick <= PredictionNeighbors.MaximumAgeTicks)
                for (int i = 0; i < neighbors.RiderCount; i++)
                    if (GameplayRules.CanDrive(neighbors.Riders[i].Mode) && !GameplayRules.CanDrive(proxyRiders[i].Mode))
                        proxyMotionTransitionCreated[i] = true;
            sandbox.EventCount = 0; return Checkpoint;
        }
        /// <summary>Pose-only value for a transition created by this bounded forecast at exactly the requested tick.</summary>
        public bool TryGetForecastedNeighborMotion(int id, long sampleTick, out RiderCheckpoint checkpoint)
        {
            checkpoint = default;
            if (neighbors == null || sampleTick != sandbox.Tick || sampleTick - baseTick > PredictionNeighbors.MaximumAgeTicks) return false;
            for (int i = 0; i < neighbors.RiderCount; i++)
                if (proxyMotionTransitionCreated[i] && proxyRiders[i].Id == id)
                { checkpoint = RiderCheckpoints.Capture(proxyRiders[i], sampleTick); return true; }
            return false;
        }
        private void AdvanceNeighbors()
        {
            if (neighbors == null) return;
            if (sandbox.Tick - baseTick > PredictionNeighbors.MaximumAgeTicks)
            { sandbox.Riders[0] = rider; sandbox.RiderCount = 1; sandbox.TrafficCount = sandbox.PedestrianCount = 0; return; }
            for (int i = 0; i < neighbors.RiderCount; i++)
            {
                var r = proxyRiders[i]; RiderCheckpoints.SetPrevious(r);
                if (!GameplayRules.CanDrive(r.Mode))
                {
                    // Only a crash created inside this sandbox has its complete
                    // recovery initialization. Old non-driving snapshot proxies
                    // lack those private fields and are not claimed exact.
                    if (proxyMotionTransitionCreated[i]) DrivingDynamics.Step(sandbox, r);
                    continue;
                }
                r.ModeAgeTicks++; RiderModeClock.AdvanceDrivingMode(r);
                r.SpeedRemainder += neighbors.Acceleration[i];
                r.SpeedMillimetersPerSecond = RaceSimulation.Clamp(r.SpeedMillimetersPerSecond + r.SpeedRemainder / 60, 0, BikeHandlingCatalog.GetAt(r.BikeCatalogIndex).MaximumSpeedMillimetersPerSecond);
                r.SpeedRemainder %= 60; r.DistanceRemainder += r.SpeedMillimetersPerSecond;
                r.DistanceMillimeters += r.DistanceRemainder / 60; r.DistanceRemainder %= 60;
                r.LateralRemainder += neighbors.LateralVelocity[i];
                r.LateralMillimeters = RaceSimulation.Clamp(r.LateralMillimeters + r.LateralRemainder / 60, -9300, 9300); r.LateralRemainder %= 60;
                r.HeightMillimeters = Math.Max(0, r.HeightMillimeters + proxyVerticalVelocity[i] / 60);
                if (r.Mode == RiderMode.Airborne) proxyVerticalVelocity[i] -= 164;
                r.BikeDistanceMillimeters = r.DistanceMillimeters; r.BikeLateralMillimeters = r.LateralMillimeters; r.BikeHeightMillimeters = r.HeightMillimeters;
            }
            for (int i = 0; i < sandbox.TrafficCount; i++)
            { var t = sandbox.Traffic[i]; t.PreviousDistance = t.DistanceMillimeters; t.DistanceRemainder += t.SpeedMillimetersPerSecond; t.DistanceMillimeters += t.DistanceRemainder / 60; t.DistanceRemainder %= 60; }
            for (int i = 0; i < sandbox.PedestrianCount; i++)
            {
                var p = sandbox.Pedestrians[i]; p.PreviousDistance = p.DistanceMillimeters; p.PreviousLateral = p.LateralMillimeters;
                p.ModeAgeTicks++;
                var ended = PedestrianMotion.AdvanceKnownState(p, sandbox.Track.RoadHalfWidthMillimeters + 1200);
                // The next random wait is chosen later by authority. Its known
                // minimum already exceeds the remaining30tick proxy horizon;
                // use that lower bound without drawing RNG or claiming events.
                if (ended == PedestrianWalkEnd.Crossing) p.WaitTicks = 180;
                else if (ended == PedestrianWalkEnd.AlongRoad) p.WaitTicks = 120;
            }
        }
    }
}
