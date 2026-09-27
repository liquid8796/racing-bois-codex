using System;
using System.Collections.Generic;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    /// <summary>Renders application read models and emits intents. It owns no room or match state.</summary>
    public sealed class MultiplayerLobbyView : MonoBehaviour
    {
        public event Action<LobbyOptions> CreateRequested;
        public event Action<string> JoinRequested;
        public event Action ReadyRequested, StartRequested, LeaveRequested, DisconnectRequested, RefreshRequested, RematchRequested;
        public event Action UiFeedbackRequested;
        private readonly UiBindingScope bindings = new UiBindingScope();
        private VisualElement surface, root, browser, roomPanel, resultsPanel, members;
        private Label title, message, roomInfo, countdown, empty, resultNote, readyHint;
        private TextField roomName, joinCode, roomCode;
        private DropdownField bots, level, course;
        private Toggle publicRoom;
        private TextField inviteLink;
        private ScrollView rooms, resultRows;
        private Button ready, start, rematch, create, join, disconnect;
        private LobbyReadModel renderedRoom;
        private IReadOnlyList<LobbySummaryReadModel> renderedRooms;
        private MultiplayerResultReadModel renderedResult;
        private readonly List<RoomRow> roomPool = new List<RoomRow>(8);
        private readonly List<InfoRow> memberPool = new List<InfoRow>(8), resultPool = new List<InfoRow>(8);
        public string Locale { get; private set; } = DisplayLanguage.Default;
        private string localError = "", localErrorKey = "";
        private UiTextArgument[] localErrorArguments = Array.Empty<UiTextArgument>();
        private float localErrorUntil;
        private bool joinSubmitHeld;
        private int careerLevel;
        private MultiplayerSession currentSession;
        private readonly List<int> availableCourses = new List<int>();
        private bool contentReady = true;
        private string contentStatus = "";
        public void SetContentReady(bool value, string status)
        {
            contentReady = value; contentStatus = status ?? "";
            if (!value) { ready?.SetEnabled(false); start?.SetEnabled(false); }
        }
        private int shownPanel, previousCountdown = -1;
        public void ShowError(string text) { localError = text; localErrorKey = ""; localErrorArguments = Array.Empty<UiTextArgument>(); localErrorUntil = Time.unscaledTime + 6; }
        private void ShowErrorKey(string key, params UiTextArgument[] arguments)
        { localError = ""; localErrorKey = key; localErrorArguments = arguments; localErrorUntil = Time.unscaledTime + 6; }
        private string Text(string key) => UiText.Get(Locale, key);
        private string Format(string key, params UiTextArgument[] arguments) => UiText.Format(Locale, key, arguments);
        public void SetLocale(string locale)
        {
            string next = DisplayLanguage.Normalize(locale); if (next == Locale) return; Locale = next;
            if (root == null) return;
            ApplyLocalizedChrome();
            renderedRoom = null; renderedRooms = null; renderedResult = null; previousCountdown = -1;
            SetCareerLevel(careerLevel);
            if (currentSession != null) Render(currentSession);
        }
        private void ShowRoomLevelError(MultiplayerSession session)
        {
            if (session.IsGuest) ShowErrorKey("multiplayer.level.guest");
            else ShowErrorKey("multiplayer.level.mismatch", new UiTextArgument("current", (careerLevel + 1).ToString()), new UiTextArgument("room", (session.Room.LevelIndex + 1).ToString()));
        }

        public void SetCareerLevel(int unlocked)
        {
            careerLevel = Math.Min(4, Math.Max(0, unlocked));
            if (level == null) return;
            level.choices = new List<string> { Format("multiplayer.level.current", new UiTextArgument("level", (careerLevel + 1).ToString())) };
            level.index = 0;
            if (currentSession != null && !RoomLevelMatches(currentSession))
            {
                ready?.SetEnabled(false); start?.SetEnabled(false);
                if (readyHint != null) readyHint.text = RoomLevelHint(currentSession);
            }
        }
        public void PrefillInvite(string code)
        {
            if (string.IsNullOrEmpty(code)) return;
            joinCode.value = code;
            ShowErrorKey("multiplayer.invite.received", new UiTextArgument("code", code));
        }
        public void Initialize(UIDocument document, string locale = null)
        {
            if (root != null) return;
            if (locale != null) Locale = DisplayLanguage.Normalize(locale);
            surface = document.rootVisualElement;
            root = surface.Q("multiplayer"); browser = root.Q("mp-browser"); roomPanel = root.Q("mp-room"); resultsPanel = root.Q("mp-results");
            title = root.Q<Label>("mp-title"); message = root.Q<Label>("mp-message"); roomInfo = root.Q<Label>("mp-room-info");
            countdown = root.Q<Label>("mp-countdown"); empty = root.Q<Label>("mp-empty"); resultNote = root.Q<Label>("mp-result-note"); readyHint = root.Q<Label>("mp-ready-hint");
            roomName = root.Q<TextField>("mp-room-name"); joinCode = root.Q<TextField>("mp-join-code"); roomCode = root.Q<TextField>("mp-code");
            bots = root.Q<DropdownField>("mp-bots"); bots.choices = new List<string> { "0", "1", "2", "3", "4", "5", "6" }; bots.index = 5;
            publicRoom=root.Q<Toggle>("mp-public");level=root.Q<DropdownField>("mp-level");SetCareerLevel(0);
            course = root.Q<DropdownField>("mp-course");
            var courseNames = new List<string>();
            foreach (var route in CampaignCatalog.Routes)
            {
                if (!route.IsPlayable) continue;
                availableCourses.Add(route.CourseIndex); courseNames.Add(route.DisplayName);
            }
            course.choices = courseNames; course.index = courseNames.Count > 0 ? 0 : -1;
            course.SetEnabled(courseNames.Count > 0);
            inviteLink=root.Q<TextField>("mp-invite-link");
            bindings.Click(root.Q<Button>("mp-copy-invite"), ()=>
            {
                inviteLink.Focus();inviteLink.SelectAll();
                GUIUtility.systemCopyBuffer=inviteLink.value;
            });
            rooms = root.Q<ScrollView>("mp-room-list"); members = root.Q("mp-members"); resultRows = root.Q<ScrollView>("mp-result-list");
            ready = root.Q<Button>("mp-ready"); start = root.Q<Button>("mp-start"); rematch = root.Q<Button>("mp-rematch");
            create = root.Q<Button>("mp-create"); join = root.Q<Button>("mp-join"); disconnect = root.Q<Button>("mp-disconnect");
            bindings.Click(create, CreateRoom);
            bindings.Click(join, JoinCode);
            bindings.Click(root.Q<Button>("mp-refresh"), () => RefreshRequested?.Invoke());
            bindings.Click(disconnect, () => DisconnectRequested?.Invoke());
            bindings.Click(root.Q<Button>("mp-leave"), () => LeaveRequested?.Invoke());
            bindings.Click(root.Q<Button>("mp-result-leave"), () => LeaveRequested?.Invoke());
            bindings.Click(ready, () => { if (CanUseRoomActions(false)) ReadyRequested?.Invoke(); });
            bindings.Click(start, () => { if (CanUseRoomActions(true)) StartRequested?.Invoke(); });
            bindings.Click(rematch, () => RematchRequested?.Invoke());
            bindings.Value(roomName, e => create.SetEnabled(availableCourses.Count > 0 && !string.IsNullOrWhiteSpace(e.newValue)));
            bindings.Value(joinCode, e => join.SetEnabled(e.newValue.Trim().Length == 6));
            // TextField consumes Return during its own handling, before a bubble callback runs.
            // Handle it once per press, before the inner text input can submit or move focus.
            bindings.Register<KeyDownEvent>(joinCode, e =>
            {
                if (e.keyCode != KeyCode.Return && e.keyCode != KeyCode.KeypadEnter) return;
                e.StopImmediatePropagation(); surface.panel?.focusController.IgnoreEvent(e);
                if (joinSubmitHeld) return;
                joinSubmitHeld = true;
                JoinCode();
            }, TrickleDown.TrickleDown);
            bindings.Register<KeyUpEvent>(joinCode, e =>
            {
                if (e.keyCode != KeyCode.Return && e.keyCode != KeyCode.KeypadEnter) return;
                joinSubmitHeld = false;
                e.StopImmediatePropagation(); surface.panel?.focusController.IgnoreEvent(e);
            }, TrickleDown.TrickleDown);
            bindings.Register<NavigationSubmitEvent>(joinCode, e =>
            {
                if (!joinSubmitHeld) return;
                e.StopImmediatePropagation(); surface.panel?.focusController.IgnoreEvent(e);
            }, TrickleDown.TrickleDown);
            bindings.Register<FocusOutEvent>(joinCode, e => joinSubmitHeld = false);
            join.SetEnabled(false);
            root.Query<TextElement>().ForEach(element => element.enableRichText = false);
            foreach (var panel in new[] { root, browser, roomPanel, resultsPanel }) panel.style.display = DisplayStyle.None;
            ApplyLocalizedChrome();
        }

        private void ApplyLocalizedChrome()
        {
            UiViewState.Text(root.Q<TextElement>("mp-copy-eyebrow"), Text("multiplayer.heading.eyebrow"));
            UiViewState.Text(root.Q<TextElement>("mp-title"), Text("multiplayer.heading.initial-title"));
            UiViewState.Text(root.Q<TextElement>("mp-disconnect"), Text("multiplayer.menu.return"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-create-heading"), Text("multiplayer.browser.create-heading"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-room-name-label"), Text("multiplayer.browser.room-name-label"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-bot-label"), Text("multiplayer.browser.bot-label"));
            root.Q<Toggle>("mp-public").text = Text("multiplayer.browser.public-toggle");
            UiViewState.Text(root.Q<TextElement>("mp-copy-route-label"), Text("multiplayer.browser.route-label"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-profile-level-label"), Text("multiplayer.browser.profile-level-label"));
            UiViewState.Text(root.Q<TextElement>("mp-create"), Text("multiplayer.browser.create"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-invite-heading"), Text("multiplayer.browser.invite-heading"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-join-code-hint"), Text("multiplayer.browser.join-code-hint"));
            UiViewState.Text(root.Q<TextElement>("mp-join"), Text("multiplayer.join"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-room-list-heading"), Text("multiplayer.browser.room-list-heading"));
            UiViewState.Text(root.Q<TextElement>("mp-refresh"), Text("multiplayer.browser.refresh"));
            UiViewState.Text(root.Q<TextElement>("mp-empty"), Text("multiplayer.browser.empty-rooms"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-invite-code-label"), Text("multiplayer.room.invite-code-label"));
            UiViewState.Text(root.Q<TextElement>("mp-copy-invite"), Text("multiplayer.invite.copy"));
            root.Q<VisualElement>("mp-invite-link").tooltip = Text("multiplayer.invite.link-hint");
            UiViewState.Text(root.Q<TextElement>("mp-ready"), Text("multiplayer.ready"));
            UiViewState.Text(root.Q<TextElement>("mp-start"), Text("multiplayer.start"));
            UiViewState.Text(root.Q<TextElement>("mp-leave"), Text("multiplayer.leave"));
            UiViewState.Text(root.Q<TextElement>("mp-rematch"), Text("multiplayer.rematch"));
            UiViewState.Text(root.Q<TextElement>("mp-result-leave"), Text("multiplayer.leave"));
        }

        private void JoinCode()
        {
            string code = joinCode.value.Trim().ToUpperInvariant();
            if (code.Length != 6) { ShowErrorKey("multiplayer.validation.code"); joinCode.Focus(); return; }
            JoinRequested?.Invoke(code);
        }
        private void CreateRoom()
        {
            if (course.index < 0 || course.index >= availableCourses.Count || string.IsNullOrWhiteSpace(roomName.value))
            { ShowErrorKey("multiplayer.validation.create"); return; }
            int courseIndex = availableCourses[course.index];
            if (!CampaignCatalog.IsPlayableRoute(courseIndex)) { ShowErrorKey("multiplayer.validation.route"); return; }
            int selectedLevel = currentSession != null && currentSession.IsGuest ? 0 : careerLevel;
            CreateRequested?.Invoke(new LobbyOptions(roomName.value.Trim(), bots.index, publicRoom.value, courseIndex, selectedLevel));
        }
        private bool RoomLevelMatches(MultiplayerSession session)
            => session.Room == null || session.Room.LevelIndex == (session.IsGuest ? 0 : careerLevel);
        private string RoomLevelHint(MultiplayerSession session)
        {
            int expected = session.IsGuest ? 0 : careerLevel;
            return session.IsGuest
                ? Text("multiplayer.level.guest")
                : Format("multiplayer.level.mismatch", new UiTextArgument("current", (expected + 1).ToString()), new UiTextArgument("room", (session.Room.LevelIndex + 1).ToString()));
        }
        private bool CanUseRoomActions(bool starting)
        {
            var session = currentSession;
            if (session == null || session.Status != SessionStatus.Connected || session.Room == null || session.Room.Phase != LobbyPhase.Lobby) return false;
            if (!RoomLevelMatches(session)) { ShowRoomLevelError(session); return false; }
            if (!contentReady) { if (string.IsNullOrEmpty(contentStatus)) ShowErrorKey("multiplayer.content.incomplete"); else ShowError(contentStatus); return false; }
            if (starting)
            {
                if (!session.IsHost || session.Room.Members.Count == 0) return false;
                foreach (var member in session.Room.Members) if (!member.Ready || !member.Connected) return false;
            }
            return true;
        }

        public void Hide() { UiViewState.Show(root, false); shownPanel = 0; }

        public void Render(MultiplayerSession session)
        {
            currentSession = session;
            bool connected = session.Status == SessionStatus.Connected;
            bool waiting = session.IsReconnecting || session.IsSuspended || session.Status == SessionStatus.Connecting;
            var room = session.Room;
            bool racing = room != null && room.Phase == LobbyPhase.Racing;
            waiting |= racing && session.LatestAuthoritativeWorld == null;
            waiting |= session.ResultsPending;
            bool results = room != null && room.Phase == LobbyPhase.Results;
            create.SetEnabled(connected && !waiting && availableCourses.Count > 0 && !string.IsNullOrWhiteSpace(roomName.value));
            int nextPanel = waiting ? 1 : !connected || racing ? 0 : room == null ? 2 : results ? 4 : 3;
            UiViewState.Show(root, nextPanel != 0);
            root.EnableInClassList("reconnecting", waiting);
            UiViewState.Show(browser, nextPanel == 2); UiViewState.Show(roomPanel, nextPanel == 3); UiViewState.Show(resultsPanel, nextPanel == 4);
            if (shownPanel != nextPanel)
            {
                shownPanel = nextPanel;
                bool settingsOpen = UiViewState.Visible(surface.Q("settings"));
                if (!settingsOpen)
                {
                    if (nextPanel == 2) create.Focus();
                    else if (nextPanel == 3) ready.Focus();
                    else if (nextPanel == 4) (session.IsHost ? rematch : root.Q<Button>("mp-result-leave")).Focus();
                    else if (nextPanel == 1) disconnect.Focus();
                }
            }
            UiViewState.Text(title, session.ResultsPending ? Text("multiplayer.title.saving") : waiting ? (session.IsSuspended ? Text("multiplayer.title.suspended") : session.IsReconnecting ? Text("multiplayer.title.reconnecting") : Text("multiplayer.title.connecting")) : results ? Text("multiplayer.title.results") : room == null ? Text("multiplayer.title.browser") : room.Name);
            bool hasError = Time.unscaledTime < localErrorUntil || !string.IsNullOrEmpty(session.Error);
            UiViewState.Text(message, Time.unscaledTime < localErrorUntil ? (localErrorKey.Length > 0 ? Format(localErrorKey, localErrorArguments) : MultiplayerCopy.Error(localError, Locale)) : !string.IsNullOrEmpty(session.Error) ? MultiplayerCopy.Error(session.Error, Locale) : session.ResultsPending ? Text("multiplayer.message.saving") : waiting ?
                Text("multiplayer.message.reconnecting") : results ?
                Text("multiplayer.message.results") : room == null ?
                Text("multiplayer.message.browser") :
                Text("multiplayer.message.room"));
            message.EnableInClassList("error-text", hasError);

            if (!ReferenceEquals(renderedRooms, session.Lobbies))
            {
                renderedRooms = session.Lobbies;
                int count = renderedRooms == null ? 0 : renderedRooms.Count;
                for (int i = 0; i < count; i++)
                {
                    if (i == roomPool.Count)
                    {
                        var pooled = new RoomRow(code => { UiFeedbackRequested?.Invoke(); JoinRequested?.Invoke(code); });
                        roomPool.Add(pooled); rooms.Add(pooled.Root);
                    }
                    roomPool[i].Bind(renderedRooms[i], Locale);
                }
                for (int i = count; i < roomPool.Count; i++) UiViewState.Show(roomPool[i].Root, false);
                UiViewState.Show(empty, count == 0);
            }
            if (room != null)
            {
                if (!ReferenceEquals(renderedRoom, room))
                {
                    renderedRoom = room;
                    for (int i = 0; i < room.Members.Count; i++)
                    {
                        var player = room.Members[i]; bool own = player.PlayerId == session.PlayerId;
                        string suffix = own ? Text("multiplayer.member.you") : "";
                        if (player.PlayerId == room.HostPlayerId) suffix += Text("multiplayer.member.host");
                        var row = GetRow(memberPool, members, i);
                        row.Root.EnableInClassList("mp-empty-seat", false);
                        row.Bind((i + 1).ToString("00") + "   " + player.DisplayName + suffix, player.Guest ? Text("multiplayer.member.guest") : Text("multiplayer.member.saved"), !player.Connected ? Text("multiplayer.member.held") : player.Ready ? Text("multiplayer.ready") : Text("multiplayer.member.not-ready"), own, !player.Connected || !player.Ready);
                    }
                    for (int i = room.Members.Count; i < room.MaxPlayers; i++)
                    {
                        var row = GetRow(memberPool, members, i);
                        row.Bind(Format("multiplayer.seat.waiting", new UiTextArgument("seat", (i + 1).ToString("00"))), "", Text("multiplayer.seat.empty"), false, true);
                        row.Root.EnableInClassList("mp-empty-seat", true);
                    }
                    for (int i = room.MaxPlayers; i < memberPool.Count; i++) UiViewState.Show(memberPool[i].Root, false);
                    roomCode.SetValueWithoutNotify(room.Code);
                    roomInfo.text = Format("multiplayer.room.info", new UiTextArgument("players", room.Members.Count.ToString()), new UiTextArgument("capacity", room.MaxPlayers.ToString()), new UiTextArgument("bots", room.BotCount.ToString()), new UiTextArgument("course", CampaignCatalog.GetRoute(room.CourseIndex).DisplayName), new UiTextArgument("level", (room.LevelIndex + 1).ToString()), new UiTextArgument("visibility", Text(room.PublicRoom ? "multiplayer.room.public" : "multiplayer.room.private")));
                    string page=UnityEngine.Application.absoluteURL;
                    inviteLink.SetValueWithoutNotify(Uri.TryCreate(page,UriKind.Absolute,out var uri) ? new UriBuilder(uri){Query="room="+room.Code,Fragment=""}.Uri.AbsoluteUri : Format("multiplayer.invite.code", new UiTextArgument("code", room.Code)));
                }
                bool ownReady = false, allReady = room.Members.Count > 0;
                for (int i = 0; i < room.Members.Count; i++)
                {
                    var player = room.Members[i]; if (player.PlayerId == session.PlayerId) ownReady = player.Ready;
                    allReady &= player.Ready && player.Connected;
                }
                UiViewState.Text(ready, ownReady ? Text("multiplayer.ready.cancel") : Text("multiplayer.ready"));
                bool levelMatches = RoomLevelMatches(session);
                ready.EnableInClassList("is-ready", ownReady); ready.SetEnabled(contentReady && levelMatches && room.Phase == LobbyPhase.Lobby);
                UiViewState.Show(start, session.IsHost); start.SetEnabled(contentReady && levelMatches && allReady && room.Phase == LobbyPhase.Lobby);
                UiViewState.Text(readyHint, room.Phase == LobbyPhase.Countdown ? Text("multiplayer.hint.countdown") : !ownReady ? Text("multiplayer.hint.not-ready") : !allReady ? Text("multiplayer.hint.waiting") : session.IsHost ? Text("multiplayer.hint.host") : Text("multiplayer.hint.members"));
                int seconds = room.Phase == LobbyPhase.Countdown ? Mathf.Max(0, Mathf.CeilToInt((float)session.CountdownSeconds)) : -1;
                if (!levelMatches) readyHint.text = RoomLevelHint(session);
                else if (!contentReady) readyHint.text = string.IsNullOrEmpty(contentStatus) ? Text("multiplayer.content.preparing") : UiText.ClientMessage(Locale, contentStatus);
                readyHint.EnableInClassList("error-text", !levelMatches);
                if (previousCountdown != seconds) { previousCountdown = seconds; countdown.text = seconds >= 0 ? Format("multiplayer.countdown", new UiTextArgument("seconds", seconds.ToString())) : ""; }
                rematch.SetEnabled(session.IsHost); UiViewState.Text(rematch, session.IsHost ? Text("multiplayer.rematch") : Text("multiplayer.rematch.waiting"));
            }
            else renderedRoom = null;
            var result = session.Result;
            if (results && (result == null || !ReferenceEquals(renderedResult, result)))
            {
                renderedResult = result;
                if (result == null)
                {
                    UiViewState.Text(resultNote, Text("multiplayer.result.receiving"));
                    foreach (var row in resultPool) UiViewState.Show(row.Root, false);
                    return;
                }
                resultNote.text = result.Persisted ? Text("multiplayer.result.saved") : Text("multiplayer.result.pending");
                resultNote.EnableInClassList("result-confirmed", result.Persisted);
                for (int i = 0; i < result.Entries.Count; i++)
                {
                    var entry = result.Entries[i];
                    string outcome = entry.Outcome == RaceOutcome.Finished ? Format("multiplayer.result.finished", new UiTextArgument("rank", entry.Rank.ToString()), new UiTextArgument("seconds", (entry.FinishTick / 60f).ToString("0.0"))) : entry.Outcome == RaceOutcome.Busted ? Text("multiplayer.result.busted") : entry.Outcome == RaceOutcome.Wrecked ? Text("multiplayer.result.wrecked") : Text("multiplayer.result.incomplete");
                    GetRow(resultPool, resultRows, i).Bind(entry.DisplayName, outcome, Format("multiplayer.result.wallet", new UiTextArgument("reward", (entry.Reward >= 0 ? "+" : "") + "$" + entry.Reward), new UiTextArgument("credits", entry.Credits.ToString())), entry.PlayerId == session.PlayerId, entry.Reward < 0);
                }
                for (int i = result.Entries.Count; i < resultPool.Count; i++) UiViewState.Show(resultPool[i].Root, false);
            }
        }

        private void OnDestroy()
        {
            bindings.Dispose();
            foreach (var row in roomPool) row.Root.RemoveFromHierarchy();
            foreach (var row in memberPool) row.Root.RemoveFromHierarchy();
            foreach (var row in resultPool) row.Root.RemoveFromHierarchy();
            CreateRequested = null; JoinRequested = null;
            ReadyRequested = StartRequested = LeaveRequested = DisconnectRequested = RefreshRequested = RematchRequested = UiFeedbackRequested = null;
            currentSession = null;
        }
        private static InfoRow GetRow(List<InfoRow> pool, VisualElement parent, int index)
        {
            if (index == pool.Count) { var row = new InfoRow(); pool.Add(row); parent.Add(row.Root); }
            return pool[index];
        }
        private static Label Label(string text, string className)
        {
            var label = new Label(text) { enableRichText = false }; label.AddToClassList(className); return label;
        }
        private sealed class InfoRow
        {
            public readonly VisualElement Root = new VisualElement();
            private readonly Label name = Label("", "mp-row-name"), detail = Label("", "mp-row-detail"), state = Label("", "mp-ready-status");
            public InfoRow() { Root.AddToClassList("mp-row"); Root.Add(name); Root.Add(detail); Root.Add(state); }
            public void Bind(string displayName, string description, string status, bool local, bool waiting)
            {
                UiViewState.Show(Root, true); UiViewState.Text(name, displayName); UiViewState.Text(detail, description); UiViewState.Text(state, status);
                Root.EnableInClassList("local-player", local); state.EnableInClassList("mp-waiting-status", waiting);
                name.tooltip = displayName;
            }
        }
        private sealed class RoomRow
        {
            public readonly VisualElement Root = new VisualElement();
            private readonly Label name = Label("", "mp-row-name"), detail = Label("", "mp-row-detail");
            private readonly Button button;
            private string code;
            public RoomRow(Action<string> join)
            {
                Root.AddToClassList("mp-row"); button = new Button(() => join(code)); button.AddToClassList("small-button");
                Root.Add(name); Root.Add(detail); Root.Add(button);
            }
            public void Bind(LobbySummaryReadModel entry, string locale)
            {
                code = entry.Code; UiViewState.Show(Root, true); UiViewState.Text(name, entry.Name); name.tooltip = entry.Name;
                UiViewState.Text(detail, UiText.Format(locale, "multiplayer.room.summary", new UiTextArgument("players", entry.Players.ToString()), new UiTextArgument("capacity", entry.MaxPlayers.ToString()), new UiTextArgument("level", (entry.LevelIndex + 1).ToString())));
                bool full = entry.Players >= entry.MaxPlayers;
                UiViewState.Text(button, entry.Phase != LobbyPhase.Lobby ? UiText.Get(locale, "multiplayer.room.racing") : full ? UiText.Get(locale, "multiplayer.room.full") : UiText.Get(locale, "multiplayer.join"));
                button.SetEnabled(entry.Phase == LobbyPhase.Lobby && !full);
            }
        }
    }
}
