using System;
using System.Globalization;

namespace RacingBois.Client.Application
{
    /// <summary>Display copy only. Scene IDs, timing, actors and gameplay remain in the authored catalog.</summary>
    public static partial class CinematicText
    {
        public const string DefaultLocale = "VI";
        public const string FallbackLocale = "ENU";

        public static string NormalizeLocale(string value) => DisplayLanguage.Normalize(value);
        /// <summary>Global --language applies by default; the existing cinematic-specific option remains an explicit override.</summary>
        public static string LocaleFromArguments(string[] arguments)
            => DisplayLanguage.ResolveOption(arguments,"--cinematic-language",DisplayLanguage.FromArguments(arguments));

        public static string Get(string locale, string key)
        {
            if (key == null || !Rows.TryGetValue(key, out var row)) return "";
            int index = LocaleIndex(NormalizeLocale(locale));
            return string.IsNullOrWhiteSpace(row[index]) ? row[0] : row[index];
        }
        public static string Format(string locale, string key, int count)
            => string.Format(CultureInfo.InvariantCulture, Get(locale, key), count);
        public static string Role(string locale, CinematicRole role) => Get(locale, "role." + role);
        public static string Title(string locale, CinematicDefinition scene)
            => scene == null ? "" : WithSource(locale, scene.Id + "/title", scene.Title);
        public static string Synopsis(string locale, CinematicDefinition scene)
            => scene == null ? "" : WithSource(locale, scene.Id + "/synopsis", scene.Synopsis);
        public static string Dialogue(string locale, CinematicDefinition scene, CinematicBeat beat)
        {
            if (beat == null) return "";
            if (scene != null)
                for (int index = 0; index < scene.Beats.Count; index++)
                    if (ReferenceEquals(scene.Beats[index], beat))
                        return WithSource(locale, scene.Id + "/beat/" + index.ToString(CultureInfo.InvariantCulture), beat.Dialogue);
            return beat.Dialogue ?? "";
        }
        private static string WithSource(string locale, string key, string authoredEnglish)
        {
            // A stale generated translation must never silently replace changed authored text.
            if (!Rows.TryGetValue(key, out var row) || !string.Equals(row[0], authoredEnglish, StringComparison.Ordinal))
                return authoredEnglish ?? "";
            return Get(locale, key);
        }
        private static int LocaleIndex(string locale)
        {
            switch (locale) { case "DEU": return 1; case "ESP": return 2; case "FRA": return 3; case "ITA": return 4; case "VI": return 5; default: return 0; }
        }
    }
}
