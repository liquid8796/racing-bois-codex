using System;
using System.Collections.Generic;
using System.Text;

namespace RacingBois.Client.Application
{
    public readonly struct UiTextArgument
    {
        public string Name { get; }
        public string Value { get; }
        public UiTextArgument(string name, string value)
        { Name = name; Value = value ?? ""; }
    }

    /// <summary>Keyed display templates. Inserted user/catalog values are opaque and are never translated or parsed again.</summary>
    public static partial class UiText
    {
        private static readonly Dictionary<string, string[]> Rows = CreateRows();
        private static Dictionary<string, string[]> CreateRows()
        {
            var rows = new Dictionary<string, string[]>(StringComparer.Ordinal);
            AddMain(rows); AddCareer(rows); AddMultiplayer(rows); AddClientMessages(rows);
            return rows;
        }
        static partial void AddMain(Dictionary<string, string[]> rows);
        static partial void AddCareer(Dictionary<string, string[]> rows);
        static partial void AddMultiplayer(Dictionary<string, string[]> rows);
        static partial void AddClientMessages(Dictionary<string, string[]> rows);
        static partial void TranslateClientMessage(string locale, string raw, ref string translated);
        /// <summary>For client-owned error/status channels only. Unknown text and user/catalog values remain untouched.</summary>
        public static string ClientMessage(string locale, string raw)
        {
            string translated = raw ?? "";
            TranslateClientMessage(DisplayLanguage.Normalize(locale), translated, ref translated);
            return translated;
        }
        public static bool Contains(string key) => key != null && Rows.ContainsKey(key);
        public static string Get(string locale, string key)
        {
            if (key == null || !Rows.TryGetValue(key, out var row)) return "";
            int index;
            switch (DisplayLanguage.Normalize(locale))
            { case "DEU": index = 1; break; case "ESP": index = 2; break; case "FRA": index = 3; break; case "ITA": index = 4; break; case "VI": index = 5; break; default: index = 0; break; }
            return string.IsNullOrEmpty(row[index]) ? row[0] : row[index];
        }
        public static string Format(string locale, string key, params UiTextArgument[] arguments)
        {
            string template = Get(locale, key);
            var values = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var argument in arguments ?? Array.Empty<UiTextArgument>())
            {
                if (string.IsNullOrEmpty(argument.Name) || values.ContainsKey(argument.Name)) throw new ArgumentException("Invalid or duplicate display argument.");
                values.Add(argument.Name, argument.Value ?? "");
            }
            var used = new HashSet<string>(StringComparer.Ordinal); var text = new StringBuilder(template.Length + 32);
            for (int i = 0; i < template.Length; i++)
            {
                char c = template[i];
                if (c == '}') throw new FormatException("Unmatched display-template brace.");
                if (c != '{') { text.Append(c); continue; }
                int end = template.IndexOf('}', i + 1);
                if (end < 0) throw new FormatException("Unclosed display-template argument.");
                string name = template.Substring(i + 1, end - i - 1);
                if (!values.TryGetValue(name, out string value)) throw new ArgumentException("Missing display argument: " + name);
                text.Append(value); used.Add(name); i = end;
            }
            if (used.Count != values.Count) throw new ArgumentException("Unexpected display argument.");
            return text.ToString();
        }
    }
}
