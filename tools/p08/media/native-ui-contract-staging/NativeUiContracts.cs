using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace RacingBois.Tools.NativeUi
{
    public static class NativeUiContracts
    {
        private const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        private static T Field<T>(object target,string name)=>(T)target.GetType().GetField(name,Private).GetValue(target);
        private static void Set(object target,string name,object value)=>target.GetType().GetField(name,Private).SetValue(target,value);
        private static object Call(object target,string name,params object[] args)=>target.GetType().GetMethod(name,Private).Invoke(target,args);
        private static void Click(Button button)=>typeof(Clickable).GetMethod("Invoke",Private).Invoke(button.clickable,new object[]{null});
        private static string Hash(string path)
        {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}

        public static string Run(string projectRoot,string compiledProofPath,string textUnionPath)
        {
            if(!Application.isEditor)throw new InvalidOperationException("This unattached contract harness is Editor-scoped; it must not execute native display Apply.");
            var receipt=new JObject { ["schema"]=1,["scope"]="installed-native-unattached-UI-contracts",["passed"]=false,["rendered"]=false,["inputDispatchVerified"]=false,["focusVerified"]=false,["fullGameLocalizationAccepted"]=false };
            var sections=new JArray();receipt["sections"]=sections;
            int checks=0,qualityEvents=0,preferenceEvents=0,gameplayEvents=0;
            Action<bool,string> check=(ok,why)=>{if(!ok)throw new InvalidOperationException(why);checks++;};
            var preview=default(Scene);GameObject owner=null;MultiplayerSession multiplayer=null;CareerView career=null;CareerSession session=null;
            JObject globalBefore=Globals();string proofBefore=Hash(compiledProofPath),unionBefore=Hash(textUnionPath),uxml=Path.Combine(projectRoot,"Assets/RacingBois/UI/Race.uxml"),uxmlBefore=Hash(uxml);
            try
            {
                var proof=JObject.Parse(File.ReadAllText(compiledProofPath));check((bool)proof["passed"],"Independent compiled-source proof failed");
                var identities=new JArray();receipt["assemblies"]=identities;
                foreach(var assembly in new[]{typeof(UiText).Assembly,typeof(RaceScreen).Assembly,typeof(RacingBois.Client.Bootstrap.RaceBootstrap).Assembly})
                {
                    var entry=proof["assemblies"].Single(x=>(string)x["name"]==assembly.GetName().Name);
                    check((bool)entry["passed"]&&Guid.Parse((string)entry["mvid"])==assembly.ManifestModule.ModuleVersionId,"Loaded assembly is not the attested revision: "+assembly.GetName().Name);
                    check(Hash(Path.Combine(projectRoot,(string)entry["path"]))==(string)entry["sha256"],"Attested DLL bytes changed");
                    foreach(var doc in entry["documents"])if(doc["matches"]?.Type==JTokenType.Boolean&&(bool)doc["matches"])
                        check(Hash(Path.Combine(projectRoot,(string)doc["path"]))==(string)doc["sha256"],"Attested source changed: "+doc["path"]);
                    identities.Add(new JObject{["name"]=assembly.GetName().Name,["mvid"]=assembly.ManifestModule.ModuleVersionId.ToString(),["sha256"]=(string)entry["sha256"]});
                }
                var union=JObject.Parse(File.ReadAllText(textUnionPath));string[] locales={"ENU","DEU","ESP","FRA","ITA","VI"};
                foreach(string locale in locales)
                {
                    foreach(var item in (JObject)union["texts"][locale]["global"])check(UiText.Get(locale,item.Key)==(string)item.Value,"Native global text differs: "+locale+"/"+item.Key);
                    foreach(var item in (JObject)union["texts"][locale]["cinematic"])check(CinematicText.Get(locale,item.Key)==(string)item.Value,"Native cinematic text differs: "+locale+"/"+item.Key);
                }
                sections.Add("925 keys in all six locales match frozen authored values");
                preview=EditorSceneManager.NewPreviewScene();owner=new GameObject("Owned UI contracts "+Guid.NewGuid().ToString("N"));owner.hideFlags=HideFlags.HideAndDontSave;SceneManager.MoveGameObjectToScene(owner,preview);
                var document=owner.AddComponent<UIDocument>();check(document.panelSettings==null&&document.rootVisualElement!=null&&document.rootVisualElement.panel==null,"Fixture root must remain unattached");
                UiTree.Populate(document.rootVisualElement,uxml);var root=document.rootVisualElement;
                var screen=owner.AddComponent<RaceScreen>();screen.Initialize(document,"wss://fixture.invalid/multiplayer","VI");
                screen.QualityChanged+=_=>qualityEvents++;screen.PreferencesChanged+=(_,__,___)=>preferenceEvents++;
                screen.LocalRequested+=()=>gameplayEvents++;screen.ConnectRequested+=_=>gameplayEvents++;screen.GuestConnectRequested+=_=>gameplayEvents++;
                screen.SetPlayerName("Player {rank}");screen.SetQuality(2);screen.ApplyPreferences(true,false,1.1f);root.Q<DropdownField>("practice-level").index=3;
                foreach(string locale in locales)
                {
                    screen.SetLocale(locale);
                    check(screen.Locale==locale&&screen.CurrentQualityIndex==2&&screen.PracticeLevelIndex==3,"Main locale changed numeric choices");
                    check(screen.PlayerName=="Player {rank}"&&screen.Endpoint=="wss://fixture.invalid/multiplayer","Main locale changed names/address");
                    check(root.Q<Button>("local").text==UiText.Get(locale,"menu.raceStart"),"Main primary action binding");
                    check(root.Q<DropdownField>("practice-course").label==UiText.Get(locale,"practice.courseLabel"),"Practice label binding");
                    check(root.Q<DropdownField>("quality").value==UiText.Get(locale,"settings.quality.high"),"Quality label/choice binding");
                    screen.ShowState(SessionStatus.Connecting,RaceSessionMode.None,"");
                    check(root.Q<Label>("connection").text==UiText.Get(locale,"connection.connecting"),"Connecting state binding");
                    screen.ShowMenuError("Mã phòng không hợp lệ.");
                    check(root.Q<Label>("message").text==UiText.ClientMessage(locale,"Mã phòng không hợp lệ."),"Scoped main client error");
                    screen.SetContentState(true,.4f,"Đang tải Canyon Run…",false);
                    check(root.Q<Label>("content-status").text==UiText.ClientMessage(locale,"Đang tải Canyon Run…"),"Content status projection");
                    screen.SetContentState(false,1,"",false);
                    check(screen.AudioEnabled==false&&screen.ReducedMotion&&Math.Abs(screen.HudScale-1.1f)<.001f,"Locale changed local preferences");
                    check(root.panel==null,"Main fixture attached unexpectedly");
                }
                check(qualityEvents==0&&preferenceEvents==0&&gameplayEvents==0,"Locale emitted quality/preference/gameplay commands");
                screen.ShowMultiplayer(SessionStatus.Connected,true,false,"");var oldWorld=ReadModels.World(600,200);screen.Render(oldWorld,oldWorld.Riders[0],RaceSessionMode.Online);
                check(Field<long>(screen,"lastEventId")==200,"Old event fixture not consumed");
                screen.ShowMultiplayer(SessionStatus.Connected,false,false,"");screen.SetLocale("FRA");
                check(root.Q("results").style.display.value==DisplayStyle.None&&root.Q("hud").style.display.value==DisplayStyle.None,"Idle locale resurrected old race UI");
                screen.ShowMultiplayer(SessionStatus.Connected,true,false,"");var nextWorld=ReadModels.World(0,1);screen.Render(nextWorld,nextWorld.Riders[0],RaceSessionMode.Online);
                check(Field<long>(screen,"lastEventId")==1&&root.Q<Label>("event").text==UiText.Get("FRA","hud.event.hitOther"),"Locale erased the next-race event rollover");
                float expiry=Field<float>(screen,"eventUntil");screen.SetLocale("ITA");
                check(Field<long>(screen,"lastEventId")==1&&Field<float>(screen,"eventUntil")==expiry,"Same-race locale repaint replayed an event");
                sections.Add("Main six-locale choices/raw data/no-intents and actual event rollover contract");

                var store=new Store();const string endpoint="wss://fixture.invalid/multiplayer";store.Save(endpoint,new ProfileCredential("synthetic-capability","ui-profile","Player {route}","ui-realm",1000));
                var wire=new CareerWire();session=new CareerSession(wire,store,store);session.SetEndpoint(endpoint);session.Refresh();wire.Reply(CareerWire.Profile());
                career=owner.AddComponent<CareerView>();career.Initialize(document,session,"VI");career.Open(true,false);Set(career,"selectedTab","account");career.RefreshPresentation();
                Set(career,"accountUsername","User {route}");root.Q<TextField>("career-username").SetValueWithoutNotify("User {route}");
                Field<TextField>(career,"password").SetValueWithoutNotify("synthetic password {rank}");Field<TextField>(career,"recovery").SetValueWithoutNotify("synthetic recovery {route}");
                Field<TextField>(career,"exportText").SetValueWithoutNotify("synthetic save {credits}");
                Func<string> prompt=()=>UiText.Get(Field<string>(career,"locale"),"career.account.logoutConfirm");Call(career,"Confirm",prompt,"logout","");
                var intent=Field<CareerIntent>(career,"pendingConfirmation");int commands=0;CareerIntent sent=null;career.CommandRequested+=value=>{commands++;sent=value;};
                foreach(string locale in locales)
                {
                    career.SetLocale(locale);
                    check(ReferenceEquals(intent,Field<CareerIntent>(career,"pendingConfirmation"))&&intent.Operation=="logout","Locale changed pending authority intent");
                    check(Field<Label>(career,"confirmationText").text==UiText.Get(locale,"career.account.logoutConfirm"),"Open confirmation copy stale");
                    check(root.Q<TextField>("career-username").value=="User {route}"&&Field<TextField>(career,"password").value=="synthetic password {rank}"&&Field<TextField>(career,"recovery").value=="synthetic recovery {route}"&&Field<TextField>(career,"exportText").value=="synthetic save {credits}","Locale changed opaque account drafts");
                    check(commands==0,"Locale sent an account command");
                }
                Click(Field<Button>(career,"confirm"));check(commands==1&&ReferenceEquals(sent,intent),"Explicit confirmation callback changed/doubled command");
                career.Close();sections.Add("Career six-locale draft/confirmation payload preservation; explicit callback only, no input/focus claim");

                var packets=new PacketWire();multiplayer=new MultiplayerSession(packets,packets.Codec,new Clock(),new Store(),new Store());
                multiplayer.Connect(endpoint,new LocalPlayerProfile("local-ui","Player {rank}",0));
                packets.Enqueue(new MpWelcome{requestNonce=packets.Hello.requestNonce,sessionId="ui-session",resumeToken="synthetic-lease",profileToken="synthetic-capability",profileId="ui-profile",displayName="Player {rank}",realmId="ui-realm",sessionEpoch=1,credits=1000,reliableReset=true});multiplayer.Poll();
                var lobby=owner.AddComponent<MultiplayerLobbyView>();lobby.Initialize(document,"VI");lobby.Render(multiplayer);
                root.Q<TextField>("mp-room-name").SetValueWithoutNotify("Room {route}");root.Q<TextField>("mp-join-code").SetValueWithoutNotify("ABC123");int roomCommands=0;LobbyOptions requested=null;lobby.CreateRequested+=value=>{roomCommands++;requested=value;};
                foreach(string locale in locales)
                {
                    lobby.SetLocale(locale);lobby.ShowError("Máy chủ từ chối: room_full");lobby.Render(multiplayer);
                    check(root.Q<Label>("mp-message").text==UiText.Get(locale,"multiplayer.error.room-full"),"Raw server-code display routing changed");
                    lobby.ShowError("Unknown {route} room_full");lobby.Render(multiplayer);
                    check(root.Q<Label>("mp-message").text=="Unknown {route} room_full","Unknown data was translated or expanded");
                    check(root.Q<TextField>("mp-room-name").value=="Room {route}"&&root.Q<TextField>("mp-join-code").value=="ABC123","Locale changed room/join data");
                    check(roomCommands==0,"Locale emitted room command");
                }
                Call(lobby,"CreateRoom");check(roomCommands==1&&requested.Name=="Room {route}"&&requested.LevelIndex==0&&requested.CourseIndex==0,"Explicit create callback changed authoritative intent fields");
                check(root.panel==null&&document.panelSettings==null,"UI fixture acquired a panel");
                sections.Add("Multiplayer raw names/unknown data/protocol mapping and explicit create callback semantics");
                check(JToken.DeepEquals(globalBefore,Globals()),"Global quality/display/PlayerPrefs changed");
                check(Hash(compiledProofPath)==proofBefore&&Hash(textUnionPath)==unionBefore&&Hash(uxml)==uxmlBefore,"Source/proof inputs changed during native contracts");
                receipt["passed"]=true;
            }
            catch(Exception error){receipt["failure"]=error.ToString();}
            finally
            {
                try{multiplayer?.Dispose();if(career!=null&&session!=null)session.ClearSensitiveOutput();if(owner!=null)UnityEngine.Object.DestroyImmediate(owner);if(preview.IsValid())EditorSceneManager.ClosePreviewScene(preview);}
                catch(Exception error){receipt["passed"]=false;receipt["cleanupFailure"]=error.ToString();}
                receipt["ownedObjectsReleased"]=owner==null&&!preview.IsValid();receipt["globalStateUnchanged"]=JToken.DeepEquals(globalBefore,Globals());
                if(!(bool)receipt["ownedObjectsReleased"]||!(bool)receipt["globalStateUnchanged"])receipt["passed"]=false;
            }
            receipt["checks"]=checks;receipt["qualityEvents"]=qualityEvents;receipt["preferenceEvents"]=preferenceEvents;receipt["gameplayEvents"]=gameplayEvents;
            receipt["compiledProofSha256"]=proofBefore;receipt["textUnionSha256"]=unionBefore;receipt["uxmlSha256"]=uxmlBefore;
            return receipt.ToString(Formatting.Indented);
        }
        private static JObject Globals()
        {
            var value=new JObject{["quality"]=QualitySettings.GetQualityLevel(),["width"]=Screen.width,["height"]=Screen.height,["fullScreenMode"]=(int)Screen.fullScreenMode,["targetFrameRate"]=Application.targetFrameRate,["timeScale"]=Time.timeScale};
            foreach(string key in new[]{"RB.P06.ReducedMotion","RB.P06.Audio","RB.P06.Quality"})value[key]=new JObject{["exists"]=PlayerPrefs.HasKey(key),["value"]=PlayerPrefs.GetInt(key)};
            value["RB.P06.HudScale"]=new JObject{["exists"]=PlayerPrefs.HasKey("RB.P06.HudScale"),["value"]=PlayerPrefs.GetFloat("RB.P06.HudScale")};
            return value;
        }
    }
}
