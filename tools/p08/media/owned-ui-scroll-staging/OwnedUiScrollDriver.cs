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
    public static class OwnedUiScrollDriver
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
            internal readonly JObject Report = new JObject { ["schema"] = 1, ["scope"] = "actual-owned-Editor-scroll-viewport-focus-coverage", ["passed"] = false,
                ["finished"] = false, ["actualNetwork"] = false, ["physicalInputDeviceAcceptance"] = false, ["fullGameAccepted"] = false, ["visualConceptAccepted"] = false };
            internal readonly string ReceiptPath;
            private readonly string runId, proofPath, unionPath, proofHash, unionHash;
            private readonly JObject globalBefore;
            private readonly JArray captures = new JArray(), checks = new JArray(), scrollPairs = new JArray();
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
                Report["scrollPairs"] = scrollPairs;
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
                    typeof(RacingBois.Client.Bootstrap.RaceBootstrap).Assembly, typeof(OwnedUiRenderFixture).Assembly, typeof(OwnedUiScrollDriver).Assembly })
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
            private static JObject Bounds(Rect bounds) => new JObject { ["x"]=bounds.x,["y"]=bounds.y,["width"]=bounds.width,["height"]=bounds.height };
            private JObject ViewportProof(VisualElement target,ScrollView scroll)
            {
                Require(target!=null && scroll!=null && scroll.Contains(target) && Visible(target),"visible-scroll-target-present");
                Rect bounds=target.worldBound,viewport=scroll.contentViewport.worldBound;
                bool contained=bounds.xMin>=viewport.xMin && bounds.xMax<=viewport.xMax && bounds.yMin>=viewport.yMin && bounds.yMax<=viewport.yMax;
                var proof=new JObject { ["targetName"]=target.name,["targetType"]=target.GetType().Name,
                    ["targetBounds"]=Bounds(bounds),["viewportBounds"]=Bounds(viewport),["fullyWithinViewport"]=contained,
                    ["offsetX"]=scroll.scrollOffset.x,["offsetY"]=scroll.scrollOffset.y,
                    ["low"]=scroll.verticalScroller.lowValue,["high"]=scroll.verticalScroller.highValue };
                Report["lastViewportProof"]=proof;
                Require(contained,"target-fully-inside-clipped-scroll-viewport");
                return proof;
            }
            private IEnumerator ScrollEdge(ScrollView scroll,bool bottom)
            {
                Require(scroll!=null,"actual-scroll-view-present");yield return Frames();
                float edge=bottom?scroll.verticalScroller.highValue:scroll.verticalScroller.lowValue;
                Require(!float.IsNaN(edge)&&!float.IsInfinity(edge)&&edge>=0,"actual-scroll-range-valid");
                scroll.scrollOffset=new Vector2(0,edge);yield return Frames();
                float currentEdge=bottom?scroll.verticalScroller.highValue:scroll.verticalScroller.lowValue;
                Require(Mathf.Abs(scroll.scrollOffset.y-currentEdge)<=0.01f,bottom?"explicit-native-scroll-bottom":"explicit-native-scroll-top");
            }
            private IEnumerator FocusInside(VisualElement target,ScrollView scroll)
            {
                ViewportProof(target,scroll);
                Require(target.focusable&&target.enabledInHierarchy,"visible-scroll-target-focusable");
                target.Focus();yield return Frames();
                var focused=Root.panel?.focusController.focusedElement as VisualElement;
                Require(focused!=null&&(focused==target||target.Contains(focused)),"actual-focus-owned-by-visible-target");
                ViewportProof(target,scroll);
            }
            private JObject CaptureScroll(ScrollView scroll,VisualElement target,bool bottom,VisualElement companion=null)
            {
                var viewport=ViewportProof(target,scroll);var responsive=ObserveResponsive();
                float expected=bottom?scroll.verticalScroller.highValue:scroll.verticalScroller.lowValue;
                Require(Mathf.Abs(scroll.scrollOffset.y-expected)<=0.01f,"focused-capture-retains-requested-edge");
                var focused=Root.panel?.focusController.focusedElement as VisualElement;
                Require(focused!=null&&(focused==target||target.Contains(focused)),"capture-focus-remains-in-viewport-target");
                var companionProof=companion!=null?ViewportProof(companion,scroll):null;
                var value=JObject.Parse(fixture.CapturePng(scenario+"-"+locale.ToLowerInvariant()+".png"));
                Require(((JArray)value["textLayout"]).Count>0,"rendered-text-layout-present");
                var capture=new JObject { ["width"]=width,["height"]=height,["locale"]=locale,["scenario"]=scenario,
                    ["image"]=value["image"],["sha256"]=value["sha256"],["viewport"]=viewport,["companionViewport"]=companionProof,
                    ["responsive"]=responsive,["focusedElement"]=value["focusedElement"],["focusedTextField"]=value["focusedTextField"],
                    ["focusedType"]=focused.GetType().Name,["bottom"]=bottom };
                captures.Add(capture);return capture;
            }
            private void Pair(string area,JObject top,JObject bottom)
            {
                bool scrollAvailable=(float)bottom["viewport"]["high"]>(float)bottom["viewport"]["low"];
                bool differentOffsets=(float)bottom["viewport"]["offsetY"]>(float)top["viewport"]["offsetY"];
                bool differentImages=(string)top["sha256"]!=(string)bottom["sha256"];
                scrollPairs.Add(new JObject { ["area"]=area,["locale"]=locale,["width"]=width,["scrollAvailable"]=scrollAvailable,
                    ["topImage"]=top["image"],["topSha256"]=top["sha256"],["bottomImage"]=bottom["image"],["bottomSha256"]=bottom["sha256"],
                    ["topOffset"]=top["viewport"]["offsetY"],["bottomOffset"]=bottom["viewport"]["offsetY"],
                    ["differentOffsets"]=differentOffsets,["differentImages"]=differentImages });
                Require(!scrollAvailable||(differentOffsets&&differentImages),"scrollable-area-has-distinct-top-and-bottom-evidence");
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
                multiplayer?.Dispose(); packets = new PacketWire();
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
            private IEnumerator Cases()
            {
                foreach(var size in new[]{new[]{1920,1080},new[]{1366,768}})
                {
                    width=size[0];height=size[1];scenario="prepare";
                    fixture=OwnedUiRenderFixture.Prepare(runId+"-"+width,width,height);fixture.Attach();SetupViews();yield return Frames(6);
                    foreach(string language in new[]{"ENU","DEU","ESP","FRA","ITA","VI"})
                    {
                        locale=language;career.Close();screen.CloseSettings();
                        screen.SetLocale(locale);career.SetLocale(locale);lobby.SetLocale(locale);lobby.Hide();screen.ShowState(SessionStatus.Offline,RaceSessionMode.None,"");
                        yield return Frames();yield return Submit("career-open");yield return Submit("career-tab-account");
                        var username=Root.Q<TextField>("career-username");Require(username!=null,"actual-account-username-present");
                        username.value="User {route}";
                        var account=Root.Q<VisualElement>("career-content").Q<ScrollView>();
                        scenario="career-account-top";yield return ScrollEdge(account,false);yield return FocusInside(username,account);
                        var top=CaptureScroll(account,username,false);
                        var export=account.Query<Button>().ToList().Single(value=>value.text==UiText.Get(locale,"career.backup.export"));
                        scenario="career-account-bottom";yield return ScrollEdge(account,true);yield return FocusInside(export,account);
                        var bottom=CaptureScroll(account,export,true);Pair("career-account",top,bottom);
                        yield return Submit("career-close");Require(!career.IsOpen,"career-closed-by-native-submit");
                        OpenSyntheticConnection();screen.ShowMultiplayer(SessionStatus.Connected,false,false,"");lobby.Render(multiplayer);yield return Frames();
                        var name=Root.Q<TextField>("mp-room-name");var join=Root.Q<Button>("mp-join");var heading=Root.Q<Label>("mp-copy-invite-heading");
                        name.value="Room {route}";Root.Q<TextField>("mp-join-code").value="ABC123";
                        var browser=Root.Q<VisualElement>("mp-browser").Q<ScrollView>();
                        scenario="multiplayer-browser-top";yield return ScrollEdge(browser,false);yield return FocusInside(name,browser);
                        top=CaptureScroll(browser,name,false);
                        scenario="multiplayer-browser-bottom";yield return ScrollEdge(browser,true);yield return FocusInside(join,browser);
                        bottom=CaptureScroll(browser,join,true,heading);Pair("multiplayer-browser",top,bottom);
                        Require(name.value=="Room {route}"&&Root.Q<TextField>("mp-join-code").value=="ABC123","scroll-focus-preserves-opaque-room-data");
                    }
                    multiplayer.Dispose();multiplayer=null;ReleaseCareerState();fixture.Detach();yield return Frames(4,false);fixture.Dispose();fixture=null;
                    screen=null;career=null;lobby=null;
                }
                Require(captures.Count==48&&scrollPairs.Count==24,"two-areas-two-edges-six-locales-two-sizes-captured");
                Require(commandEvents==0&&createEvents==0&&readyEvents==0&&rematchEvents==0&&created==null,"scroll-and-focus-emit-no-gameplay-or-account-command");
                Require(JToken.DeepEquals(globalBefore,Globals()),"global-quality-display-preferences-preserved");
                Require(Hash(proofPath)==proofHash&&Hash(unionPath)==unionHash&&boundInputs.All(pair=>Hash(pair.Key)==pair.Value),"attested-inputs-stable-through-attached-run");
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
                Report["passed"] = passed && fixture == null && (bool)Report["globalStateUnchanged"] && captures.Count == 48;
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
