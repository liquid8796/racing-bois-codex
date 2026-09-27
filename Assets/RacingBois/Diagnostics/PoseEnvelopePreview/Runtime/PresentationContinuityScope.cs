using System;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    /// <summary>Render lifetime identity. These values never grant authority.</summary>
    public readonly struct PresentationContinuityScope
    {
        public readonly int SessionEpoch, RaceEpoch, RiderId;
        public readonly string RoomId;
        public readonly bool Frozen;
        public readonly long CorrectionRevision;
        public readonly float RawCorrectionMeters;
        public bool IsValid => SessionEpoch > 0 && RaceEpoch > 0 && RiderId > 0 && !string.IsNullOrEmpty(RoomId);
        public PresentationContinuityScope(int sessionEpoch, int raceEpoch, string roomId, int riderId, bool frozen,
            long correctionRevision = 0, float rawCorrectionMeters = 0)
        {
            if (!float.IsFinite(rawCorrectionMeters) || rawCorrectionMeters < 0) throw new ArgumentException("Invalid presentation correction observation.");
            SessionEpoch = sessionEpoch; RaceEpoch = raceEpoch; RoomId = roomId ?? ""; RiderId = riderId; Frozen = frozen;
            CorrectionRevision = correctionRevision; RawCorrectionMeters = rawCorrectionMeters;
        }
        public bool DetachedCorrectionSince(long previousRevision, bool detached) => detached && CorrectionRevision > 0 &&
            CorrectionRevision != previousRevision && RawCorrectionMeters >= 1f;
        public bool SameIdentity(PresentationContinuityScope other) => IsValid && other.IsValid &&
            SessionEpoch == other.SessionEpoch && RaceEpoch == other.RaceEpoch && RiderId == other.RiderId &&
            string.Equals(RoomId, other.RoomId, StringComparison.Ordinal);
    }
}
