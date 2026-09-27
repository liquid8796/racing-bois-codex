using System;
using System.Collections.Generic;

namespace RacingBois.Gameplay.Definitions
{
    /// <summary>Immutable commerce definition. A SKU is not a claim of a distinct production model.</summary>
    public sealed class BikeDefinition
    {
        public int CatalogIndex { get; }
        public string Id { get; }
        public string DisplayName { get; }
        public int PriceCredits { get; }
        public int TradeInCredits => EconomyRules.TradeInValue(PriceCredits);
        public int RepairCredits => EconomyRules.RepairCost(PriceCredits);
        public string ArtId => "RB_P08_Bike_" + CatalogIndex.ToString("D2");
        public bool HasDistinctArt => ProductionContent.BikeArtAvailable(CatalogIndex);
        public string HandlingProfileId => "p08-bike-" + CatalogIndex;
        public BikeHandlingProfile Handling => BikeHandlingCatalog.GetAt(CatalogIndex);
        public int MaximumSpeedMillimetersPerSecond => Handling.MaximumSpeedMillimetersPerSecond;

        internal BikeDefinition(int index, string id, string displayName, int priceCredits)
        {
            CatalogIndex = index;
            Id = id;
            DisplayName = displayName;
            PriceCredits = priceCredits;
        }
    }

    /// <summary>
    /// Original Racing Bois names with the recovered reference price schedule.
    /// Stable commerce IDs map to immutable P08 handling and original art definitions.
    /// </summary>
    public static class BikeCatalog
    {
        public const int Version = 2;
        public const int Count = 15;
        public const string StarterBikeId = "rb-spark-450";
        public const string SharedArtId = "RB_P06_Motorcycle";

        private static readonly BikeDefinition[] entries =
        {
            new BikeDefinition(0, "rb-spark-450", "Spark 450", 4495),
            new BikeDefinition(1, "rb-kestrel", "Kestrel", 3249),
            new BikeDefinition(2, "rb-rift-250", "Rift 250", 3497),
            new BikeDefinition(3, "rb-jackal", "Jackal", 5489),
            new BikeDefinition(4, "rb-ember", "Ember", 2999),
            new BikeDefinition(5, "rb-apex", "Apex", 29998),
            new BikeDefinition(6, "rb-corvus", "Corvus", 18999),
            new BikeDefinition(7, "rb-viper", "Viper", 40000),
            new BikeDefinition(8, "rb-rift-750n", "Rift 750 N", 21789),
            new BikeDefinition(9, "rb-specter", "Specter", 34888),
            new BikeDefinition(10, "rb-nightjar", "Nightjar", 13796),
            new BikeDefinition(11, "rb-cinder-10", "Cinder 10", 16875),
            new BikeDefinition(12, "rb-rift-750", "Rift 750", 11988),
            new BikeDefinition(13, "rb-odyssey", "Odyssey", 9199),
            new BikeDefinition(14, "rb-havoc", "Havoc", 6994)
        };

        public static IReadOnlyList<BikeDefinition> All { get; } = Array.AsReadOnly(entries);

        public static BikeDefinition GetAt(int catalogIndex)
        {
            if (catalogIndex < 0 || catalogIndex >= Count) throw new ArgumentOutOfRangeException(nameof(catalogIndex));
            return entries[catalogIndex];
        }

        public static BikeDefinition Get(string id)
        {
            if (!TryGet(id, out var definition)) throw new ArgumentException("Unknown bike ID.", nameof(id));
            return definition;
        }

        public static bool TryGet(string id, out BikeDefinition definition)
        {
            for (int i = 0; i < entries.Length; i++)
                if (string.Equals(entries[i].Id, id, StringComparison.Ordinal))
                {
                    definition = entries[i];
                    return true;
                }
            definition = null;
            return false;
        }
    }
}
