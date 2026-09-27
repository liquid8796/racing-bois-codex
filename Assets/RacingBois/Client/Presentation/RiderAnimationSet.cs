using System;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    /// <summary>Clips authored for this prefab's rest pose; older prefabs retain the shared fallback.</summary>
    [DisallowMultipleComponent]
    public sealed class RiderAnimationSet : MonoBehaviour
    {
        private static readonly string[] Required = { "Ride", "LeanLeft", "LeanRight", "AttackLeft", "AttackRight", "KickLeft", "KickRight", "Hit", "Fall", "Run", "Remount", "Idle" };
        [SerializeField] private AnimationClip[] clips = Array.Empty<AnimationClip>();

        public void Configure(AnimationClip[] source)
        {
            Validate(source);
            clips = (AnimationClip[])source.Clone();
        }

        public static AnimationClip[] Resolve(Transform actor, AnimationClip[] fallback)
        {
            var set = actor.GetComponentInChildren<RiderAnimationSet>(true);
            if (set == null) return fallback;
            Validate(set.clips);
            return set.clips;
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
