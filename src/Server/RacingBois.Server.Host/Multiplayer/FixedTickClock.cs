namespace RacingBois.Server.Host.Multiplayer;

/// <summary>Fractional 60 Hz deadlines use monotonic elapsed time; OS timer rounding cannot speed up simulation.</summary>
internal sealed class FixedTickClock
{
    private long accountedTicks;
    private double previousSeconds;
    public long DroppedTicks { get; private set; }
    public int Advance(double elapsedSeconds)
    {
        if (!double.IsFinite(elapsedSeconds) || elapsedSeconds < previousSeconds) throw new ArgumentOutOfRangeException(nameof(elapsedSeconds));
        previousSeconds = elapsedSeconds;
        long dueTotal = checked((long)Math.Floor(elapsedSeconds * 60 + 1e-8));
        long due = dueTotal - accountedTicks; accountedTicks = dueTotal;
        int steps = (int)Math.Min(6, Math.Max(0, due));
        DroppedTicks += Math.Max(0, due - steps);
        return steps;
    }
}
