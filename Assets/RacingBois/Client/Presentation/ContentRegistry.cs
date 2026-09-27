using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using UnityEngine;
namespace RacingBois.Client.Presentation
{
    /// <summary>Loaded presentation assets only. No project-wide Resources scan and no authority state.</summary>
    public static class ContentRegistry
    {
        private static readonly IReadOnlyList<GameObject> empty = Array.AsReadOnly(new GameObject[0]);
        private static readonly IReadOnlyDictionary<string, AudioClip> emptyClips = new ReadOnlyDictionary<string, AudioClip>(new Dictionary<string, AudioClip>());
        public static P08ActorContent Actors { get; private set; }
        public static P08RouteContent Route { get; private set; }
        public static string MusicId { get; private set; } = "";
        public static string MusicUrl { get; private set; } = "";
        public static IReadOnlyList<GameObject> Bikes { get; private set; } = empty;
        public static IReadOnlyList<GameObject> Riders { get; private set; } = empty;
        public static IReadOnlyDictionary<string, AudioClip> Sfx { get; private set; } = emptyClips;
        public static IReadOnlyDictionary<string, AudioClip> Voices { get; private set; } = emptyClips;
        public static bool ReadyFor(int course) => Actors != null && Route != null && Route.CourseIndex == course && MusicId == Route.RouteMusicId && !string.IsNullOrEmpty(MusicUrl);
        public static void SetActors(P08ActorContent value)
        {
            value.Validate(); Actors = value;
            Bikes = Array.AsReadOnly((GameObject[])value.Bikes.Clone()); Riders = Array.AsReadOnly((GameObject[])value.Riders.Clone());
            Sfx = Index(value.Library.Sfx); Voices = Index(value.Library.Voices);
        }
        public static void SetRoute(P08RouteContent value, string musicId, string musicUrl)
        { if (value == null || string.IsNullOrEmpty(musicId) || string.IsNullOrEmpty(musicUrl)) throw new ArgumentException("A complete route and its music binding are required."); Route = value; MusicId = musicId; MusicUrl = musicUrl; }
        public static void ClearRoute() { Route = null; MusicId = MusicUrl = ""; }
        public static void Clear()
        { ClearRoute(); Actors = null; Bikes = Riders = empty; Sfx = Voices = emptyClips; }
        private static IReadOnlyDictionary<string, AudioClip> Index(P08NamedClip[] entries)
        { var result = new Dictionary<string, AudioClip>(StringComparer.Ordinal); foreach (var item in entries) result.Add(item.Id,item.Clip); return new ReadOnlyDictionary<string,AudioClip>(result); }
    }
}
