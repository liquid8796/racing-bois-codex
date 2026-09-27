using System;
using System.Numerics;

namespace RacingBois.Client.Presentation
{
    /// <summary>
    /// Candidate renderer-only continuity state. It never writes an authority checkpoint,
    /// prediction, input, health, outcome or read model. Ordinary target motion is unchanged.
    /// Large/mode-changing targets retain the last visible transform, then shed a bounded
    /// visual offset. The offset is a visible error budget, not a corrected gameplay state.
    /// </summary>
    public sealed class VisualTransformReconciler
    {
        private const float PositionEpsilon = .001f;
        private const float AngleEpsilon = .001f;
        private readonly float translationSpeed, translationTime, angularSpeed, angularTime;
        private Vector3 offset, previousTarget;
        private Quaternion rotationOffset = Quaternion.Identity, previousRotation = Quaternion.Identity;
        private bool initialized, wasFrozen;
        public Vector3 Position { get; private set; }
        public Quaternion Rotation { get; private set; } = Quaternion.Identity;
        public float RemainingTranslation => offset.Length();
        public float RemainingAngle => Angle(rotationOffset);
        public int ReconciliationCount { get; private set; }
        public bool BeganReconciliation { get; private set; }

        public VisualTransformReconciler(float maximumTranslationCorrectionSpeed = 20, float translationDecaySeconds = .12f,
            float maximumAngularCorrectionRadiansPerSecond = 12.5663706f, float angularDecaySeconds = .07f)
        {
            if (!Positive(maximumTranslationCorrectionSpeed) || !Positive(translationDecaySeconds) ||
                !Positive(maximumAngularCorrectionRadiansPerSecond) || !Positive(angularDecaySeconds))
                throw new ArgumentOutOfRangeException(nameof(maximumTranslationCorrectionSpeed));
            translationSpeed = maximumTranslationCorrectionSpeed; translationTime = translationDecaySeconds;
            angularSpeed = maximumAngularCorrectionRadiansPerSecond; angularTime = angularDecaySeconds;
        }
        public void Reset(Vector3 target, Quaternion rotation)
        {
            Validate(target, rotation); Position = previousTarget = target;
            Rotation = previousRotation = Quaternion.Normalize(rotation);
            offset = Vector3.Zero; rotationOffset = Quaternion.Identity;
            initialized = true; wasFrozen = false; BeganReconciliation = false;
        }

        public void Sample(Vector3 target, Quaternion rotation, float deltaSeconds, float continuousSpeedBound,
            bool discretePoseChanged, bool frozen = false, bool reset = false)
        {
            Validate(target, rotation);
            if (!float.IsFinite(deltaSeconds) || deltaSeconds < 0 || !float.IsFinite(continuousSpeedBound) || continuousSpeedBound < 0)
                throw new ArgumentOutOfRangeException(nameof(deltaSeconds));
            rotation = Quaternion.Normalize(rotation); BeganReconciliation = false;
            if (!initialized || reset) { Reset(target, rotation); return; }
            if (frozen) { wasFrozen = true; return; }
            float dt = Math.Min(.1f, deltaSeconds);
            // 35 cm permits fixed-tick/float quantization without softening ordinary steering.
            bool largeStep = Vector3.Distance(target, previousTarget) > .35f + continuousSpeedBound * dt;
            bool largeTurn = Angle(rotation * Quaternion.Inverse(previousRotation)) > .08f + angularSpeed * dt;
            bool rebase = wasFrozen || discretePoseChanged || largeStep || largeTurn;
            previousTarget = target; previousRotation = rotation; wasFrozen = false;
            if (rebase)
            {
                offset = Position - target;
                rotationOffset = Quaternion.Normalize(Rotation * Quaternion.Inverse(rotation));
                BeganReconciliation = true; ReconciliationCount++;
                // No movement on the discontinuity sample itself. Decay begins on later frames.
                return;
            }
            float distance = offset.Length();
            if (distance <= PositionEpsilon) offset = Vector3.Zero;
            else
            {
                float step = Math.Min(translationSpeed * dt, distance * (1 - (float)Math.Exp(-dt / translationTime)));
                offset *= Math.Max(0, 1 - step / distance);
            }
            float angle = Angle(rotationOffset);
            if (angle <= AngleEpsilon) rotationOffset = Quaternion.Identity;
            else
            {
                float step = Math.Min(angularSpeed * dt, angle * (1 - (float)Math.Exp(-dt / angularTime)));
                rotationOffset = Quaternion.Normalize(Quaternion.Slerp(rotationOffset, Quaternion.Identity, Math.Min(1, step / angle)));
            }
            Position = target + offset;
            Rotation = Quaternion.Normalize(rotationOffset * rotation);
        }
        private static bool Positive(float value) => float.IsFinite(value) && value > 0;
        private static float Angle(Quaternion value)
            => 2 * (float)Math.Acos(Math.Min(1, Math.Abs(Quaternion.Normalize(value).W)));
        private static void Validate(Vector3 position, Quaternion rotation)
        {
            if (!float.IsFinite(position.X) || !float.IsFinite(position.Y) || !float.IsFinite(position.Z) ||
                !float.IsFinite(rotation.X) || !float.IsFinite(rotation.Y) || !float.IsFinite(rotation.Z) || !float.IsFinite(rotation.W) || rotation.LengthSquared() < .000001f)
                throw new ArgumentException("Non-finite or invalid visual target.");
        }
    }
}
