using System;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    /// <summary>Clips authored for this prefab's rest pose; older prefabs retain the shared fallback.</summary>
    [DisallowMultipleComponent]
    public sealed class RiderAnimationSet : MonoBehaviour
    {
        public const float DefaultFallenRootOffset = -.55f;
        private static readonly string[] Required = { "Ride", "LeanLeft", "LeanRight", "AttackLeft", "AttackRight", "KickLeft", "KickRight", "Hit", "Fall", "Run", "Remount", "Idle" };
        [SerializeField] private AnimationClip[] clips = Array.Empty<AnimationClip>();
        [SerializeField] private float fallenRootOffset = DefaultFallenRootOffset;

        /// <summary>Visual root offset in meters for fallen poses; legacy rigs retain their original placement.</summary>
        public float FallenRootOffset
        {
            get { ValidateFallenRootOffset(fallenRootOffset); return fallenRootOffset; }
        }

        public void Configure(AnimationClip[] source) => Configure(source, DefaultFallenRootOffset);

        public void Configure(AnimationClip[] source, float fallenOffset)
        {
            Validate(source);
            ValidateFallenRootOffset(fallenOffset);
            clips = (AnimationClip[])source.Clone();
            fallenRootOffset = fallenOffset;
        }

        public static AnimationClip[] Resolve(Transform actor, AnimationClip[] fallback)
        {
            var set = actor.GetComponentInChildren<RiderAnimationSet>(true);
            if (set == null) return fallback;
            Validate(set.clips);
            return set.clips;
        }

        public static float ResolveFallenRootOffset(Transform actor)
        {
            var set = actor.GetComponentInChildren<RiderAnimationSet>(true);
            return set == null ? DefaultFallenRootOffset : set.FallenRootOffset;
        }

        public static void ValidateFallenRootOffset(float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value) || value < -1f || value > 1f)
                throw new ArgumentOutOfRangeException(nameof(value), "Fallen visual root offset must be finite and between -1 and 1 meter.");
        }

        private static void Validate(AnimationClip[] source)
        {
            if (source == null) throw new InvalidOperationException("Rider animation override is missing.");
            foreach (string name in Required)
            {
                int matches = 0;
                foreach (var clip in source)
                    if (clip != null && clip.length > 0 && clip.name.EndsWith("RB_" + name, StringComparison.Ordinal)) matches++;
                if (matches != 1) throw new InvalidOperationException("Rider animation override requires exactly one RB_" + name + " clip.");
            }
        }
    }
}
