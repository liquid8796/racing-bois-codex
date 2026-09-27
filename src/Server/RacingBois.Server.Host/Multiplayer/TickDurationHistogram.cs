namespace RacingBois.Server.Host.Multiplayer;

/// <summary>Constant-memory cumulative latency buckets. Percentiles are bucket upper bounds, not exact samples.</summary>
internal sealed class TickDurationHistogram
{
    private static readonly double[] Bounds = [0.05, 0.1, 0.25, 0.5, 1, 2, 4, 6, 8, 10, 12, 16.667, 25, 50, 100, 250, double.PositiveInfinity];
    private readonly long[] buckets = new long[Bounds.Length];

    public void Record(double milliseconds)
    {
        int index = 0;
        while (index < Bounds.Length - 1 && milliseconds > Bounds[index]) index++;
        Interlocked.Increment(ref buckets[index]);
    }

    public object Snapshot()
    {
        var values = new long[buckets.Length];
        for (int i = 0; i < values.Length; i++) values[i] = Interlocked.Read(ref buckets[i]);
        long samples = values.Sum();
        return new
        {
            samples,
            p50UpperBoundMilliseconds = Percentile(values, samples, 0.5),
            p95UpperBoundMilliseconds = Percentile(values, samples, 0.95),
            p99UpperBoundMilliseconds = Percentile(values, samples, 0.99),
            overflowSamples = values[^1],
            bucketUpperBoundsMilliseconds = Bounds.Select(value => double.IsFinite(value) ? (double?)value : null).ToArray(),
            bucketCounts = values
        };
    }

    private static double? Percentile(long[] values, long samples, double fraction)
    {
        if (samples == 0) return null;
        long target = (long)Math.Ceiling(samples * fraction), seen = 0;
        for (int i = 0; i < values.Length; i++)
        {
            seen += values[i];
            if (seen >= target) return double.IsFinite(Bounds[i]) ? Bounds[i] : null;
        }
        return null;
    }
}
