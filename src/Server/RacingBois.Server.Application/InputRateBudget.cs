namespace RacingBois.Server.Application;

/// <summary>Bounded per-connection ingress burst budget, driven by an explicit monotonic clock.</summary>
public sealed class InputRateBudget
{
    public const int SustainedMessagesPerSecond = 90;
    public const int BurstCapacity = 180;
    private double available = BurstCapacity;
    private double lastSeconds;

    public bool TryConsume(double elapsedSeconds)
    {
        if (!double.IsFinite(elapsedSeconds) || elapsedSeconds < 0) throw new ArgumentOutOfRangeException(nameof(elapsedSeconds));
        // Clock rollback cannot refill tokens or move the refill origin backwards.
        double now = Math.Max(elapsedSeconds, lastSeconds);
        available = Math.Min(BurstCapacity, available + (now - lastSeconds) * SustainedMessagesPerSecond);
        lastSeconds = now;
        if (available < 1) return false;
        available -= 1;
        return true;
    }
}
