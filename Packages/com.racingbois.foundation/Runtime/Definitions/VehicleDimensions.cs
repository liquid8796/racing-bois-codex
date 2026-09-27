namespace RacingBois.Gameplay.Definitions
{
    /// <summary>Millimeter bounds measured from the original Racing Bois Blender production meshes, not legacy assets.</summary>
    public static class VehicleDimensions
    {
        public const int MotorcycleHalfWidth = 475;
        // Mesh length2120 centered z=-10; symmetric half-length1070 covers the rear without moving gameplay origin.
        public const int MotorcycleHalfLength = 1070;
        public const int MotorcycleHeight = 1200;
        public const int CoupeWidth = 2160;
        public const int CoupeLength = 4540;
        public const int CoupeHeight = 1360;
        public const int VanWidth = 2310;
        public const int VanLength = 4640;
        public const int VanHeight = 2290;
        public static bool IsVan(int trafficId) => trafficId % 3 == 0;
    }
}
