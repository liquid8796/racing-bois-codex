using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    /// <summary>Validated visual state and immutable private prediction context from one snapshot.</summary>
    internal sealed class MultiplayerSnapshotReadModel
    {
        public RaceWorldReadModel World { get; }
        public IReadOnlyDictionary<int, long> CollisionUntilByRider { get; }
        public IReadOnlyDictionary<int, PedestrianPredictionContext> PedestrianContexts { get; }
        public IReadOnlyDictionary<int, RiderCombatPredictionContext> RiderCombatContexts { get; }
        public MultiplayerSnapshotReadModel(RaceWorldReadModel world, IDictionary<int, long> collisionUntilByRider, IDictionary<int, PedestrianPredictionContext> pedestrianContexts, IDictionary<int, RiderCombatPredictionContext> riderCombatContexts)
        {
            World = world ?? throw new ArgumentNullException(nameof(world));
            if (collisionUntilByRider == null) throw new ArgumentNullException(nameof(collisionUntilByRider));
            CollisionUntilByRider = new ReadOnlyDictionary<int, long>(new Dictionary<int, long>(collisionUntilByRider));
            if (pedestrianContexts == null) throw new ArgumentNullException(nameof(pedestrianContexts));
            PedestrianContexts = new ReadOnlyDictionary<int, PedestrianPredictionContext>(new Dictionary<int, PedestrianPredictionContext>(pedestrianContexts));
            if (riderCombatContexts == null) throw new ArgumentNullException(nameof(riderCombatContexts));
            RiderCombatContexts = new ReadOnlyDictionary<int, RiderCombatPredictionContext>(new Dictionary<int, RiderCombatPredictionContext>(riderCombatContexts));
        }
    }
}
