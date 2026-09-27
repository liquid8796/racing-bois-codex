using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;

int checks = 0;
void Check(bool value, string label) { if (!value) throw new Exception(label); checks++; }
string stage = Path.GetFullPath("tools/p08/media/global-copy-multiplayer-staging");
using var source = JsonDocument.Parse(File.ReadAllText(Path.Combine(stage, "canonical-source.json")));
foreach (string locale in new[] { "ENU", "DEU", "ESP", "FRA", "ITA", "VI" })
{
    using var translation = locale == "VI" ? null : JsonDocument.Parse(File.ReadAllText(Path.Combine(stage, "locales", locale + ".json")));
    foreach (var entry in source.RootElement.GetProperty("entries").EnumerateArray())
    {
        string key = entry.GetProperty("key").GetString();
        string expected = locale == "VI" ? entry.GetProperty("vi").GetString() : translation.RootElement.GetProperty("entries").GetProperty(key).GetString();
        Check(UiText.Get(locale, key) == expected, locale + ": exact keyed projection " + key);
        var arguments = new List<UiTextArgument>();
        foreach (var name in entry.GetProperty("arguments").EnumerateArray())
        {
            string token = name.GetString(); string opaque = "<user:{not-a-key}:" + token + ":Cùng lên đường>";
            arguments.Add(new UiTextArgument(token, opaque)); expected = expected.Replace("{" + token + "}", opaque, StringComparison.Ordinal);
        }
        Check(UiText.Format(locale, key, arguments.ToArray()) == expected, locale + ": opaque named arguments " + key);
        foreach (var binding in entry.GetProperty("bindings").EnumerateArray())
            if (binding.TryGetProperty("serverCodes", out var codes))
                foreach (var code in codes.EnumerateArray())
                    Check(MultiplayerCopy.Error("Máy chủ từ chối: " + code.GetString(), locale) == UiText.Get(locale, key), locale + ": raw server code " + code);
    }
    Check(MultiplayerCopy.Error("Máy chủ từ chối: not_a_known_code", locale) == UiText.Get(locale, "multiplayer.error.unknown"), locale + ": unknown typed code fallback");
    const string raw = "room_full <Player {level}> Cùng lên đường";
    Check(MultiplayerCopy.Error(raw, locale) == raw, locale + ": unknown raw display value remains opaque");
}
bool missing = false, extra = false, duplicate = false;
try { UiText.Format("DEU", "multiplayer.level.current"); } catch (ArgumentException) { missing = true; }
try { UiText.Format("ESP", "multiplayer.ready", new UiTextArgument("unexpected", "x")); } catch (ArgumentException) { extra = true; }
try { UiText.Format("ITA", "multiplayer.level.current", new UiTextArgument("level", "1"), new UiTextArgument("level", "2")); } catch (ArgumentException) { duplicate = true; }
Check(missing && extra && duplicate, "invalid argument sets reject at display boundary");
Console.WriteLine($"PASS {checks} exact six-locale projection, opaque-value and raw-code boundary checks; no native UI acceptance.");
