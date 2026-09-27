using System;
using System.Collections.Generic;
namespace RacingBois.Gameplay.Definitions
{
    /// <summary>Integer handling units shared by server, local play and reconciliation.</summary>
    public sealed class BikeHandlingProfile
    {
        public int CatalogIndex { get; }
        public int MaximumSpeedMillimetersPerSecond { get; }
        public int EnginePermille { get; }
        public int BrakeDeceleration { get; }
        public int SteeringResponse { get; }
        public int CorneringPermille { get; }
        public int OffroadEnginePermille { get; }
        internal BikeHandlingProfile(int index, int speed, int engine, int brake, int response, int cornering, int offroad)
        {
            if (index < 0 || index >= 15 || speed < 40000 || speed > 80000 || engine < 650 || engine > 1600 ||
                brake < 18000 || brake > 30000 || response < 60 || response > 150 || cornering < 700 || cornering > 1300 || offroad < 250 || offroad > 650)
                throw new ArgumentOutOfRangeException(nameof(index), "Invalid authored bike tuning.");
            CatalogIndex = index; MaximumSpeedMillimetersPerSecond = speed; EnginePermille = engine;
            BrakeDeceleration = brake; SteeringResponse = response; CorneringPermille = cornering; OffroadEnginePermille = offroad;
        }
    }
    public static class BikeHandlingCatalog
    {
        // Spark preserves the P06 player handling exactly. Every other SKU differs in at least three dimensions.
        private static readonly BikeHandlingProfile[] entries = {
            new BikeHandlingProfile(0,58000,1000,23000,95,1000,400),
            new BikeHandlingProfile(1,52000,930,22000,112,1100,450),
            new BikeHandlingProfile(2,50000,880,21500,125,1180,500),
            new BikeHandlingProfile(3,60000,1080,24000,87,940,380),
            new BikeHandlingProfile(4,47000,820,20500,105,1060,560),
            new BikeHandlingProfile(5,74000,1350,28000,115,1160,280),
            new BikeHandlingProfile(6,69000,1240,26700,102,1080,320),
            new BikeHandlingProfile(7,79000,1460,29000,92,1000,260),
            new BikeHandlingProfile(8,71500,1310,27200,122,1210,290),
            new BikeHandlingProfile(9,76000,1410,28500,108,1120,270),
            new BikeHandlingProfile(10,65000,1170,25300,119,1180,370),
            new BikeHandlingProfile(11,68000,1220,26000,82,910,350),
            new BikeHandlingProfile(12,64000,1140,24900,128,1240,390),
            new BikeHandlingProfile(13,62000,1100,24500,78,880,440),
            new BikeHandlingProfile(14,61000,1120,23800,100,1030,530)
        };
        public static IReadOnlyList<BikeHandlingProfile> All { get; } = Array.AsReadOnly(entries);
        public static BikeHandlingProfile GetAt(int index)
        { if (index < 0 || index >= entries.Length) throw new ArgumentOutOfRangeException(nameof(index)); return entries[index]; }
    }
}
