using System;
using System.Collections.Generic;
using UnityEngine;
namespace RacingBois.Client.Presentation
{
    [Serializable] public sealed class P08NamedClip { public string Id; public AudioClip Clip; }
    [CreateAssetMenu(menuName = "Racing Bois/P08 Content Library")]
    public sealed class P08ContentLibrary : ScriptableObject
    {
        public RaceAudioBank AudioBank;
        public P08NamedClip[] Sfx = new P08NamedClip[0];
        public P08NamedClip[] Voices = new P08NamedClip[0];
        public void Validate()
        {
            ValidateClips(Sfx); ValidateClips(Voices);
        }
        private static void ValidateClips(P08NamedClip[] clips)
        {
            if (clips == null || clips.Length > 256) throw new InvalidOperationException("Audio library exceeds its bounded catalog.");
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var item in clips) if (item == null || string.IsNullOrWhiteSpace(item.Id) || item.Id.Length > 64 || item.Clip == null || !ids.Add(item.Id))
                throw new InvalidOperationException("Audio library has invalid or duplicate bindings.");
        }
    }
}
