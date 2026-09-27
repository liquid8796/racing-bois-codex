namespace RacingBois.Gameplay.Definitions
{
    /// <summary>Build-time availability gate. Promote only after the matching production prefab/scene audit.</summary>
    public static class ProductionContent
    {
        public const int AvailableRouteMask = 1;
        public const int AvailableBikeArtMask = 1;
        public const int AvailableCharacterArtMask = 1;
        public static bool RouteAvailable(int index) => index >= 0 && index < 5 && (AvailableRouteMask & (1 << index)) != 0;
        public static bool BikeArtAvailable(int index) => index >= 0 && index < 15 && (AvailableBikeArtMask & (1 << index)) != 0;
        public static bool CharacterArtAvailable(int index) => index >= 0 && index < 8 && (AvailableCharacterArtMask & (1 << index)) != 0;
    }
}
