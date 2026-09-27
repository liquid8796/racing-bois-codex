using System;
using UnityEngine;

namespace RacingBois.Golden
{
    /// <summary>Restores the audited animation envelope when the inspection prefab is instantiated.</summary>
    public sealed class GoldenSkinBounds : MonoBehaviour
    {
        [Serializable] public sealed class Entry { public SkinnedMeshRenderer Renderer; public Bounds Bounds; }
        public Entry[] Entries = Array.Empty<Entry>();

        private void OnEnable() => Apply();

        public void Apply()
        {
            foreach (var entry in Entries)
                if (entry.Renderer != null) entry.Renderer.localBounds = entry.Bounds;
        }
    }
}
