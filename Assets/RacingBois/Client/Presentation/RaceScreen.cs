using System;
using System.Collections.Generic;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Presentation
{
    public sealed partial class RaceScreen : MonoBehaviour
    {
        public event Action LocalRequested, LeaveRequested, RestartRequested, CareerRequested;
        public event Action<string> ConnectRequested;
        public event Action<string> GuestConnectRequested;
        public event Action<bool, bool, float> PreferencesChanged;
        public event Action<int> QualityChanged;
        public event Action UiFeedbackRequested;
        public string Endpoint => endpoint == null ? "" : endpoint.value.Trim();
        public void ShowMenuError(string text) { message.text=text; message.EnableInClassList("error-text",true); }
        public string PlayerName => playerName == null ? "Tay đua" : playerName.value.Trim();
        public bool ReducedMotion { get; private set; }
        public bool AudioEnabled { get; private set; } = true;
        public bool Cruise { get; private set; }
        public float HudScale { get; private set; } = 1;
        public int CurrentQualityIndex { get; private set; } = 1;
        public bool SettingsOpen => UiViewState.Visible(settings);
        public bool IsMenuOpen => UiViewState.Visible(menu);
        public bool IsTyping => UiViewState.HasTextFocus(root);
        public bool BlocksGameplayInput => SettingsOpen || PracticeOpen || ContentBusy || IsTyping || (raceActive && !UiViewState.Visible(results) && HasControlFocus());
        private readonly UiBindingScope bindings = new UiBindingScope();
        private readonly DesktopDisplaySettings desktopDisplay = new DesktopDisplaySettings();
        private SceneScrim sceneScrim;
        private int viewportWidth, viewportHeight;
        private VisualElement root, surface, menu, hud, results, recovery, health, condition, progress, networkPanel, settings, controls;
        private VisualElement positionBlock, vitalsBlock, speedBlock;
        private TextField endpoint, playerName;
        private Label connection, message, speed, rank, distance, weapon, state, resultTitle, resultDetail, recoveryTitle, recoveryHint, eventLabel, settingsContext, hudScaleLabel;
        private Button localButton, connectButton, guestButton, restartButton, cruiseButton, settingsButton, settingsClose, networkToggle;
        private Toggle reducedToggle, audioToggle;
        private Slider hudScaleSlider;
        private DropdownField quality;
        private VisualElement focusBeforeSettings;
        private bool networkOpen, gamepadNavigation, raceActive;
        private int consumedBackFrame = -1;
        private int lastSpeed = -1, lastRank = -1, lastCompetitors = -1, lastDistance = -1, lastTrack = -1;
        private float eventUntil;
        private RiderMode previousMode=(RiderMode)(-1);
        private long lastEventId;
        private long previousTick=-1;
        public void Initialize(UIDocument document,string defaultEndpoint)
        {
            if (root != null) return;
            root=document.rootVisualElement;surface=root.Q("surface");menu=root.Q("menu");hud=root.Q("hud");results=root.Q("results");
            sceneScrim = new SceneScrim(); surface.Insert(0, sceneScrim);
            root.focusable=true;
            networkPanel=root.Q("network-panel");settings=root.Q("settings");
            positionBlock=root.Q("position-block");vitalsBlock=root.Q("vitals-block");speedBlock=root.Q("speed-block");
            recovery=root.Q("recovery"); health=root.Q("health");condition=root.Q("condition");progress=root.Q("progress");
            endpoint=root.Q<TextField>("endpoint");endpoint.value=defaultEndpoint;
            playerName=root.Q<TextField>("player-name");
            connection=root.Q<Label>("connection");message=root.Q<Label>("message");
            speed=root.Q<Label>("speed");rank=root.Q<Label>("rank");distance=root.Q<Label>("distance");
            weapon=root.Q<Label>("weapon");state=root.Q<Label>("state");
            resultTitle=root.Q<Label>("result-title");resultDetail=root.Q<Label>("result-detail");
            recoveryTitle=root.Q<Label>("recovery-title");recoveryHint=root.Q<Label>("recovery-hint");eventLabel=root.Q<Label>("event");
            controls=root.Q<VisualElement>("controls");RefreshControlHints(false);settingsContext=root.Q<Label>("settings-context");hudScaleLabel=root.Q<Label>("hud-scale-label");
            RefreshPracticeSummary();
            localButton=root.Q<Button>("local");bindings.Click(localButton, ()=>LocalRequested?.Invoke());
            connectButton=root.Q<Button>("connect");bindings.Click(connectButton, ()=>ConnectRequested?.Invoke(endpoint.value.Trim()));
            guestButton=root.Q<Button>("connect-guest");bindings.Click(guestButton, ()=>GuestConnectRequested?.Invoke(endpoint.value.Trim()));
            networkToggle=root.Q<Button>("network-toggle");bindings.Click(networkToggle, ()=>SetNetworkOpen(!networkOpen));
            bindings.Click(root.Q<Button>("leave"), ()=>LeaveRequested?.Invoke());
            bindings.Click(root.Q<Button>("home"), ()=>LeaveRequested?.Invoke());
            restartButton=root.Q<Button>("restart");bindings.Click(restartButton, ()=>RestartRequested?.Invoke());
            cruiseButton=root.Q<Button>("cruise");bindings.Click(cruiseButton, ()=>{SetCruise(!Cruise);root.Focus();});
            settingsButton=root.Q<Button>("settings-open");settingsClose=root.Q<Button>("settings-close");
            bindings.Click(settingsButton, OpenSettings);bindings.Click(settingsClose, CloseSettings);
            bindings.Click(root.Q<Button>("career-open"), ()=>CareerRequested?.Invoke());
            InitializeP08();
            reducedToggle=root.Q<Toggle>("reduced-motion");audioToggle=root.Q<Toggle>("audio");hudScaleSlider=root.Q<Slider>("hud-scale");
            quality=root.Q<DropdownField>("quality");quality.choices=new List<string>{"THẤP — ưu tiên tốc độ","VỪA — cân bằng","CAO — chi tiết"};quality.index=1;
            bindings.Value(reducedToggle, e=>PreferencesUpdated());
            bindings.Value(audioToggle, e=>PreferencesUpdated());
            bindings.Value(hudScaleSlider, e=>PreferencesUpdated());
            bindings.Value(quality, e=>{CurrentQualityIndex=quality.index;QualityChanged?.Invoke(CurrentQualityIndex);UiFeedbackRequested?.Invoke();});
            root.Query<Button>().ForEach(button=>bindings.Click(button, ()=>UiFeedbackRequested?.Invoke()));
            root.Query<TextElement>().ForEach(element=>element.enableRichText=false);
            // Unity 6 InputForUI supplies keyboard and gamepad Navigate/Submit/Cancel.
            bindings.Register<NavigationCancelEvent>(root, e=>{if(HandleBack()){e.StopImmediatePropagation();root.panel?.focusController.IgnoreEvent(e);}});
            bindings.Register<NavigationMoveEvent>(root, e=>
            {
                if(raceActive&&!SettingsOpen&&!UiViewState.Visible(results)&&!HasControlFocus()){e.StopImmediatePropagation();root.panel?.focusController.IgnoreEvent(e);}
            },TrickleDown.TrickleDown);
            bindings.Register<NavigationSubmitEvent>(root, e=>
            {
                if(raceActive&&!SettingsOpen&&!UiViewState.Visible(results)&&!HasControlFocus()){e.StopImmediatePropagation();root.panel?.focusController.IgnoreEvent(e);}
            },TrickleDown.TrickleDown);
            bindings.Register<FocusOutEvent>(settings, e=>
            {
                if(!ContentBusy && settings.enabledInHierarchy && SettingsOpen && e.relatedTarget is VisualElement next && !settings.Contains(next))
                    settings.schedule.Execute(()=>{if(!ContentBusy && settings.enabledInHierarchy && SettingsOpen)settingsClose.Focus();});
            });
            bindings.Register<FocusInEvent>(root, e=>
            {
                if(!ContentBusy && settings.enabledInHierarchy && SettingsOpen&&e.target is VisualElement target&&target!=settings&&!settings.Contains(target))
                    settings.schedule.Execute(()=>{if(!ContentBusy && settings.enabledInHierarchy && SettingsOpen)settingsClose.Focus();});
            });
            bindings.Register<KeyDownEvent>(settings, e=>
            {
                if(e.keyCode!=KeyCode.Tab)return;
                var targets=new List<VisualElement>();
                foreach(var element in settings.Query<VisualElement>().ToList())
                    if((element is Button || element is DropdownField || element is Toggle || element is Slider) && element.enabledInHierarchy && element.resolvedStyle.display!=DisplayStyle.None)
                        targets.Add(element);
                if(targets.Count==0)return;
                var focused=root.panel?.focusController.focusedElement as VisualElement;
                var first=targets[0];var last=targets[targets.Count-1];
                if(e.shiftKey&&(focused==first||first.Contains(focused))){last.Focus();e.StopImmediatePropagation();root.panel?.focusController.IgnoreEvent(e);}
                else if(!e.shiftKey&&(focused==last||last.Contains(focused))){first.Focus();e.StopImmediatePropagation();root.panel?.focusController.IgnoreEvent(e);}
            },TrickleDown.TrickleDown);
            bindings.Register<GeometryChangedEvent>(surface, e=>UpdateResponsiveLayout(e.newRect));
            // Stylesheet display:none has no inline value yet; initialize explicitly for transition helpers.
            foreach(var panel in new[]{hud,results,recovery,networkPanel,settings,eventLabel})panel.style.display=DisplayStyle.None;
            desktopDisplay.Initialize(settings);
            ApplyPreferences(false,true,1);
            localButton.Focus();
        }
        public void ApplyPreferences(bool reducedMotion,bool audioEnabled,float hudScale)
        {
            ReducedMotion=reducedMotion;AudioEnabled=audioEnabled;HudScale=Mathf.Clamp(hudScale,.85f,1.15f);
            reducedToggle.SetValueWithoutNotify(reducedMotion);audioToggle.SetValueWithoutNotify(audioEnabled);hudScaleSlider.SetValueWithoutNotify(HudScale);
            surface.EnableInClassList("reduced-motion",ReducedMotion);
            var scale=new Scale(new Vector3(HudScale,HudScale,1));
            positionBlock.style.scale=scale;vitalsBlock.style.scale=scale;speedBlock.style.scale=scale;
            hudScaleLabel.text="KÍCH THƯỚC HUD  ·  "+Mathf.RoundToInt(HudScale*100)+"%";
        }
        public void SetQuality(int index)
        {
            CurrentQualityIndex=Mathf.Clamp(index,0,2);quality.SetValueWithoutNotify(quality.choices[CurrentQualityIndex]);
        }
        private void PreferencesUpdated()
        {
            ApplyPreferences(reducedToggle.value,audioToggle.value,hudScaleSlider.value);
            PreferencesChanged?.Invoke(ReducedMotion,AudioEnabled,HudScale);UiFeedbackRequested?.Invoke();
        }
        public void OpenSettings()
        {
            ClosePractice();
            if(SettingsOpen || ContentBusy)return;
            focusBeforeSettings=root.panel?.focusController.focusedElement as VisualElement;
            settingsContext.text=raceActive?"Cuộc đua vẫn tiếp tục khi mở cài đặt. Xe ngừng nhận điều khiển.":"Tinh chỉnh để tìm nhịp đua phù hợp với bạn.";
            SetCruise(false);UiViewState.Show(settings,true);settingsClose.Focus();
        }
        public void CloseSettings()
        {
            if(!SettingsOpen)return;UiViewState.Show(settings,false);
            if(raceActive&&!UiViewState.Visible(results))root.Focus();
            else if(focusBeforeSettings!=null&&focusBeforeSettings.enabledInHierarchy&&focusBeforeSettings.resolvedStyle.display!=DisplayStyle.None)focusBeforeSettings.Focus();
            else settingsButton.Focus();
        }
        public bool HandleBack()
        {
            // Native UI Cancel and gameplay input can observe the same physical press.
            if(consumedBackFrame==Time.frameCount)return true;
            if(ContentBusy){consumedBackFrame=Time.frameCount;return true;}
            if(PracticeOpen){ClosePractice();consumedBackFrame=Time.frameCount;return true;}
            if(SettingsOpen){CloseSettings();consumedBackFrame=Time.frameCount;return true;}
            if(IsMenuOpen&&networkOpen){SetNetworkOpen(false);consumedBackFrame=Time.frameCount;return true;}
            if(raceActive&&HasControlFocus()&&!UiViewState.Visible(results)){root.Focus();consumedBackFrame=Time.frameCount;return true;}
            return false;
        }
        private bool HasControlFocus()
        {
            var focused=root?.panel?.focusController.focusedElement as VisualElement;
            return focused!=null&&focused!=root&&focused!=surface;
        }
        private void SetNetworkOpen(bool open)
        {
            networkOpen=open;UiViewState.Show(networkPanel,open);menu.EnableInClassList("network-open",open);
            if (menu is ScrollView scroll) scroll.verticalScrollerVisibility = open ? ScrollerVisibility.Auto : ScrollerVisibility.Hidden;
            networkToggle.text=open?"ĐÓNG KẾT NỐI":"ONLINE / LAN";
            if(open)playerName.Focus();else networkToggle.Focus();
        }
        public void SetGamepadNavigation(bool value)
        {
            if(gamepadNavigation==value)return;gamepadNavigation=value;
            RefreshControlHints(value);
            if(value&&IsMenuOpen&&!SettingsOpen&&!IsTyping)localButton.Focus();
        }
        private void RefreshControlHints(bool gamepad)
        {
            controls.Clear();
            string[] keys = gamepad ? new[] { "RT / LT", "CẦN TRÁI", "LB / RB", "A + LB / RB" } : new[] { "W / S", "A / D", "Q / E", "Shift + Q / E" };
            string[] actions = { "Ga/Phanh", "Lái", "Đánh", "Đá" };
            for (int i = 0; i < keys.Length; i++)
            {
                var pair = new VisualElement(); pair.AddToClassList("control-pair");
                var key = new Label(keys[i]) { enableRichText = false }; key.AddToClassList("keycap");
                var action = new Label(actions[i]) { enableRichText = false }; action.AddToClassList("control-action");
                pair.Add(key); pair.Add(action); controls.Add(pair);
            }
        }
        public void SetCruise(bool value)
        {
            Cruise=value;cruiseButton.text=value?"GIỮ GA: BẬT":"GIỮ GA: TẮT";
        }
        public void SetPlayerName(string value) { playerName.SetValueWithoutNotify(value); }
        public void ShowMultiplayer(SessionStatus status,bool racing,bool reconnecting,string error,double roundTripMs=0,bool degraded=false)
        {
            bool wasMenu=IsMenuOpen;
            bool enteringRace=racing&&!raceActive;
            raceActive=racing;surface.EnableInClassList("race-active",racing);UiViewState.Show(root.Q("career-open"),!racing);
            UiViewState.Show(menu,status==SessionStatus.Offline||status==SessionStatus.Failed);
            UiViewState.Show(sceneScrim, IsMenuOpen);
            UiViewState.Show(hud,racing);UiViewState.Show(results,false);
            if(IsMenuOpen&&!wasMenu)localButton.Focus();
            if(enteringRace&&!SettingsOpen)root.Focus();
            connection.text=reconnecting?"ĐANG KẾT NỐI LẠI":status==SessionStatus.Connected?"ONLINE / LAN":status==SessionStatus.Connecting?"ĐANG KẾT NỐI":"SẴN SÀNG LÊN ĐƯỜNG";
            if(status==SessionStatus.Connected&&racing&&!reconnecting)connection.text=(degraded?"ĐỘ TRỄ CAO / ":"ONLINE / ")+roundTripMs.ToString("0")+" MS";
            connection.EnableInClassList("connection-warning",reconnecting||degraded);
            message.text=string.IsNullOrEmpty(error)?"Hồ sơ lưu trên máy chủ; Khách mới tạo một người chơi riêng.":MultiplayerCopy.Error(error);
            connectButton.SetEnabled(status!=SessionStatus.Connecting);
            guestButton.SetEnabled(status!=SessionStatus.Connecting);
            localButton.SetEnabled(!ContentBusy && status!=SessionStatus.Connecting);
            message.EnableInClassList("error-text",!string.IsNullOrEmpty(error));
            connectButton.text="HỒ SƠ ĐÃ LƯU";
            if(!racing||reconnecting)SetCruise(false);
        }
        public void ShowState(SessionStatus status,RaceSessionMode mode,string error)
        {
            bool active=status==SessionStatus.Connected;
            bool wasMenu=IsMenuOpen;raceActive=active;surface.EnableInClassList("race-active",active);UiViewState.Show(root.Q("career-open"),!active);
            UiViewState.Show(menu,!active);UiViewState.Show(hud,active);
            UiViewState.Show(sceneScrim, !active);
            if(!active)UiViewState.Show(results,false);
            localButton.SetEnabled(!ContentBusy && status!=SessionStatus.Connecting);
            connectButton.SetEnabled(status!=SessionStatus.Connecting);
            guestButton.SetEnabled(status!=SessionStatus.Connecting);
            connectButton.text=status==SessionStatus.Connecting?"ĐANG KẾT NỐI...":"KẾT NỐI";
            connection.text=active?(mode==RaceSessionMode.Local?"CHƠI ĐƠN / OFFLINE":"ĐÃ KẾT NỐI MÁY CHỦ"):
                status==SessionStatus.Connecting?"ĐANG KẾT NỐI":"SẴN SÀNG LÊN ĐƯỜNG";
            message.text=string.IsNullOrEmpty(error)?"Kết quả luyện tập không cộng vào hồ sơ máy chủ.":error;
            message.EnableInClassList("error-text",!string.IsNullOrEmpty(error));
            connection.EnableInClassList("connection-warning",status==SessionStatus.Failed);
            if(!active) { SetCruise(false);previousMode=(RiderMode)(-1);previousTick=-1;lastEventId=0; }
            if(active)root.Focus();
            else if(!wasMenu)localButton.Focus();
        }
        public void Render(RaceWorldReadModel world,RaceRiderReadModel rider,RaceSessionMode sessionMode,LocalCampaignReadModel campaign=default,int participantCount=0)
        {
            if(world==null)return;
            if(world.Tick<previousTick) { previousMode=(RiderMode)(-1);lastEventId=0;eventUntil=0; }
            previousTick=world.Tick;
            int competitors=0;foreach(var other in world.Riders)if(other.Kind!=RiderKind.Police)competitors++;
            if(participantCount>0)competitors=participantCount;
            int currentSpeed=Mathf.RoundToInt(rider.SpeedMetersPerSecond*3.6f);
            if(lastSpeed!=currentSpeed){lastSpeed=currentSpeed;speed.text=currentSpeed.ToString("000");}
            if(lastRank!=rider.Rank||lastCompetitors!=competitors){lastRank=rider.Rank;lastCompetitors=competitors;rank.text=rider.Rank.ToString("00")+" / "+competitors.ToString("00");}
            int distanceUnits=Mathf.RoundToInt(Mathf.Max(0,rider.LongitudinalMeters)/10),trackUnits=Mathf.RoundToInt(world.TrackLengthMeters/10);
            if(lastDistance!=distanceUnits||lastTrack!=trackUnits){lastDistance=distanceUnits;lastTrack=trackUnits;distance.text=(distanceUnits/100f).ToString("0.00")+" / "+(trackUnits/100f).ToString("0.00")+" KM";}
            UiViewState.Text(weapon,rider.Weapon==WeaponKind.Club?"GẬY":rider.Weapon==WeaponKind.Chain?"DÂY XÍCH":"TAY KHÔNG");
            health.style.width=Length.Percent(Mathf.Clamp01(rider.Health/(float)GameplayRules.InitialHealth)*100);
            condition.style.width=Length.Percent(Mathf.Clamp01(rider.BikeCondition/(float)GameplayRules.InitialBikeCondition)*100);
            vitalsBlock.EnableInClassList("vitals-danger",rider.Health<GameplayRules.InitialHealth*.25f||rider.BikeCondition<GameplayRules.InitialBikeCondition*.25f);
            progress.style.width=Length.Percent(Mathf.Clamp01(rider.LongitudinalMeters/world.TrackLengthMeters)*100);
            UiViewState.Text(state,ModeText(rider.Mode));
            if(rider.Mode!=previousMode)
            {
                previousMode=rider.Mode;
                bool detached=rider.Mode==RiderMode.Falling||rider.Mode==RiderMode.Detached||rider.Mode==RiderMode.Running||rider.Mode==RiderMode.Remounting;
                UiViewState.Show(recovery,detached);
                recoveryTitle.text=ModeText(rider.Mode);
                recoveryHint.text=rider.Mode==RiderMode.Running?"Tay đua đang chạy về xe. Cuộc đua vẫn tiếp tục.":"Giữ bình tĩnh. Lấy lại nhịp đua.";
                bool terminal=GameplayRules.IsTerminal(rider.Mode);
                UiViewState.Show(results,terminal&&sessionMode==RaceSessionMode.Local);
                if(terminal)
                {
                    resultTitle.text=rider.Mode==RiderMode.Finished?(rider.Qualified?"VƯỢT QUA CHẶNG.":"VỀ ĐÍCH.") : rider.Mode==RiderMode.Busted?"BỊ BẮT.":"XE HƯ HỎNG.";
                    resultDetail.text=rider.Mode==RiderMode.Finished?
                        "Hạng "+rider.Rank+" · "+(rider.FinishTick/60f).ToString("0.0")+" giây\nThưởng luyện tập trong phiên: $"+rider.Reward:
                        rider.Mode==RiderMode.Busted?"Tiền phạt luyện tập trong phiên: $"+Mathf.Abs(rider.Reward):"Cuộc đua kết thúc. Thử lại với một đường chạy tốt hơn.";
                    if(sessionMode==RaceSessionMode.Local)resultDetail.text+="\nQuỹ luyện tập trong phiên: $"+campaign.Credits;
                    restartButton.style.display=sessionMode==RaceSessionMode.Local?DisplayStyle.Flex:DisplayStyle.None;
                    if(sessionMode==RaceSessionMode.Local)restartButton.Focus();
                    Cruise=false;
                }
            }
            foreach(var item in world.Events)
            {
                if(item.Id<=lastEventId)continue;
                lastEventId=item.Id;
                if(item.SourceId!=rider.Id&&item.TargetId!=rider.Id)continue;
                string text=item.Kind==RaceEventKind.Hit?(item.SourceId==rider.Id?"ĐÁNH TRÚNG":"TRÚNG ĐÒN"):
                    item.Kind==RaceEventKind.WeaponStolen?"ĐỔI VŨ KHÍ":item.Kind==RaceEventKind.Remounted?"TRỞ LẠI CUỘC ĐUA":
                    item.Kind==RaceEventKind.Landed?"TIẾP ĐẤT":"";
                if(text.Length>0){eventLabel.text=text;eventUntil=Time.unscaledTime+1.3f;}
            }
            UiViewState.Show(eventLabel,Time.unscaledTime<eventUntil);
        }
        private void Update()
        {
            if (root != null && (viewportWidth != Screen.width || viewportHeight != Screen.height))
                UpdateResponsiveLayout(surface.contentRect);
        }
        private void UpdateResponsiveLayout(Rect bounds)
        {
            viewportWidth = Screen.width; viewportHeight = Screen.height;
            // ScaleWithScreenSize may keep logical bounds constant as output pixels shrink.
            surface.EnableInClassList("compact", viewportHeight < 900 || viewportWidth < 1440);
            surface.EnableInClassList("narrow", viewportWidth < 1200 || bounds.width < 1100);
            surface.EnableInClassList("race-active", raceActive);
        }
        private void OnDestroy()
        {
            ReleaseContentOwnership();
            sceneScrim?.RemoveFromHierarchy();
            desktopDisplay.Dispose(); bindings.Dispose();
            LocalRequested = LeaveRequested = RestartRequested = CareerRequested = null;
            ConnectRequested = GuestConnectRequested = null;
            PreferencesChanged = null; QualityChanged = null; UiFeedbackRequested = null;
            ContentRetryRequested = GalleryRequested = null;
        }
        private static string ModeText(RiderMode mode)
        {
            switch(mode)
            {
                case RiderMode.Attacking:return "ĐANG RA ĐÒN";
                case RiderMode.Hit:return "TRÚNG ĐÒN";
                case RiderMode.Airborne:return "RỜI MẶT ĐƯỜNG";
                case RiderMode.Falling:return "MẤT THĂNG BẰNG";
                case RiderMode.Detached:return "ĐỨNG DẬY";
                case RiderMode.Running:return "CHẠY VỀ XE";
                case RiderMode.Remounting:return "LÊN XE";
                case RiderMode.Wrecked:return "XE HƯ HỎNG";
                case RiderMode.Busted:return "BỊ CẢNH SÁT BẮT";
                case RiderMode.Finished:return "ĐÃ VỀ ĐÍCH";
                default:return "ĐANG ĐUA";
            }
        }
    }
}
