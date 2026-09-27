using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    internal enum PedestrianWalkEnd { None, Crossing, AlongRoad, Recovered }
    /// <summary>Deterministic motion/transitions shared by authority and snapshot prediction; no RNG, spawning or events.</summary>
    internal static class PedestrianMotion
    {
        internal const int StumbledRecoveryTicks = 180;
        internal const int RecoveryWaitTicks = 120;
        internal const int AlongRoadWalkingTicks = 300;

        // ModeAgeTicks was advanced once by the caller. Wait duration and
        // desired speed come from authority; no default-duration inference.
        internal static PedestrianWalkEnd AdvanceKnownState(RacePedestrian pedestrian, int shoulder)
        {
            if (pedestrian.Mode == PedestrianMode.Stumbled)
            {
                pedestrian.WalkingSpeedMillimetersPerSecond = 0;
                return TryRecoverStumbled(pedestrian) ? PedestrianWalkEnd.Recovered : PedestrianWalkEnd.None;
            }
            if (pedestrian.Mode == PedestrianMode.Waiting)
            {
                pedestrian.WalkingSpeedMillimetersPerSecond = 0;
                if (pedestrian.ModeAgeTicks < pedestrian.WaitTicks) return PedestrianWalkEnd.None;
                pedestrian.Mode = PedestrianMode.Walking; pedestrian.ModeAgeTicks = 0;
            }
            pedestrian.WalkingSpeedMillimetersPerSecond = pedestrian.FacingSide * pedestrian.DesiredWalkingSpeed;
            return AdvanceWalking(pedestrian, shoulder);
        }

        // Caller advances ModeAgeTicks exactly once before invoking this.
        internal static bool TryRecoverStumbled(RacePedestrian pedestrian)
        {
            if (pedestrian.Mode != PedestrianMode.Stumbled || pedestrian.ModeAgeTicks < StumbledRecoveryTicks) return false;
            pedestrian.Mode = PedestrianMode.Waiting; pedestrian.ModeAgeTicks = 0;
            pedestrian.WaitTicks = RecoveryWaitTicks; pedestrian.WalkingSpeedMillimetersPerSecond = 0;
            return true;
        }

        // Authority supplies its desired speed; prediction supplies the latest
        // observed walking speed. Random wait duration remains authority-owned.
        internal static PedestrianWalkEnd AdvanceWalking(RacePedestrian pedestrian, int shoulder)
        {
            pedestrian.MotionRemainder += pedestrian.WalkingSpeedMillimetersPerSecond;
            int step = pedestrian.MotionRemainder / 60; pedestrian.MotionRemainder %= 60;
            if (pedestrian.IsCrossing)
            {
                pedestrian.LateralMillimeters += step;
                if (pedestrian.LateralMillimeters * pedestrian.FacingSide < shoulder) return PedestrianWalkEnd.None;
                pedestrian.LateralMillimeters = pedestrian.FacingSide * shoulder;
                pedestrian.FacingSide = -pedestrian.FacingSide; pedestrian.Mode = PedestrianMode.Waiting;
                pedestrian.ModeAgeTicks = 0; pedestrian.WalkingSpeedMillimetersPerSecond = 0;
                return PedestrianWalkEnd.Crossing;
            }
            pedestrian.DistanceMillimeters += step;
            if (pedestrian.ModeAgeTicks < AlongRoadWalkingTicks) return PedestrianWalkEnd.None;
            pedestrian.Mode = PedestrianMode.Waiting; pedestrian.ModeAgeTicks = 0; pedestrian.WalkingSpeedMillimetersPerSecond = 0;
            return PedestrianWalkEnd.AlongRoad;
        }
    }
}
