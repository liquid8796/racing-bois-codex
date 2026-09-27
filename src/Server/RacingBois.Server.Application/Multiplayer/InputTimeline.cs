using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Server.Application.Multiplayer;

public sealed class InputTimeline
{
    private readonly Queue<MpInput> frames = new();
    private int lastReceivedSequence;
    private long lastReceivedTick;
    public int LastProcessedSequence { get; private set; }
    public long LastAppliedInputTick { get; private set; } = -100;
    public RaceInput HeldAnalog { get; private set; }
    public int LateInputs { get; private set; }
    public int FutureInputs { get; private set; }
    public int MissingInputs { get; private set; }
    public int Count => frames.Count;

    public string? Add(MpInput input, long resolvedTick)
    {
        if (input.sequence <= lastReceivedSequence || input.sequence - (long)lastReceivedSequence > 256 || input.targetTick <= lastReceivedTick) return "input_sequence";
        if (input.throttlePermille is < 0 or > 1000 || input.brakePermille is < 0 or > 1000 || input.steerPermille is < -1000 or > 1000 || input.attackSide is < -1 or > 1) return "input_range";
        if (input.targetTick > resolvedTick + MultiplayerProtocol.FutureInputTicks) { FutureInputs++; return "input_future"; }
        if (frames.Count >= MultiplayerProtocol.InputQueueCapacity) return "input_queue_full";
        lastReceivedSequence = input.sequence; lastReceivedTick = input.targetTick;
        if (input.targetTick <= resolvedTick)
        {
            LateInputs++; LastProcessedSequence = Math.Max(LastProcessedSequence, input.sequence); return "input_late";
        }
        frames.Enqueue(input); return null;
    }
    public RaceInput Sample(long tick)
    {
        while (frames.Count > 0 && frames.Peek().targetTick < tick)
        { var expired = frames.Dequeue(); LastProcessedSequence = expired.sequence; LateInputs++; }
        if (frames.Count > 0 && frames.Peek().targetTick == tick)
        {
            var frame = frames.Dequeue(); LastProcessedSequence = frame.sequence; LastAppliedInputTick = tick;
            HeldAnalog = new RaceInput(frame.throttlePermille, frame.brakePermille, frame.steerPermille);
            return new RaceInput(frame.throttlePermille, frame.brakePermille, frame.steerPermille, frame.attackSide, frame.kick);
        }
        MissingInputs++;
        return tick - LastAppliedInputTick <= MultiplayerProtocol.AnalogHoldTicks ? HeldAnalog : default;
    }
    public void ResetEpoch()
    {
        frames.Clear(); lastReceivedSequence = LastProcessedSequence = 0; lastReceivedTick = 0;
        LastAppliedInputTick = -100; HeldAnalog = default;
    }
    public void Suspend() { frames.Clear(); LastAppliedInputTick = -100; HeldAnalog = default; }
}
