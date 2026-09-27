using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Fixed 60 Hz authority. Input -> AI -> movement -> swept contacts -> simultaneous combat -> outcome -> rank.</summary>
    public static class RaceSimulation
    {
        public static GameplayWorld CreateDefault(int seed = 1996, int botCount = 5, int level = 0, int courseIndex = 0)
        {
            var world = new GameplayWorld(unchecked((uint)seed), level, courseIndex);
            botCount = Clamp(botCount, 0, 6);
            for (int i = 0; i < botCount; i++)
            {
                var rider = new RaceRider { Id = GameplayRules.BotIdMinimum + i, Kind = RiderKind.Opponent,
                    BikeCatalogIndex = (i * 2 + world.Level * 3 + world.CourseIndex) % BikeCatalog.Count, CharacterCatalogIndex = (i + 1) % CharacterCatalog.Count,
                    DistanceMillimeters = 7500L + i * 6200, LateralMillimeters = i % 2 == 0 ? -1800 : 1800,
                    Weapon = (WeaponKind)(i % 3), AiLane = i % 2 == 0 ? -1800 : 1800 };
                rider.BikeDistanceMillimeters = rider.DistanceMillimeters; rider.BikeLateralMillimeters = rider.LateralMillimeters;
                world.Riders[world.RiderCount++] = rider;
            }
            var police = new RaceRider { BikeCatalogIndex = 6, CharacterCatalogIndex = 3, Id = GameplayRules.PoliceId, Kind = RiderKind.Police, Weapon = WeaponKind.Club,
                DistanceMillimeters = -90000, BikeDistanceMillimeters = -90000, LateralMillimeters = 3000, BikeLateralMillimeters = 3000 };
            world.Riders[world.RiderCount++] = police;
            UpdateRanks(world);
            return world;
        }

        public static RaceRider AddPlayer(GameplayWorld world, int id, int gridSlot = -1)
        {
            if (world == null || id < GameplayRules.PlayerIdMinimum || id >= GameplayRules.BotIdMinimum || FindRider(world, id) != null || world.RiderCount >= GameplayRules.MaxRiders) return null;
            int players = 0;
            for (int i = 0; i < world.RiderCount; i++) if (world.Riders[i].Kind == RiderKind.Player) players++;
            if (players >= GameplayRules.MaxPlayers) return null;
            int slot = gridSlot < 0 ? players : Clamp(gridSlot, 0, 7);
            var rider = new RaceRider { Id = id, Kind = RiderKind.Player, DistanceMillimeters = -slot / 2 * 4000L,
                LateralMillimeters = slot == 0 ? 0 : (slot % 2 == 0 ? -1800 : 1800), LastInputTick = world.Tick };
            rider.BikeDistanceMillimeters = rider.DistanceMillimeters; rider.BikeLateralMillimeters = rider.LateralMillimeters;
            int index = world.RiderCount;
            while (index > 0 && world.Riders[index - 1].Id > id) { world.Riders[index] = world.Riders[index - 1]; index--; }
            world.Riders[index] = rider; world.RiderCount++; UpdateRanks(world);
            return rider;
        }

        public static bool RemovePlayer(GameplayWorld world, int id)
        {
            for (int i = 0; i < world.RiderCount; i++)
                if (world.Riders[i].Id == id && world.Riders[i].Kind == RiderKind.Player)
                { for (int j = i + 1; j < world.RiderCount; j++) world.Riders[j - 1] = world.Riders[j]; world.Riders[--world.RiderCount] = null; UpdateRanks(world); return true; }
            return false;
        }

        public static RaceRider FindRider(GameplayWorld world, int id)
        { for (int i = 0; i < world.RiderCount; i++) if (world.Riders[i].Id == id) return world.Riders[i]; return null; }

        public static bool SetInput(GameplayWorld world, int id, RaceInput input)
        {
            var rider = FindRider(world, id);
            if (rider == null || rider.Kind != RiderKind.Player) return false;
            rider.Input = input; rider.LastInputTick = world.Tick; return true;
        }

        public static void Step(GameplayWorld world, RaceInput[] inputs)
        {
            if (inputs == null) throw new ArgumentNullException(nameof(inputs));
            for (int i = 0; i < world.RiderCount && i < inputs.Length; i++)
                if (world.Riders[i].Kind == RiderKind.Player) { world.Riders[i].Input = inputs[i]; world.Riders[i].LastInputTick = world.Tick; }
            Step(world);
        }

        public static void Step(GameplayWorld world)
        {
            if (world == null) throw new ArgumentNullException(nameof(world));
            world.Tick++; world.EventCount = 0;
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                rider.PreviousDistance = rider.DistanceMillimeters; rider.PreviousLateral = rider.LateralMillimeters;
                rider.PreviousHeight = rider.HeightMillimeters; rider.PreviousBikeDistance = rider.BikeDistanceMillimeters;
                rider.PreviousBikeLateral = rider.BikeLateralMillimeters;
                if (rider.Kind != RiderKind.Player) rider.Input = RaceBrains.Decide(world, rider);
                else if (world.Tick - rider.LastInputTick > 30) rider.Input = default;
                DrivingDynamics.Step(world, rider);
            }
            RaceBrains.StepTraffic(world);
            PedestrianSimulation.Step(world);
            DrivingDynamics.ResolveContacts(world);
            CombatResolver.Step(world);
            RaceBrains.ResolvePolice(world);
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (rider.Kind != RiderKind.Police && GameplayRules.CanDrive(rider.Mode) && rider.DistanceMillimeters >= world.Track.LengthMillimeters)
                {
                    rider.FinishTick = world.Tick; rider.Rank = ++world.FinishedCount;
                    rider.Qualified = rider.Rank <= 3; rider.Reward = RewardForRank(rider.Rank, world.Level);
                    rider.Mode = RiderMode.Finished; rider.ModeAgeTicks = 0; rider.SpeedMillimetersPerSecond = 0;
                    Emit(world, RaceEventKind.Finished, rider.Id, 0, rider.Rank);
                }
            }
            UpdateRanks(world);
        }

        public static int RewardForRank(int oneBasedRank, int level)
        {
            int reward;
            switch (oneBasedRank) { case 1: reward = 1000; break; case 2: reward = 750; break; case 3: reward = 500; break;
                case 4: reward = 400; break; case 5: reward = 300; break; case 6: reward = 250; break; case 7: reward = 200; break;
                case 8: reward = 160; break; case 9: reward = 130; break; case 10: reward = 100; break; case 11: reward = 70; break;
                case 12: reward = 50; break; case 13: reward = 30; break; case 14: reward = 20; break; default: reward = 0; break; }
            return reward * (Clamp(level, 0, 4) + 1);
        }

        private static void UpdateRanks(GameplayWorld world)
        {
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (rider.Kind == RiderKind.Police) { rider.Rank = 0; continue; }
                if (rider.Mode == RiderMode.Finished) continue;
                int rank = world.FinishedCount + 1;
                for (int j = 0; j < world.RiderCount; j++)
                {
                    var other = world.Riders[j];
                    if (other.Kind == RiderKind.Police || other.Mode == RiderMode.Finished || other == rider) continue;
                    if (other.DistanceMillimeters > rider.DistanceMillimeters || (other.DistanceMillimeters == rider.DistanceMillimeters && other.Id < rider.Id)) rank++;
                }
                rider.Rank = rank;
            }
        }

        internal static void Emit(GameplayWorld world, RaceEventKind kind, int actor, int target, int value)
        {
            long id = world.NextEventId++;
            if (world.EventCount < world.Events.Length) world.Events[world.EventCount++] = new RaceEvent(id, world.Tick, kind, actor, target, value);
        }
        internal static int NextRandom(GameplayWorld world)
        { world.RandomState = unchecked(world.RandomState * 214013u + 2531011u); return (int)((world.RandomState >> 16) & 0x7fff); }
        internal static int Clamp(int value, int min, int max) => value < min ? min : value > max ? max : value;
        internal static int Approach(int current, int target, int amount) => current < target ? Math.Min(current + amount, target) : Math.Max(current - amount, target);
    }
}
