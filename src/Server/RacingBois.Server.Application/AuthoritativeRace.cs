using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Server.Application;

/// <summary>Single-owner gameplay authority. A peer can supply intent only for its assigned rider.</summary>
public sealed class AuthoritativeRace
{
    private sealed class Player(int riderId)
    {
        public int RiderId { get; } = riderId;
        public int LastSequence;
        public long LastInputTick;
        public RaceInput Input;
        public int PendingAttackSide;
        public bool PendingKick;
    }
    private readonly Dictionary<string, Player> players = new(StringComparer.Ordinal);
    private readonly List<RaceEvent> recentEvents = new(RaceProtocol.MaxEvents);
    private GameplayWorld world = RaceSimulation.CreateDefault();
    private long nextConnection;
    public long Tick => world.Tick;
    public int PlayerCount => players.Count;

    public string? Join()
    {
        if (players.Count >= RaceProtocol.MaxPlayers) return null;
        if (players.Count == 0) { world = RaceSimulation.CreateDefault(); recentEvents.Clear(); }
        int riderId = 1;
        while (players.Values.Any(player => player.RiderId == riderId)) riderId++;
        if (RaceSimulation.AddPlayer(world, riderId) == null) return null;
        string id = "r" + (++nextConnection).ToString(System.Globalization.CultureInfo.InvariantCulture);
        players.Add(id, new Player(riderId));
        return id;
    }

    public int RiderId(string playerId) => players.TryGetValue(playerId, out var player) ? player.RiderId : 0;
    public void Leave(string playerId)
    {
        if (!players.Remove(playerId, out var player)) return;
        RaceSimulation.RemovePlayer(world, player.RiderId);
    }

    public string? Apply(string owner, RaceInputMessage input)
    {
        if (input.protocolVersion != RaceProtocol.Version) return "protocol_mismatch";
        if (input.kind != "raceInput") return "invalid_kind";
        if (input.playerId != owner || !players.TryGetValue(owner, out var player)) return "not_owner";
        if (input.sequence <= player.LastSequence || (long)input.sequence - player.LastSequence > 10000) return "invalid_sequence";
        if (!Finite(input.throttle) || !Finite(input.brake) || !Finite(input.steer) ||
            input.throttle < 0 || input.throttle > 1 || input.brake < 0 || input.brake > 1 || input.steer < -1 || input.steer > 1 ||
            input.attackSide < -1 || input.attackSide > 1) return "input_out_of_range";
        player.Input = new RaceInput(Quantize(input.throttle), Quantize(input.brake), Quantize(input.steer), input.attackSide, input.kick);
        // A press/release may both arrive before the next authority tick. Keep the latest press
        // independently from continuously sampled movement and consume it at most once.
        if (input.attackSide != 0) { player.PendingAttackSide = input.attackSide; player.PendingKick = input.kick; }
        player.LastSequence = input.sequence; player.LastInputTick = Tick;
        return null;
    }

    public void Step()
    {
        if (players.Count == 0) return;
        foreach (var player in players.Values)
        {
            var latest = player.Input;
            var sampled = Tick - player.LastInputTick >= 30 ? default : new RaceInput(
                latest.ThrottlePermille, latest.BrakePermille, latest.SteerPermille,
                player.PendingAttackSide != 0 ? player.PendingAttackSide : latest.AttackSide,
                player.PendingAttackSide != 0 ? player.PendingKick : latest.Kick);
            RaceSimulation.SetInput(world, player.RiderId, sampled);
            player.PendingAttackSide = 0; player.PendingKick = false;
        }
        RaceSimulation.Step(world);
        for (int i = 0; i < world.EventCount; i++)
        {
            if (recentEvents.Count == RaceProtocol.MaxEvents) recentEvents.RemoveAt(0);
            recentEvents.Add(world.Events[i]);
        }
        while (recentEvents.Count > 0 && recentEvents[0].Tick < Tick - 120) recentEvents.RemoveAt(0);
    }

    public RaceSnapshotMessage Snapshot(string playerId)
    {
        var riders = new RaceEntitySnapshot[world.RiderCount];
        for (int i = 0; i < riders.Length; i++)
        {
            var rider = world.Riders[i];
            riders[i] = new RaceEntitySnapshot
            {
                id = rider.Id, bikeCatalogIndex = rider.BikeCatalogIndex, characterCatalogIndex = rider.CharacterCatalogIndex, kind = (int)rider.Kind, mode = (int)rider.Mode, weapon = (int)rider.Weapon, attackWeapon = (int)rider.AttackWeapon,
                distanceMillimeters = rider.DistanceMillimeters, lateralMillimeters = rider.LateralMillimeters,
                speedMillimetersPerSecond = rider.SpeedMillimetersPerSecond, heightMillimeters = rider.HeightMillimeters,
                leanMillidegrees = rider.LeanMillidegrees, bikeDistanceMillimeters = rider.BikeDistanceMillimeters,
                bikeLateralMillimeters = rider.BikeLateralMillimeters, bikeHeightMillimeters = rider.BikeHeightMillimeters,
                health = rider.Health, bikeCondition = rider.BikeCondition, strength = rider.Strength,
                rank = rider.Rank, finishTick = rider.FinishTick, reward = rider.Reward, qualified = rider.Qualified,
                attackSide = rider.AttackSide, attackAgeTicks = rider.AttackAgeTicks, modeAgeTicks = rider.ModeAgeTicks, gear = rider.Gear
            };
        }
        var traffic = new RaceTrafficSnapshot[world.TrafficCount];
        for (int i = 0; i < traffic.Length; i++)
        {
            var vehicle = world.Traffic[i];
            traffic[i] = new RaceTrafficSnapshot { id = vehicle.Id, kind = vehicle.Oncoming ? 1 : 0,
                distanceMillimeters = vehicle.DistanceMillimeters, lateralMillimeters = vehicle.LateralMillimeters,
                speedMillimetersPerSecond = vehicle.SpeedMillimetersPerSecond,
                halfLengthMillimeters = vehicle.LengthMillimeters / 2, halfWidthMillimeters = vehicle.WidthMillimeters / 2,
                heightMillimeters = vehicle.HeightMillimeters };
        }
        var events = new RaceEventSnapshot[recentEvents.Count];
        for (int i = 0; i < events.Length; i++)
        {
            var item = recentEvents[i];
            events[i] = new RaceEventSnapshot { id = item.Id, tick = item.Tick, kind = (int)item.Kind,
                sourceId = item.ActorId, targetId = item.TargetId, value = item.Value };
        }
        var pedestrians = new RacePedestrianSnapshot[world.PedestrianCount];
        for (int i = 0; i < pedestrians.Length; i++)
        {
            var person = world.Pedestrians[i];
            pedestrians[i] = new RacePedestrianSnapshot { id = person.Id, distanceMillimeters = person.DistanceMillimeters,
                lateralMillimeters = person.LateralMillimeters, heightMillimeters = person.HeightMillimeters,
                walkingSpeedMillimetersPerSecond = person.WalkingSpeedMillimetersPerSecond, mode = (int)person.Mode,
                stateTicks = person.ModeAgeTicks, facingSide = person.FacingSide, isCrossing = person.IsCrossing };
        }
        players.TryGetValue(playerId, out var own);
        return new RaceSnapshotMessage { tick = Tick, playerId = playerId, riderId = own?.RiderId ?? 0,
            ackSequence = own?.LastSequence ?? 0, level = world.Level, courseIndex = world.CourseIndex, trackLengthMillimeters = world.Track.LengthMillimeters,
            riders = riders, traffic = traffic, events = events, pedestrians = pedestrians };
    }

    private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    private static int Quantize(float value) => (int)Math.Round(value * 1000, MidpointRounding.AwayFromZero);
}
