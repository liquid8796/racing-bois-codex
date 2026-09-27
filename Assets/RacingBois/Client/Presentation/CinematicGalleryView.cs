using System;
using System.Collections.Generic;
using RacingBois.Client.Application;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Keyboard-friendly gallery and skippable captions. No media loads or gameplay commands.</summary>
    [DisallowMultipleComponent]
    public sealed class CinematicGalleryView : MonoBehaviour
    {
        public event Action<CinematicDefinition> PlayRequested;
        public event Action Closed;
        public bool IsOpen { get; private set; }
        public int BackHandledFrame { get; private set; } = -1;
        private CinematicDirector director;
        private VisualElement surface, gallery, playback, listPanel, detail, progressFill, topBar, bottomBar;
        private Label detailTitle, detailBody, detailMeta, message, caption, title, progressText;
        private Button play, close, skip;
        private ScrollView list;
        private DropdownField filter;
        private CinematicDefinition selected;
        private VisualElement previousFocus;
        private readonly Dictionary<VisualElement, StyleEnum<Visibility>> siblingVisibility = new Dictionary<VisualElement, StyleEnum<Visibility>>();
        private bool playbackVisible;
        private int displayedSecond = -1;
        private string totalDuration = "";
        private static readonly CinematicRole[] GalleryOrder = { CinematicRole.Intro, CinematicRole.Showcase, CinematicRole.Duel, CinematicRole.Rival, CinematicRole.Start, CinematicRole.Win, CinematicRole.Lose, CinematicRole.Wreck, CinematicRole.Busted, CinematicRole.Level, CinematicRole.FinalWin };

        public void Initialize(UIDocument document, CinematicDirector value)
        {
            if (surface != null) return;
            if (document == null || value == null) throw new ArgumentNullException(nameof(document));
            director = value; surface = document.rootVisualElement.Q<VisualElement>("surface") ?? document.rootVisualElement;
            BuildGallery(); BuildPlayback(); director.Changed += RefreshPlayback;
        }
        private static Label Text(string value, string classes)
        { var label = new Label(value) { enableRichText = false }; foreach (string css in classes.Split(' ')) label.AddToClassList(css); return label; }
        private static VisualElement Element(string css)
        { var element = new VisualElement(); element.AddToClassList(css); return element; }
        private static Button Button(string text, Action click, bool primary = false)
        { var button = new Button(click) { text = text }; button.AddToClassList(primary ? "primary" : "secondary"); return button; }
        private void BuildGallery()
        {
            gallery = new VisualElement { name = "cinematic-gallery", focusable = true }; gallery.AddToClassList("gallery-overlay"); gallery.style.display = DisplayStyle.None;
            var panel = Element("gallery-panel"); gallery.Add(panel);
            var header = Element("gallery-heading"); var heading = Element("gallery-heading-copy");
            heading.Add(Text("RACING BOIS / CÂU CHUYỆN", "eyebrow amber")); heading.Add(Text("CÂU CHUYỆN.", "gallery-title")); header.Add(heading);
            close = Button("QUAY LẠI / ESC", Hide); close.name = "cinematic-close"; close.AddToClassList("small-button"); header.Add(close); panel.Add(header);
            panel.Add(Text(CinematicCatalog.All.Count + " cảnh 3D · Bỏ qua bất cứ lúc nào", "hint"));
            var choices = new List<string> { "Tất cả" }; foreach (CinematicRole role in Enum.GetValues(typeof(CinematicRole))) choices.Add(RoleLabel(role));
            filter = new DropdownField("THỂ LOẠI", choices, 0) { name = "cinematic-filter" }; filter.AddToClassList("gallery-filter");
            filter.RegisterValueChangedCallback(_ => BuildList()); panel.Add(filter);
            var body = Element("gallery-body"); panel.Add(body); listPanel = Element("gallery-list-panel"); body.Add(listPanel);
            list = new ScrollView(ScrollViewMode.Vertical) { name = "cinematic-list", horizontalScrollerVisibility = ScrollerVisibility.Hidden }; list.AddToClassList("gallery-list"); listPanel.Add(list);
            detail = Element("gallery-detail"); body.Add(detail);
            detailMeta = Text("", "eyebrow amber"); detail.Add(detailMeta);
            detailTitle = Text("", "gallery-detail-title"); detail.Add(detailTitle);
            detailBody = Text("", "description gallery-synopsis"); detail.Add(detailBody);
            play = Button("PHÁT CẢNH  >", () => { if (selected != null) PlayRequested?.Invoke(selected); }, true); play.name = "cinematic-play"; detail.Add(play);
            message = Text("", "hint error-text"); detail.Add(message);
            gallery.RegisterCallback<KeyDownEvent>(OnKeyDown, TrickleDown.TrickleDown); surface.Add(gallery); BuildList();
        }
        private void BuildPlayback()
        {
            playback = new VisualElement { name = "cinematic-playback", focusable = true }; playback.AddToClassList("cinematic-playback"); playback.style.display = DisplayStyle.None;
            topBar = Element("cinematic-topbar"); title = Text("", "brand cinematic-scene-title"); topBar.Add(title);
            skip = Button("BỎ QUA / ESC", () => { BackHandledFrame = Time.frameCount; director.Stop(true); }); skip.name = "cinematic-skip"; topBar.Add(skip); playback.Add(topBar);
            bottomBar = Element("cinematic-caption-strip"); caption = Text("", "cinematic-caption"); bottomBar.Add(caption);
            progressText = Text("", "cinematic-time"); bottomBar.Add(progressText);
            var track = Element("cinematic-progress-track"); progressFill = Element("cinematic-progress-fill"); progressFill.style.width = Length.Percent(0); track.Add(progressFill); bottomBar.Add(track); playback.Add(bottomBar);
            playback.RegisterCallback<KeyDownEvent>(OnKeyDown, TrickleDown.TrickleDown); surface.Add(playback);
        }
        private void BuildList()
        {
            list.Clear(); int index = filter?.index ?? 0; CinematicDefinition first = null, retained = null;
            var ordered = new List<CinematicDefinition>(59);
            foreach (var role in GalleryOrder) foreach (var item in CinematicCatalog.ForRole(role)) ordered.Add(item);
            foreach (var item in ordered)
            {
                if (index > 0 && (int)item.Role != index - 1) continue;
                if (first == null) first = item;
                if (selected != null && selected.Id == item.Id) retained = item;
                var entry = item; var button = Button(entry.Title, () => Select(entry)); button.name = "cinematic-option-" + entry.Id;
                button.AddToClassList("gallery-entry");
                button.tooltip = RoleLabel(entry.Role) + " • " + Duration(entry.DurationSeconds); list.Add(button);
            }
            if (retained != null || first != null) Select(retained ?? first);
        }
        private void Select(CinematicDefinition item)
        {
            selected = item; detailTitle.text = item.Title; detailBody.text = item.Synopsis;
            detailMeta.text = RoleLabel(item.Role).ToUpperInvariant() + "  /  " + Duration(item.DurationSeconds) + "  /  " + item.Beats.Count + " GÓC CẢNH";
            message.text = "";
            foreach (var child in list.contentContainer.Children()) if (child is Button button)
                button.EnableInClassList("is-selected", button.name == "cinematic-option-" + item.Id);
        }
        public void Show()
        {
            if (surface == null) return;
            if (!IsOpen && !playbackVisible) previousFocus = surface.panel?.focusController.focusedElement as VisualElement;
            IsOpen = true; gallery.style.display = DisplayStyle.Flex; playback.style.display = DisplayStyle.None; playbackVisible = false;
            HideSiblings(); gallery.BringToFront(); close.Focus();
        }
        public void Hide()
        {
            if (!IsOpen) return; IsOpen = false; gallery.style.display = DisplayStyle.None;
            if (!playbackVisible) RestoreSiblings(); Closed?.Invoke();
        }
        public void ShowError(string error) { message.text = error ?? ""; }
        public void ShowPlayback()
        {
            IsOpen = false; gallery.style.display = DisplayStyle.None; playbackVisible = true; playback.style.display = DisplayStyle.Flex;
            HideSiblings(); playback.BringToFront(); skip.Focus(); displayedSecond = -1; totalDuration = director.Current == null ? "" : Duration(director.Current.DurationSeconds); RefreshPlayback();
        }
        public void HidePlayback()
        { playbackVisible = false; if (playback != null) playback.style.display = DisplayStyle.None; if (!IsOpen) RestoreSiblings(); }
        public bool HandleBack()
        {
            if (BackHandledFrame == Time.frameCount) return true;
            if (director != null && director.IsPlaying) { BackHandledFrame = Time.frameCount; director.Stop(true); return true; }
            if (IsOpen) { BackHandledFrame = Time.frameCount; Hide(); return true; }
            return false;
        }
        private void OnKeyDown(KeyDownEvent evt)
        {
            if (evt.keyCode == KeyCode.Escape && HandleBack()) { evt.StopImmediatePropagation(); return; }
            // Confine keyboard navigation while a modal is visible.
            if (evt.keyCode != KeyCode.Tab) return;
            var targets = new List<VisualElement>();
            if (playbackVisible) targets.Add(skip);
            else { targets.Add(close); targets.Add(filter); foreach (var button in list.Query<Button>().ToList()) targets.Add(button); targets.Add(play); }
            targets.RemoveAll(element => !element.enabledInHierarchy || element.resolvedStyle.display == DisplayStyle.None);
            if (targets.Count == 0) return;
            var current = surface.panel?.focusController.focusedElement as VisualElement; int at = targets.IndexOf(current);
            int next = (at + (evt.shiftKey ? -1 : 1) + targets.Count) % targets.Count; targets[next].Focus(); evt.StopImmediatePropagation();
        }
        private void HideSiblings()
        {
            foreach (var child in surface.Children())
            {
                if (child == gallery || child == playback) continue;
                if (!siblingVisibility.ContainsKey(child)) siblingVisibility.Add(child, child.style.visibility);
                child.style.visibility = Visibility.Hidden;
            }
        }
        private void RestoreSiblings()
        {
            foreach (var entry in siblingVisibility) entry.Key.style.visibility = entry.Value; siblingVisibility.Clear();
            if (previousFocus != null && previousFocus.panel != null && previousFocus.enabledInHierarchy) previousFocus.Focus();
        }
        private void RefreshPlayback()
        {
            if (!playbackVisible || director.Current == null) return;
            title.text = director.Current.Title; caption.text = director.CurrentBeat?.Dialogue ?? "";
        }
        private void Update()
        {
            if (!playbackVisible || director == null || director.Current == null) return;
            progressFill.style.width = Length.Percent(Mathf.Clamp01(director.ElapsedSeconds / director.Current.DurationSeconds) * 100);
            int second = Mathf.Max(0, Mathf.FloorToInt(director.ElapsedSeconds));
            if (second != displayedSecond)
            {
                displayedSecond = second; progressText.text = Duration(second) + "  /  " + totalDuration;
            }
        }
        private static string Duration(float seconds) { int s = Mathf.Max(0, Mathf.FloorToInt(seconds)); return (s / 60).ToString("00") + ":" + (s % 60).ToString("00"); }
        private static string RoleLabel(CinematicRole role)
        {
            switch (role)
            {
                case CinematicRole.Showcase: return "Khám phá xe";
                case CinematicRole.Busted: return "Bên lề đường";
                case CinematicRole.Start: return "Vạch xuất phát";
                case CinematicRole.Win: return "Chiến thắng";
                case CinematicRole.Lose: return "Sau một cuộc đua";
                case CinematicRole.Wreck: return "Dựng xe lên";
                case CinematicRole.Level: return "Chặng đường mới";
                case CinematicRole.Intro: return "Mở đầu";
                case CinematicRole.Duel: return "Hai đối thủ";
                case CinematicRole.Rival: return "Chuyện của Juno";
                default: return "Đường vẫn rộng mở";
            }
        }
        private void OnDestroy()
        {
            if (director != null) director.Changed -= RefreshPlayback; RestoreSiblings(); gallery?.RemoveFromHierarchy(); playback?.RemoveFromHierarchy();
            PlayRequested = null; Closed = null;
        }
    }
}
