using UnityEngine;
using NVector = System.Numerics.Vector3;
using NRotation = System.Numerics.Quaternion;

namespace RacingBois.Client.Presentation
{
    /// <summary>Unity value conversion; owns no simulation or GameObject.</summary>
    internal sealed class UnityVisualPoseEnvelope
    {
        private readonly VisualPoseEnvelope value = new VisualPoseEnvelope();
        internal Vector3 Offset => Unity(value.PositionOffset);
        internal Vector3 RawTargetShift => Unity(value.RawTargetShift);
        internal bool BeganReconciliation => value.BeganReconciliation;
        internal bool ResetThisSample => value.ResetThisSample;
        internal VisualPoseResetReason ResetReason => value.ResetReason;
        internal double RemainingSeconds => value.RemainingSeconds;
        internal int HardResetCount => value.HardResetCount;
        internal void Sample(Vector3 position, Quaternion rotation, double now, float speedBound,
            bool poseChanged, bool frozen, bool reset, out Vector3 shown, out Quaternion orientation)
        {
            value.Sample(new NVector(position.x, position.y, position.z), new NRotation(rotation.x, rotation.y, rotation.z, rotation.w),
                now, speedBound, poseChanged, frozen, reset);
            shown = Unity(value.Position); var q = value.Rotation; orientation = new Quaternion(q.X, q.Y, q.Z, q.W);
        }
        private static Vector3 Unity(NVector p) => new Vector3(p.X, p.Y, p.Z);
    }
}
