using System;
using System.Numerics;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{

    /// <summary>
    /// Bounded renderer-only error envelope. Neither targets nor gameplay state
    /// are changed. Ordinary movement is direct; discontinuities retain the last
    /// displayed pose, then remove a finite offset. Hard resets remain observable.
    /// </summary>
    public sealed class VisualPoseEnvelope20Comparison
    {
        public const float MaximumOffsetMeters = 10f;
        public const float MaximumCorrectionSpeed = 20f;
        public const float MaximumAngularCorrectionSpeed = 16f;
        public const double MinimumDurationSeconds = .12;
        public const double MaximumDurationSeconds = .75;
        public const double MaximumBurstSeconds = 1.2;
        public const double MaximumFrameGapSeconds = .25;
        private Vector3 previousTarget, startOffset;
        private Quaternion previousRotation = Quaternion.Identity, startRotationOffset = Quaternion.Identity;
        private double lastAt, startedAt, duration, burstAt, frozenAt;
        private bool initialized, wasFrozen;

        public Vector3 Position { get; private set; }
        public Quaternion Rotation { get; private set; } = Quaternion.Identity;
        public Vector3 PositionOffset { get; private set; }
        public Vector3 RawTargetShift { get; private set; }
        public bool BeganReconciliation { get; private set; }
        public bool ResetThisSample { get; private set; }
        public VisualPoseResetReason ResetReason { get; private set; }
        public double RemainingSeconds { get; private set; }
        public double ActiveAgeSeconds { get; private set; }
        public int ReconciliationCount { get; private set; }
        public int HardResetCount { get; private set; }

        public void Reset(Vector3 target, Quaternion rotation, double now)
        {
            Validate(target, rotation, now, 0);
            ResetTo(target, Quaternion.Normalize(rotation), now, VisualPoseResetReason.ExplicitReset);
        }

        public void Sample(Vector3 target, Quaternion rotation, double now, float continuousSpeedBound,
            bool discretePoseChanged = false, bool frozen = false, bool reset = false)
        {
            Validate(target, rotation, now, continuousSpeedBound);
            rotation = Quaternion.Normalize(rotation);
            Vector3 change = initialized ? target - previousTarget : Vector3.Zero;
            float distance = change.Length();
            if (!Finite(change) || !float.IsFinite(distance))
                throw new ArgumentException("Visual target difference is not finite.");
            BeganReconciliation = ResetThisSample = false; ResetReason = VisualPoseResetReason.None; RawTargetShift = Vector3.Zero;
            if (!initialized || reset)
            { ResetTo(target, rotation, now, initialized ? VisualPoseResetReason.ExplicitReset : VisualPoseResetReason.Initialization); return; }
            double elapsedFrame = now - lastAt;
            if (elapsedFrame < 0) { ResetTo(target, rotation, now, VisualPoseResetReason.ClockRewind); return; }
            if (frozen)
            {
                if (!wasFrozen) frozenAt = now;
                wasFrozen = true; lastAt = now;
                return;
            }
            if (wasFrozen && now - frozenAt > MaximumFrameGapSeconds)
            { ResetTo(target, rotation, now, VisualPoseResetReason.FrozenResume); return; }
            if (elapsedFrame > MaximumFrameGapSeconds)
            { ResetTo(target, rotation, now, VisualPoseResetReason.ClockGap); return; }
            if (distance > MaximumOffsetMeters + continuousSpeedBound * elapsedFrame)
            { ResetTo(target, rotation, now, VisualPoseResetReason.Teleport); return; }
            bool discontinuity = wasFrozen || discretePoseChanged || distance > .35f + continuousSpeedBound * elapsedFrame ||
                Angle(rotation * Quaternion.Inverse(previousRotation)) > .08f + MaximumAngularCorrectionSpeed * elapsedFrame;
            bool previousActive = duration > 0 && now < startedAt + duration;
            previousTarget = target; previousRotation = rotation; lastAt = now; wasFrozen = false;
            if (discontinuity)
            {
                Vector3 wantedOffset = Position - target;
                Quaternion wantedRotation = Quaternion.Normalize(Rotation * Quaternion.Inverse(rotation));
                float translation = wantedOffset.Length(), angle = Angle(wantedRotation);
                if (!float.IsFinite(translation) || translation > MaximumOffsetMeters)
                { ResetTo(target, rotation, now, VisualPoseResetReason.OffsetBudget); return; }
                if (translation < .00001f && angle < .00001f)
                { SetDirect(target, rotation); return; }
                double wantedDuration = Math.Max(MinimumDurationSeconds,
                    Math.Max(1.5 * translation / MaximumCorrectionSpeed, 1.5 * angle / MaximumAngularCorrectionSpeed));
                double firstAt = previousActive ? burstAt : now;
                if (wantedDuration > MaximumDurationSeconds || now + wantedDuration > firstAt + MaximumBurstSeconds + 1e-9)
                { ResetTo(target, rotation, now, VisualPoseResetReason.BurstBudget); return; }
                burstAt = firstAt; startedAt = now; duration = wantedDuration;
                startOffset = PositionOffset = wantedOffset; startRotationOffset = wantedRotation;
                RawTargetShift = change; BeganReconciliation = true; ReconciliationCount++;
                RemainingSeconds = duration; ActiveAgeSeconds = now - burstAt;
                return;
            }
            double u = duration <= 0 ? 1 : Math.Min(1, Math.Max(0, (now - startedAt) / duration));
            float remaining = (float)((1 - u) * (1 - u) * (1 + 2 * u));
            PositionOffset = startOffset * remaining; Position = target + PositionOffset;
            Rotation = Quaternion.Normalize(Quaternion.Slerp(Quaternion.Identity, startRotationOffset, remaining) * rotation);
            RemainingSeconds = Math.Max(0, startedAt + duration - now);
            ActiveAgeSeconds = RemainingSeconds > 0 ? now - burstAt : 0;
            if (u >= 1) SetDirect(target, rotation);
        }

        private void ResetTo(Vector3 target, Quaternion rotation, double now, VisualPoseResetReason reason)
        {
            Position = previousTarget = target; Rotation = previousRotation = rotation;
            SetDirect(target, rotation); RawTargetShift = Vector3.Zero;
            lastAt = startedAt = burstAt = now; initialized = true; wasFrozen = false;
            BeganReconciliation = false; ResetThisSample = true; ResetReason = reason;
            if (reason != VisualPoseResetReason.Initialization && reason != VisualPoseResetReason.ExplicitReset) HardResetCount++;
        }
        private void SetDirect(Vector3 target, Quaternion rotation)
        {
            Position = target; Rotation = rotation; PositionOffset = startOffset = Vector3.Zero;
            startRotationOffset = Quaternion.Identity; duration = RemainingSeconds = ActiveAgeSeconds = 0;
        }
        private static float Angle(Quaternion value)
            => 2 * (float)Math.Acos(Math.Min(1, Math.Abs(Quaternion.Normalize(value).W)));
        private static bool Finite(Vector3 value) => float.IsFinite(value.X) && float.IsFinite(value.Y) && float.IsFinite(value.Z);
        private static void Validate(Vector3 position, Quaternion rotation, double now, float speed)
        {
            if (!Finite(position) || !float.IsFinite(position.LengthSquared()) || !float.IsFinite(rotation.X) || !float.IsFinite(rotation.Y) || !float.IsFinite(rotation.Z) ||
                !float.IsFinite(rotation.W) || !float.IsFinite(rotation.LengthSquared()) || rotation.LengthSquared() < .000001f ||
                !double.IsFinite(now) || now < 0 || !float.IsFinite(speed) || speed < 0)
                throw new ArgumentException("Invalid visual pose or clock.");
        }
    }
}
