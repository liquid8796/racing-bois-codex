using UnityEngine;

namespace RacingBois.Client.Presentation
{
    [CreateAssetMenu(menuName = "Racing Bois/Audio Bank", fileName = "RB_P06_AudioBank")]
    public sealed class RaceAudioBank : ScriptableObject
    {
        public AudioClip EngineLow, EngineHigh, Tire, Gravel, Wind, Ambient, Music;
        public AudioClip Impact, Crash, WeaponClub, WeaponFist, WeaponChain, WeaponSwing, Shift;
        public AudioClip UiConfirm, UiBack, Finish;
        public bool IsComplete => HasGameplayEffects && Music != null;
        public bool HasGameplayEffects => EngineLow != null && EngineHigh != null && Tire != null && Gravel != null &&
            Wind != null && Ambient != null && Impact != null && Crash != null &&
            WeaponClub != null && WeaponFist != null && WeaponChain != null && WeaponSwing != null &&
            Shift != null && UiConfirm != null && UiBack != null && Finish != null;
    }
}
