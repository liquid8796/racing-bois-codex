using System;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
namespace RacingBois.Client.Presentation
{
    [CreateAssetMenu(menuName = "Racing Bois/P08 Actor Content")]
    public sealed class P08ActorContent : ScriptableObject
    {
        public GameObject[] Bikes = new GameObject[BikeCatalog.Count];
        public GameObject[] Riders = new GameObject[CharacterCatalog.Count];
        public Sprite[] Portraits = new Sprite[CharacterCatalog.Count * 3];
        public GameObject PoliceBike, PoliceRider, Coupe, Van, Pedestrian, Club;
        public GameObject[] TrafficExtras = new GameObject[0];
        public AnimationClip[] RiderClips = new AnimationClip[0];
        public P08ContentLibrary Library;
        public void Validate()
        {
            if (Bikes == null || Bikes.Length != BikeCatalog.Count || Riders == null || Riders.Length != CharacterCatalog.Count)
                throw new InvalidOperationException("Actor catalog count differs from content contract.");
            for (int i = 0; i < Bikes.Length; i++) if (Bikes[i] == null) throw new InvalidOperationException("Missing production bike " + i);
            for (int i = 0; i < Riders.Length; i++) if (Riders[i] == null) throw new InvalidOperationException("Missing production rider " + i);
            if (Portraits == null || Portraits.Length != CharacterCatalog.Count * 3) throw new InvalidOperationException("Portrait catalog count differs from content contract.");
            foreach (var portrait in Portraits) if (portrait == null) throw new InvalidOperationException("Missing character portrait state.");
            if (PoliceBike == null || PoliceRider == null || Coupe == null || Van == null || Pedestrian == null || Club == null || RiderClips == null || RiderClips.Length != 12)
                throw new InvalidOperationException("Actor pack is incomplete.");
            foreach (var clip in RiderClips) if (clip == null) throw new InvalidOperationException("Missing rider clip.");
            if (Library == null || Library.AudioBank == null || !Library.AudioBank.HasGameplayEffects) throw new InvalidOperationException("Actor audio bank is incomplete.");
            if (Library.AudioBank.Music != null) throw new InvalidOperationException("Full music belongs to streamed media, not the actor bundle.");
            Library.Validate();
        }
    }
}
