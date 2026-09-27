namespace RacingBois.Gameplay.Definitions
{
    /// <summary>Canonical FNV-1a content digest, independent of JSON, culture and source whitespace. This is compatibility identity, not a security signature.</summary>
    public static class ContentFingerprint
    {
        public static string Compute()
        {
            ulong hash = 14695981039346656037UL;
            Mix(ref hash, ProductionContent.AvailableRouteMask); Mix(ref hash, ProductionContent.AvailableBikeArtMask); Mix(ref hash, ProductionContent.AvailableCharacterArtMask);
            Mix(ref hash, GameplayRules.Version); Mix(ref hash, CampaignCatalog.Version); Mix(ref hash, BikeCatalog.Version);
            for (int course = 0; course < CampaignCatalog.RouteCount; course++)
            {
                Text(ref hash, CampaignCatalog.GetRoute(course).Id);
                for (int level = 0; level < CampaignCatalog.LevelCount; level++)
                {
                    var track = TrackDefinition.ForCourse(course, level);
                    Mix(ref hash, course); Mix(ref hash, level); Mix(ref hash, track.LengthMillimeters);
                    Mix(ref hash, track.RoadHalfWidthMillimeters); Mix(ref hash, track.ShoulderWidthMillimeters);
                    for (int section = 0; section < track.SectionCount; section++)
                    {
                        long distance = track.SectionStartMillimeters(section);
                        Mix(ref hash, distance); Mix(ref hash, track.CurvatureAt(distance)); Mix(ref hash, track.GradeAt(distance));
                    }
                }
            }
            foreach (var bike in BikeCatalog.All)
            {
                Text(ref hash, bike.Id); Text(ref hash, bike.ArtId); Mix(ref hash, bike.PriceCredits);
                var h = bike.Handling;
                Mix(ref hash, h.MaximumSpeedMillimetersPerSecond); Mix(ref hash, h.EnginePermille); Mix(ref hash, h.BrakeDeceleration);
                Mix(ref hash, h.SteeringResponse); Mix(ref hash, h.CorneringPermille); Mix(ref hash, h.OffroadEnginePermille);
            }
            foreach (var character in CharacterCatalog.All) { Text(ref hash, character.Id); Text(ref hash, character.ArtId); }
            return "p08-" + hash.ToString("X16");
        }
        private static void Text(ref ulong hash, string value)
        { Mix(ref hash, value.Length); for (int i = 0; i < value.Length; i++) Mix(ref hash, value[i]); }
        private static void Mix(ref ulong hash, long value)
        { for (int i = 0; i < 8; i++) { hash = unchecked((hash ^ (byte)(value >> (i * 8))) * 1099511628211UL); } }
    }
}
