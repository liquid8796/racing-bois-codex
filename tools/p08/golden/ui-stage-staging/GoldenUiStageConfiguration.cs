#if UNITY_EDITOR
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Explicit candidate inputs and measured screen composition; no production catalog overrides.</summary>
    public sealed class GoldenUiStageConfiguration
    {
        public string ApexPrefab = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Apex_v8_r2.prefab";
        public string AshPrefab = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Ash_V3.prefab";
        public string CanyonPrefab = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Canyon_v14.prefab";
        public string WorkshopPrefab;
        public Sprite[] RenderedBikeThumbnails;
        public Vector3 CanyonEuler = new Vector3(0, 180, 0);
        public Vector3 BikePosition = Vector3.zero;
        public Vector3 BikeEuler = Vector3.zero;
        public Vector3 StandingRiderPosition = new Vector3(.35f, 0, -.12f);
        public Vector3 StandingRiderEuler = Vector3.zero;
        public Vector3 CameraDirection = new Vector3(-1, .40f, 1.60f);
        public float MainVerticalFov = 35;
        public float GarageVerticalFov = 35;
        // Measured visual subject bounds in the locked 1672x941 images.
        // Rects use Unity bottom-left normalized coordinates, not UI top-left pixels.
        public Rect MainSubjectRect = new Rect(806f / 1672, 52f / 941, 802f / 1672, 810f / 941);
        public Rect GarageSubjectRect = new Rect(593f / 1672, 216f / 941, 857f / 1672, 547f / 941);
        public const float ReferenceAspect = 1672f / 941;
        public const string MainConceptSha256 = "9b7ad175234636c591846552178f2d25a279434763ce5d0f252af738c6c8e95e";
        public const string GarageConceptSha256 = "65b237da2f4a13b554de13d5a70ec2c3aed995e9cba5c95af6601ca7d0201ef5";
    }
}
#endif
