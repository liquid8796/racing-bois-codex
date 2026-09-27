using System;
using System.Runtime.InteropServices;
using RacingBois.Client.Adapters;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Profiling;
using Unity.Profiling;
using UnityEngine.UIElements;

namespace RacingBois.Client.Bootstrap
{
    public sealed class RaceBootstrap : MonoBehaviour
    {
        public RaceStageView Stage;
        public UIDocument Document;
        public RaceAudioBank AudioBank;
        public Material DustMaterial, SparkMaterial, SkidMaterial;
        public RaceVisualQuality VisualQuality;
        public string EditorContentBaseUrl = "";
        private DesktopRuntimeConfig desktopConfig = new DesktopRuntimeConfig();
        private string runtimeConfigError = "";
        private P08ContentLoader contentLoader;
        private P08MusicDirector musicDirector;
        private BootstrapCinematicCoordinator cinematics;
        private bool outcomeShown,returnToCareerAfterShowcase;
        private string refreshedResultId="";
        private int practiceCourse,practiceLevel,practiceBike,practiceCharacter,pendingShowcase=-1;
        public P08ContentLoader ContentLoader => contentLoader;
        private BrowserSocketTransport transport;
        private RaceSession session;
        private MultiplayerSession multiplayer;
        private UnityMultiplayerStorage storage;
        private LocalPlayerProfile profile;
        private MultiplayerLobbyView lobby;
        private CareerSession career;
        private CareerView careerView;
        private RaceStageView.MenuPreviewState priorMenuPreview;
        private bool careerPreviewVisible, menuPreviewCaptured, menuPreviewDirty, menuPreviewRestorePending, previewShowsRider;
        private int inspectedBikeIndex, inspectedCharacterIndex;
        private CareerIntent queuedCareerIntent;
        private bool openCareerAfterConnect, reconnectForCareer;
        private LobbyOptions pendingCareerRace;
        private string careerSessionPlayerId="";
        private bool useMultiplayer, returningToMenu, wasReconnecting, pendingLocalStart, storageWarningShown;
        private RaceScreen screen;
        private RaceAudio audioView;
        private RaceEffectsView effectsView;
        private float accumulated,telemetryTime,uiTime;
        private bool debugVisible;
        private int bufferedAttack;
        private bool bufferedKick;
        private readonly float[] frames=new float[360],sorted=new float[360];
        private int frameIndex,frameCount;
        private readonly FrameTiming[] timings=new FrameTiming[1];
        private readonly Metrics metrics=new Metrics();
        private ProfilerRecorder allocations;
        public RaceSession Session => session;
        public MultiplayerSession Multiplayer => multiplayer;
#if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern void RB_RegisterLifecycle(string receiver);
#endif
        [Serializable] private sealed class Metrics
        {
            public string state,mode,riderState,weapon,content=GameplayRules.ContentHash;
            public int player,inputs,peers,traffic,pedestrians,rank,health,bike,fps,width,height;
            public long tick;public int ack;public float speed,distance,lateral,frameP50Ms,frameP95Ms;
            public double gameUpdateMs,cpuFrameMs,gpuFrameMs;
            public long unityAllocatedBytes,managedBytes;public bool frameTimingAvailable,gpuTimingAvailable;
            public long frameGcBytes;public bool allocationCounterAvailable;
            public bool sharedGameplayPassed;public string gameplayReplayHash;public int gameplayReplayTicks;
            public string room,roomPhase;public double rttMs;public float correctionMeters;
            public string buildVersion,sessionId,contentLoadError,musicId,musicState,musicError,cinematicId;
            public bool cinematicPlaying;
            public int courseIndex,levelIndex,bikeCatalogIndex,characterCatalogIndex,loadedCourse;
            public bool contentReady,contentLoading;public long contentDownloadedBytes;
            public int pendingInputs,lateInputs,futureInputs,missingInputs,staleRemotes;public bool reconnecting;
            public int graphicsQuality,activeDustEmitters,impactEffects,audioEvents;
            public bool audioUnlocked,audioMuted,audioBankReady;
        }
        private void Start()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            try { desktopConfig = DesktopConfiguration.Read(); }
            catch (Exception error) when (error is ArgumentException || error is System.IO.IOException || error is UnauthorizedAccessException)
            {
                desktopConfig = new DesktopRuntimeConfig();
                runtimeConfigError = "Cấu hình máy chủ không hợp lệ. Đang dùng chế độ LAN tại máy này; hãy sửa RacingBois.runtime.json để chơi online.";
                Debug.LogWarning("Desktop configuration rejected: " + error.GetType().Name);
            }
#endif
            UnityEngine.Application.targetFrameRate=60;
            metrics.buildVersion=UnityEngine.Application.version;
            allocations=ProfilerRecorder.StartNew(ProfilerCategory.Memory,"GC Allocated In Frame",1);
            var verification=GameplayVerification.Run();
            metrics.sharedGameplayPassed=verification.Passed;metrics.gameplayReplayHash=verification.Hash;metrics.gameplayReplayTicks=verification.Ticks;
            Debug.Log("RB_GAMEPLAY_REPLAY "+(verification.Passed?"PASS ":"FAIL ")+verification.Hash);
            transport=gameObject.AddComponent<BrowserSocketTransport>();gameObject.name="RacingBoisNetwork";
            session=new RaceSession(transport,new UnityWireCodec());
            storage=new UnityMultiplayerStorage();profile=storage.LoadOrCreate();
            multiplayer=new MultiplayerSession(transport,new UnityWireCodec(),new UnityMonotonicClock(),storage,storage);
            screen=gameObject.AddComponent<RaceScreen>();screen.Initialize(Document,DefaultEndpoint());
            screen.ApplyPreferences(PlayerPrefs.GetInt("RB.P06.ReducedMotion",0)!=0,PlayerPrefs.GetInt("RB.P06.Audio",1)!=0,PlayerPrefs.GetFloat("RB.P06.HudScale",1));
            screen.SetQuality(PlayerPrefs.GetInt("RB.P06.Quality",1));
            screen.PreferencesChanged+=SavePreferences;screen.QualityChanged+=ApplyQuality;
            screen.UiFeedbackRequested+=UiFeedback;
            screen.SetPlayerName(profile.DisplayName);
            screen.LocalRequested+=StartLocal;screen.ConnectRequested+=Connect;screen.LeaveRequested+=Leave;screen.RestartRequested+=Restart;
            screen.GuestConnectRequested+=ConnectGuest;
            screen.ContentRetryRequested+=RetryContent;screen.GalleryRequested+=OpenCinematicGallery;
            career=new CareerSession(gameObject.AddComponent<UnityCareerTransport>(),storage,storage);
            career.SetEndpoint(DefaultEndpoint());
            careerView=gameObject.AddComponent<CareerView>();careerView.Initialize(Document,career);
            screen.CareerRequested+=OpenCareer;
            careerView.CommandRequested+=CareerCommand;careerView.RefreshRequested+=career.Refresh;careerView.RetryRequested+=career.Retry;
            careerView.ConnectRequested+=ConnectCareer;careerView.RaceRequested+=CreateCareerRace;careerView.ShowcaseRequested+=PlayShowcase;
            careerView.SelectedBikePreviewRequested+=PreviewBike;careerView.SelectedCharacterPreviewRequested+=PreviewCharacter;careerView.PreviewVisibilityChanged+=PreviewVisibilityChanged;
            career.Changed+=()=>{if(career.Profile!=null)lobby?.SetCareerLevel(career.Profile.LevelIndex);};
            session.Changed+=StateChanged;
            multiplayer.Changed+=MultiplayerChanged;
            lobby=gameObject.AddComponent<MultiplayerLobbyView>();lobby.Initialize(Document);
            lobby.UiFeedbackRequested+=UiFeedback;
            lobby.PrefillInvite(CareerSession.InviteCode(UnityEngine.Application.absoluteURL));
            lobby.CreateRequested+=options=>RunCommand(()=>multiplayer.CreateLobby(options));
            lobby.JoinRequested+=code=>RunCommand(()=>multiplayer.JoinLobby(code));
            lobby.ReadyRequested+=ToggleReady;lobby.StartRequested+=()=>{if(multiplayer.Room!=null&&contentLoader.IsReady(multiplayer.Room.CourseIndex))RunCommand(multiplayer.StartRace);};
            lobby.LeaveRequested+=()=>RunCommand(multiplayer.LeaveLobby);lobby.DisconnectRequested+=DisconnectMultiplayer;
            lobby.RefreshRequested+=()=>RunCommand(multiplayer.RequestLobbyList);lobby.RematchRequested+=()=>RunCommand(multiplayer.BackToLobby);
            audioView=gameObject.AddComponent<RaceAudio>();audioView.Initialize(AudioBank);
            Stage.UseExternalEffects=DustMaterial!=null&&SparkMaterial!=null&&SkidMaterial!=null;
            Stage.Build();
            musicDirector=gameObject.AddComponent<P08MusicDirector>();
            contentLoader=gameObject.AddComponent<P08ContentLoader>();contentLoader.Configure(EditorContentBaseUrl,desktopConfig);
#if !UNITY_WEBGL || UNITY_EDITOR
            musicDirector.ConfigureContentBase(DesktopConfiguration.ContentBase(desktopConfig,EditorContentBaseUrl));
#endif
            contentLoader.MusicRequested+=PlayStreamedMusic;contentLoader.BeforeRouteUnload+=BeforeContentUnload;contentLoader.Ready+=ContentReady;contentLoader.Changed+=ContentChanged;
            cinematics=gameObject.AddComponent<BootstrapCinematicCoordinator>();
            cinematics.Initialize(Stage,Document,musicDirector,contentLoader.ResolveMusicUrl,()=>!useMultiplayer||multiplayer.Room==null||multiplayer.Room.Phase==LobbyPhase.Lobby||multiplayer.Room.Phase==LobbyPhase.Results);
            cinematics.ContentRequired+=LoadGalleryContent;cinematics.Director.Completed+=CinematicCompleted;
            if(DustMaterial!=null&&SparkMaterial!=null&&SkidMaterial!=null)
            {
                effectsView=gameObject.AddComponent<RaceEffectsView>();
                effectsView.Initialize(Stage.Road,DustMaterial,SparkMaterial,SkidMaterial);
                Stage.UseExternalEffects=true;
            }
            ApplyQuality(screen.CurrentQualityIndex);StateChanged();
            if(runtimeConfigError.Length>0)screen.ShowMenuError(runtimeConfigError);
#if UNITY_STANDALONE_WIN && !UNITY_EDITOR
            DesktopAcceptanceRecorder.TryAttach(this,()=>useMultiplayer,()=>screen.CurrentQualityIndex,
                ()=>cinematics!=null&&cinematics.Director.IsPlaying,
                ()=>screen.BlocksGameplayInput||careerView.IsOpen||(cinematics!=null&&cinematics.BlocksGameplayInput));
#endif
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_RegisterLifecycle(gameObject.name);
#endif
        }
        private void SavePreferences(bool reduced,bool audio,float scale)
        {
            PlayerPrefs.SetInt("RB.P06.ReducedMotion",reduced?1:0);PlayerPrefs.SetInt("RB.P06.Audio",audio?1:0);
            PlayerPrefs.SetFloat("RB.P06.HudScale",scale);PlayerPrefs.Save();
            if(audioView!=null)audioView.SetMuted(!audio);if(cinematics!=null)cinematics.ApplyPreferences(reduced,audio);
        }
        private void ApplyQuality(int index)
        {
            if(VisualQuality!=null)VisualQuality.Apply(index);
            if(effectsView!=null)effectsView.SetQuality(index==0);
            Stage.Road.SetSceneryQuality(index);
            PlayerPrefs.SetInt("RB.P06.Quality",index);PlayerPrefs.Save();
        }
        private void UiFeedback()
        {
            if(audioView==null)return;
            audioView.UnlockFromUserGesture();musicDirector?.UnlockFromUserGesture();audioView.SetMuted(!screen.AudioEnabled);audioView.PlayUi();
        }
        private string DefaultEndpoint()
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            if(Uri.TryCreate(UnityEngine.Application.absoluteURL,UriKind.Absolute,out var page))
                return (page.Scheme=="https"?"wss://":"ws://")+page.Authority+"/multiplayer";
            return DesktopRuntimeConfigRules.DefaultLanEndpoint;
#else
            return DesktopRuntimeConfigRules.BackendEndpoint(desktopConfig ?? new DesktopRuntimeConfig());
#endif
        }
        private void OpenCareer()
        {
            if(screen.SettingsOpen)screen.CloseSettings();
            try { career.SetEndpoint(screen.Endpoint); }
            catch(ArgumentException error) { screen.ShowMenuError(error.Message); return; }
            bool guest=multiplayer.Status==SessionStatus.Connected&&multiplayer.IsGuest;
            if(guest)career.ClearView();
            careerView.Open(multiplayer.Status==SessionStatus.Connected,multiplayer.Room!=null,guest);
            if(career.HasCredential&&!guest)career.Refresh();
            if(ContentRegistry.Actors==null)EnsureContent(0,0);
        }
        private void PreviewVisibilityChanged(bool visible)
        {
            if(visible==careerPreviewVisible)return;
            careerPreviewVisible=visible;
            if(visible)
            {
                if(!menuPreviewCaptured){priorMenuPreview=Stage.CaptureMenuPreview();menuPreviewCaptured=true;}
                menuPreviewRestorePending=false;menuPreviewDirty=true;
            }
            else{menuPreviewRestorePending=menuPreviewCaptured;menuPreviewDirty=false;UpdateMenuPreview(false);}
        }
        private void PreviewBike(int index)
        {
            if(index<0||index>=BikeCatalog.Count)return;
            inspectedBikeIndex=index;previewShowsRider=false;menuPreviewDirty=true;
        }
        private void PreviewCharacter(int index)
        {
            if(index<0||index>=CharacterCatalog.Count)return;
            inspectedCharacterIndex=index;previewShowsRider=true;menuPreviewDirty=true;
        }
        private void UpdateMenuPreview(bool renderingRace)
        {
            if(Stage==null||renderingRace||!Stage.MenuPreviewReady||cinematics!=null&&cinematics.Director.IsPlaying)return;
            if(menuPreviewRestorePending)
            {
                if(Stage.RestoreMenuPreview(priorMenuPreview))menuPreviewRestorePending=menuPreviewCaptured=false;
            }
            if(careerPreviewVisible&&menuPreviewDirty&&Stage.SetMenuPreview(inspectedBikeIndex,inspectedCharacterIndex,previewShowsRider))menuPreviewDirty=false;
        }
        private void CareerCommand(CareerIntent request)
        {
            if(request==null||career.Busy||queuedCareerIntent!=null)return;
            if(CareerSession.ChangesIdentity(request.Operation)&&multiplayer.Status!=SessionStatus.Offline)
            {
                queuedCareerIntent=request;returningToMenu=true;multiplayer.Disconnect();
            }
            else career.Execute(request);
        }
        private void ConnectCareer()
        {
            openCareerAfterConnect=true;
            if(multiplayer.Status!=SessionStatus.Offline||multiplayer.IsDisconnecting)
            { reconnectForCareer=true;returningToMenu=true;multiplayer.Disconnect(); }
            else ConnectMultiplayer(screen.Endpoint,false);
        }
        private void CreateCareerRace(int level,int course)
        {
            var options=new LobbyOptions(CampaignCatalog.GetRoute(course).DisplayName+" · Cấp "+(level+1),5,false,course,level);
            if(multiplayer.Status==SessionStatus.Connected&&!multiplayer.IsGuest)RunCommand(()=>multiplayer.CreateLobby(options));
            else { pendingCareerRace=options;openCareerAfterConnect=false;ConnectMultiplayer(screen.Endpoint,false); }
        }
        private void StartLocal()
        {
            pendingShowcase=-1;practiceCourse=screen.PracticeCourseIndex;practiceLevel=screen.PracticeLevelIndex;
            practiceBike=screen.PracticeBikeIndex;practiceCharacter=screen.PracticeCharacterIndex;pendingLocalStart=true;
            if(multiplayer.Status!=SessionStatus.Offline||multiplayer.IsDisconnecting)
            {
                pendingLocalStart=true;returningToMenu=true;multiplayer.Disconnect();
                if(pendingLocalStart&&multiplayer.Status==SessionStatus.Offline)BeginLocal();
                return;
            }
            BeginLocal();
        }
        private void BeginLocal()
        {
            useMultiplayer=false;returningToMenu=false;lobby.Hide();accumulated=0;
            if(!contentLoader.IsReady(practiceCourse)){EnsureContent(practiceCourse,practiceLevel);return;}
            CompleteLocalStart();
        }
        private void CompleteLocalStart()
        {
            if(!ContentRegistry.ReadyFor(practiceCourse))return;
            if(Stage.Road.CourseIndex!=practiceCourse||Stage.Road.LevelIndex!=practiceLevel)Stage.ApplyContent(practiceCourse,practiceLevel);
            audioView.ApplyContent(ContentRegistry.Actors.Library);
            pendingLocalStart=false;accumulated=0;outcomeShown=false;session.StartLocal(1996,5,practiceLevel,practiceCourse,practiceBike,practiceCharacter);
            cinematics?.PlayIntro();
        }
        private void EnsureContent(int course,int level)
        {
            if(contentLoader==null)return;
            if(contentLoader.IsReady(course))
            {
                if(Stage.Road.CourseIndex!=course||Stage.Road.LevelIndex!=level){Stage.ApplyContent(course,level);audioView.ApplyContent(ContentRegistry.Actors.Library);}
                ContentChanged();return;
            }
            if(contentLoader.Busy&&contentLoader.RequestedCourse==course)return;
            if(!contentLoader.Busy&&contentLoader.Error.Length>0&&contentLoader.RequestedCourse==course){ContentChanged();return;}
            contentLoader.RequestCourse(course);ContentChanged();
        }
        private void BeforeContentUnload()
        {
            returnToCareerAfterShowcase=false;
            if(cinematics!=null)cinematics.PrepareContentUnload();
            if(Stage!=null){if(menuPreviewCaptured)Stage.RestoreMenuPreview(priorMenuPreview);Stage.BeforeContentUnload();}
            menuPreviewCaptured=menuPreviewRestorePending=false;menuPreviewDirty=careerPreviewVisible;
            if(audioView!=null)audioView.BeforeContentUnload();if(musicDirector!=null)musicDirector.Stop();
        }
        private void ContentReady(int course)
        {
            int level=useMultiplayer&&multiplayer.Room!=null?multiplayer.Room.LevelIndex:pendingLocalStart?practiceLevel:0;
            Stage.ApplyContent(course,level);audioView.ApplyContent(ContentRegistry.Actors.Library);
            if(careerPreviewVisible){priorMenuPreview=Stage.CaptureMenuPreview();menuPreviewCaptured=true;}
            careerView.RefreshPresentation();
            if(careerPreviewVisible)menuPreviewDirty=true;
            if(cinematics!=null&&cinematics.IsOpen)cinematics.Gallery.ShowError("");
            if(pendingLocalStart&&!useMultiplayer)CompleteLocalStart();
            if(pendingShowcase>=0){int index=pendingShowcase;pendingShowcase=-1;returnToCareerAfterShowcase=cinematics.PlayShowcase(index);}
            ContentChanged();
        }
        private void ContentChanged()
        {
            if(screen==null||contentLoader==null)return;
            screen.SetContentState(contentLoader.Busy,contentLoader.Progress,contentLoader.Status,!contentLoader.Busy&&contentLoader.Error.Length>0);
            if(multiplayer!=null&&multiplayer.Room!=null)lobby.SetContentReady(contentLoader.IsReady(multiplayer.Room.CourseIndex)&&(cinematics==null||!cinematics.BlocksGameplayInput),contentLoader.Status);
        }
        private void PlayShowcase(int index)
        {
            if(index<0||index>=BikeCatalog.Count)return;
            if(ContentRegistry.Actors==null||ContentRegistry.Route==null)
            {pendingShowcase=index;EnsureContent(screen.PracticeCourseIndex,screen.PracticeLevelIndex);return;}
            returnToCareerAfterShowcase=cinematics.PlayShowcase(index);
        }
        private void CinematicCompleted(CinematicDefinition definition,bool skipped)
        {
            if(!returnToCareerAfterShowcase)return;returnToCareerAfterShowcase=false;
            if(!contentLoader.Busy&&(!useMultiplayer||multiplayer.Room==null||multiplayer.Room.Phase==LobbyPhase.Lobby||multiplayer.Room.Phase==LobbyPhase.Results))OpenCareer();
        }
        private void OpenCinematicGallery(){cinematics?.OpenGallery();}
        private void LoadGalleryContent(){EnsureContent(screen.PracticeCourseIndex,screen.PracticeLevelIndex);}
        private void StopCinematicsForRace()
        {
            if(cinematics==null||!cinematics.BlocksGameplayInput)return;
            returnToCareerAfterShowcase=false;cinematics.StopForGameplay();
            if(ContentRegistry.ReadyFor(contentLoader.LoadedCourse))musicDirector.Play(ContentRegistry.MusicId,ContentRegistry.MusicUrl,true,.077f);
        }
        private void PlayStreamedMusic(string id,string url,bool loop,float gain){musicDirector.Play(id,url,loop,gain);}
        private void RetryContent(){if(contentLoader!=null)contentLoader.Retry();if(musicDirector!=null)musicDirector.Retry();}
        private void Restart(){StopCinematicsForRace();outcomeShown=false;accumulated=0;screen.SetCruise(false);session.RestartLocal();}
        private void Leave()
        {
            accumulated=0;StopCinematicsForRace();
            if(useMultiplayer&&multiplayer.Room!=null)RunCommand(multiplayer.LeaveLobby);
            else if(useMultiplayer)DisconnectMultiplayer();else session.Disconnect();
        }
        private void Connect(string endpoint){ConnectMultiplayer(endpoint,false);}
        private void ConnectGuest(string endpoint){ConnectMultiplayer(endpoint,true);}
        private void ConnectMultiplayer(string endpoint,bool guest)
        {
            if(multiplayer.IsDisconnecting)return;
            accumulated=0;
            session.Disconnect();useMultiplayer=true;returningToMenu=false;
            try
            {
                if(!guest)
                {
                    ((IProfileCredentialStore)storage).Load(endpoint);
                    if(!storage.PersistenceAvailable)throw new ArgumentException("Trình duyệt không cho đọc hồ sơ đã lưu. Hãy cho phép lưu dữ liệu trang hoặc chọn Khách mới.");
                }
                var nextProfile=new LocalPlayerProfile(profile.ProfileId,screen.PlayerName,profile.ColorIndex);
                multiplayer.Connect(endpoint,nextProfile,guest);profile=nextProfile;storage.Save(profile);
            }
            catch(ArgumentException error){screen.ShowMultiplayer(SessionStatus.Failed,false,false,error.Message);}
        }
        private void DisconnectMultiplayer(){returningToMenu=true;multiplayer.Disconnect();MultiplayerChanged();}
        private void RunCommand(Action command)
        {
            try{command();}catch(ArgumentException error){lobby.ShowError(error.Message);}catch(InvalidOperationException error){lobby.ShowError(error.Message);}
        }
        private void ToggleReady()
        {
            if(multiplayer.Room!=null&&!contentLoader.IsReady(multiplayer.Room.CourseIndex)){EnsureContent(multiplayer.Room.CourseIndex,multiplayer.Room.LevelIndex);return;}
            bool ownReady=false;
            if(multiplayer.Room!=null)foreach(var member in multiplayer.Room.Members)if(member.PlayerId==multiplayer.PlayerId)ownReady=member.Ready;
            RunCommand(()=>multiplayer.SetReady(!ownReady));
        }
        private void StateChanged()
        {
            if(useMultiplayer)return;
            bufferedAttack=0;bufferedKick=false;screen.ShowState(session.Status,session.Mode,session.Error);
        }
        private void MultiplayerChanged()
        {
            if(!useMultiplayer)return;
            if(multiplayer.Room!=null&&multiplayer.Room.Phase==LobbyPhase.Countdown)outcomeShown=false;
            if(multiplayer.Room!=null&&(multiplayer.Room.Phase==LobbyPhase.Countdown||multiplayer.Room.Phase==LobbyPhase.Racing))StopCinematicsForRace();
            if(multiplayer.Room!=null&&multiplayer.Room.Phase!=LobbyPhase.Closing)EnsureContent(multiplayer.Room.CourseIndex,multiplayer.Room.LevelIndex);
            if(returningToMenu&&multiplayer.Status==SessionStatus.Offline&&!multiplayer.IsDisconnecting)
            {
                if(pendingLocalStart){BeginLocal();return;}
                useMultiplayer=false;returningToMenu=false;lobby.Hide();screen.ShowState(SessionStatus.Offline,RaceSessionMode.None,multiplayer.Error);return;
            }
            bool recovering=multiplayer.IsReconnecting||multiplayer.IsSuspended;
            if(wasReconnecting&&!recovering&&multiplayer.Status==SessionStatus.Connected)Stage.ResetInterpolation();
            wasReconnecting=recovering;
            bool race=multiplayer.Status==SessionStatus.Connected&&multiplayer.Room!=null&&multiplayer.Room.Phase==LobbyPhase.Racing&&multiplayer.LatestAuthoritativeWorld!=null;
            if(!race||recovering){bufferedAttack=0;bufferedKick=false;}
            screen.ShowMultiplayer(multiplayer.Status,race,recovering,multiplayer.Error,multiplayer.RttMs,multiplayer.RttMs>180||multiplayer.StaleRemoteCount>0);lobby.Render(multiplayer);
            if(careerView.IsOpen&&race)careerView.Close();
            if(!storageWarningShown&&multiplayer.Status==SessionStatus.Connected&&(!storage.PersistenceAvailable||!storage.ResumeStorageAvailable))
            {
                storageWarningShown=true;
                lobby.ShowError("Không thể lưu dữ liệu trên thiết bị. Phiên này vẫn chạy, nhưng khởi động lại có thể không khôi phục hồ sơ hoặc chỗ đang giữ.");
            }
        }
        private void Update()
        {
            if(session==null)return;
            double began=Time.realtimeSinceStartupAsDouble;
            float dt=Time.unscaledDeltaTime;
            frames[frameIndex++%frames.Length]=dt*1000;frameCount=Mathf.Min(frameCount+1,frames.Length);
            multiplayer.Poll();
            if(multiplayer.Status==SessionStatus.Connected&&careerSessionPlayerId!=multiplayer.PlayerId&&!career.Busy)
            {
                careerSessionPlayerId=multiplayer.PlayerId;
                if(multiplayer.IsGuest) { career.ClearView();lobby.SetCareerLevel(0); }
                else
                {
                    try { career.SetEndpoint(screen.Endpoint);career.Refresh(); }
                    catch(ArgumentException error) { lobby.ShowError(error.Message); }
                }
            }
            if(multiplayer.Status==SessionStatus.Connected&&multiplayer.Result!=null&&multiplayer.Result.Persisted&&multiplayer.Result.ResultId!=refreshedResultId&&!multiplayer.IsGuest&&!career.Busy)
            {refreshedResultId=multiplayer.Result.ResultId;career.Refresh();}
            if(queuedCareerIntent!=null&&multiplayer.Status==SessionStatus.Offline&&!multiplayer.IsDisconnecting)
            { var request=queuedCareerIntent;queuedCareerIntent=null;career.Execute(request); }
            if(reconnectForCareer&&multiplayer.Status==SessionStatus.Offline&&!multiplayer.IsDisconnecting)
            { reconnectForCareer=false;ConnectMultiplayer(screen.Endpoint,false); }
            if(multiplayer.Status==SessionStatus.Connected)
            {
                if(openCareerAfterConnect) { openCareerAfterConnect=false;OpenCareer(); }
                if(pendingCareerRace!=null) { var options=pendingCareerRace;pendingCareerRace=null;RunCommand(()=>multiplayer.CreateLobby(options)); }
            }
            if(contentLoader!=null&&contentLoader.Busy)ContentChanged();
            careerView.SetConnectionState(multiplayer.Status==SessionStatus.Connected,multiplayer.Room!=null);
            var keyboard=Keyboard.current;var gamepad=Gamepad.current;
            bool keyboardGesture=keyboard!=null&&keyboard.anyKey.wasPressedThisFrame;
            bool pointerGesture=Mouse.current!=null&&Mouse.current.leftButton.wasPressedThisFrame;
            bool padGesture=gamepad!=null&&(gamepad.buttonSouth.wasPressedThisFrame||gamepad.startButton.wasPressedThisFrame||gamepad.leftShoulder.wasPressedThisFrame||gamepad.rightShoulder.wasPressedThisFrame||gamepad.leftStick.ReadValue().sqrMagnitude>.1f);
            if(keyboardGesture||pointerGesture){screen.SetGamepadNavigation(false);audioView.UnlockFromUserGesture();musicDirector?.UnlockFromUserGesture();}
            else if(padGesture){screen.SetGamepadNavigation(true);audioView.UnlockFromUserGesture();musicDirector?.UnlockFromUserGesture();}
            bool active=useMultiplayer?multiplayer.Status==SessionStatus.Connected&&multiplayer.Room!=null&&multiplayer.Room.Phase==LobbyPhase.Racing:
                session.Status==SessionStatus.Connected;
            active=active&&contentLoader!=null&&contentLoader.IsReady(useMultiplayer&&multiplayer.Room!=null?multiplayer.Room.CourseIndex:practiceCourse);
            if(keyboard!=null&&keyboard.escapeKey.wasPressedThisFrame)
            {
                if(!(cinematics!=null&&cinematics.HandleBack())&&!careerView.HandleBack()&&!screen.HandleBack()&&active){Leave();active=false;}
            }
            if(gamepad!=null&&gamepad.startButton.wasPressedThisFrame&&!careerView.IsOpen&&(cinematics==null||!cinematics.BlocksGameplayInput))
            {
                if(screen.SettingsOpen)screen.CloseSettings();else screen.OpenSettings();
            }
            float throttle=0,brake=0,steer=0;int attack=0;bool kick=false;
            if(active&&(cinematics==null||!cinematics.BlocksGameplayInput)&&!careerView.IsOpen&&!screen.BlocksGameplayInput&&UnityEngine.Application.isFocused)
            {
                throttle=screen.Cruise?1:0;
                if(keyboard!=null)
                {
                    if(keyboard.wKey.isPressed||keyboard.upArrowKey.isPressed)throttle=1;
                    brake=keyboard.sKey.isPressed||keyboard.downArrowKey.isPressed?1:0;
                    steer=(keyboard.dKey.isPressed||keyboard.rightArrowKey.isPressed?1:0)-(keyboard.aKey.isPressed||keyboard.leftArrowKey.isPressed?1:0);
                    attack=(keyboard.eKey.isPressed?1:0)-(keyboard.qKey.isPressed?1:0);
                    kick=keyboard.leftShiftKey.isPressed||keyboard.rightShiftKey.isPressed||keyboard.leftShiftKey.wasPressedThisFrame||keyboard.rightShiftKey.wasPressedThisFrame;
                    int pressedSide=(keyboard.eKey.wasPressedThisFrame?1:0)-(keyboard.qKey.wasPressedThisFrame?1:0);
                    if(pressedSide!=0){bufferedAttack=pressedSide;bufferedKick=kick;}
                    if(keyboard.rKey.wasPressedThisFrame&&!useMultiplayer&&session.Mode==RaceSessionMode.Local)Restart();
                }
                if(gamepad!=null)
                {
                    throttle=Mathf.Max(throttle,gamepad.rightTrigger.ReadValue());brake=Mathf.Max(brake,gamepad.leftTrigger.ReadValue());
                    if(Mathf.Abs(gamepad.leftStick.x.ReadValue())>.08f)steer=gamepad.leftStick.x.ReadValue();
                    if(gamepad.leftShoulder.isPressed)attack=-1;if(gamepad.rightShoulder.isPressed)attack=1;
                    kick|=gamepad.buttonSouth.isPressed;
                    int pressedSide=(gamepad.rightShoulder.wasPressedThisFrame?1:0)-(gamepad.leftShoulder.wasPressedThisFrame?1:0);
                    if(pressedSide!=0){bufferedAttack=pressedSide;bufferedKick=gamepad.buttonSouth.isPressed||gamepad.buttonSouth.wasPressedThisFrame;}
                }
                if(brake>0){throttle=0;if(screen.Cruise)screen.SetCruise(false);}
            }
            else {bufferedAttack=0;bufferedKick=false;}
            if(keyboard!=null&&Debug.isDebugBuild&&keyboard.f3Key.wasPressedThisFrame)debugVisible=!debugVisible;
            // Bounded catch-up prevents an unfocused window from fast-forwarding a local race on resume.
            accumulated+=Mathf.Min(dt,.1f);int steps=0;
            while(accumulated>=1f/GameplayRules.TickRate&&steps++<6)
            {
                accumulated-=1f/GameplayRules.TickRate;
                // Preserve a discrete press that starts and ends between two60Hz simulation ticks.
                if(useMultiplayer)multiplayer.Step(throttle,brake,steer,attack!=0?attack:bufferedAttack,attack!=0?kick:bufferedKick);
                else if(cinematics==null||!cinematics.BlocksGameplayInput)session.Step(throttle,brake,steer,attack!=0?attack:bufferedAttack,attack!=0?kick:bufferedKick);
                bufferedAttack=0;bufferedKick=false;
            }
            var world=useMultiplayer?multiplayer.SamplePresentation():session.LatestWorld;
            var local=useMultiplayer?multiplayer.LocalRider:session.LocalRider;
            if(useMultiplayer&&world!=null)for(int i=0;i<world.Riders.Count;i++)if(world.Riders[i].Id==multiplayer.RiderId){local=world.Riders[i];break;}
            bool showRace=useMultiplayer?world!=null&&multiplayer.Room!=null&&(multiplayer.Room.Phase==LobbyPhase.Racing||multiplayer.Room.Phase==LobbyPhase.Results):active;
            showRace=showRace&&world!=null&&contentLoader.IsReady(world.CourseIndex);
            bool cinematicPlaying=cinematics!=null&&cinematics.Director.IsPlaying;
            if(!cinematicPlaying)
            {
                bool renderingRace=showRace&&(!careerPreviewVisible||active);
                UpdateMenuPreview(renderingRace);
                var continuity=useMultiplayer&&multiplayer.Room!=null?
                    new PresentationContinuityScope(multiplayer.PresentationSessionEpoch,multiplayer.Room.RaceEpoch,multiplayer.Room.RoomId,multiplayer.RiderId,
                        multiplayer.PresentationFrozen||multiplayer.IsReconnecting||multiplayer.IsSuspended,multiplayer.PresentationCorrectionRevision,multiplayer.LastCorrectionMeters):default;
                Stage.RenderFrame(world,local,renderingRace,dt,screen.ReducedMotion,useMultiplayer,continuity);
            }
            audioView.Render(world,local,active&&!cinematicPlaying,screen.AudioEnabled,dt);
            musicDirector.SetMix(screen.AudioEnabled,active&&!cinematicPlaying?.82f:1f);
            if(!cinematicPlaying)musicDirector.SetDucking(1-audioView.MusicDuck*.7f);
            if(cinematics!=null)cinematics.Director.ReducedMotion=screen.ReducedMotion;
            if(!useMultiplayer&&active&&!outcomeShown&&GameplayRules.IsTerminal(local.Mode))
            {
                outcomeShown=true;
                var role=local.Mode==RiderMode.Busted?CinematicRole.Busted:local.Mode==RiderMode.Wrecked?CinematicRole.Wreck:local.Qualified?CinematicRole.Win:CinematicRole.Lose;
                cinematics?.PlayOutcome(role,practiceCourse);
            }
            if(useMultiplayer&&multiplayer.Room!=null&&multiplayer.Room.Phase==LobbyPhase.Results&&multiplayer.Result!=null&&multiplayer.Result.Persisted&&!outcomeShown&&contentLoader.IsReady(multiplayer.Room.CourseIndex))
            {
                foreach(var entry in multiplayer.Result.Entries)if(entry.PlayerId==multiplayer.PlayerId)
                {
                    outcomeShown=true;
                    var role=entry.Outcome==RaceOutcome.Busted?CinematicRole.Busted:entry.Outcome==RaceOutcome.Wrecked?CinematicRole.Wreck:entry.Outcome==RaceOutcome.Finished&&entry.Rank<=3?CinematicRole.Win:CinematicRole.Lose;
                    cinematics?.PlayOutcome(role,multiplayer.Room.CourseIndex);break;
                }
            }
            if(effectsView!=null)effectsView.Render(world,local,showRace&&!cinematicPlaying,dt,screen.ReducedMotion);
            uiTime+=dt;
            if(uiTime>.1f)
            {
                uiTime=0;
                if(useMultiplayer)
                {
                    bool race=showRace&&multiplayer.Status==SessionStatus.Connected&&multiplayer.Room.Phase==LobbyPhase.Racing;
                    screen.ShowMultiplayer(multiplayer.Status,race,multiplayer.IsReconnecting||multiplayer.IsSuspended,multiplayer.Error,multiplayer.RttMs,multiplayer.RttMs>180||multiplayer.StaleRemoteCount>0);
                    if(race)screen.Render(world,local,RaceSessionMode.Online,default,multiplayer.RacingParticipantCount);lobby.Render(multiplayer);ContentChanged();
                }
                else if(active)screen.Render(world,local,session.Mode,session.LocalCampaign);
            }
            metrics.gameUpdateMs=(Time.realtimeSinceStartupAsDouble-began)*1000;
            FrameTimingManager.CaptureFrameTimings();
            telemetryTime+=dt;
            if(telemetryTime>.5f)
            {
                telemetryTime=0;Array.Copy(frames,sorted,frameCount);Array.Sort(sorted,0,frameCount);
                metrics.frameP50Ms=sorted[frameCount/2];metrics.frameP95Ms=sorted[Mathf.Min(frameCount-1,Mathf.FloorToInt(frameCount*.95f))];
                metrics.state=(useMultiplayer?multiplayer.Status:session.Status).ToString();metrics.mode=useMultiplayer?"Online":session.Mode.ToString();metrics.player=useMultiplayer?multiplayer.RiderId:session.RiderId;
                metrics.tick=world==null?0:world.Tick;metrics.ack=world==null?0:world.AcknowledgedInputSequence;metrics.inputs=useMultiplayer?multiplayer.SentInputs:session.SentInputs;
                metrics.room=useMultiplayer&&multiplayer.Room!=null?multiplayer.Room.Code:"";metrics.roomPhase=useMultiplayer&&multiplayer.Room!=null?multiplayer.Room.Phase.ToString():"";
                metrics.sessionId=useMultiplayer?multiplayer.PlayerId:session.PlayerId;
                metrics.rttMs=useMultiplayer?multiplayer.RttMs:0;metrics.correctionMeters=useMultiplayer?multiplayer.LastCorrectionMeters:0;
                metrics.pendingInputs=useMultiplayer?multiplayer.PendingInputCount:0;metrics.reconnecting=useMultiplayer&&multiplayer.IsReconnecting;
                metrics.lateInputs=useMultiplayer?multiplayer.LateInputs:0;metrics.futureInputs=useMultiplayer?multiplayer.FutureInputs:0;
                metrics.missingInputs=useMultiplayer?multiplayer.MissingInputs:0;metrics.staleRemotes=useMultiplayer?multiplayer.StaleRemoteCount:0;
                metrics.peers=world==null?0:world.Riders.Count;metrics.traffic=world==null?0:world.Traffic.Count;metrics.pedestrians=world==null?0:world.Pedestrians.Count;
                metrics.speed=local.SpeedMetersPerSecond;metrics.distance=local.LongitudinalMeters;metrics.lateral=local.LateralMeters;
                metrics.courseIndex=world==null?practiceCourse:world.CourseIndex;metrics.levelIndex=world==null?practiceLevel:world.Level;
                metrics.bikeCatalogIndex=local.BikeCatalogIndex;metrics.characterCatalogIndex=local.CharacterCatalogIndex;
                metrics.contentReady=contentLoader.IsReady(metrics.courseIndex);metrics.contentLoading=contentLoader.Busy;metrics.loadedCourse=contentLoader.LoadedCourse;
                metrics.contentLoadError=contentLoader.Error;metrics.contentDownloadedBytes=contentLoader.DownloadedBytes;
                metrics.musicId=musicDirector.CurrentId;metrics.musicState=musicDirector.CurrentStatus;metrics.musicError=musicDirector.LastErrorCode;
                metrics.cinematicPlaying=cinematics!=null&&cinematics.Director.IsPlaying;
                metrics.cinematicId=cinematics!=null&&cinematics.Director.Current!=null?cinematics.Director.Current.Id:"";
                metrics.rank=local.Rank;metrics.health=local.Health;metrics.bike=local.BikeCondition;metrics.riderState=local.Mode.ToString();metrics.weapon=local.Weapon.ToString();
                metrics.fps=Mathf.RoundToInt(1000/Mathf.Max(.01f,metrics.frameP50Ms));metrics.width=Screen.width;metrics.height=Screen.height;
                metrics.unityAllocatedBytes=Profiler.GetTotalAllocatedMemoryLong();metrics.managedBytes=GC.GetTotalMemory(false);
                metrics.frameTimingAvailable=FrameTimingManager.GetLatestTimings(1,timings)>0;
                metrics.cpuFrameMs=metrics.frameTimingAvailable?timings[0].cpuFrameTime:0;metrics.gpuFrameMs=metrics.frameTimingAvailable?timings[0].gpuFrameTime:0;
                metrics.gpuTimingAvailable=metrics.frameTimingAvailable&&metrics.gpuFrameMs>0;
                metrics.allocationCounterAvailable=allocations.Valid&&allocations.Count>0;
                metrics.frameGcBytes=metrics.allocationCounterAvailable?allocations.LastValue:0;
                metrics.graphicsQuality=screen.CurrentQualityIndex;metrics.audioUnlocked=audioView.Unlocked;
                metrics.audioMuted=audioView.Muted;metrics.audioBankReady=audioView.HasBank;metrics.audioEvents=audioView.PlayedEventCount;
                metrics.activeDustEmitters=effectsView==null?0:effectsView.ActiveDustEmitters;
                metrics.impactEffects=effectsView==null?0:effectsView.EmittedImpactCount;
                BrowserSocketTransport.Report(JsonUtility.ToJson(metrics));
            }
        }
        private void OnApplicationFocus(bool focused)
        {
            if(focused)return;
            bufferedAttack=0;bufferedKick=false;
            if(screen!=null&&screen.Cruise)screen.SetCruise(false);
        }
        [UnityEngine.Scripting.Preserve]
        public void OnPageVisibility(string value)
        {
            bool visible=value=="visible";
            if(!visible){bufferedAttack=0;bufferedKick=false;if(screen!=null)screen.SetCruise(false);}
            if(useMultiplayer)multiplayer.NotifyVisibility(visible);
        }
        private void OnGUI()
        {
            if(!Debug.isDebugBuild||!debugVisible||session==null)return;
            GUI.Box(new Rect(15,Screen.height/2,410,105),"P03/P04 DEVELOPMENT");
            GUI.Label(new Rect(25,Screen.height/2+24,390,85),"tick "+metrics.tick+" / "+metrics.riderState+"\np50/p95 "+metrics.frameP50Ms.ToString("0.0")+"/"+metrics.frameP95Ms.ToString("0.0")+" ms\nUnity allocated "+(metrics.unityAllocatedBytes/1048576)+" MiB");
        }
        private void OnDestroy()
        {
            if(screen!=null){screen.ContentRetryRequested-=RetryContent;screen.GalleryRequested-=OpenCinematicGallery;screen.LocalRequested-=StartLocal;screen.ConnectRequested-=Connect;screen.GuestConnectRequested-=ConnectGuest;screen.LeaveRequested-=Leave;screen.RestartRequested-=Restart;}
            if(careerView!=null){careerView.ShowcaseRequested-=PlayShowcase;careerView.SelectedBikePreviewRequested-=PreviewBike;careerView.SelectedCharacterPreviewRequested-=PreviewCharacter;careerView.PreviewVisibilityChanged-=PreviewVisibilityChanged;}
            if(session!=null){session.Changed-=StateChanged;session.Dispose();}
            if(multiplayer!=null){multiplayer.Changed-=MultiplayerChanged;multiplayer.Dispose();}
            if(contentLoader!=null){contentLoader.MusicRequested-=PlayStreamedMusic;contentLoader.BeforeRouteUnload-=BeforeContentUnload;contentLoader.Ready-=ContentReady;contentLoader.Changed-=ContentChanged;}
            if(cinematics!=null){cinematics.ContentRequired-=LoadGalleryContent;cinematics.Director.Completed-=CinematicCompleted;}
            BeforeContentUnload();allocations.Dispose();
        }
    }
}
