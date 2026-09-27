using System;
using System.Collections.Generic;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    public sealed partial class RaceScreen
    {
        public string Locale { get; private set; } = DisplayLanguage.Default;
        private bool copyNetwork, copyRacing, copyReconnecting, copyDegraded, copyMenuErrorActive, applyingCopy;
        private SessionStatus copyStatus;
        private RaceSessionMode copyMode, copyRenderMode;
        private string copyError = "", copyMenuError = "", copyEventKey = "";
        private double copyRtt;
        private RaceWorldReadModel copyWorld;
        private RaceRiderReadModel copyRider;
        private LocalCampaignReadModel copyCampaign;
        private int copyParticipants;
        private string T(string key) => UiText.Get(Locale, key);
        private string F(string key, params UiTextArgument[] arguments) => UiText.Format(Locale, key, arguments);
        private static UiTextArgument A(string name, string value) => new UiTextArgument(name, value);
        private List<string> QualityChoices() => new List<string> { T("settings.quality.low"), T("settings.quality.medium"), T("settings.quality.high") };
        private List<string> LevelChoices()
        {
            var result = new List<string>();
            for (int i = 1; i <= CampaignCatalog.LevelCount; i++) result.Add(F("practice.levelChoice", A("level", i.ToString())));
            return result;
        }
        private void CopyText(string name, string key)
        {
            var element = root.Q(name);
            if (element is Toggle toggle) toggle.text = T(key);
            else if (element is TextElement text) text.text = T(key);
            else throw new InvalidOperationException("Display-copy target is absent or has the wrong type: " + name);
        }
        private void ApplyStaticCopy()
        {
            CopyText("career-open", "menu.careerOpen"); CopyText("gallery-open", "menu.galleryOpen"); CopyText("settings-open", "settings.open");
            CopyText("copy-menu-offline", "menu.offlinePractice"); CopyText("local", "menu.raceStart"); CopyText("practice-open", "menu.practiceChoose");
            CopyText("copy-menu-player-name", "menu.playerNameLabel"); CopyText("copy-menu-endpoint", "menu.endpointLabel"); CopyText("connect-guest", "menu.connectGuest");
            CopyText("connect", "menu.connectSaved"); CopyText("connection", "connection.ready"); CopyText("message", "menu.practiceDisclaimer");
            CopyText("copy-hud-position", "hud.positionLabel"); CopyText("copy-hud-rider", "hud.riderLabel"); CopyText("copy-hud-bike", "hud.bikeLabel"); CopyText("leave", "hud.leave");
            CopyText("weapon", "hud.weapon.fist"); CopyText("state", "hud.mode.riding"); CopyText("result-title", "results.finished");
            CopyText("copy-results-heading", "results.practiceHeading"); CopyText("restart", "results.restart"); CopyText("home", "common.backMenu");
            CopyText("copy-settings-eyebrow", "settings.eyebrow"); CopyText("copy-settings-title", "settings.title"); CopyText("settings-close", "common.done");
            CopyText("copy-settings-quality", "settings.qualityLabel"); CopyText("copy-settings-quality-help", "settings.qualityHelp");
            CopyText("reduced-motion", "settings.reducedMotion"); CopyText("copy-settings-motion-help", "settings.reducedMotionHelp"); CopyText("audio", "settings.audio");
            CopyText("copy-settings-hud-range", "settings.hudRange"); CopyText("copy-settings-navigation", "settings.navigationHelp");
            CopyText("copy-practice-title", "practice.title"); CopyText("practice-close", "common.done"); CopyText("copy-practice-help", "practice.help");
            CopyText("practice-start", "practice.start"); CopyText("copy-content-heading", "content.heading"); CopyText("content-retry", "common.retry");
            practiceCourse.label = T("practice.courseLabel"); practiceLevel.label = T("practice.levelLabel");
            practiceBike.label = T("practice.bikeLabel"); practiceCharacter.label = T("practice.riderLabel");
            if (!ContentBusy) contentStatus.text = T("content.defaultStatus");
            networkToggle.text = T(networkOpen ? "menu.networkClose" : "menu.networkOpen");
        }
        private void RefreshStatusCopy()
        {
            if (connection == null || message == null || connectButton == null) return;
            if (copyNetwork)
            {
                connection.text = T(copyReconnecting ? "connection.reconnecting" : copyStatus == SessionStatus.Connected ? "connection.onlineLan" :
                    copyStatus == SessionStatus.Connecting ? "connection.connecting" : "connection.ready");
                if (copyStatus == SessionStatus.Connected && copyRacing && !copyReconnecting)
                    connection.text = F(copyDegraded ? "connection.highLatency" : "connection.latency", A("milliseconds", copyRtt.ToString("0")));
                message.text = copyError.Length == 0 ? T("menu.profileHelp") : MultiplayerCopy.Error(copyError, Locale);
                connectButton.text = T("menu.connectSaved");
            }
            else
            {
                connection.text = T(copyStatus == SessionStatus.Connected ? (copyMode == RaceSessionMode.Local ? "connection.local" : "connection.server") :
                    copyStatus == SessionStatus.Connecting ? "connection.connecting" : "connection.ready");
                connectButton.text = T(copyStatus == SessionStatus.Connecting ? "menu.connecting" : "menu.connect");
                message.text = copyError.Length == 0 ? T("menu.practiceDisclaimer") : UiText.ClientMessage(Locale, copyError);
            }
            if (copyMenuErrorActive) message.text = UiText.ClientMessage(Locale, copyMenuError);
        }
        public void SetLocale(string value)
        {
            Locale = DisplayLanguage.Normalize(value);
            if (root == null) return;
            var focused = root.panel?.focusController.focusedElement as VisualElement;
            applyingCopy = true;
            try
            {
                int level = practiceLevel.index;
                quality.choices = QualityChoices(); quality.SetValueWithoutNotify(quality.choices[CurrentQualityIndex]);
                practiceLevel.choices = LevelChoices(); practiceLevel.SetValueWithoutNotify(practiceLevel.choices[Math.Max(0, Math.Min(level, practiceLevel.choices.Count - 1))]);
                ApplyStaticCopy(); RefreshControlHints(gamepadNavigation); RefreshPracticeSummary(); RefreshStatusCopy();
                SetCruise(Cruise); ApplyPreferences(ReducedMotion, AudioEnabled, HudScale); desktopDisplay.SetLocale(Locale);
                settingsContext.text = T(raceActive ? "settings.contextRace" : "settings.contextIdle");
                if (copyHasContentStatus) contentStatus.text = UiText.ClientMessage(Locale, copyContentStatus);
                lastSpeed = lastRank = lastCompetitors = lastDistance = lastTrack = -1; previousMode = (RiderMode)(-1);
                if (raceActive && copyWorld != null) Render(copyWorld, copyRider, copyRenderMode, copyCampaign, copyParticipants);
                if (copyEventKey.Length > 0) eventLabel.text = T(copyEventKey);
                if (focused != null && focused.panel != null && focused.enabledInHierarchy) focused.Focus();
            }
            finally { applyingCopy = false; }
        }
    }
}
