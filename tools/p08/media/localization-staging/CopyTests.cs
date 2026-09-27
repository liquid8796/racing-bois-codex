using RacingBois.Client.Application;
using System.Text.Json;

int assertions = 0;
void Check(bool condition, string name)
{ if (!condition) throw new Exception(name); assertions++; }
string root = Directory.GetCurrentDirectory();
string localeRoot = Path.Combine(root, "tools/p08/media/localization-staging/locales");
string[] locales = { "ENU", "DEU", "ESP", "FRA", "ITA", "VI" };
foreach (string locale in locales)
{
    using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(localeRoot, locale + ".json")));
    var strings = document.RootElement.GetProperty("strings");
    Check(strings.EnumerateObject().Count() == CinematicText.KeyCount, locale + " key count");
    foreach (var item in strings.EnumerateObject()) Check(CinematicText.Get(locale, item.Name) == item.Value.GetString(), locale + "/" + item.Name);
    foreach (var scene in CinematicCatalog.All)
    {
        Check(CinematicText.Title(locale, scene) == strings.GetProperty(scene.Id + "/title").GetString(), "title projection");
        Check(CinematicText.Synopsis(locale, scene) == strings.GetProperty(scene.Id + "/synopsis").GetString(), "synopsis projection");
        for (int index = 0; index < scene.Beats.Count; index++)
            Check(CinematicText.Dialogue(locale, scene, scene.Beats[index]) == strings.GetProperty(scene.Id + "/beat/" + index).GetString(), "beat identity projection");
    }
    foreach (CinematicRole role in Enum.GetValues<CinematicRole>()) Check(!string.IsNullOrWhiteSpace(CinematicText.Role(locale, role)), "role coverage");
    Check(CinematicText.Format(locale, "ui.summary", 59).Contains("59") && !CinematicText.Format(locale, "ui.shots", 7).Contains("{0}"), "count formatting");
}
var first = CinematicCatalog.All[0];
Check(CinematicText.Title("unsupported", first) == first.Title, "unknown locale uses exact English");
Check(CinematicText.Get("VI", "unknown-key") == "", "unknown key does not leak an internal identifier");
Check(CinematicText.Get("VI", null) == "", "null key");
Check(CinematicText.Title("VI", null) == "" && CinematicText.Dialogue("VI", first, null) == "", "null scene/beat");
var changed = new CinematicDefinition(first.Id, "Changed authored English", "Changed synopsis", first.Role, first.Variant,
    first.DurationSeconds, first.BikeIndex, first.CharacterIndex, first.MusicId, first.Beats.ToArray());
Check(CinematicText.Title("VI", changed) == changed.Title && CinematicText.Synopsis("DEU", changed) == changed.Synopsis, "stale localized text cannot hide changed English");
var beat = first.Beats[0];
var changedBeat = new CinematicBeat(beat.StartSeconds, beat.DurationSeconds, beat.Shot, beat.CameraFrom, beat.CameraTo, beat.LookAtFrom, beat.LookAtTo,
    beat.FieldOfViewFrom, beat.FieldOfViewTo, beat.SpeakerSlot, "Changed dialogue", beat.ParticipantMask, beat.Transition, beat.TransitionSeconds, beat.Actors.ToArray());
var changedScene = new CinematicDefinition(first.Id, first.Title, first.Synopsis, first.Role, first.Variant, first.DurationSeconds, first.BikeIndex, first.CharacterIndex, first.MusicId, changedBeat);
Check(CinematicText.Dialogue("ITA", changedScene, changedBeat) == changedBeat.Dialogue, "stale beat translation rejected");
Check(CinematicText.Dialogue("VI", first, changedBeat) == changedBeat.Dialogue, "foreign beat cannot borrow another scene/index");
Check(CinematicText.NormalizeLocale("fr-CA") == "FRA" && CinematicText.NormalizeLocale("de_DE") == "DEU" && CinematicText.NormalizeLocale("es") == "ESP", "locale aliases");
Check(CinematicText.NormalizeLocale("de-Latn-DE") == "DEU" && CinematicText.NormalizeLocale("es-419") == "ESP", "script and numeric-region tags");
foreach (string invalid in new[] { "DEU-", "fr-???", "it--IT", "de-DE-DE", "fr-1234", "vi-US-extra", "fr-" + new string('A', 40) })
    Check(CinematicText.NormalizeLocale(invalid) == "ENU", "malformed culture tag fallback: " + invalid);
Check(CinematicText.LocaleFromArguments(Array.Empty<string>()) == "VI", "existing UI default");
Check(CinematicText.LocaleFromArguments(new[] { "game.exe", "--cinematic-language=it-IT" }) == "ITA", "desktop selection");
Check(CinematicText.LocaleFromArguments(new[] { "--cinematic-language=" }) == "ENU", "blank explicit choice fallback");
Check(CinematicText.LocaleFromArguments(new[] { "--cinematic-language=VI", "--cinematic-language=DEU" }) == "ENU", "ambiguous choice fallback");
Check(CinematicText.LocaleFromArguments(new[] { "--cinematic-language", "VI" }) == "ENU", "malformed option fallback");
Console.WriteLine($"PASS {assertions} exact display-copy assertions across six locales, 59 scenes and 389 beats; no native or linguistic acceptance.");
