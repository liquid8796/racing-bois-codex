using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Protocol
{
    /// <summary>P03/P04 contracts are independent of the preserved P02 transport fixture.</summary>
    public static class RaceProtocol
    {
        public const int Version = 3;
        public const int SimulationRulesVersion = GameplayRules.Version;
        public static readonly string ContentHash = GameplayRules.ContentHash;
        public const int TickRate = 60;
        public const int SnapshotRate = 20;
        public const int MaxPlayers = 8;
        public const int MaxRiders = 16;
        public const int MaxTraffic = 12;
        public const int MaxPedestrians = 6;
        public const int MaxEvents = 128;
    }

    [Serializable]
    public sealed class RaceHelloMessage
    {
        public string kind = "raceHello";
        public int protocolVersion = RaceProtocol.Version;
        public int simulationRulesVersion = RaceProtocol.SimulationRulesVersion;
        public string contentHash = RaceProtocol.ContentHash;
    }

    [Serializable]
    public sealed class RaceWelcomeMessage
    {
        public string kind = "raceWelcome";
        public int protocolVersion = RaceProtocol.Version;
        public int simulationRulesVersion = RaceProtocol.SimulationRulesVersion;
        public string contentHash = RaceProtocol.ContentHash;
        public string playerId = "";
        public int riderId;
        public int tickRate = RaceProtocol.TickRate;
        public int snapshotRate = RaceProtocol.SnapshotRate;
        public int maxPlayers = RaceProtocol.MaxPlayers;
    }

    [Serializable]
    public sealed class RaceInputMessage
    {
        public string kind = "raceInput";
        public int protocolVersion = RaceProtocol.Version;
        public string playerId = "";
        public int sequence;
        public float throttle;
        public float brake;
        public float steer;
        public int attackSide;
        public bool kick;
    }

    [Serializable]
    public sealed class RaceSnapshotMessage
    {
        public string kind = "raceSnapshot";
        public int protocolVersion = RaceProtocol.Version;
        public long tick;
        public int ackSequence;
        public string playerId = "";
        public int riderId;
        public int level, courseIndex;
        public long trackLengthMillimeters;
        public RaceEntitySnapshot[] riders = new RaceEntitySnapshot[0];
        public RaceTrafficSnapshot[] traffic = new RaceTrafficSnapshot[0];
        public RacePedestrianSnapshot[] pedestrians = new RacePedestrianSnapshot[0];
        public RaceEventSnapshot[] events = new RaceEventSnapshot[0];
    }

    [Serializable]
    public sealed class RaceEntitySnapshot
    {
        public int id, kind, mode, weapon, attackWeapon, bikeCatalogIndex, characterCatalogIndex;
        public long distanceMillimeters, bikeDistanceMillimeters, finishTick;
        public int lateralMillimeters, speedMillimetersPerSecond, heightMillimeters, leanMillidegrees;
        public int bikeLateralMillimeters, bikeHeightMillimeters, health, bikeCondition, strength, rank, reward;
        public int attackSide, attackAgeTicks, modeAgeTicks, gear;
        public bool qualified;
    }

    [Serializable]
    public sealed class RaceTrafficSnapshot
    {
        public int id, kind, lateralMillimeters, speedMillimetersPerSecond, halfLengthMillimeters, halfWidthMillimeters, heightMillimeters;
        public long distanceMillimeters;
    }

    [Serializable]
    public sealed class RacePedestrianSnapshot
    {
        public int id, lateralMillimeters, heightMillimeters, walkingSpeedMillimetersPerSecond, mode, stateTicks, facingSide;
        public long distanceMillimeters;
        public bool isCrossing;
    }

    [Serializable]
    public sealed class RaceEventSnapshot
    {
        public long id, tick;
        public int kind, sourceId, targetId, value;
    }
}
