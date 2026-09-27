using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Tools.OwnedUi;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Tools.NativeUi
{
    /// <summary>Actual attached view/focus/event rendering with synthetic local transports only.</summary>
    public static class AttachedUiDriver
    {
        private static Run active;
        private static string last = "";
        public static string Start(string runId, string compiledProofPath, string textUnionPath)
        {
            if (active != null) throw new InvalidOperationException("Attached UI driver already active.");
            if (!System.Text.RegularExpressions.Regex.IsMatch(runId ?? "", "^[a-z0-9][a-z0-9-]{0,35}$")) throw new ArgumentException("Fresh bounded run ID required.");
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating) throw new InvalidOperationException("Idle editor required.");
            var run = new Run(runId, compiledProofPath, textUnionPath); active = run;
            try { run.Begin(); } catch { active = null; throw; }
            return "running: " + run.ReceiptPath;
        }
        public static string Snapshot() => active == null ? last : active.Report.ToString(Formatting.Indented);
        public static void Abort()
        {
            if (active == null) return;
            active.Fail(new OperationCanceledException("Root interrupted attached UI driver."));
        }
        private static string Hash(string path)
        { using (var sha = SHA256.Create()) using (var file = File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant(); }
        private static string ExistingProjectFile(string path)
        {
            string root = Path.GetFullPath(".").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar; string full = Path.GetFullPath(path);
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !File.Exists(full)) throw new ArgumentException("Existing project file required.");
            for (var item = new FileInfo(full).Directory; item != null; item = item.Parent)
                if ((item.Attributes & FileAttributes.ReparsePoint) != 0) throw new ArgumentException("Linked input parent rejected.");
            return full;
        }

        private sealed class Run
        {
            internal readonly JObject Report = new JObject { ["schema"] = 1, ["scope"] = "actual-owned-Editor-UI-render-focus-and-synthetic-navigation", ["passed"] = false,
                ["finished"] = false, ["actualNetwork"] = false, ["physicalInputDeviceAcceptance"] = false, ["fullGameAccepted"] = false, ["visualConceptAccepted"] = false };
            internal readonly string ReceiptPath;
            private readonly string runId, proofPath, unionPath, proofHash, unionHash;
            private readonly JObject globalBefore;
            private readonly JArray captures = new JArray(), checks = new JArray(), actionMeasurements = new JArray();
            private readonly Dictionary<string, string> boundInputs = new Dictionary<string, string>(StringComparer.Ordinal);
            private readonly Stack<IEnumerator> routines = new Stack<IEnumerator>();
            private OwnedUiRenderFixture fixture;
            private RaceScreen screen;
            private CareerView career;
            private MultiplayerLobbyView lobby;
            private CareerSession careerSession;
            private CareerWire careerWire;
            private Store careerStore;
            private MultiplayerSession multiplayer;
            private PacketWire packets;
            private int tick, commandEvents, createEvents, readyEvents, rematchEvents, pumpCount;
            private long reliableSequence;
            private int roomRevision;
            private LobbyOptions created;
            private bool failing, cleanupPending;
            private int detachedAt;
            private string locale = "VI", scenario = "prepare";
            private int width, height;
            private VisualElement Root => fixture.Document.rootVisualElement;

            internal Run(string id, string proof, string union)
            {
                runId = id; proofPath = ExistingProjectFile(proof); unionPath = ExistingProjectFile(union); proofHash = Hash(proofPath); unionHash = Hash(unionPath);
                ReceiptPath = Path.GetFullPath("docs/p08/ui-owned-render/" + runId + "-driver.json");
                if (File.Exists(ReceiptPath)) throw new InvalidOperationException("Fresh driver receipt required.");
                Directory.CreateDirectory(Path.GetDirectoryName(ReceiptPath));
                globalBefore = Globals(); Report["startedUtc"] = DateTime.UtcNow.ToString("O"); Report["compiledProofSha256"] = proofHash;
                Report["textUnionSha256"] = unionHash; Report["captures"] = captures; Report["checks"] = checks;
                Report["singleLineActionMeasurements"] = actionMeasurements;
            }
            internal void Begin()
            {
                ValidateLoadedSources();
                routines.Push(Cases()); EditorApplication.update += Tick; AssemblyReloadEvents.beforeAssemblyReload += BeforeReload;
            }
            private void BeforeReload() => Fail(new InvalidOperationException("Unexpected assembly reload during UI render controls."));
            private void ValidateLoadedSources()
            {
                var proof = JObject.Parse(File.ReadAllText(proofPath)); Require((bool)proof["passed"], "independent-source-proof-passed");
                var identities = new JArray(); Report["assemblies"] = identities;
                foreach (var assembly in new[] { typeof(UiText).Assembly, typeof(RaceScreen).Assembly, typeof(RacingBois.Client.Adapters.UnityWireCodec).Assembly,
                    typeof(RacingBois.Client.Bootstrap.RaceBootstrap).Assembly, typeof(OwnedUiRenderFixture).Assembly, typeof(AttachedUiDriver).Assembly })
                {
                    string name = assembly.GetName().Name; var row = proof["assemblies"].FirstOrDefault(value => (string)value["name"] == name);
                    if (!name.StartsWith("RacingBois.Tools.", StringComparison.Ordinal))
                    {
                        Require(row != null && (bool)row["passed"] && Guid.Parse((string)row["mvid"]) == assembly.ManifestModule.ModuleVersionId, "loaded-attested-assembly:" + name);
                        foreach (var document in row["documents"])
                            if (document["matches"]?.Type == JTokenType.Boolean && (bool)document["matches"])
                            { string path = ExistingProjectFile((string)document["path"]); Require(Hash(path) == (string)document["sha256"], "attested-source:" + path); boundInputs[path] = Hash(path); }
                    }
                    string hash = Hash(assembly.Location); boundInputs[assembly.Location] = hash;
                    if (row != null) Require(hash == (string)row["sha256"], "attested-dll:" + name);
                    identities.Add(new JObject { ["name"] = name, ["mvid"] = assembly.ManifestModule.ModuleVersionId.ToString(), ["sha256"] = hash });
                }
                var union = JObject.Parse(File.ReadAllText(unionPath)); int slots = 0;
                foreach (string language in new[] { "ENU", "DEU", "ESP", "FRA", "ITA", "VI" })
                {
                    foreach (var entry in (JObject)union["texts"][language]["global"]) { if (UiText.Get(language, entry.Key) != (string)entry.Value) throw new InvalidOperationException("Global text union mismatch."); slots++; }
                    foreach (var entry in (JObject)union["texts"][language]["cinematic"]) { if (CinematicText.Get(language, entry.Key) != (string)entry.Value) throw new InvalidOperationException("Cinematic text union mismatch."); slots++; }
                }
                Require(slots == 5550, "current-six-locale-text-union-5550-slots");
            }
            private void Require(bool passed, string name)
            {
                checks.Add(new JObject { ["name"] = name, ["passed"] = passed, ["locale"] = locale, ["scenario"] = scenario, ["width"] = width, ["tick"] = tick });
                if (!passed) throw new InvalidOperationException(name);
            }
            private IEnumerator Frames(int count = 4, bool markChanged = true)
            { if (markChanged) fixture?.MarkChanged(); int until = tick + count; while (tick < until) yield return null; }
            private void PumpOwnedPanel()
            {
                if (fixture == null || fixture.Document == null || !fixture.Document.enabled) return;
                var panel = fixture.Document.rootVisualElement?.panel; if (panel == null) return;
                Type type = panel.GetType(); const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
                var update = type.GetMethod("Update", flags, null, Type.EmptyTypes, null);
                var repaint = type.GetMethod("Repaint", flags, null, new[] { typeof(UnityEngine.Event) }, null);
                var render = type.GetMethod("Render", flags, null, Type.EmptyTypes, null);
                if (update == null || repaint == null || render == null) throw new InvalidOperationException("Owned runtime-panel pump API changed.");
                // Exact scoped order proved by root's R2 native render. Never pumps global panels.
                update.Invoke(panel, null);
                repaint.Invoke(panel, new object[] { new UnityEngine.Event { type = EventType.Repaint } });
                // UI-only target has no scene camera to clear last frame. Preserve source panel settings.
                var previousTarget = RenderTexture.active;
                try { RenderTexture.active = fixture.Target; GL.Clear(true, true, Color.clear); }
                finally { RenderTexture.active = previousTarget; }
                render.Invoke(panel, null); pumpCount++;
            }
            private bool OwnsFocus(string name)
            {
                var element = Root.Q<VisualElement>(name); var focus = Root.panel?.focusController.focusedElement as VisualElement;
                return element != null && focus != null && (element == focus || element.Contains(focus));
            }
            private IEnumerator Focus(string name)
            {
                // Revealing a different panel changes display immediately but bounds settle during layout.
                yield return Frames();
                var target = Root.Q<VisualElement>(name);
                var details = new JObject { ["target"] = name, ["exists"] = target != null, ["scenario"] = scenario, ["locale"] = locale, ["tick"] = tick };
                if (target != null)
                {
                    details["type"] = target.GetType().FullName; details["focusable"] = target.focusable; details["enabledInHierarchy"] = target.enabledInHierarchy;
                    details["display"] = target.resolvedStyle.display.ToString(); details["visibility"] = target.resolvedStyle.visibility.ToString();
                    details["opacity"] = target.resolvedStyle.opacity; details["bounds"] = new JObject { ["x"] = target.worldBound.x, ["y"] = target.worldBound.y,
                        ["width"] = target.worldBound.width, ["height"] = target.worldBound.height };
                }
                Report["lastFocusTarget"] = details;
                try { fixture.FocusControl(name); }
                catch (Exception error) { throw new InvalidOperationException("Native focus target unavailable after layout barrier: " + details.ToString(Formatting.None), error); }
                yield return Frames(); Require(OwnsFocus(name), "native-panel-focus:" + name);
            }
            private IEnumerator Submit(string name)
            {
                yield return Focus(name); fixture.SubmitFocused(); yield return Frames();
            }
            private void Capture()
            {
                var responsive = ObserveResponsive(); MeasureActions();
                string file = scenario + "-" + locale.ToLowerInvariant() + ".png";
                var value = JObject.Parse(fixture.CapturePng(file));
                Require(((JArray)value["textLayout"]).Count > 0, "rendered-text-layout-present");
                captures.Add(new JObject { ["width"] = width, ["height"] = height, ["locale"] = locale, ["scenario"] = scenario,
                    ["image"] = value["image"], ["sha256"] = value["sha256"], ["focusedElement"] = value["focusedElement"], ["focusedTextField"] = value["focusedTextField"],
                    ["layoutRows"] = ((JArray)value["textLayout"]).Count, ["elidedRows"] = ((JArray)value["textLayout"]).Count(item => (bool)item["elided"]),
                    ["responsive"] = responsive });
            }
            private JObject ObserveResponsive()
            {
                var surface = Root.Q<VisualElement>("surface"); Require(surface != null, "actual-responsive-surface-present");
                var target = fixture.Document.panelSettings.targetTexture;
                Require(target == fixture.Target && target.width == width && target.height == height, "actual-panel-target-size-bound");
                bool compact = width < 1440 || height < 900, narrow = width < 1200 || surface.contentRect.width < 1100;
                var result = new JObject { ["screenWidth"] = Screen.width, ["screenHeight"] = Screen.height,
                    ["targetWidth"] = target.width, ["targetHeight"] = target.height,
                    ["logicalSurfaceWidth"] = surface.contentRect.width, ["logicalSurfaceHeight"] = surface.contentRect.height,
                    ["actualCompact"] = surface.ClassListContains("compact"), ["expectedCompact"] = compact,
                    ["actualNarrow"] = surface.ClassListContains("narrow"), ["expectedNarrow"] = narrow };
                Report["lastResponsiveObservation"] = result;
                Require(surface.ClassListContains("compact") == compact && surface.ClassListContains("narrow") == narrow,
                    "actual-responsive-classes-match-owned-output");
                return result;
            }
            private bool Visible(VisualElement value)
            {
                if (!value.worldBound.Overlaps(Root.worldBound) || value.worldBound.width <= 0 || value.worldBound.height <= 0) return false;
                for (var item = value; item != null; item = item.parent)
                {
                    if (item.resolvedStyle.display == DisplayStyle.None || item.resolvedStyle.visibility != Visibility.Visible || item.resolvedStyle.opacity <= 0) return false;
                    if (item is ScrollView scroll && !value.worldBound.Overlaps(scroll.contentViewport.worldBound)) return false;
                }
                return true;
            }
            private void MeasureActions()
            {
                // Both quantities are native logical points, so no output-pixel/DPI conversion or
                // arbitrary clipping allowance is needed. Images remain the visual evidence.
                foreach (var button in Root.Query<Button>().ToList())
                {
                    if (!Visible(button) || string.IsNullOrEmpty(button.text) || button.text.Contains("\n") || button.resolvedStyle.whiteSpace != WhiteSpace.NoWrap) continue;
                    var measured = button.MeasureTextSize(button.text, 0, TextElement.MeasureMode.Undefined, 0, TextElement.MeasureMode.Undefined);
                    float available = button.contentRect.width;
                    bool finite = !float.IsNaN(measured.x) && !float.IsInfinity(measured.x) && !float.IsNaN(available) && !float.IsInfinity(available);
                    actionMeasurements.Add(new JObject { ["locale"] = locale, ["scenario"] = scenario, ["width"] = width,
                        ["name"] = button.name, ["text"] = button.text, ["enabled"] = button.enabledInHierarchy,
                        ["measuredWidth"] = measured.x, ["contentWidth"] = available, ["measuredHeight"] = measured.y,
                        ["contentHeight"] = button.contentRect.height, ["overflowWidth"] = finite ? Mathf.Max(0, measured.x - available) : -1,
                        ["worldX"] = button.worldBound.x, ["worldY"] = button.worldBound.y,
                        ["isElided"] = button.isElided, ["fitsWidth"] = finite && available > 0 && measured.x <= available });
                }
                if (scenario == "career-garage" && (locale == "DEU" || locale == "ESP" || locale == "FRA"))
                {
                    var button = Root.Q<Button>("career-repair"); Require(button != null && Visible(button), "pristine-action-visible-for-fit-control");
                    string before = locale == "DEU" ? "MOTORRAD UNBESCHÄDIGT" : locale == "ESP" ? "MOTO EN PERFECTO ESTADO" : "MOTO EN PARFAIT ÉTAT";
                    var measuredBefore = button.MeasureTextSize(before, 0, TextElement.MeasureMode.Undefined, 0, TextElement.MeasureMode.Undefined);
                    // Measuring an explicit string does not assign button.text or change the UI.
                    var observation = new JObject { ["name"] = width == 1920 ? "historical-overflow-negative-control" : "historical-label-under-current-compact-style",
                        ["locale"] = locale, ["scenario"] = scenario, ["width"] = width, ["beforeText"] = before,
                        ["beforeMeasuredWidth"] = measuredBefore.x, ["contentWidth"] = button.contentRect.width,
                        ["wouldOverflow"] = measuredBefore.x > button.contentRect.width };
                    if (width == 1920) { observation["passed"] = measuredBefore.x > button.contentRect.width; checks.Add(observation); }
                    else
                    {
                        if (Report["historicalCompactObservations"] == null) Report["historicalCompactObservations"] = new JArray();
                        ((JArray)Report["historicalCompactObservations"]).Add(observation);
                    }
                }
            }
            private IEnumerator ScrollBottom(ScrollView scroll)
            {
                Require(scroll != null, "actual-scroll-view-present"); yield return Frames();
                float high = scroll.verticalScroller.highValue;
                Require(!float.IsNaN(high) && !float.IsInfinity(high) && high >= 0, "actual-scroll-range-valid");
                scroll.scrollOffset = new Vector2(scroll.scrollOffset.x, high); yield return Frames();
                Require(Mathf.Abs(scroll.scrollOffset.y - scroll.verticalScroller.highValue) <= 0.01f, "actual-scroll-bottom-reached");
            }
            private void SetupViews()
            {
                var owner = fixture.Document.gameObject;
                screen = owner.AddComponent<RaceScreen>(); screen.Initialize(fixture.Document, "wss://fixture.invalid/multiplayer", "VI");
                screen.SetPlayerName("Player {rank}"); screen.SetQuality(2); screen.ApplyPreferences(false, true, 1);
                screen.LocalRequested += () => commandEvents++; screen.ConnectRequested += _ => commandEvents++; screen.GuestConnectRequested += _ => commandEvents++;
                screen.QualityChanged += _ => commandEvents++; screen.PreferencesChanged += (_, __, ___) => commandEvents++;
                screen.CareerRequested += () => career.Open(true, false);
                careerStore = new Store(); careerStore.Save("wss://fixture.invalid/multiplayer", new ProfileCredential("synthetic-capability", "ui-profile", "Player {route}", "ui-realm", 1000));
                careerWire = new CareerWire(); careerSession = new CareerSession(careerWire, careerStore, careerStore); careerSession.SetEndpoint("wss://fixture.invalid/multiplayer"); careerSession.Refresh(); careerWire.Reply(CareerWire.Profile());
                career = owner.AddComponent<CareerView>(); career.Initialize(fixture.Document, careerSession, "VI"); career.CommandRequested += _ => commandEvents++;
                lobby = owner.AddComponent<MultiplayerLobbyView>(); lobby.Initialize(fixture.Document, "VI");
                lobby.CreateRequested += value => { createEvents++; created = value; }; lobby.ReadyRequested += () => readyEvents++; lobby.RematchRequested += () => rematchEvents++;
                OpenSyntheticConnection();
            }
            private void OpenSyntheticConnection()
            {
                multiplayer?.Dispose(); packets = new PacketWire(); reliableSequence = 0; roomRevision = 1;
                multiplayer = new MultiplayerSession(packets, packets.Codec, new Clock(), new Store(), new Store());
                multiplayer.Connect("wss://fixture.invalid/multiplayer", new LocalPlayerProfile("local-ui", "Player {rank}", 0));
                packets.Enqueue(new MpWelcome { requestNonce = packets.Hello.requestNonce, sessionId = "ui-session", resumeToken = "synthetic-lease", profileToken = "synthetic-capability",
                    profileId = "ui-profile", displayName = "Player {rank}", realmId = "ui-realm", sessionEpoch = 1, credits = 1000, reliableReset = true }); multiplayer.Poll();
                Require(multiplayer.Status == SessionStatus.Connected, "synthetic-in-memory-session-connected");
            }
            private void ReleaseCareerState()
            {
                // CareerSession has no IDisposable contract. Invalidate its callback generation and
                // clear only our in-memory wire/store; CareerView.OnDestroy detaches Changed later.
                if (career != null) career.Close();
                if (careerWire != null) careerWire.Callback = null;
                if (careerSession != null)
                {
                    string oldEndpoint = careerSession.Endpoint;
                    careerSession.SetEndpoint("wss://disposed-fixture.invalid/multiplayer");
                    careerSession.ClearView(); careerStore?.Clear(oldEndpoint);
                }
                careerSession = null; careerWire = null; careerStore = null;
            }
            private void Room(LobbyPhase phase)
            {
                packets.Enqueue(new MpLobby { reliableSequence = ++reliableSequence, roomId = "ui-room", code = "ABC123", name = "Room {route}", hostSessionId = "ui-session",
                    matchId = "ui-realm/42", state = (int)phase, revision = roomRevision++, raceEpoch = 1, botCount = 2, maxPlayers = 8, courseIndex = 0, levelIndex = 0,
                    publicRoom = true, members = new[] { new MpMember { sessionId = "ui-session", displayName = "Player {rank}", riderId = 1, ready = true, connected = true },
                        new MpMember { sessionId = "guest-ui", displayName = "Guest {level}", riderId = 2, ready = false, connected = true, guest = true } } }); multiplayer.Poll();
                Require(multiplayer.Room != null && multiplayer.Room.Phase == phase && multiplayer.InvalidSnapshots == 0, "synthetic-room-projected");
            }
            private IEnumerator Cases()
            {
                foreach (var size in new[] { new[] { 1920, 1080 }, new[] { 1366, 768 } })
                {
                    width = size[0]; height = size[1]; scenario = "prepare";
                    fixture = OwnedUiRenderFixture.Prepare(runId + "-" + width, width, height); fixture.Attach(); SetupViews(); yield return Frames(6);
                    foreach (string language in new[] { "ENU", "DEU", "ESP", "FRA", "ITA", "VI" })
                    {
                        locale = language; career.Close(); screen.CloseSettings();
                        int commandsBefore = commandEvents; screen.SetLocale(locale); career.SetLocale(locale); lobby.SetLocale(locale);
                        // Locale refresh re-renders the remembered multiplayer session. Hide it after that refresh.
                        lobby.Hide(); screen.ShowState(SessionStatus.Offline, RaceSessionMode.None, "");
                        Require(commandEvents == commandsBefore && screen.PlayerName == "Player {rank}" && screen.CurrentQualityIndex == 2, "locale-preserves-data-and-choices-without-commands");
                        scenario = "menu"; yield return Focus("local"); Capture();

                        scenario = "settings"; yield return Submit("settings-open"); Require(screen.SettingsOpen, "navigation-submit-opens-settings");
                        yield return Focus("quality"); Capture(); yield return Submit("settings-close"); Require(!screen.SettingsOpen, "navigation-submit-closes-settings");

                        scenario = "career-garage"; yield return Submit("career-open"); Require(career.IsOpen, "navigation-submit-opens-career");
                        yield return Submit("career-tab-garage"); Capture();
                        scenario = "career-account"; yield return Submit("career-tab-account");
                        var username = Root.Q<TextField>("career-username"); var password = Root.Q<TextField>("career-password");
                        Require(username != null && password != null, "account-fields-built-by-real-tab-submit");
                        username.value = "User {route}"; password.SetValueWithoutNotify("synthetic password {rank}");
                        yield return Focus("career-password"); career.SetLocale(locale == "VI" ? "ENU" : "VI"); yield return Frames();
                        Require(OwnsFocus("career-password") && Root.Q<TextField>("career-password").value == "synthetic password {rank}" && Root.Q<TextField>("career-username").value == "User {route}", "password-internal-child-focus-and-draft-survive-locale-change");
                        career.SetLocale(locale); yield return Frames(); Require(OwnsFocus("career-password"), "password-focus-restored-to-original-locale"); Capture();
                        scenario = "career-account-bottom"; yield return ScrollBottom(Root.Q<VisualElement>("career-content").Q<ScrollView>()); Capture();
                        yield return Submit("career-close"); Require(!career.IsOpen, "navigation-submit-closes-career");

                        scenario = "multiplayer-browser"; OpenSyntheticConnection(); screen.ShowMultiplayer(SessionStatus.Connected, false, false, ""); lobby.Render(multiplayer);
                        Root.Q<TextField>("mp-room-name").value = "Room {route}"; Root.Q<TextField>("mp-join-code").value = "ABC123";
                        yield return Focus("mp-room-name"); Require(Root.Q<TextField>("mp-room-name").value == "Room {route}", "room-name-remains-opaque"); Capture();
                        scenario = "multiplayer-browser-actions"; yield return ScrollBottom(Root.Q<VisualElement>("mp-browser").Q<ScrollView>()); Capture();
                        int createBefore = createEvents; yield return Submit("mp-create");
                        Require(createEvents == createBefore + 1 && created != null && created.Name == "Room {route}" && created.CourseIndex == 0 && created.LevelIndex == 0, "native-submit-emits-one-create-intent");

                        scenario = "multiplayer-room"; Room(LobbyPhase.Lobby); lobby.Render(multiplayer); yield return Focus("mp-ready"); Capture();
                        int readyBefore = readyEvents; yield return Submit("mp-ready"); Require(readyEvents == readyBefore + 1, "native-submit-emits-one-ready-intent");

                        scenario = "multiplayer-results"; Room(LobbyPhase.Results);
                        packets.Enqueue(new MpResult { reliableSequence = ++reliableSequence, roomId = "ui-room", raceEpoch = 1, matchId = "ui-realm/42", resultId = "ui-realm/42", persisted = true,
                            entries = new[] { new MpResultEntry { sessionId = "ui-session", displayName = "Player {rank}", riderId = 1, outcome = (int)RaceOutcome.Finished, rank = 1, reward = 600, credits = 1600, finishTick = 6123 },
                                new MpResultEntry { sessionId = "guest-ui", displayName = "Guest {level}", riderId = 2, outcome = (int)RaceOutcome.Wrecked, rank = 0, reward = 0, credits = 0, finishTick = -1 } } }); multiplayer.Poll();
                        Require(multiplayer.Result != null && multiplayer.Result.Persisted, "synthetic-official-results-projected"); lobby.Render(multiplayer);
                        yield return Focus("mp-rematch"); Capture(); int rematchBefore = rematchEvents; yield return Submit("mp-rematch");
                        Require(rematchEvents == rematchBefore + 1, "native-submit-emits-one-rematch-intent");
                    }
                    multiplayer.Dispose(); multiplayer = null; ReleaseCareerState(); fixture.Detach(); yield return Frames(4, false); fixture.Dispose(); fixture = null;
                    screen = null; career = null; lobby = null; careerSession = null;
                }
                Require(captures.Count == 108, "six-locales-nine-viewports-two-resolutions-captured");
                Require(actionMeasurements.Count > 0, "actual-single-line-actions-measured");
                Require(actionMeasurements.All(row => (bool)row["fitsWidth"]), "all-visible-single-line-action-widths-fit");
                Require(checks.Where(row => (string)row["name"] == "historical-overflow-negative-control").Count() == 3 &&
                    checks.Where(row => (string)row["name"] == "historical-overflow-negative-control").All(row => (bool)row["passed"]), "native-measurement-detects-three-unchanged-1920-historical-overflows");
                Require(JToken.DeepEquals(globalBefore, Globals()), "global-quality-display-preferences-preserved");
                Require(Hash(proofPath) == proofHash && Hash(unionPath) == unionHash && boundInputs.All(pair => Hash(pair.Key) == pair.Value), "attested-inputs-stable-through-attached-run");
            }
            private void Tick()
            {
                tick++;
                if (cleanupPending)
                {
                    if (tick - detachedAt < 4) return;
                    try { fixture?.Dispose(); fixture = null; }
                    catch (Exception error) { Report["cleanupFailure"] = error.ToString(); }
                    Finish(false); return;
                }
                try { PumpOwnedPanel(); } catch (Exception error) { Fail(error); return; }
                while (routines.Count > 0)
                {
                    try
                    {
                        var next = routines.Peek(); if (!next.MoveNext()) { (next as IDisposable)?.Dispose(); routines.Pop(); continue; }
                        if (next.Current is IEnumerator child) { routines.Push(child); continue; }
                        return;
                    }
                    catch (Exception error) { Fail(error); return; }
                }
                Finish(true);
            }
            internal void Fail(Exception error)
            {
                if (failing) return; failing = true; Report["failure"] = error.ToString();
                foreach (var value in routines) (value as IDisposable)?.Dispose(); routines.Clear();
                try { multiplayer?.Dispose(); multiplayer = null; ReleaseCareerState(); fixture?.Detach(); }
                catch (Exception cleanup) { Report["detachFailure"] = cleanup.ToString(); }
                if (fixture != null) { cleanupPending = true; detachedAt = tick; } else Finish(false);
            }
            private void Finish(bool passed)
            {
                EditorApplication.update -= Tick; AssemblyReloadEvents.beforeAssemblyReload -= BeforeReload;
                Report["finished"] = true; Report["finishedUtc"] = DateTime.UtcNow.ToString("O"); Report["captureCount"] = captures.Count;
                Report["ownedPanelPumpCount"] = pumpCount;
                Report["ownedTargetClearedBeforeEachRender"] = true;
                Report["globalStateUnchanged"] = JToken.DeepEquals(globalBefore, Globals()); Report["ownedRenderObjectsReleased"] = fixture == null;
                Report["passed"] = passed && fixture == null && (bool)Report["globalStateUnchanged"] && captures.Count == 108;
                last = Report.ToString(Formatting.Indented); active = null;
                using (var file = new FileStream(ReceiptPath, FileMode.CreateNew, FileAccess.Write)) using (var writer = new StreamWriter(file, Encoding.UTF8)) writer.WriteLine(last);
                Debug.Log("RB_ATTACHED_UI_DRIVER " + ((bool)Report["passed"] ? "PASS " : "FAIL ") + ReceiptPath);
            }
            private static JObject Globals()
            {
                var result = new JObject { ["quality"] = QualitySettings.GetQualityLevel(), ["width"] = Screen.width, ["height"] = Screen.height,
                    ["fullScreenMode"] = (int)Screen.fullScreenMode, ["targetFrameRate"] = Application.targetFrameRate, ["timeScale"] = Time.timeScale };
                foreach (string key in new[] { "RB.P06.ReducedMotion", "RB.P06.Audio", "RB.P06.Quality" }) result[key] = new JObject { ["exists"] = PlayerPrefs.HasKey(key), ["value"] = PlayerPrefs.GetInt(key) };
                result["RB.P06.HudScale"] = new JObject { ["exists"] = PlayerPrefs.HasKey("RB.P06.HudScale"), ["value"] = PlayerPrefs.GetFloat("RB.P06.HudScale") }; return result;
            }
        }
    }
}
