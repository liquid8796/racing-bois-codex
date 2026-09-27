using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Already chosen authoritative pedestrian timing; never carries RNG state or future random choices.</summary>
    public readonly struct PedestrianPredictionContext
    {
        public const int MinimumWaitTicks = 60, MaximumWaitTicks = 359;
        public const int MinimumWalkingSpeed = 1200, MaximumWalkingSpeed = 1600;
        public readonly int WaitTicks, DesiredWalkingSpeed, MotionRemainder;
        public bool IsValid => WaitTicks >= MinimumWaitTicks && WaitTicks <= MaximumWaitTicks &&
            DesiredWalkingSpeed >= MinimumWalkingSpeed && DesiredWalkingSpeed <= MaximumWalkingSpeed && MotionRemainder > -60 && MotionRemainder < 60;
        public PedestrianPredictionContext(int waitTicks, int desiredWalkingSpeed, int motionRemainder)
        {
            WaitTicks = waitTicks; DesiredWalkingSpeed = desiredWalkingSpeed; MotionRemainder = motionRemainder;
            if (!IsValid) throw new ArgumentException("Pedestrian prediction context is outside authoritative bounds.");
        }
        public bool Matches(PedestrianMode mode, int ageTicks, int walkingSpeed, int facingSide, bool crossing)
        {
            if (!IsValid || ageTicks < 0 || (facingSide != -1 && facingSide != 1)) return false;
            if (mode == PedestrianMode.Waiting) return ageTicks < WaitTicks && walkingSpeed == 0;
            if (mode == PedestrianMode.Stumbled) return ageTicks < PedestrianMotion.StumbledRecoveryTicks && walkingSpeed == 0;
            return mode == PedestrianMode.Walking && (crossing || ageTicks < PedestrianMotion.AlongRoadWalkingTicks) && walkingSpeed == facingSide * DesiredWalkingSpeed;
        }
    }
    public static class PedestrianCheckpoints
    {
        public static PedestrianPredictionContext CapturePredictionContext(RacePedestrian pedestrian)
        {
            if (pedestrian == null) throw new ArgumentNullException(nameof(pedestrian));
            return new PedestrianPredictionContext(pedestrian.WaitTicks, pedestrian.DesiredWalkingSpeed, pedestrian.MotionRemainder);
        }
        public static void RestorePredictionContext(RacePedestrian pedestrian, PedestrianPredictionContext context)
        {
            if (pedestrian == null) throw new ArgumentNullException(nameof(pedestrian));
            if (!context.IsValid) throw new ArgumentException("Invalid pedestrian prediction context.");
            pedestrian.WaitTicks = context.WaitTicks; pedestrian.DesiredWalkingSpeed = context.DesiredWalkingSpeed; pedestrian.MotionRemainder = context.MotionRemainder;
        }
    }
}
