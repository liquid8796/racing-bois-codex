using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace RacingBois.Client.Presentation
{
    /// <summary>Manual clip sampling follows authoritative state age. No root motion or animation events drive gameplay.</summary>
    public sealed class RiderAnimationView : MonoBehaviour
    {
        private static readonly string[] Names = { "RB_Ride", "RB_LeanLeft", "RB_LeanRight", "RB_AttackLeft", "RB_AttackRight", "RB_KickLeft", "RB_KickRight", "RB_Hit", "RB_Fall", "RB_Run", "RB_Remount", "RB_Idle" };
        private readonly AnimationClipPlayable[] players = new AnimationClipPlayable[12];
        private readonly float[] lengths = new float[12], weights = new float[12];
        private PlayableGraph graph;
        private AnimationMixerPlayable mixer;
        private float cycle;
        private bool initialized;
        public bool Initialize(Transform model, AnimationClip[] clips)
        {
            if (initialized) return true;
            var animator = model.GetComponentInChildren<Animator>(true);
            if (animator == null || clips == null || clips.Length < Names.Length) return false;
            var selected = new AnimationClip[Names.Length];
            for (int i = 0; i < Names.Length; i++)
            {
                foreach (var clip in clips) if (clip != null && clip.name.EndsWith(Names[i], System.StringComparison.Ordinal)) { selected[i] = clip; break; }
                if (selected[i] == null) throw new System.InvalidOperationException("Missing rider clip: " + Names[i]);
            }
            animator.applyRootMotion = false; animator.runtimeAnimatorController = null;
            animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            graph = PlayableGraph.Create("Racing Bois rider"); graph.SetTimeUpdateMode(DirectorUpdateMode.Manual);
            mixer = AnimationMixerPlayable.Create(graph, Names.Length);
            for (int i = 0; i < Names.Length; i++)
            {
                players[i] = AnimationClipPlayable.Create(graph, selected[i]);
                players[i].SetApplyFootIK(false); players[i].SetApplyPlayableIK(false); players[i].SetSpeed(0);
                lengths[i] = Mathf.Max(.001f, selected[i].length);
                graph.Connect(players[i], 0, mixer, i);
            }
            var output = AnimationPlayableOutput.Create(graph, "Rider pose", animator); output.SetSourcePlayable(mixer);
            graph.Play(); initialized = true; weights[0] = 1;
            return true;
        }
        public void Render(RiderMode mode, int side, int attackAge, int modeAge, float speed, bool kick, float lean, float dt)
        {
            if (!initialized) return;
            cycle += Mathf.Clamp(dt, 0, .1f) * (mode == RiderMode.Running ? 1 : .5f + Mathf.Min(1, speed / 58) * .4f);
            int selected = 0; float phase = cycle;
            switch (mode)
            {
                case RiderMode.Attacking: selected = kick ? side < 0 ? 5 : 6 : side < 0 ? 3 : 4; phase = Mathf.Clamp01(attackAge / (float)GameplayRules.AttackDurationTicks) * lengths[selected]; break;
                case RiderMode.Hit: selected = 7; phase = Mathf.Min(lengths[7], modeAge / 60f); break;
                case RiderMode.Falling: case RiderMode.Detached: case RiderMode.Wrecked: selected = 8; phase = mode == RiderMode.Falling ? Mathf.Min(lengths[8], modeAge / 60f) : lengths[8]; break;
                case RiderMode.Running: selected = 9; phase = modeAge / 60f; break;
                case RiderMode.Remounting: selected = 10; phase = Mathf.Clamp01(modeAge / (float)GameplayRules.RemountDurationTicks) * lengths[10]; break;
                case RiderMode.Busted: case RiderMode.Finished: selected = 11; break;
            }
            float leanWeight = selected == 0 ? Mathf.Clamp01(Mathf.Abs(lean) / 35) : 0;
            int leaning = lean < 0 ? 1 : 2;
            float blend = 1 - Mathf.Exp(-Mathf.Clamp(dt, 0, .1f) * 25);
            float total = 0;
            for (int i = 0; i < Names.Length; i++)
            {
                float target = i == selected ? 1 - leanWeight : i == leaning ? leanWeight : 0;
                weights[i] = Mathf.Lerp(weights[i], target, blend); total += weights[i];
                float t = i == selected ? phase : cycle;
                bool loop = i < 3 || i == 9 || i == 11;
                players[i].SetTime(loop ? t % lengths[i] : Mathf.Min(t, lengths[i]));
            }
            for (int i = 0; i < Names.Length; i++) mixer.SetInputWeight(i, weights[i] / Mathf.Max(.0001f, total));
            graph.Evaluate(0);
        }
        public void ResetPose()
        {
            cycle=0;if(!initialized)return;
            for(int i=0;i<players.Length;i++){weights[i]=i==0?1:0;players[i].SetTime(0);mixer.SetInputWeight(i,weights[i]);}
            graph.Evaluate(0);
        }
        private void OnDestroy() { if (graph.IsValid()) graph.Destroy(); }
    }
}
