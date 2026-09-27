using System;
using System.Numerics;

namespace RacingBois.Client.Presentation
{
    /// <summary>
    /// Renderer-only candidate with a finite visible-error window. New authority/read-model
    /// targets are never changed. A discontinuity preserves the last displayed transform;
    /// its render offset fades with zero endpoint slope in at most300ms. Camera filter state
    /// must rebase by RawTargetShift and apply PositionOffset, preventing camera/actor separation.
    /// </summary>
    public sealed class TimedVisualTransformReconciler
    {
        private Vector3 previousTarget, startOffset;
        private Quaternion previousRotation = Quaternion.Identity, startRotationOffset = Quaternion.Identity;
        private float elapsed, duration;
        private bool initialized, wasFrozen;
        public Vector3 Position { get; private set; }
        public Quaternion Rotation { get; private set; } = Quaternion.Identity;
        public Vector3 PositionOffset { get; private set; }
        public Vector3 RawTargetShift { get; private set; }
        public bool BeganReconciliation { get; private set; }
        public float RemainingSeconds => Math.Max(0, duration - elapsed);
        public float RemainingTranslation => PositionOffset.Length();
        public int ReconciliationCount { get; private set; }

        public void Reset(Vector3 target, Quaternion rotation)
        {
            Validate(target, rotation); Position = previousTarget = target; Rotation = previousRotation = Quaternion.Normalize(rotation);
            PositionOffset = startOffset = RawTargetShift = Vector3.Zero; startRotationOffset = Quaternion.Identity;
            elapsed = duration = 0; initialized = true; wasFrozen = false; BeganReconciliation = false;
        }
        public void Sample(Vector3 target, Quaternion rotation, float deltaSeconds, float continuousSpeedBound,
            bool discretePoseChanged, bool frozen = false, bool reset = false)
        {
            Validate(target, rotation);
            if (!float.IsFinite(deltaSeconds) || deltaSeconds < 0 || !float.IsFinite(continuousSpeedBound) || continuousSpeedBound < 0)
                throw new ArgumentOutOfRangeException(nameof(deltaSeconds));
            rotation = Quaternion.Normalize(rotation); BeganReconciliation = false; RawTargetShift = Vector3.Zero;
            if (!initialized || reset) { Reset(target, rotation); return; }
            if (frozen) { wasFrozen = true; return; }
            float dt = Math.Min(.1f, deltaSeconds);
            var change = target - previousTarget;
            bool largeStep = change.Length() > .35f + continuousSpeedBound * dt;
            bool largeTurn = Angle(rotation * Quaternion.Inverse(previousRotation)) > .08f + 12.5663706f * dt;
            bool rebase = wasFrozen || discretePoseChanged || largeStep || largeTurn;
            previousTarget = target; previousRotation = rotation; wasFrozen = false;
            if (rebase)
            {
                startOffset = PositionOffset = Position - target;
                startRotationOffset = Quaternion.Normalize(Rotation * Quaternion.Inverse(rotation));
                duration = Math.Clamp(.08f + Math.Max(startOffset.Length() / 100, Angle(startRotationOffset) / 12.5663706f), .12f, .30f);
                elapsed = 0; RawTargetShift = change; BeganReconciliation = true; ReconciliationCount++;
                return;
            }
            elapsed = Math.Min(duration, elapsed + dt);
            float u = duration <= 0 ? 1 : elapsed / duration;
            float remaining = (1 - u) * (1 - u) * (1 + 2 * u);
            PositionOffset = startOffset * remaining; Position = target + PositionOffset;
            Rotation = Quaternion.Normalize(Quaternion.Slerp(Quaternion.Identity, startRotationOffset, remaining) * rotation);
        }
        private static float Angle(Quaternion value) => 2 * (float)Math.Acos(Math.Min(1, Math.Abs(Quaternion.Normalize(value).W)));
        private static void Validate(Vector3 position, Quaternion rotation)
        {
            if (!float.IsFinite(position.X) || !float.IsFinite(position.Y) || !float.IsFinite(position.Z) ||
                !float.IsFinite(rotation.X) || !float.IsFinite(rotation.Y) || !float.IsFinite(rotation.Z) || !float.IsFinite(rotation.W) || rotation.LengthSquared() < .000001f)
                throw new ArgumentException("Invalid visual target.");
        }
    }
}
