using RacingBois.Protocol;

namespace RacingBois.Client.Application
{
    public sealed partial class MultiplayerSession
    {
        // A single completed race's unacknowledged input range. Its value-only
        // context survives only the confirmed same-room turnover sequence.
        private readonly struct RetiredInputRange
        {
            public readonly string RoomId;
            public readonly int SessionEpoch, RaceEpoch, First, Last;
            public RetiredInputRange(string roomId, int sessionEpoch, int raceEpoch, int first, int last)
            { RoomId = roomId; SessionEpoch = sessionEpoch; RaceEpoch = raceEpoch; First = first; Last = last; }
            public bool Contains(int sequence) => First > 0 && sequence >= First && sequence <= Last;
        }
        private RetiredInputRange retiredInputRange;
        private void RetireRaceInputs()
        {
            if (Room == null || raceEpoch <= 0 || processedSequence >= sequence) return;
            retiredInputRange = new RetiredInputRange(Room.RoomId, sessionEpoch, raceEpoch, processedSequence + 1, sequence);
        }
        private bool IsRetiredInputError(MpError error)
        {
            if (error.terminal || error.code != "race_epoch" || error.requestId != 0 || error.sessionEpoch != sessionEpoch ||
                retiredInputRange.SessionEpoch != sessionEpoch || !retiredInputRange.Contains(error.sequence) || Room == null ||
                Room.RoomId != retiredInputRange.RoomId) return false;
            if (Room.Phase != LobbyPhase.Results && Room.Phase != LobbyPhase.Lobby && Room.Phase != LobbyPhase.Countdown) return false;
            if (Room.RaceEpoch == retiredInputRange.RaceEpoch) return true;
            // Sequence numbers restart each race and the rejection has no race
            // epoch. Once any new input is sent, preserve every ambiguous error.
            return Room.RaceEpoch == retiredInputRange.RaceEpoch + 1 && sequence == 0;
        }
    }
}
