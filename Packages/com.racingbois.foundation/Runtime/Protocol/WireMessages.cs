using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Protocol
{
    public static class WireProtocol { public const int Version = 1; public const int MaximumMessageBytes = 2048; }

    // Public fields deliberately support Unity JsonUtility and explicit System.Text.Json IncludeFields.
    [Serializable]
    public sealed class HelloMessage
    {
        public string kind = "hello";
        public int protocolVersion = WireProtocol.Version;
        public int simulationRulesVersion = PrototypeRules.Version;
        public string contentHash = PrototypeRules.ContentHash;
    }

    [Serializable]
    public sealed class WelcomeMessage
    {
        public string kind = "welcome";
        public int protocolVersion = WireProtocol.Version;
        public int simulationRulesVersion = PrototypeRules.Version;
        public string contentHash = PrototypeRules.ContentHash;
        public string playerId = "";
        public int tickRate = PrototypeRules.TickRate;
        public int snapshotRate = PrototypeRules.SnapshotRate;
        public int maxPlayers = PrototypeRules.MaxPlayers;
    }

    [Serializable]
    public sealed class InputMessage
    {
        public string kind = "input";
        public int protocolVersion = WireProtocol.Version;
        public string playerId = "";
        public int sequence;
        public float throttle;
        public float brake;
        public float steer;
    }

    [Serializable]
    public sealed class SnapshotMessage
    {
        public string kind = "snapshot";
        public int protocolVersion = WireProtocol.Version;
        public long tick;
        public int ackSequence;
        public string playerId = "";
        public EntitySnapshot[] entities = new EntitySnapshot[0];
    }

    [Serializable]
    public sealed class EntitySnapshot
    {
        public string id = "";
        public float s;
        public float d;
        public float speed;
    }

    [Serializable]
    public sealed class ErrorMessage
    {
        public string kind = "error";
        public int protocolVersion = WireProtocol.Version;
        public string code = "";
        public string message = "";
        public int sequence;
    }
}
