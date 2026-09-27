using System;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace RacingBois.Client.Presentation
{
    /// <summary>Absolute time sampling for cosmetic scenes; root motion and events do not drive state.</summary>
    internal sealed class CinematicPoseSampler : IDisposable
    {
        private static readonly string[] Names = { "Ride", "LeanLeft", "LeanRight", "AttackLeft", "AttackRight", "KickLeft", "KickRight", "Hit", "Fall", "Run", "Remount", "Idle" };
        private readonly AnimationClipPlayable[] clips = new AnimationClipPlayable[12];
        private readonly float[] lengths = new float[12];
        private PlayableGraph graph;
        private AnimationMixerPlayable mixer;
        public bool SamplingValid { get; private set; }
        public CinematicPoseSampler(Transform model, AnimationClip[] source)
        {
            source = RiderAnimationSet.Resolve(model, source);
            var animator = model.GetComponentInChildren<Animator>(true);
            if (animator == null || source == null) throw new InvalidOperationException("Cinematic actor needs an imported animator and clips.");
            var selected = new AnimationClip[12];
            for (int i = 0; i < Names.Length; i++)
            {
                foreach (var clip in source) if (clip != null && clip.name.EndsWith("RB_" + Names[i], StringComparison.Ordinal)) { selected[i] = clip; break; }
                if (selected[i] == null || selected[i].length <= 0) throw new InvalidOperationException("Missing cinematic clip: " + Names[i]);
            }
            animator.applyRootMotion = false; animator.runtimeAnimatorController = null; animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            graph = PlayableGraph.Create("Racing Bois cinematic pose"); graph.SetTimeUpdateMode(DirectorUpdateMode.Manual);
            mixer = AnimationMixerPlayable.Create(graph, 12);
            for (int i = 0; i < 12; i++)
            {
                lengths[i] = selected[i].length; clips[i] = AnimationClipPlayable.Create(graph, selected[i]);
                clips[i].SetApplyFootIK(false); clips[i].SetApplyPlayableIK(false); clips[i].SetSpeed(0); graph.Connect(clips[i], 0, mixer, i);
            }
            AnimationPlayableOutput.Create(graph, "Cinematic actor", animator).SetSourcePlayable(mixer); graph.Play(); Sample("Idle", 0);
        }
        public void Sample(string action, float seconds)
        {
            int index = Array.IndexOf(Names, action); if (index < 0) index = 11;
            bool loop = index <= 2 || index == 9 || index == 11;
            float time = loop ? Mathf.Repeat(Mathf.Max(0, seconds), lengths[index]) : Mathf.Clamp(seconds, 0, lengths[index]);
            SamplingValid = !float.IsNaN(time) && !float.IsInfinity(time) && time >= 0 && time <= lengths[index];
            for (int i = 0; i < 12; i++) { mixer.SetInputWeight(i, i == index ? 1 : 0); clips[i].SetTime(i == index ? time : 0); }
            graph.Evaluate(0);
        }
        public void Dispose() { if (graph.IsValid()) graph.Destroy(); }
    }
}
