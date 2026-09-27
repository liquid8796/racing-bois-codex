using System;
using System.Collections.Generic;

namespace RacingBois.Gameplay.Definitions
{
    public sealed class CampaignRouteDefinition
    {
        public int CourseIndex { get; }
        public string Id { get; }
        public string DisplayName { get; }
        public bool IsPlayable => ProductionContent.RouteAvailable(CourseIndex);
        public string ContentId => GameplayRules.ContentHash + ":" + CourseIndex;

        internal CampaignRouteDefinition(int courseIndex, string id, string displayName)
        {
            CourseIndex = courseIndex;
            Id = id;
            DisplayName = displayName;
        }
    }

    /// <summary>Five authored routes across five levels. Production content audit controls playable availability.</summary>
    public static class CampaignCatalog
    {
        public const int Version = 2;
        public const int LevelCount = 5;
        public const int RouteCount = 5;
        public const int CompleteQualificationMask = (1 << RouteCount) - 1;
        public const int QualifyingRank = 3;

        private static readonly CampaignRouteDefinition[] routes =
        {
            new CampaignRouteDefinition(0, "rb-canyon-run", "Canyon Run"),
            new CampaignRouteDefinition(1, "rb-neon-district", "Neon District"),
            new CampaignRouteDefinition(2, "rb-ridge-pass", "Ridge Pass"),
            new CampaignRouteDefinition(3, "rb-coastal-line", "Coastal Line"),
            new CampaignRouteDefinition(4, "rb-orchard-road", "Orchard Road")
        };

        public static IReadOnlyList<CampaignRouteDefinition> Routes { get; } = Array.AsReadOnly(routes);

        public static CampaignRouteDefinition GetRoute(int courseIndex)
        {
            if (courseIndex < 0 || courseIndex >= RouteCount) throw new ArgumentOutOfRangeException(nameof(courseIndex));
            return routes[courseIndex];
        }

        public static bool TryGetRoute(string id, out CampaignRouteDefinition definition)
        {
            for (int i = 0; i < routes.Length; i++)
                if (string.Equals(routes[i].Id, id, StringComparison.Ordinal))
                {
                    definition = routes[i];
                    return true;
                }
            definition = null;
            return false;
        }

        public static bool IsPlayableRoute(int courseIndex)
            => courseIndex >= 0 && courseIndex < RouteCount && routes[courseIndex].IsPlayable;

        public static void ValidateLevel(int levelIndex)
        {
            if (levelIndex < 0 || levelIndex >= LevelCount) throw new ArgumentOutOfRangeException(nameof(levelIndex));
        }
    }
}
