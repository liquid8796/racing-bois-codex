using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        private static IEnumerable<ClipSpec> AllClips(AssetSpec spec) =>
            (spec.clips ?? Array.Empty<ClipSpec>()).Concat(spec.previewClips ?? Array.Empty<ClipSpec>());

        private static void ApplyAnimationPolicy(ModelImporter importer, AssetSpec spec)
        {
            // Older descriptors retain their exact import policy. A new policy is explicit
            // and does not add menu-only clips to the gameplay animation set.
            if (spec.kind != "rider" || spec.loopClips == null) return;
            var clips = importer.clipAnimations;
            if (clips.Length == 0) clips = importer.defaultClipAnimations;
            var names = AllClips(spec).Select(clip => clip.name).ToArray();
            Require(clips.Length == names.Length && clips.All(clip => names.Count(name => name == clip.name) == 1),
                "Explicit animation policy does not cover the imported clip set.");
            foreach (var clip in clips)
            {
                clip.loopTime = spec.loopClips.Contains(clip.name);
                clip.loopPose = false; // Preserve the authored endpoint; do not synthesize a pose correction.
                clip.lockRootRotation = true; clip.lockRootHeightY = true; clip.lockRootPositionXZ = true;
                clip.keepOriginalOrientation = true; clip.keepOriginalPositionY = true; clip.keepOriginalPositionXZ = true;
            }
            importer.clipAnimations = clips;
        }
    }
}
