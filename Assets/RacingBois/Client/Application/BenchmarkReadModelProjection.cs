using System;
using System.Collections.Generic;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    /// <summary>Authoring benchmark adapter; uses the production projection without exposing mutable state to views.</summary>
    public static class BenchmarkReadModelProjection
    {
        public static RaceRiderReadModel Rider(RaceRider rider)
        {
            if (rider == null) throw new ArgumentNullException(nameof(rider));
            return RaceStateProjection.Rider(rider);
        }

        public static RaceWorldReadModel World(GameplayWorld world, IReadOnlyList<RaceEvent> events)
        {
            if (world == null) throw new ArgumentNullException(nameof(world));
            if (events == null) throw new ArgumentNullException(nameof(events));
            var projected = new RaceEventReadModel[events.Count];
            for (int i = 0; i < projected.Length; i++)
            {
                var item = events[i];
                projected[i] = new RaceEventReadModel(item.Id, item.Tick, item.Kind, item.ActorId, item.TargetId, item.Value);
            }
            return RaceStateProjection.World(world, 0, projected);
        }
    }
}
