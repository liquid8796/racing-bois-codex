using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using RacingBois.Client.Application;

static class Program
{
    private static void Require(bool value, string failure) { if (!value) throw new InvalidOperationException(failure); }
    public static void Main(string[] args)
    {
        string stage = Path.GetFullPath(args[0]);
        using var canonical = JsonDocument.Parse(File.ReadAllText(Path.Combine(stage, "canonical-source.json")));
        var entries = canonical.RootElement.GetProperty("entries").EnumerateArray().ToArray();
        string[] locales = { "ENU", "DEU", "ESP", "FRA", "ITA", "VI" };
        string[] aliases = { "en-US", "de-DE", "es-ES", "fr-FR", "it-IT", "vi-VN" };
        int assertions = 0, formattedCells = 0;
        var english = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int language = 0; language < locales.Length; language++)
        {
            string locale = locales[language];
            string path = locale == "VI" ? Path.Combine(stage, "VI.json") : Path.Combine(stage, "locales", locale + ".json");
            using var data = JsonDocument.Parse(File.ReadAllText(path));
            var texts = data.RootElement.GetProperty("strings");
            foreach (var entry in entries)
            {
                string key = entry.GetProperty("key").GetString();
                string expected = texts.GetProperty(key).GetString();
                if (locale == "ENU") english.Add(key, expected);
                Require(UiText.Contains(key), "Missing generated key: " + key); assertions++;
                Require(UiText.Get(locale, key) == expected, "Generated translation differs: " + locale + "/" + key); assertions++;
                Require(UiText.Get(aliases[language], key) == expected, "Locale alias lookup differs: " + key); assertions++;
                string[] names = entry.GetProperty("arguments").EnumerateArray().Select(value => value.GetString()).ToArray();
                var values = names.ToDictionary(name => name, name => "Ω_" + name + "_{literal}<name>", StringComparer.Ordinal);
                var parameters = names.Reverse().Select(name => new UiTextArgument(name, values[name])).ToArray();
                string expanded = Regex.Replace(expected, @"\{([A-Za-z][A-Za-z0-9]*)\}", match => values[match.Groups[1].Value]);
                Require(UiText.Format(locale, key, parameters) == expanded, "Opaque named formatting differs: " + locale + "/" + key); assertions++;
                if (names.Length > 0) formattedCells++;
            }
        }
        foreach (var entry in entries)
        {
            string key = entry.GetProperty("key").GetString();
            Require(UiText.Get("unsupported", key) == english[key], "English fallback differs: " + key); assertions++;
            Require(UiText.Get("fr--FR", key) == english[key], "Malformed locale fallback differs: " + key); assertions++;
        }
        var result = new { passed = true, keys = entries.Length, locales = 6, explicitCells = entries.Length * 6,
            assertions, formattedCells, providerOrder = locales, missingTranslationCells = 0,
            scope = "Managed exact six-locale generated lookup, aliases, English fallback and opaque formatting. No native UI rendering or language-quality acceptance." };
        string json = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(args[1], json + "\n"); Console.WriteLine(json);
    }
}
