"""Derive a bounded scroll-coverage driver from frozen, native-passed R5."""
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'owned-ui-driver-r5-staging'
path=HERE/'OwnedUiScrollDriver.cs'
if path.exists(): raise SystemExit('Fresh driver source required')
raw=(SOURCE/'AttachedUiDriver.cs').read_bytes()
if hashlib.sha256(raw).hexdigest()!='732c3abb0526d84e745f01efe28e2f148ddc7c5aa4f690f0cdea9e064440a796':
    raise SystemExit('Frozen R5 source differs')
source=raw.decode('utf-8').replace('AttachedUiDriver','OwnedUiScrollDriver')
source=source.replace('actual-owned-Editor-UI-render-focus-and-synthetic-navigation','actual-owned-Editor-scroll-viewport-focus-coverage')
source=source.replace('private readonly JArray captures = new JArray(), checks = new JArray(), actionMeasurements = new JArray(), headingMeasurements = new JArray();',
                      'private readonly JArray captures = new JArray(), checks = new JArray(), scrollPairs = new JArray();')
source=source.replace('            private long reliableSequence;\n            private int roomRevision;\n','')
start=source.index('                Report["singleLineActionMeasurements"]')
end=source.index('\n            }',start)
source=source[:start]+'                Report["scrollPairs"] = scrollPairs;'+source[end:]
start=source.index('            private void Capture()')
end=source.index('            private JObject ObserveResponsive()',start)
source=source[:start]+r'''            private static JObject Bounds(Rect bounds) => new JObject { ["x"]=bounds.x,["y"]=bounds.y,["width"]=bounds.width,["height"]=bounds.height };
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
'''+source[end:]
start=source.index('            private void MeasureActions()')
end=source.index('            private void SetupViews()',start)
source=source[:start]+source[end:]
source=source.replace('packets = new PacketWire(); reliableSequence = 0; roomRevision = 1;','packets = new PacketWire();')
start=source.index('            private void Room(LobbyPhase phase)')
end=source.index('            private void Tick()',start)
source=source[:start]+r'''            private IEnumerator Cases()
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
'''+source[end:]
source=source.replace('captures.Count == 108','captures.Count == 48')
path.write_text(source,encoding='utf-8')
project=(SOURCE/'Driver.csproj').read_text(encoding='utf-8').replace('RacingBois.Tools.AttachedUiDriverR5','RacingBois.Tools.OwnedUiScrollDriver')
project=project.replace('<Compile Include="AttachedUiDriver.cs" /><Compile Include="TextFit.cs" />','<Compile Include="OwnedUiScrollDriver.cs" />')
(HERE/'Driver.csproj').write_text(project,encoding='utf-8')
print('Created bounded owned scroll driver; no production writes')
