using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Server.Application;

/// <summary>One owner calls this class from the match loop. Network callbacks must enqueue intents.</summary>
public sealed class AuthoritativeMatch
{
    private sealed class Rider
    {
        public RiderState State;
        public RiderInput Input;
        public int LastSequence;
        public long LastInputTick;
    }
    private readonly SortedDictionary<string, Rider> riders = new(StringComparer.Ordinal);
    private int nextId;
    public long Tick { get; private set; }
    public int PlayerCount => riders.Count;

    public string? Join()
    {
        if (riders.Count >= PrototypeRules.MaxPlayers) return null;
        string id = "p" + (++nextId).ToString(System.Globalization.CultureInfo.InvariantCulture);
        riders.Add(id, new Rider());
        return id;
    }

    public void Leave(string playerId) => riders.Remove(playerId);

    public string? Apply(string connectionPlayerId, InputMessage input)
    {
        if (input.protocolVersion != WireProtocol.Version) return "protocol_mismatch";
        if (input.playerId != connectionPlayerId || !riders.TryGetValue(connectionPlayerId, out var rider)) return "not_owner";
        if (input.sequence <= rider.LastSequence || (long)input.sequence - rider.LastSequence > 10000) return "invalid_sequence";
        if (!Finite(input.throttle) || !Finite(input.brake) || !Finite(input.steer)
            || input.throttle < 0 || input.throttle > 1 || input.brake < 0 || input.brake > 1 || input.steer < -1 || input.steer > 1) return "input_out_of_range";
        rider.Input = new RiderInput(Quantize(input.throttle), Quantize(input.brake), Quantize(input.steer));
        rider.LastSequence = input.sequence;
        rider.LastInputTick = Tick;
        return null;
    }

    public void Step()
    {
        foreach (var rider in riders.Values)
        {
            // Lost input must not leave a disconnected/tab-suspended rider accelerating indefinitely.
            var input = Tick - rider.LastInputTick >= PrototypeRules.InputTimeoutTicks ? default : rider.Input;
            rider.State = RoadSpaceSimulation.Step(rider.State, input);
        }
        Tick++;
    }

    public SnapshotMessage Snapshot(string playerId)
    {
        return new SnapshotMessage
        {
            tick = Tick,
            playerId = playerId,
            ackSequence = riders.TryGetValue(playerId, out var own) ? own.LastSequence : 0,
            entities = riders.Select(pair => new EntitySnapshot
            {
                id = pair.Key,
                s = pair.Value.State.DistanceMillimeters / 1000f,
                d = pair.Value.State.LateralMillimeters / 1000f,
                speed = pair.Value.State.SpeedMillimetersPerSecond / 1000f
            }).ToArray()
        };
    }

    private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    private static int Quantize(float value) => (int)Math.Round(value * 1000, MidpointRounding.AwayFromZero);
}
