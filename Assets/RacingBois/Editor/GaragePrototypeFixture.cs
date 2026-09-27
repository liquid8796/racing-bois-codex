using System;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Protocol;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Authoring.Editor
{
    /// <summary>
    /// Editor-only visual fixture for garage-v2. Uses the real CareerSession/read-model path,
    /// an in-memory credential store and a transport which cannot contact a server or mutate a profile.
    /// It is not an account, ownership, online, or production-content acceptance test.
    /// </summary>
    public static class GaragePrototypeFixture
    {
        private const string Endpoint = "ws://garage-prototype.invalid/multiplayer";
        private static GameObject owner;
        private static CareerView view;
        private static VisualElement previousFocus;
        private static Label fixtureNotice;

        public static bool IsOpen => owner != null;

        public static string Open(UIDocument document, Sprite[] renderedThumbnails = null, Action<int> previewRequested = null)
        {
            if (!EditorApplication.isPlaying || EditorApplication.isCompiling)
                throw new InvalidOperationException("The isolated garage fixture requires idle Play mode.");
            if (IsOpen) throw new InvalidOperationException("Close the existing garage fixture first.");
            if (document == null || document.rootVisualElement.Q("surface") == null)
                throw new ArgumentException("A live Racing Bois UIDocument is required.", nameof(document));
            foreach (var career in UnityEngine.Object.FindObjectsByType<CareerView>())
                if (career.IsOpen) throw new InvalidOperationException("Close the current career view before opening the fixture.");
            var surface = document.rootVisualElement.Q("surface");
            if (surface.ClassListContains("race-active") || IsVisible(surface.Q("content-loading")) || IsVisible(surface.Q("multiplayer")))
                throw new InvalidOperationException("The fixture is available only from an idle menu without a room or content overlay.");

            previousFocus = document.rootVisualElement.panel?.focusController.focusedElement as VisualElement;
            owner = new GameObject("Garage prototype fixture - read-only test data") { hideFlags = HideFlags.DontSave };
            try
            {
                var session = new CareerSession(new ReadOnlyTransport(), new MemoryCredentials(), new EmptyLeases());
                view = owner.AddComponent<CareerView>();
                view.Initialize(document, session);
                view.SetBikeThumbnails(renderedThumbnails);
                view.CommandRequested += session.Execute;
                view.RefreshRequested += session.Refresh;
                view.RetryRequested += session.Retry;
                if (previewRequested != null) view.SelectedBikePreviewRequested += previewRequested;
                view.Closed += Close;
                session.SetEndpoint(Endpoint);
                session.Refresh();
                view.Open(false, false);
                fixtureNotice = new Label("UI FIXTURE · DỮ LIỆU THỬ · MODEL / THUMBNAIL CHƯA NGHIỆM THU") { pickingMode = PickingMode.Ignore };
                fixtureNotice.style.position = Position.Absolute;
                fixtureNotice.style.left = 24; fixtureNotice.style.bottom = 12;
                fixtureNotice.style.fontSize = 14; fixtureNotice.style.color = new Color(1f, .76f, .34f);
                fixtureNotice.style.backgroundColor = new Color(.04f, .05f, .06f, .95f);
                fixtureNotice.style.paddingLeft = fixtureNotice.style.paddingRight = 10;
                fixtureNotice.style.paddingTop = fixtureNotice.style.paddingBottom = 5;
                surface.Add(fixtureNotice);
                EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
                return "EDITOR VISUAL FIXTURE: Spark 450 + Apex owned; Apex selected; condition 100. " +
                    "Read-only in-memory transport, no network/account/mask changes. Missing genuine rendered thumbnails and " +
                    "unbound/unaccepted 3D workshop or bike remain visual failures. This is not live account acceptance.";
            }
            catch { Close(); throw; }
        }

        public static void Close()
        {
            EditorApplication.playModeStateChanged -= OnPlayModeStateChanged;
            var currentOwner = owner;
            var currentView = view;
            owner = null; view = null;
            fixtureNotice?.RemoveFromHierarchy(); fixtureNotice = null;
            if (currentView != null)
            {
                currentView.Closed -= Close;
                currentView.Close();
            }
            if (currentOwner != null) UnityEngine.Object.DestroyImmediate(currentOwner);
            if (previousFocus != null && previousFocus.enabledInHierarchy && previousFocus.panel != null) previousFocus.Focus();
            previousFocus = null;
        }

        private static void OnPlayModeStateChanged(PlayModeStateChange state)
        { if (state == PlayModeStateChange.ExitingPlayMode || state == PlayModeStateChange.EnteredEditMode) Close(); }

        private static bool IsVisible(VisualElement element)
        { return element != null && element.resolvedStyle.display != DisplayStyle.None && element.resolvedStyle.visibility == Visibility.Visible; }

        private sealed class ReadOnlyTransport : ICareerTransport
        {
            public void Send(string endpoint, string bearer, CareerRequest request, Action<CareerResponse, bool> completed)
            {
                if (endpoint != CareerSession.ApiEndpoint(Endpoint) || request.operation != "view")
                { completed(new CareerResponse { ok = false, code = "fixture_read_only" }, false); return; }
                completed(new CareerResponse
                {
                    ok = true,
                    profile = new CareerProfileData
                    {
                        profileId = "garage-prototype-fixture", displayName = "Visual fixture", realmId = "editor-visual-fixture",
                        realmKind = "offline", selectedBikeId = "rb-apex", selectedCharacterId = "rb-ash",
                        credits = 0, levelIndex = 0, revision = 1,
                        bikes = new[] { new CareerBikeData { bikeId = "rb-spark-450", condition = 100 }, new CareerBikeData { bikeId = "rb-apex", condition = 100 } }
                    }
                }, false);
            }
        }

        private sealed class MemoryCredentials : IProfileCredentialStore
        {
            private ProfileCredential credential = new ProfileCredential("editor-fixture-not-a-server-token", "garage-prototype-fixture", "Visual fixture", "editor-visual-fixture", 0);
            public ProfileCredential Load(string endpoint) => endpoint == Endpoint ? credential : null;
            public void Save(string endpoint, ProfileCredential value) { if (endpoint == Endpoint) credential = value; }
            public void Clear(string endpoint) { if (endpoint == Endpoint) credential = null; }
        }

        private sealed class EmptyLeases : IResumeReceiptStore
        {
            public ResumeReceipt Load(string endpoint) => null;
            public void Save(string endpoint, ResumeReceipt receipt) { }
            public void Clear(string endpoint) { }
        }
    }
}
