using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEditor;
public static class NativeCopyProbe { public static object Run() {
// Method body for root-owned native execution AFTER installing the reviewed runtime.
// Uses only the tool default wrapper imports; custom and UI Toolkit types are fully qualified.
// This deliberately exercises only an unattached UI tree, not a rendered scene or actual playback.
var preview = UnityEditor.SceneManagement.EditorSceneManager.NewPreviewScene();
GameObject owned = null;
int checks = 0, titles = 0, captions = 0, filters = 0;
Action<bool, string> check = (passed, reason) => { if (!passed) throw new InvalidOperationException(reason); checks++; };
try
{
    owned = new GameObject("Cinematic copy probe / " + Guid.NewGuid().ToString("N"));
    owned.hideFlags = HideFlags.HideAndDontSave;
    UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(owned, preview);
    var document = owned.AddComponent<UnityEngine.UIElements.UIDocument>();
    check(document.panelSettings == null, "Fixture must have no PanelSettings");
    check(document.rootVisualElement != null && document.rootVisualElement.panel == null, "Fixture must have an unattached root");
    var director = owned.AddComponent<RacingBois.Client.Presentation.CinematicDirector>();
    var gallery = owned.AddComponent<RacingBois.Client.Presentation.CinematicGalleryView>();
    gallery.SetLocale("ITA");
    gallery.Initialize(document, director);
    check(gallery.Locale == "ITA", "Pre-initialize locale choice is retained");
    var surface = document.rootVisualElement;
    var filter = UnityEngine.UIElements.UQueryExtensions.Q<UnityEngine.UIElements.DropdownField>(surface, "cinematic-filter");
    var list = UnityEngine.UIElements.UQueryExtensions.Q<UnityEngine.UIElements.ScrollView>(surface, "cinematic-list");
    var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
    var select = typeof(RacingBois.Client.Presentation.CinematicGalleryView).GetMethod("Select", flags);
    var buildList = typeof(RacingBois.Client.Presentation.CinematicGalleryView).GetMethod("BuildList", flags);
    Func<string, UnityEngine.UIElements.Label> label = field => (UnityEngine.UIElements.Label)typeof(RacingBois.Client.Presentation.CinematicGalleryView).GetField(field, flags).GetValue(gallery);
    Func<RacingBois.Client.Application.CinematicDefinition> selected = () => (RacingBois.Client.Application.CinematicDefinition)typeof(RacingBois.Client.Presentation.CinematicGalleryView).GetField("selected", flags).GetValue(gallery);
    string[] locales = { "ENU", "DEU", "ESP", "FRA", "ITA", "VI" };
    foreach (string locale in locales)
    {
        gallery.SetLocale(locale); filter.index = 0;
        // Unattached DropdownField setters do not dispatch ChangeEvent. Exercise the real rebuild explicitly;
        // this fixture verifies filtering/binding only and makes no UI input-dispatch claim.
        buildList.Invoke(gallery, null);
        check(gallery.Locale == locale && filter.choices.Count == 12, "Locale/filter identity");
        check(UnityEngine.UIElements.UQueryExtensions.Q<UnityEngine.UIElements.Button>(surface, "cinematic-play").text == RacingBois.Client.Application.CinematicText.Get(locale, "ui.play"), "Localized play control");
        check(UnityEngine.UIElements.UQueryExtensions.Q<UnityEngine.UIElements.Button>(surface, "cinematic-close").text == RacingBois.Client.Application.CinematicText.Get(locale, "ui.close"), "Localized back control");
        check(UnityEngine.UIElements.UQueryExtensions.Q<UnityEngine.UIElements.Button>(surface, "cinematic-skip").text == RacingBois.Client.Application.CinematicText.Get(locale, "ui.skip"), "Localized skip control");
        int entries = 0; foreach (var child in list.contentContainer.Children()) if (child is UnityEngine.UIElements.Button) entries++;
        check(entries == RacingBois.Client.Application.CinematicCatalog.All.Count, "All actual gallery entries exist");
        foreach (var scene in RacingBois.Client.Application.CinematicCatalog.All)
        {
            var button = UnityEngine.UIElements.UQueryExtensions.Q<UnityEngine.UIElements.Button>(surface, "cinematic-option-" + scene.Id);
            check(button != null && button.text == RacingBois.Client.Application.CinematicText.Title(locale, scene), "Localized list title: " + scene.Id);
            select.Invoke(gallery, new object[] { scene });
            check(label("detailTitle").text == RacingBois.Client.Application.CinematicText.Title(locale, scene), "Localized detail title");
            check(label("detailBody").text == RacingBois.Client.Application.CinematicText.Synopsis(locale, scene), "Localized synopsis");
            check(selected().Id == scene.Id && button.ClassListContains("is-selected"), "Stable selected scene"); titles++;
            // Synthetic director read state drives the real view binding; StartPlayback/Evaluate is never called.
            typeof(RacingBois.Client.Presentation.CinematicDirector).GetProperty("Current").SetValue(director, scene);
            foreach (var beat in scene.Beats)
            {
                typeof(RacingBois.Client.Presentation.CinematicDirector).GetProperty("CurrentBeat").SetValue(director, beat);
                gallery.ShowPlayback();
                check(label("title").text == RacingBois.Client.Application.CinematicText.Title(locale, scene), "Playback title binding");
                check(label("caption").text == RacingBois.Client.Application.CinematicText.Dialogue(locale, scene, beat), "Caption binding"); captions++;
            }
            gallery.HidePlayback();
        }
        foreach (RacingBois.Client.Application.CinematicRole role in Enum.GetValues(typeof(RacingBois.Client.Application.CinematicRole)))
        {
            int expected = 0; foreach (var scene in RacingBois.Client.Application.CinematicCatalog.ForRole(role)) expected++;
            filter.index = (int)role + 1; buildList.Invoke(gallery, null);
            int actual = 0; foreach (var child in list.contentContainer.Children()) if (child is UnityEngine.UIElements.Button) actual++;
            check(actual == expected && selected().Role == role, "Role filter retains semantic IDs");
            string priorId = selected().Id;
            gallery.ShowErrorKey("ui.loading");
            gallery.SetLocale(locale == "VI" ? "ENU" : "VI");
            check(filter.index == (int)role + 1 && selected().Id == priorId, "Locale switch retains category and selected scene");
            check(label("message").text == RacingBois.Client.Application.CinematicText.Get(gallery.Locale, "ui.loading"), "Localized loading survives switch");
            gallery.SetLocale(locale); filters++;
        }
        foreach (string key in new[] { "ui.waiting", "ui.loading", "ui.unavailable", "ui.failed" })
        { gallery.ShowErrorKey(key); check(label("message").text == RacingBois.Client.Application.CinematicText.Get(locale, key), "Localized error: " + key); }
        gallery.ShowError(""); check(label("message").text == "", "Cleared error");
        check(surface.panel == null && director.OwnedActorCount == 0 && director.OwnedPropCount == 0, "No panel, rendering or actor content");
    }
    gallery.SetLocale("unsupported");
    check(gallery.Locale == "ENU" && UnityEngine.UIElements.UQueryExtensions.Q<UnityEngine.UIElements.Button>(surface, "cinematic-play").text == "PLAY SCENE  >", "Explicit English fallback");
    check(!director.StartPlayback(null) && director.LastErrorCode == "content-unavailable", "Unavailable content error code");
    check(surface.panel == null, "Root remained unattached throughout");
}
finally
{
    if (owned != null) UnityEngine.Object.DestroyImmediate(owned);
    if (preview.IsValid()) UnityEditor.SceneManagement.EditorSceneManager.ClosePreviewScene(preview);
}
check(owned == null && !preview.IsValid(), "Owned GameObject and preview scene cleaned up");
return "{\"scope\":\"unattached-cinematic-copy-binding\",\"passed\":true,\"checks\":" + checks +
    ",\"localizedSceneSelections\":" + titles + ",\"captionBindings\":" + captions + ",\"roleFilterSwitches\":" + filters +
    ",\"uiInputDispatch\":false,\"renderedPlayback\":false,\"linguisticAccepted\":false,\"fullGameLocalizationAccepted\":false}";

} }
