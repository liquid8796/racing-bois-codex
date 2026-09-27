using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;

int checks = 0;
void Check(bool value, string label) { if (!value) throw new InvalidOperationException(label); checks++; }
string folder = Path.GetFullPath("tools/p08/media/global-copy-client-staging");
var rows = File.ReadAllLines(Path.Combine(folder, "author-client.tsv")).Select(line => line.Split('\t')).ToArray();
string[] locales = { "VI", "ENU", "DEU", "ESP", "FRA", "ITA" };
foreach (var row in rows)
{
    string key = row[0], original = row[1];
    Check(UiText.Contains(key), "key present");
    for (int i = 0; i < locales.Length; i++)
    {
        Check(UiText.Get(locales[i], key) == row[i + 1], "authored language projection: " + key);
        if (key != "content.route.loading")
        {
            Check(UiText.ClientMessage(locales[i], original) == row[i + 1], "scoped exact-message classifier");
            Check(UiText.ClientMessage(locales[i], " " + original) == " " + original, "no trimmed arbitrary match");
            Check(UiText.ClientMessage(locales[i], "player: " + original) == "player: " + original, "inserted user data is opaque");
        }
    }
}
foreach (string locale in locales)
{
    for (int i = 0; i < CampaignCatalog.RouteCount; i++)
    {
        string name = CampaignCatalog.GetRoute(i).DisplayName;
        Check(UiText.ClientMessage(locale, "Đang tải " + name + "…") ==
            UiText.Format(locale, "content.route.loading", new UiTextArgument("route", name)), "known route status");
    }
    foreach (string raw in new[] { "", "unknown", "Đang tải Player-owned route…", "Máy chủ từ chối: room_full", "Mã phòng không hợp lệ. extra" })
        Check(UiText.ClientMessage(locale, raw) == raw, "unknown/protocol text unchanged");
    Check(UiText.ClientMessage(locale, null) == "", "null channel input");
    string value = "Mã phòng không hợp lệ. {route} <player>";
    Check(UiText.Format(locale, "content.route.loading", new UiTextArgument("route", value)).Contains(value, StringComparison.Ordinal), "argument is not recursively parsed/localized");
}
Check(UiText.ClientMessage("unsupported", rows[0][1]) == rows[0][2], "unsupported locale uses ENU");
Console.WriteLine(JsonSerializer.Serialize(new { passed = true, checks, keys = rows.Length, locales = locales.Length,
    scope = "Pure scoped-copy projection using actual staged shared formatter and installed route catalog. No runtime authority or UI rendering." }));
