using UnityEngine;
using NVector = System.Numerics.Vector3;
using NRotation = System.Numerics.Quaternion;

namespace RacingBois.Client.Presentation
{
    /// <summary>Unity conversion boundary for renderer-only continuity; owns no GameObject or simulation state.</summary>
    internal sealed class UnityVisualTransformReconciler
    {
        private readonly TimedVisualTransformReconciler state = new TimedVisualTransformReconciler();
        public bool BeganReconciliation => state.BeganReconciliation;
        public Vector3 Offset => Unity(state.PositionOffset);
        public Vector3 RawTargetShift => Unity(state.RawTargetShift);
        public void Sample(Vector3 target, Quaternion rotation, float deltaTime, bool modeChanged, bool frozen, bool reset,
            out Vector3 position, out Quaternion orientation)
        {
            state.Sample(new NVector(target.x, target.y, target.z), new NRotation(rotation.x, rotation.y, rotation.z, rotation.w),
                deltaTime, 100, modeChanged, frozen, reset);
            position = Unity(state.Position); var q = state.Rotation; orientation = new Quaternion(q.X, q.Y, q.Z, q.W);
        }
        private static Vector3 Unity(NVector value) => new Vector3(value.X, value.Y, value.Z);
    }
}
