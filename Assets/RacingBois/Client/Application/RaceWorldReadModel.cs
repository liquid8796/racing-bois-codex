using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Client.Application
{
    public readonly struct RaceRiderReadModel
    {
        public int BikeCatalogIndex { get; }
        public int CharacterCatalogIndex { get; }
        public int Id { get; }
        public RiderKind Kind { get; }
        public RiderMode Mode { get; }
        public WeaponKind Weapon { get; }
        public WeaponKind AttackWeapon { get; }
        public float LongitudinalMeters { get; }
        public float LateralMeters { get; }
        public float SpeedMetersPerSecond { get; }
        public float HeightMeters { get; }
        public float LeanDegrees { get; }
        public float BikeLongitudinalMeters { get; }
        public float BikeLateralMeters { get; }
        public float BikeHeightMeters { get; }
        public int Health { get; }
        public int MaxHealth { get; }
        public int BikeCondition { get; }
        public int MaxBikeCondition { get; }
        public int Strength { get; }
        public int Rank { get; }
        public long FinishTick { get; }
        public int Reward { get; }
        public bool Qualified { get; }
        public int AttackSide { get; }
        public int AttackTicksRemaining { get; }
        public int AttackAgeTicks { get; }
        public int StateTicks { get; }
        public int ModeAgeTicks { get { return StateTicks; } }
        public int Gear { get; }

        internal RaceRiderReadModel(int id, RiderKind kind, RiderMode mode, WeaponKind weapon, WeaponKind attackWeapon,
            float longitudinal, float lateral, float speed, float height, float lean,
            float bikeLongitudinal, float bikeLateral, float bikeHeight, int health, int maxHealth, int bikeCondition,
            int maxBikeCondition, int strength, int rank, long finishTick, int reward, bool qualified,
            int attackSide, int attackAgeTicks, int stateTicks, int gear, int bikeCatalogIndex = 0, int characterCatalogIndex = 0)
        {
            BikeCatalogIndex = bikeCatalogIndex; CharacterCatalogIndex = characterCatalogIndex;
            Id = id; Kind = kind; Mode = mode; Weapon = weapon; AttackWeapon = attackWeapon;
            LongitudinalMeters = longitudinal; LateralMeters = lateral; SpeedMetersPerSecond = speed;
            HeightMeters = height; LeanDegrees = lean;
            BikeLongitudinalMeters = bikeLongitudinal; BikeLateralMeters = bikeLateral; BikeHeightMeters = bikeHeight;
            Health = health; MaxHealth = maxHealth; BikeCondition = bikeCondition; MaxBikeCondition = maxBikeCondition;
            Strength = strength; Rank = rank; FinishTick = finishTick; Reward = reward; Qualified = qualified;
            AttackSide = attackSide; AttackAgeTicks = attackAgeTicks;
            AttackTicksRemaining = mode == RiderMode.Attacking ? Math.Max(0, GameplayRules.AttackDurationTicks - attackAgeTicks) : 0;
            StateTicks = stateTicks; Gear = gear;
        }
    }

    public readonly struct RaceTrafficReadModel
    {
        public int Id { get; }
        public int Kind { get; }
        public bool Oncoming { get { return Kind == 1; } }
        public bool IsVan { get { return VehicleDimensions.IsVan(Id); } }
        public float LongitudinalMeters { get; }
        public float LateralMeters { get; }
        public float SpeedMetersPerSecond { get; }
        public float HalfLengthMeters { get; }
        public float HalfWidthMeters { get; }
        public float HeightMeters { get; }
        internal RaceTrafficReadModel(int id, int kind, float longitudinal, float lateral, float speed, float halfLength, float halfWidth, float height)
        {
            Id = id; Kind = kind; LongitudinalMeters = longitudinal; LateralMeters = lateral;
            SpeedMetersPerSecond = speed; HalfLengthMeters = halfLength; HalfWidthMeters = halfWidth; HeightMeters = height;
        }
    }

    public readonly struct RaceEventReadModel
    {
        public long Id { get; }
        public long Tick { get; }
        public RaceEventKind Kind { get; }
        public int SourceId { get; }
        public int TargetId { get; }
        public int Value { get; }
        internal RaceEventReadModel(long id, long tick, RaceEventKind kind, int sourceId, int targetId, int value)
        { Id = id; Tick = tick; Kind = kind; SourceId = sourceId; TargetId = targetId; Value = value; }
    }

    public sealed class RacePedestrianReadModel
    {
        public int Id { get; }
        public float LongitudinalMeters { get; }
        public float LateralMeters { get; }
        public float HeightMeters { get; }
        public float WalkingSpeedMetersPerSecond { get; }
        public bool IsCrossing { get; }
        public float LateralSpeedMetersPerSecond { get { return IsCrossing ? WalkingSpeedMetersPerSecond : 0; } }
        public float LongitudinalSpeedMetersPerSecond { get { return IsCrossing ? 0 : WalkingSpeedMetersPerSecond; } }
        public PedestrianMode Mode { get; }
        public int StateTicks { get; }
        public int ModeAgeTicks { get { return StateTicks; } }
        public int FacingSide { get; }
        internal RacePedestrianReadModel(int id, float longitudinal, float lateral, float height, float walkingSpeed,
            PedestrianMode mode, int stateTicks, int facingSide, bool isCrossing)
        {
            Id = id; LongitudinalMeters = longitudinal; LateralMeters = lateral; HeightMeters = height;
            WalkingSpeedMetersPerSecond = walkingSpeed; Mode = mode; StateTicks = stateTicks; FacingSide = facingSide; IsCrossing = isCrossing;
        }
    }

    /// <summary>Presentation never receives mutable simulation state or a wire DTO.</summary>
    public sealed class RaceWorldReadModel
    {
        public long Tick { get; }
        public int AcknowledgedInputSequence { get; }
        public float TrackLengthMeters { get; }
        public int Level { get; }
        public int CourseIndex { get; }
        public TrackDefinition Track => TrackDefinition.ForCourse(CourseIndex, Level);
        public IReadOnlyList<RaceRiderReadModel> Riders { get; }
        public IReadOnlyList<RaceTrafficReadModel> Traffic { get; }
        public IReadOnlyList<RaceEventReadModel> Events { get; }
        public IReadOnlyList<RacePedestrianReadModel> Pedestrians { get; }
        public int RiderCount { get { return Riders.Count; } }
        internal RaceWorldReadModel(long tick, int ack, float trackLength, int level,
            RaceRiderReadModel[] riders, RaceTrafficReadModel[] traffic, RaceEventReadModel[] events,
            RacePedestrianReadModel[] pedestrians = null, int courseIndex = 0)
        {
            Tick = tick; AcknowledgedInputSequence = ack; TrackLengthMeters = trackLength; Level = level; CourseIndex = courseIndex;
            Riders = Array.AsReadOnly((RaceRiderReadModel[])riders.Clone());
            Traffic = Array.AsReadOnly((RaceTrafficReadModel[])traffic.Clone());
            Events = Array.AsReadOnly((RaceEventReadModel[])events.Clone());
            Pedestrians = Array.AsReadOnly(pedestrians == null ? Array.Empty<RacePedestrianReadModel>() : (RacePedestrianReadModel[])pedestrians.Clone());
        }
    }
}
