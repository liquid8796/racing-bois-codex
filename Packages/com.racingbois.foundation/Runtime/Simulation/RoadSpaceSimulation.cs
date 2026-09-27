using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    public static class RoadSpaceSimulation
    {
        /// <summary>Exactly one fixed tick; no wall clock, random state, rendering or network dependencies.</summary>
        public static RiderState Step(RiderState state, RiderInput input)
        {
            int acceleration = PrototypeRules.AccelerationMillimetersPerSecondSquared * input.ThrottlePermille / 1000
                - PrototypeRules.BrakingMillimetersPerSecondSquared * input.BrakePermille / 1000;
            if (input.ThrottlePermille == 0 && input.BrakePermille == 0)
                acceleration = -PrototypeRules.CoastingMillimetersPerSecondSquared;
            int accelerationTotal = acceleration + state.AccelerationRemainder;
            state.SpeedMillimetersPerSecond += accelerationTotal / PrototypeRules.TickRate;
            state.AccelerationRemainder = accelerationTotal % PrototypeRules.TickRate;
            if (state.SpeedMillimetersPerSecond <= 0)
            {
                state.SpeedMillimetersPerSecond = 0;
                state.AccelerationRemainder = 0;
            }
            else if (state.SpeedMillimetersPerSecond >= PrototypeRules.MaximumSpeedMillimetersPerSecond)
            {
                state.SpeedMillimetersPerSecond = PrototypeRules.MaximumSpeedMillimetersPerSecond;
                state.AccelerationRemainder = 0;
            }
            int distanceTotal = state.SpeedMillimetersPerSecond + state.DistanceRemainder;
            state.DistanceMillimeters += distanceTotal / PrototypeRules.TickRate;
            state.DistanceRemainder = distanceTotal % PrototypeRules.TickRate;
            int lateralTotal = PrototypeRules.LateralSpeedMillimetersPerSecond * input.SteerPermille / 1000 + state.LateralRemainder;
            if (state.SpeedMillimetersPerSecond == 0) lateralTotal = 0;
            state.LateralMillimeters += lateralTotal / PrototypeRules.TickRate;
            state.LateralRemainder = lateralTotal % PrototypeRules.TickRate;
            if (state.LateralMillimeters > PrototypeRules.RoadHalfWidthMillimeters)
            {
                state.LateralMillimeters = PrototypeRules.RoadHalfWidthMillimeters;
                state.LateralRemainder = 0;
            }
            else if (state.LateralMillimeters < -PrototypeRules.RoadHalfWidthMillimeters)
            {
                state.LateralMillimeters = -PrototypeRules.RoadHalfWidthMillimeters;
                state.LateralRemainder = 0;
            }
            return state;
        }
    }
}
