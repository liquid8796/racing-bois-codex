namespace RacingBois.Simulation
{
    /// <summary>Integer road-space state. Remainders preserve sub-tick integration across native/Web builds.</summary>
    public struct RiderState
    {
        public long DistanceMillimeters;
        public int LateralMillimeters;
        public int SpeedMillimetersPerSecond;
        public int DistanceRemainder;
        public int LateralRemainder;
        public int AccelerationRemainder;
    }

    public readonly struct RiderInput
    {
        public readonly int ThrottlePermille;
        public readonly int BrakePermille;
        public readonly int SteerPermille;

        public RiderInput(int throttlePermille, int brakePermille, int steerPermille)
        {
            ThrottlePermille = Clamp(throttlePermille, 0, 1000);
            BrakePermille = Clamp(brakePermille, 0, 1000);
            SteerPermille = Clamp(steerPermille, -1000, 1000);
        }

        private static int Clamp(int value, int min, int max) => value < min ? min : value > max ? max : value;
    }
}
