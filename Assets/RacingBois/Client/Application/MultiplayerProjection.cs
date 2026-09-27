using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    internal static class MultiplayerProjection
    {
        public static MultiplayerSnapshotReadModel World(MpSnapshot s, int sent, int previousAck, RaceEventReadModel[] events)
        {
            Require(s != null && s.protocolVersion == MultiplayerProtocol.Version && s.tick >= 0 && s.tick == s.resolvedThroughTick &&
                s.own != null && s.own.tick == s.tick && s.own.rider != null && s.own.rider.id == s.riderId &&
                s.lastAppliedInputTick >= -100 && s.lastAppliedInputTick <= s.tick && s.serverServiceTick >= 0 && s.startServiceTick >= 0 &&
                s.lastProcessedSequence >= previousAck && s.lastProcessedSequence <= sent && s.lateInputs >= 0 && s.futureInputs >= 0 && s.missingInputs >= 0,
                "Invalid snapshot envelope");
            CheckpointMapper.Validate(s.own); CheckpointMapper.ValidateInput(s.heldAnalog);
            Require(s.heldAnalog.attackSide == 0 && !s.heldAnalog.kick, "Fallback must not replay attack");
            Require(s.riders != null && s.riders.Length <= RaceProtocol.MaxRiders && s.traffic != null && s.traffic.Length <= RaceProtocol.MaxTraffic &&
                s.pedestrians != null && s.pedestrians.Length <= RaceProtocol.MaxPedestrians && s.standings != null && s.standings.Length <= RaceProtocol.MaxRiders,
                "Invalid snapshot capacity");
            var riders = new List<RaceEntitySnapshot>(s.riders.Length + 1); var ids = new HashSet<int>();
            var collisionUntil = new Dictionary<int, long>(s.riders.Length);
            var combatContexts = new Dictionary<int, RiderCombatPredictionContext>(s.riders.Length);
            foreach (var row in s.riders)
            {
                var v = Row(row, 31); Require(ids.Add(v[0]), "Duplicate actor");
                Require(v[26] >= 0 && v[26] <= MultiplayerProtocol.MaximumCollisionProtectionTicks && s.tick <= long.MaxValue - v[26], "Invalid remote collision protection");
                collisionUntil.Add(v[0], s.tick + v[26]);
                combatContexts.Add(v[0], new RiderCombatPredictionContext(s.tick, v[27], Bool(v[28]), v[29], v[30]));
                Require(v[0] != s.riderId, "Own rider must use exact checkpoint");
                riders.Add(new RaceEntitySnapshot { id = v[0], kind = v[1], mode = v[2], weapon = v[3], attackWeapon = v[4],
                    distanceMillimeters = Mm(v[5]), lateralMillimeters = Mm(v[6]), speedMillimetersPerSecond = Mm(v[7]), heightMillimeters = Mm(v[8]),
                    leanMillidegrees = checked(v[9] * 100), bikeDistanceMillimeters = Mm(v[10]), bikeLateralMillimeters = Mm(v[11]), bikeHeightMillimeters = Mm(v[12]),
                    health = v[13], bikeCondition = v[14], strength = v[15], rank = v[16], finishTick = v[17], reward = v[18], qualified = Bool(v[19]),
                    attackSide = v[20], attackAgeTicks = v[21], modeAgeTicks = v[22], gear = v[23], bikeCatalogIndex = v[24], characterCatalogIndex = v[25] });
            }
            riders.Add(s.own.rider);
            var traffic = new RaceTrafficSnapshot[s.traffic.Length];
            for (int i = 0; i < traffic.Length; i++)
            { var v = Row(s.traffic[i], 8); traffic[i] = new RaceTrafficSnapshot { id = v[0], kind = v[1], distanceMillimeters = Mm(v[2]), lateralMillimeters = Mm(v[3]), speedMillimetersPerSecond = Mm(v[4]), halfLengthMillimeters = Mm(v[5]), halfWidthMillimeters = Mm(v[6]), heightMillimeters = Mm(v[7]) }; }
            var pedestrians = new RacePedestrianSnapshot[s.pedestrians.Length];
            var pedestrianContexts = new Dictionary<int, PedestrianPredictionContext>(s.pedestrians.Length);
            for (int i = 0; i < pedestrians.Length; i++)
            {
                var v = Row(s.pedestrians[i], 12); var context = new PedestrianPredictionContext(v[9], v[10], v[11]);
                Require(v[7] == -1 || v[7] == 1, "Invalid pedestrian facing");
                int expectedSpeed = v[5] == (int)PedestrianMode.Walking ? v[7] * context.DesiredWalkingSpeed : 0;
                Require(context.Matches((PedestrianMode)v[5], v[6], expectedSpeed, v[7], Bool(v[8])) && v[4] == expectedSpeed / 10, "Incoherent pedestrian prediction context");
                Require(!pedestrianContexts.ContainsKey(v[0]), "Duplicate pedestrian context"); pedestrianContexts.Add(v[0], context);
                pedestrians[i] = new RacePedestrianSnapshot { id = v[0], distanceMillimeters = Mm(v[1]), lateralMillimeters = Mm(v[2]), heightMillimeters = Mm(v[3]), walkingSpeedMillimetersPerSecond = Mm(v[4]), mode = v[5], stateTicks = v[6], facingSide = v[7], isCrossing = Bool(v[8]) }; }
            var standings = new HashSet<int>();
            foreach (var row in s.standings)
            { var v = Row(row, 4); Require(v[0] > 0 && standings.Add(v[0]) && v[1] >= 0 && v[1] <= 16 && v[2] >= 0 && v[2] <= 4 && v[3] >= -25000 && v[3] <= (s.trackLengthMillimeters + 500000) / 10, "Invalid standing"); }
            var legacy = new RaceSnapshotMessage { tick = s.tick, ackSequence = s.lastProcessedSequence, riderId = s.riderId, level = s.level, courseIndex = s.courseIndex,
                trackLengthMillimeters = s.trackLengthMillimeters, riders = riders.ToArray(), traffic = traffic, pedestrians = pedestrians };
            RaceSnapshotValidator.Validate(legacy, s.riderId, sent, previousAck);
            var projected = RaceStateProjection.World(legacy);
            return new MultiplayerSnapshotReadModel(Copy(projected, events), collisionUntil, pedestrianContexts, combatContexts);
        }
        public static RaceWorldReadModel Copy(RaceWorldReadModel source, RaceEventReadModel[] events)
        {
            var r = new RaceRiderReadModel[source.Riders.Count]; for (int i = 0; i < r.Length; i++) r[i] = source.Riders[i];
            var t = new RaceTrafficReadModel[source.Traffic.Count]; for (int i = 0; i < t.Length; i++) t[i] = source.Traffic[i];
            var p = new RacePedestrianReadModel[source.Pedestrians.Count]; for (int i = 0; i < p.Length; i++) p[i] = source.Pedestrians[i];
            return new RaceWorldReadModel(source.Tick, source.AcknowledgedInputSequence, source.TrackLengthMeters, source.Level, r, t, events, p, source.CourseIndex);
        }
        public static LobbyReadModel Lobby(MpLobby message)
        {
            Require(message != null && Text(message.roomId, 64) && Text(message.code, 16) && Text(message.name, 64) && message.hostSessionId != null && message.hostSessionId.Length <= 128 &&
                message.state >= 0 && message.state <= 4 && message.revision >= 0 && message.raceEpoch >= 0 && message.botCount >= 0 && message.botCount <= 6 &&
                message.courseIndex >= 0 && message.courseIndex < CampaignCatalog.RouteCount && message.levelIndex >= 0 && message.levelIndex < CampaignCatalog.LevelCount &&
                message.maxPlayers == 8 && message.serverServiceTick >= 0 && message.startServiceTick >= 0 && message.members != null && message.members.Length <= 8,
                "Invalid lobby");
            var members = new LobbyMemberReadModel[message.members.Length]; var ids = new HashSet<string>(); var riders = new HashSet<int>();
            for (int i = 0; i < members.Length; i++)
            {
                var m = message.members[i]; Require(m != null && Text(m.sessionId, 128) && ids.Add(m.sessionId) && Text(m.displayName, 32) && m.riderId >= 1 && m.riderId <= 999 && riders.Add(m.riderId), "Invalid lobby member");
                members[i] = new LobbyMemberReadModel(m.sessionId, m.displayName, m.riderId, m.ready, m.connected, m.guest);
            }
            bool connected = false; foreach (var member in members) connected |= member.Connected;
            Require(!connected ? message.hostSessionId == "" || ids.Contains(message.hostSessionId) : ids.Contains(message.hostSessionId), "Host absent");
            return new LobbyReadModel(message.roomId, message.code, message.name, message.hostSessionId, message.matchId ?? "", (LobbyPhase)message.state,
                message.revision, message.raceEpoch, message.botCount, message.maxPlayers, message.startServiceTick, members, message.publicRoom, message.courseIndex, message.levelIndex);
        }
        internal static bool Text(string value, int max) => !string.IsNullOrWhiteSpace(value) && value.Length <= max;
        internal static void Require(bool valid, string reason) { if (!valid) throw new ArgumentException(reason); }
        private static int[] Row(NumericRow row, int count) { Require(row != null && row.values != null && row.values.Length == count, "Invalid numeric row"); return row.values; }
        private static int Mm(int value) => checked(value * 10);
        private static bool Bool(int value) { Require(value == 0 || value == 1, "Invalid boolean"); return value == 1; }
    }
}
