using System;
using System.Collections.Generic;

namespace RacingBois.Client.Application
{
    /// <summary>Immutable presentation values in road-space meters, detached from mutable wire DTOs.</summary>
    public readonly struct RiderReadModel
    {
        public string Id { get; }
        public float LongitudinalMeters { get; }
        public float LateralMeters { get; }
        public float SpeedMetersPerSecond { get; }

        public RiderReadModel(string id, float longitudinalMeters, float lateralMeters, float speedMetersPerSecond)
        {
            Id = id;
            LongitudinalMeters = longitudinalMeters;
            LateralMeters = lateralMeters;
            SpeedMetersPerSecond = speedMetersPerSecond;
        }
    }

    /// <summary>One validated authoritative observation. A later update replaces this object.</summary>
    public sealed class WorldReadModel
    {
        public long Tick { get; }
        public int AcknowledgedInputSequence { get; }
        public IReadOnlyList<RiderReadModel> Riders { get; }

        internal WorldReadModel(long tick, int acknowledgedInputSequence, RiderReadModel[] riders)
        {
            Tick = tick;
            AcknowledgedInputSequence = acknowledgedInputSequence;
            // Neither callers nor views retain a mutable alias to the collection backing this observation.
            Riders = Array.AsReadOnly((RiderReadModel[])riders.Clone());
        }
    }
}
