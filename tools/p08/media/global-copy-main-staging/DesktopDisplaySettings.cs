using System;
using System.Collections.Generic;
using RacingBois.Client.Application;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Native display adapter. Lists actual monitor resolutions; no display API runs in Web or Editor.</summary>
    internal sealed class DesktopDisplaySettings : IDisposable
    {
        private readonly UiBindingScope bindings = new UiBindingScope();
        private VisualElement owned = null;
        private string locale = DisplayLanguage.Default;
        private string T(string key) => UiText.Get(locale,key);
#if UNITY_STANDALONE_WIN && !UNITY_EDITOR
        private readonly List<Vector2Int> sizes = new List<Vector2Int>();
        private readonly FullScreenMode[] modes = { FullScreenMode.Windowed, FullScreenMode.FullScreenWindow, FullScreenMode.ExclusiveFullScreen };
        private DropdownField mode, resolution;
        private Label status, heading;
        private Button apply;
        private bool hasRequest;
        private int requestedMode;
        private string requestedResolution = "";
        public void Initialize(VisualElement settings,string language=null)
        {
            if(language!=null)locale=DisplayLanguage.Normalize(language);
            owned = new VisualElement(); owned.AddToClassList("desktop-display-settings");
            heading = new Label(T("display.title")); heading.AddToClassList("eyebrow amber"); owned.Add(heading);
            mode = new DropdownField(T("display.modeLabel"), ModeLabels(), 0);
            mode.AddToClassList("content-choice"); owned.Add(mode);
            var labels = new List<string>();
            AddSize(Screen.width, Screen.height, labels);
            foreach (var available in Screen.resolutions) AddSize(available.width, available.height, labels);
            resolution = new DropdownField(T("display.resolutionLabel"), labels, 0); resolution.AddToClassList("content-choice"); owned.Add(resolution);
            int index = Array.IndexOf(modes, Screen.fullScreenMode); mode.index = Math.Max(0, index);
            apply = new Button { text = T("display.apply") }; apply.AddToClassList("secondary"); owned.Add(apply); bindings.Click(apply, Apply);
            status = new Label(T("display.help")); status.AddToClassList("hint"); owned.Add(status);
            settings.Q<ScrollView>()?.Add(owned);
        }
        private void AddSize(int width, int height, List<string> labels)
        {
            var value = new Vector2Int(width, height);
            if (width <= 0 || height <= 0 || sizes.Contains(value)) return;
            sizes.Add(value); labels.Add(width + " × " + height);
        }
        private void Apply()
        {
            if (resolution.index < 0 || resolution.index >= sizes.Count || mode.index < 0 || mode.index >= modes.Length) return;
            var size = sizes[resolution.index]; Screen.SetResolution(size.x, size.y, modes[mode.index]);
            hasRequest = true; requestedResolution = resolution.value; requestedMode = mode.index; RefreshStatus();
        }
        private List<string> ModeLabels() => new List<string> { T("display.windowed"),T("display.borderless"),T("display.exclusive") };
        private void RefreshStatus()
        {
            status.text = hasRequest ? UiText.Format(locale,"display.requested",new UiTextArgument("resolution",requestedResolution),new UiTextArgument("mode",ModeLabels()[requestedMode])) : T("display.help");
        }
#else
        public void Initialize(VisualElement settings,string language=null) { if(language!=null)locale=DisplayLanguage.Normalize(language); }
#endif
        public void SetLocale(string language)
        {
            locale=DisplayLanguage.Normalize(language);
#if UNITY_STANDALONE_WIN && !UNITY_EDITOR
            if(owned==null)return;
            int index=mode.index; mode.choices=ModeLabels(); mode.SetValueWithoutNotify(mode.choices[Math.Max(0,Math.Min(index,mode.choices.Count-1))]);
            heading.text=T("display.title");mode.label=T("display.modeLabel");resolution.label=T("display.resolutionLabel");apply.text=T("display.apply");RefreshStatus();
#endif
        }
        public void Dispose() { bindings.Dispose(); owned?.RemoveFromHierarchy(); }
    }
}
