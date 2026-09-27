using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    public readonly struct RaceInput
    {
        public readonly int ThrottlePermille, BrakePermille, SteerPermille, AttackSide;
        public readonly bool Kick;
        public RaceInput(int throttlePermille, int brakePermille, int steerPermille, int attackSide = 0, bool kick = false)
        {
            ThrottlePermille = Clamp(throttlePermille, 0, 1000); BrakePermille = Clamp(brakePermille, 0, 1000);
            SteerPermille = Clamp(steerPermille, -1000, 1000); AttackSide = Clamp(attackSide, -1, 1); Kick = kick;
        }
        private static int Clamp(int value, int min, int max) => value < min ? min : value > max ? max : value;
    }

    /// <summary>Owned by one simulation thread. Copy into snapshots; never expose to presentation.</summary>
    public sealed class RaceRider
    {
        public int Id;
        public int BikeCatalogIndex, CharacterCatalogIndex;
        public RiderKind Kind;
        public RiderMode Mode;
        public WeaponKind Weapon;
        public long DistanceMillimeters, BikeDistanceMillimeters, FinishTick = -1;
        public int LateralMillimeters, BikeLateralMillimeters, HeightMillimeters, BikeHeightMillimeters;
        public int SpeedMillimetersPerSecond, LeanMillidegrees, Health = GameplayRules.InitialHealth;
        public int BikeCondition = GameplayRules.InitialBikeCondition, Strength = 7, Endurance = GameplayRules.InitialEndurance;
        public int Rank, Reward, AttackSide, AttackAgeTicks, ModeAgeTicks, Gear = 1;
        public bool Qualified;
        public long HitUntilTick = -1, StealUntilTick = -1;
        public WeaponKind AttackWeapon;
        internal RaceInput Input;
        internal long PreviousDistance, PreviousBikeDistance;
        internal int PreviousLateral, PreviousHeight, PreviousBikeLateral;
        internal int DistanceRemainder, LateralRemainder, SpeedRemainder, VerticalRemainder;
        internal int VerticalSpeed, SteeringPermille, BikeSpeed, RecoveryTicks, PoliceContactTicks;
        internal long LastInputTick, NextAttackTick, CollisionUntilTick;
        internal int AiLane, AiDecisionTicks;
        internal bool AttackResolved;
    }

    public sealed class RaceTraffic
    {
        public int Id, LateralMillimeters, SpeedMillimetersPerSecond;
        public int WidthMillimeters = VehicleDimensions.CoupeWidth, LengthMillimeters = VehicleDimensions.CoupeLength, HeightMillimeters = VehicleDimensions.CoupeHeight;
        public long DistanceMillimeters;
        public bool Active, Oncoming;
        internal long PreviousDistance;
        internal int DistanceRemainder;
    }

    public readonly struct RaceEvent
    {
        public readonly long Id, Tick;
        public readonly RaceEventKind Kind;
        public readonly int ActorId, TargetId, Value;
        public RaceEvent(long id, long tick, RaceEventKind kind, int actorId, int targetId, int value)
        { Id = id; Tick = tick; Kind = kind; ActorId = actorId; TargetId = targetId; Value = value; }
    }

    public sealed class RacePedestrian
    {
        public int Id, LateralMillimeters, HeightMillimeters, WalkingSpeedMillimetersPerSecond, ModeAgeTicks, FacingSide = 1;
        public long DistanceMillimeters;
        public PedestrianMode Mode;
        public bool IsCrossing;
        internal long PreviousDistance;
        internal int PreviousLateral, MotionRemainder, WaitTicks = 120, DesiredWalkingSpeed = 1400;
    }

    public sealed class GameplayWorld
    {
        public readonly RaceRider[] Riders = new RaceRider[GameplayRules.MaxRiders];
        public readonly RaceTraffic[] Traffic = new RaceTraffic[GameplayRules.MaxTraffic];
        public readonly RacePedestrian[] Pedestrians = new RacePedestrian[GameplayRules.MaxPedestrians];
        public readonly RaceEvent[] Events = new RaceEvent[GameplayRules.MaxEventsPerTick];
        public readonly TrackDefinition Track;
        public readonly int CourseIndex;
        public int RiderCount, TrafficCount, PedestrianCount, EventCount, Level;
        public long Tick;
        public uint RandomState;
        public uint PedestrianRandomState;
        public int FinishedCount;
        internal long NextEventId = 1, NextTrafficTick;
        internal int NextTrafficId = 3001;
        internal long NextPedestrianTick;
        internal int NextPedestrianId = 4001;
        internal readonly int[] HitSource = new int[GameplayRules.MaxRiders];
        internal readonly int[] HitDamage = new int[GameplayRules.MaxRiders];
        internal readonly WeaponKind[] HitWeapon = new WeaponKind[GameplayRules.MaxRiders];
        internal readonly int[] HitTarget = new int[GameplayRules.MaxRiders];
        internal int PendingHitCount;
        internal GameplayWorld(uint seed, int level, int courseIndex = 0)
        {
            Track = TrackDefinition.ForCourse(courseIndex, level < 0 ? 0 : level > 4 ? 4 : level); CourseIndex = courseIndex;
            RandomState = seed; PedestrianRandomState = seed ^ 0x9e3779b9u; Level = level < 0 ? 0 : level > 4 ? 4 : level;
            for (int i = 0; i < Traffic.Length; i++) Traffic[i] = new RaceTraffic();
            for (int i = 0; i < Pedestrians.Length; i++) Pedestrians[i] = new RacePedestrian();
        }
    }
}
