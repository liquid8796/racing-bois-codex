using System;
using System.Globalization;

namespace RacingBois.Client.Application
{
    /// <summary>Display copy only. Scene IDs, timing, actors and gameplay remain in the authored catalog.</summary>
    public static partial class CinematicText
    {
        public const string DefaultLocale = "VI";
        public const string FallbackLocale = "ENU";

        public static string NormalizeLocale(string value)
        {
            if (string.IsNullOrWhiteSpace(value)) return FallbackLocale;
            string tag = value.Trim().Replace('_', '-').ToUpperInvariant();
            if (tag.Length > 32) return FallbackLocale;
            string[] parts = tag.Split('-');
            if (parts.Length > 3) return FallbackLocale;
            // Supported culture form: language, optional four-letter script, optional region (AA or 123).
            for (int i = 1; i < parts.Length; i++)
            {
                if (i == 1 && parts[i].Length == 4 && Ascii(parts[i], false)) continue;
                if (i == parts.Length - 1 && (parts[i].Length == 2 && Ascii(parts[i], false) || parts[i].Length == 3 && Ascii(parts[i], true))) continue;
                return FallbackLocale;
            }
            tag = parts[0];
            switch (tag)
            {
                case "EN": case "ENG": case "ENU": return "ENU";
                case "DE": case "DEU": case "GER": return "DEU";
                case "ES": case "ESP": case "SPA": return "ESP";
                case "FR": case "FRA": case "FRE": return "FRA";
                case "IT": case "ITA": return "ITA";
                case "VI": case "VIE": return "VI";
                default: return FallbackLocale;
            }
        }

        private static bool Ascii(string value, bool digits)
        {
            foreach (char c in value) if (digits ? c < '0' || c > '9' : c < 'A' || c > 'Z') return false;
            return true;
        }

        /// <summary>There is no game-wide language selector yet. No argument preserves the current Vietnamese UI.</summary>
        public static string LocaleFromArguments(string[] arguments)
        {
            const string option = "--cinematic-language";
            string selected = null; bool seen = false;
            foreach (string argument in arguments ?? Array.Empty<string>())
            {
                if (argument == null) continue;
                if (argument == option) return FallbackLocale; // The documented form requires an explicit equals value.
                if (!argument.StartsWith(option + "=", StringComparison.Ordinal)) continue;
                if (seen) return FallbackLocale;
                seen = true; selected = argument.Substring(option.Length + 1);
            }
            return seen ? NormalizeLocale(selected) : DefaultLocale;
        }

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
