using System;

namespace RacingBois.Client.Application
{
    /// <summary>Pure display-language selection. No global culture, player data or protocol changes.</summary>
    public static class DisplayLanguage
    {
        public const string Default = "VI", Fallback = "ENU";
        public static string Normalize(string value)
        {
            if (string.IsNullOrWhiteSpace(value)) return Fallback;
            string tag = value.Trim().Replace('_', '-').ToUpperInvariant();
            if (tag.Length > 32) return Fallback;
            string[] parts = tag.Split('-'); if (parts.Length > 3) return Fallback;
            for (int i = 1; i < parts.Length; i++)
            {
                if (i == 1 && parts[i].Length == 4 && Ascii(parts[i], false)) continue;
                if (i == parts.Length - 1 && (parts[i].Length == 2 && Ascii(parts[i], false) || parts[i].Length == 3 && Ascii(parts[i], true))) continue;
                return Fallback;
            }
            switch (parts[0])
            {
                case "EN": case "ENG": case "ENU": return "ENU";
                case "DE": case "DEU": case "GER": return "DEU";
                case "ES": case "ESP": case "SPA": return "ESP";
                case "FR": case "FRA": case "FRE": return "FRA";
                case "IT": case "ITA": return "ITA";
                case "VI": case "VIE": return "VI";
                default: return Fallback;
            }
        }
        private static bool Ascii(string value, bool digits)
        { foreach (char c in value) if (digits ? c < '0' || c > '9' : c < 'A' || c > 'Z') return false; return true; }
        public static string FromArguments(string[] arguments) => ResolveOption(arguments, "--language", Default);
        public static string ResolveOption(string[] arguments, string option, string otherwise)
        {
            string selected = null; bool seen = false;
            foreach (string argument in arguments ?? Array.Empty<string>())
            {
                if (argument == null) continue;
                if (argument == option) return Fallback;
                if (!argument.StartsWith(option + "=", StringComparison.Ordinal)) continue;
                if (seen) return Fallback;
                seen = true; selected = argument.Substring(option.Length + 1);
            }
            return seen ? Normalize(selected) : Normalize(otherwise);
        }
    }
}
