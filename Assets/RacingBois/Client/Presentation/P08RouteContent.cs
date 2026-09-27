using System;
using UnityEngine;
namespace RacingBois.Client.Presentation
{
    [CreateAssetMenu(menuName = "Racing Bois/P08 Route Content")]
    public sealed class P08RouteContent : ScriptableObject
    {
        public int CourseIndex;
        public GameObject[] Props = new GameObject[6];
        public GameObject Guardrail, Chevron, UtilityPole;
        public Material Asphalt, Shoulder, Landscape, Paint, YellowPaint, Wire, Water, Skybox;
        public Color FogColor = new Color(.5f,.58f,.66f), AmbientColor = new Color(.48f,.51f,.58f), SunColor = Color.white;
        public float FogDensity = .0012f, SunIntensity = 1.2f;
        public Vector3 SunEuler = new Vector3(38,-28,0);
        public string RouteMusicId = "";
        public void Validate(int expectedCourse)
        {
            if (CourseIndex != expectedCourse || CourseIndex < 0 || CourseIndex > 4 || Props == null || Props.Length != 6)
                throw new InvalidOperationException("Route identity or prop count differs from manifest.");
            foreach (var prop in Props) if (prop == null) throw new InvalidOperationException("Missing route production prop.");
            if (Asphalt == null || Shoulder == null || Landscape == null || Paint == null || YellowPaint == null || Skybox == null)
                throw new InvalidOperationException("Route material or sky is incomplete.");
            if (string.IsNullOrEmpty(RouteMusicId) || !Finite(FogDensity) || !Finite(SunIntensity) || !Finite(SunEuler.x) || !Finite(SunEuler.y) || !Finite(SunEuler.z) || !ValidColor(FogColor) || !ValidColor(AmbientColor) || !ValidColor(SunColor) || FogDensity < 0 || FogDensity > .02f || SunIntensity < 0 || SunIntensity > 4)
                throw new InvalidOperationException("Route atmosphere or music binding invalid.");
        }
        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static bool ValidColor(Color value) => Finite(value.r) && Finite(value.g) && Finite(value.b) && Finite(value.a);
    }
}
