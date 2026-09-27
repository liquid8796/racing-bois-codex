// Isolated test assembly only. Reconstructs sanitized state, then calls unchanged production methods.
using System.Text.Json;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    public sealed partial class MultiplayerSession
    {
        internal void SeedPresentation(JsonElement state)
        {
            var options = new JsonSerializerOptions { IncludeFields = true };
            var data = ReadCheckpoint(state.GetProperty("Authority"));
            var expected = ReadCheckpoint(state.GetProperty("Predicted"));
            int level = state.GetProperty("Level").GetInt32(), course = state.GetProperty("Course").GetInt32();
            Status = SessionStatus.Connected; RiderId = data.Id; hasCheckpoint = true;
            raceEpoch = state.GetProperty("RaceEpoch").GetInt32(); sessionEpoch = state.GetProperty("SessionEpoch").GetInt32();
            Room = new LobbyReadModel("isolated", "fixture", "fixture", "", "", LobbyPhase.Racing, 1, raceEpoch, 0, 8, 0, Array.Empty<LobbyMemberReadModel>(), false, course, level);
            authoritative = new RiderCheckpoint(data); heldAnalog = ReadInput(state.GetProperty("HeldAnalog"));
            lastAppliedInputTick = state.GetProperty("LastAppliedTick").GetInt64(); lastTargetTick = state.GetProperty("LastTargetTick").GetInt64();
            lastSnapshotAt = clock.NowSeconds - state.GetProperty("SnapshotAge").GetDouble(); clockAnchorAt = clock.NowSeconds; clockAnchorTick = data.Tick;
            correctionS = state.GetProperty("SmoothingS").GetSingle(); correctionD = state.GetProperty("SmoothingD").GetSingle();
            correctionAt = clock.NowSeconds - .12 * (1 - state.GetProperty("SmoothingRemaining").GetDouble());
            var riders = new List<RaceRiderReadModel> { Model(data) };
            foreach (var row in state.GetProperty("Riders").EnumerateArray())
            {
                var d = ReadCheckpoint(row.GetProperty("State")); int index = predictionNeighbors.RiderCount++;
                RiderCheckpoints.Restore(predictionNeighbors.Riders[index], new RiderCheckpoint(d));
                predictionNeighbors.Acceleration[index] = row.GetProperty("Acceleration").GetInt32();
                predictionNeighbors.LateralVelocity[index] = row.GetProperty("LateralVelocity").GetInt32();
                predictionNeighbors.VerticalVelocity[index] = row.GetProperty("VerticalVelocity").GetInt32(); riders.Add(Model(d));
            }
            foreach (var row in state.GetProperty("Traffic").EnumerateArray())
            {
                var p = predictionNeighbors.Traffic[predictionNeighbors.TrafficCount++];
                p.Id = Int(row, "Id"); p.DistanceMillimeters = Long(row, "DistanceMillimeters"); p.LateralMillimeters = Int(row, "LateralMillimeters");
                p.SpeedMillimetersPerSecond = Int(row, "SpeedMillimetersPerSecond"); p.WidthMillimeters = Int(row, "WidthMillimeters");
                p.LengthMillimeters = Int(row, "LengthMillimeters"); p.HeightMillimeters = Int(row, "HeightMillimeters"); p.Oncoming = row.GetProperty("Oncoming").GetBoolean(); p.Active = true;
            }
            foreach (var row in state.GetProperty("Pedestrians").EnumerateArray())
            {
                var p = predictionNeighbors.Pedestrians[predictionNeighbors.PedestrianCount++]; p.Id = Int(row, "Id");
                p.DistanceMillimeters = Long(row, "DistanceMillimeters"); p.LateralMillimeters = Int(row, "LateralMillimeters"); p.HeightMillimeters = Int(row, "HeightMillimeters");
                p.Mode = (PedestrianMode)Int(row, "Mode"); p.ModeAgeTicks = Int(row, "ModeAgeTicks"); p.FacingSide = Int(row, "FacingSide");
                p.IsCrossing = row.GetProperty("IsCrossing").GetBoolean(); p.WalkingSpeedMillimetersPerSecond = Int(row, "WalkingSpeedMillimetersPerSecond");
            }
            pending.Clear();
            foreach (var row in state.GetProperty("Pending").EnumerateArray()) pending.Add(new InputFrame(Long(row, "Tick"), Int(row, "Sequence"), ReadInput(row.GetProperty("Input"))));
            var track = TrackDefinition.ForCourse(course, level);
            LatestAuthoritativeWorld = new RaceWorldReadModel(data.Tick, 0, track.LengthMillimeters / 1000f, level,
                riders.ToArray(), Array.Empty<RaceTrafficReadModel>(), Array.Empty<RaceEventReadModel>(), Array.Empty<RacePedestrianReadModel>(), course);
            remotes.Add(LatestAuthoritativeWorld); predictor = new RiderPredictor(level, course); predictor.SetNeighbors(predictionNeighbors); ReplayPrediction();
            if (JsonSerializer.Serialize(predictor.Checkpoint.Data, options) != JsonSerializer.Serialize(expected, options))
                throw new InvalidOperationException("Reconstructed predictor does not match the recorded full checkpoint.");
        }
        internal void SetFixtureEvents(JsonElement state)
        {
            events.Clear(); long id = 0;
            foreach (var row in state.GetProperty("Events").EnumerateArray())
                events.Add(new RaceEventReadModel(++id, Long(row, "Tick"), Enum.Parse<RaceEventKind>(row.GetProperty("Kind").GetString()!), Int(row, "SourceId"), Int(row, "TargetId"), Int(row, "Value")));
            eventRevision++;
        }
        internal string GameplayDigest()
        {
            var value = new { authority = authoritative.Data, predicted = predictor.Checkpoint.Data, inputs = pending.Select(p => new { p.Tick, p.Sequence, p.Input }).ToArray() };
            return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(value, new JsonSerializerOptions { IncludeFields = true })));
        }
        private static RaceInput ReadInput(JsonElement input) => new RaceInput(Int(input, "ThrottlePermille"), Int(input, "BrakePermille"), Int(input, "SteerPermille"), Int(input, "AttackSide"), input.GetProperty("Kick").GetBoolean());
        private static RiderCheckpointData ReadCheckpoint(JsonElement value)
        { var data = value.Deserialize<RiderCheckpointData>(new JsonSerializerOptions { IncludeFields = true }); data.Input = ReadInput(value.GetProperty("Input")); return data; }
        private static int Int(JsonElement value, string name) => value.GetProperty(name).GetInt32();
        private static long Long(JsonElement value, string name) => value.GetProperty(name).GetInt64();
        private static RaceRiderReadModel Model(RiderCheckpointData d) => new RaceRiderReadModel(d.Id, d.Kind, d.Mode, d.Weapon, d.AttackWeapon,
            d.DistanceMillimeters / 1000f, d.LateralMillimeters / 1000f, d.SpeedMillimetersPerSecond / 1000f, d.HeightMillimeters / 1000f, d.LeanMillidegrees / 1000f,
            d.BikeDistanceMillimeters / 1000f, d.BikeLateralMillimeters / 1000f, d.BikeHeightMillimeters / 1000f,
            d.Health, GameplayRules.InitialHealth, d.BikeCondition, GameplayRules.InitialBikeCondition, d.Strength, d.Rank, d.FinishTick, d.Reward, d.Qualified,
            d.AttackSide, d.AttackAgeTicks, d.ModeAgeTicks, d.Gear, d.BikeCatalogIndex, d.CharacterCatalogIndex);
    }
}
