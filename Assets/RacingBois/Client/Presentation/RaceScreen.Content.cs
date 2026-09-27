using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    public sealed partial class RaceScreen
    {
        public event Action ContentRetryRequested, GalleryRequested;
        private VisualElement practicePanel, contentPanel, focusBeforeContent;
        private readonly Dictionary<VisualElement, bool> contentDisabled = new Dictionary<VisualElement, bool>();
        private DropdownField practiceCourse, practiceLevel, practiceBike, practiceCharacter;
        private readonly List<int> practiceRoutes = new List<int>(), practiceBikes = new List<int>(), practiceCharacters = new List<int>();
        private Button practiceOpen, practiceClose, practiceStart, galleryOpen, contentRetry;
        private Label contentStatus;
        private ProgressBar contentProgress;
        private bool contentRetryAvailable;
        public bool ContentBusy { get; private set; }
        public bool PracticeOpen => practicePanel != null && UiViewState.Visible(practicePanel);
        public int PracticeCourseIndex => Choice(practiceRoutes, practiceCourse);
        public int PracticeLevelIndex => practiceLevel == null ? 0 : Math.Max(0, practiceLevel.index);
        public int PracticeBikeIndex => Choice(practiceBikes, practiceBike);
        public int PracticeCharacterIndex => Choice(practiceCharacters, practiceCharacter);
        private static int Choice(List<int> values, DropdownField field) => field != null && field.index >= 0 && field.index < values.Count ? values[field.index] : 0;
        private void InitializeP08()
        {
            practicePanel = root.Q("practice-panel"); practiceCourse = root.Q<DropdownField>("practice-course");
            surface.Add(practicePanel);
            practiceLevel = root.Q<DropdownField>("practice-level"); practiceBike = root.Q<DropdownField>("practice-bike");
            practiceCharacter = root.Q<DropdownField>("practice-character");
            practiceOpen = root.Q<Button>("practice-open"); practiceClose = root.Q<Button>("practice-close"); practiceStart = root.Q<Button>("practice-start");
            galleryOpen = root.Q<Button>("gallery-open");
            var courses = new List<string>(); var bikes = new List<string>(); var characters = new List<string>();
            foreach (var route in CampaignCatalog.Routes) if (route.IsPlayable) { practiceRoutes.Add(route.CourseIndex); courses.Add(route.DisplayName); }
            foreach (var bike in BikeCatalog.All) if (ProductionContent.BikeArtAvailable(bike.CatalogIndex)) { practiceBikes.Add(bike.CatalogIndex); bikes.Add(bike.DisplayName); }
            foreach (var character in CharacterCatalog.All) if (ProductionContent.CharacterArtAvailable(character.CatalogIndex)) { practiceCharacters.Add(character.CatalogIndex); characters.Add(character.DisplayName); }
            practiceCourse.choices = courses; practiceCourse.index = 0; practiceBike.choices = bikes; practiceBike.index = 0;
            practiceCharacter.choices = characters; practiceCharacter.index = 0;
            practiceLevel.choices = new List<string> { "CẤP 1", "CẤP 2", "CẤP 3", "CẤP 4", "CẤP 5" }; practiceLevel.index = 0;
            bindings.Click(practiceOpen, OpenPractice); bindings.Click(practiceClose, ClosePractice);
            bindings.Click(practiceStart, () => { ClosePractice(); LocalRequested?.Invoke(); });
            bindings.Click(galleryOpen, () => { ClosePractice(); GalleryRequested?.Invoke(); });
            practicePanel.style.display = DisplayStyle.None;
            bindings.Register<NavigationCancelEvent>(practicePanel, e => { ClosePractice(); e.StopImmediatePropagation(); });
            bindings.Register<FocusInEvent>(root, e =>
            {
                if (!ContentBusy && PracticeOpen && e.target is VisualElement target && !practicePanel.Contains(target))
                    practicePanel.schedule.Execute(() => { if (!ContentBusy && practicePanel.enabledInHierarchy && PracticeOpen) practiceClose.Focus(); });
            });
            contentPanel = root.Q("content-loading"); contentStatus = root.Q<Label>("content-status");
            surface.Add(contentPanel);
            contentProgress = root.Q<ProgressBar>("content-progress"); contentRetry = root.Q<Button>("content-retry");
            bindings.Click(contentRetry, () => ContentRetryRequested?.Invoke()); contentPanel.style.display = DisplayStyle.None;
            bindings.Register<FocusInEvent>(root, e =>
            {
                if (ContentBusy && e.target is VisualElement target && target != contentPanel && !contentPanel.Contains(target))
                    contentPanel.schedule.Execute(() => { if (ContentBusy) FocusContent(); });
            });
            bindings.Register<KeyDownEvent>(contentPanel, e =>
            {
                if (e.keyCode != KeyCode.Tab && e.keyCode != KeyCode.Escape) return;
                FocusContent(); e.StopImmediatePropagation(); root.panel?.focusController.IgnoreEvent(e);
            }, TrickleDown.TrickleDown);
            bindings.Value(practiceCourse, _ => RefreshPracticeSummary());
            bindings.Value(practiceLevel, _ => RefreshPracticeSummary());
            bindings.Value(practiceBike, _ => RefreshPracticeSummary());
            RefreshPracticeSummary();
        }
        public void OpenPractice()
        {
            if (ContentBusy) return;
            CloseSettings(); UiViewState.Show(practicePanel, true); practicePanel.BringToFront(); practiceClose.Focus();
        }
        public void ClosePractice()
        {
            if (!PracticeOpen) return;
            UiViewState.Show(practicePanel, false); practiceOpen.Focus();
        }
        private void RefreshPracticeSummary()
        {
            if (root == null) return;
            var route = CampaignCatalog.GetRoute(PracticeCourseIndex);
            root.Q<Label>("title").text = route.DisplayName.ToUpperInvariant();
            root.Q<Label>("menu-level").text = "CẤP " + (PracticeLevelIndex + 1) + " /";
            root.Q<Label>("menu-selection").text = BikeCatalog.All[PracticeBikeIndex].DisplayName.ToUpperInvariant();
        }
        private void FocusContent()
        {
            if (contentRetryAvailable && contentRetry.enabledInHierarchy) contentRetry.Focus();
            else contentPanel.Focus();
        }
        private void ReleaseContentOwnership()
        {
            foreach (var entry in contentDisabled) entry.Key.SetEnabled(entry.Value);
            contentDisabled.Clear(); ContentBusy = false;
        }
        public void SetContentState(bool busy, float value, string status, bool canRetry)
        {
            if (contentPanel == null) return;
            bool visible = busy || canRetry, wasVisible = ContentBusy;
            if (visible && !wasVisible)
            {
                focusBeforeContent = root.panel?.focusController.focusedElement as VisualElement;
                // A failed load owns input until retry succeeds, just like a pending load.
                foreach (var child in surface.Children())
                {
                    if (child == contentPanel) continue;
                    contentDisabled[child] = child.enabledSelf; child.SetEnabled(false);
                }
            }
            ContentBusy = visible;
            contentRetryAvailable = canRetry;
            UiViewState.Show(contentPanel, visible);
            contentStatus.text = status ?? ""; contentProgress.value = Mathf.Clamp01(value) * 100;
            contentProgress.title = Mathf.RoundToInt(contentProgress.value) + "%";
            contentRetry.style.display = canRetry ? DisplayStyle.Flex : DisplayStyle.None;
            if (visible)
            {
                contentPanel.BringToFront(); FocusContent();
                contentPanel.schedule.Execute(() => { if (ContentBusy) FocusContent(); });
            }
            else if (wasVisible)
            {
                ReleaseContentOwnership();
                if (focusBeforeContent != null && focusBeforeContent.enabledInHierarchy && focusBeforeContent.resolvedStyle.display != DisplayStyle.None) focusBeforeContent.Focus();
                else root.Focus();
            }
        }
    }
}
