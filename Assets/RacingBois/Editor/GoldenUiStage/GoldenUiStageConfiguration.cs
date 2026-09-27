#if UNITY_EDITOR
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Explicit candidate inputs and measured screen composition; no production catalog overrides.</summary>
    public sealed class GoldenUiStageConfiguration
    {
        public string ApexPrefab = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Apex_r4.prefab";
        public string AshPrefab = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Ash_V4.prefab";
        public string MainRiderClipSource = "Assets/RacingBois/Art/P08/Golden/Ash/V4/RB_Golden_Ash_V4.fbx";
        public string MainRiderClipName = "RB_P06_Rider_Rig|RB_MenuHero";
        public string EnvironmentPrefab = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_MenuEnvironment_v1.prefab";
        public string WorkshopPrefab;
        public string WorkshopScenePath = "Assets/RacingBois/Golden/Generated/Garage/RB_Golden_Garage_v7_cca745fcc809/GarageReview.unity";
        public string WorkshopRoomIdentity = "RB_Golden_Garage_v7";
        public bool GarageDepthOfField = true;
        public string ReviewPipeline = "Assets/RacingBois/Golden/Generated/StudioReviewPipeline.asset";
        public string MainSkyMaterial = "Assets/RacingBois/Golden/Generated/Materials/GoldenEnvironmentSky.mat";
        public float MainSkyRotation = 270f;
        public float MainSkyExposure = .6f;
        public Vector3 MainSunDirection = new Vector3(-.35650545f, .10412163f, -.92847323f);
        public Sprite[] RenderedBikeThumbnails;
        public Vector3 EnvironmentPosition = new Vector3(0, .0249681473f, 0);
        public Vector3 EnvironmentEuler = Vector3.zero;
        public Vector3 BikePosition = Vector3.zero;
        public Vector3 BikeEuler = Vector3.zero;
        public Vector3 StandingRiderPosition = new Vector3(-.30f, 0, -.25f);
        public Vector3 StandingRiderEuler = Vector3.zero;
        public Vector3 CameraDirection = new Vector3(1.6f, .32f, 1f);
        public Vector3 GarageCameraDirection = new Vector3(0, .17f, -1f);
        public Vector3 GarageBikeEuler = new Vector3(0, 122, 0);
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
