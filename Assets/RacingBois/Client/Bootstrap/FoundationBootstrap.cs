using System;
using RacingBois.Client.Application;
using RacingBois.Client.Adapters;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;

namespace RacingBois.Client.Bootstrap
{
    public sealed class FoundationBootstrap : MonoBehaviour
    {
        public RoadStageView Stage;
        public UIDocument Document;
        private BrowserSocketTransport transport;
        private FoundationSession session;
        private FoundationScreen screen;
        private float accumulated, telemetryTime, smoothedDelta=.0167f;
        private double connectStarted;
        [Serializable] private sealed class Metrics
        {
            public string state; public string player; public long tick; public int ack;
            public int inputs; public int peers; public int fps; public float speed; public float distance;
            public float correction; public bool sharedFixture;
        }
        private bool sharedFixture;
        private void Start()
        {
            UnityEngine.Application.targetFrameRate=60;
            transport=gameObject.AddComponent<BrowserSocketTransport>();
            gameObject.name="RacingBoisNetwork";
            session=new FoundationSession(transport,new UnityWireCodec());
            screen=gameObject.AddComponent<FoundationScreen>();
            screen.Initialize(Document,DefaultEndpoint());
            screen.ConnectRequested+=Connect;
            screen.LeaveRequested+=Disconnect;
            session.Changed+=StateChanged;
            Stage.Build(); StateChanged();
            var fixture=default(RiderState);
            for(int i=0;i<300;i++) fixture=RoadSpaceSimulation.Step(fixture,new RiderInput(1000,0,0));
            sharedFixture=fixture.DistanceMillimeters==150500 && fixture.SpeedMillimetersPerSecond==60000;
            Debug.Log("RB_SHARED_FIXTURE "+(sharedFixture?"PASS":"FAIL")+" distance_mm="+fixture.DistanceMillimeters+" speed_mm_s="+fixture.SpeedMillimetersPerSecond);
        }
        private string DefaultEndpoint()
        {
            if(Uri.TryCreate(UnityEngine.Application.absoluteURL,UriKind.Absolute,out var page))
                return (page.Scheme=="https"?"wss://":"ws://")+page.Authority+"/ws";
            return "ws://127.0.0.1:7777/ws";
        }
        private void Connect(string endpoint)
        {
            connectStarted=Time.realtimeSinceStartupAsDouble;
            accumulated=0; session.Connect(endpoint);
        }
        private void Disconnect() { session.Disconnect(); accumulated=0; }
        private void StateChanged() { screen.ShowState(session.Status,session.PlayerId,session.Error); }
        private void Update()
        {
            if(session==null) return;
            transport.Poll();
            if(session.Status==SessionStatus.Connecting && Time.realtimeSinceStartupAsDouble-connectStarted>8)
                session.Disconnect();
            var keyboard=Keyboard.current; var gamepad=Gamepad.current;
            float throttle=0,brake=0,steer=0;
            if(session.Status==SessionStatus.Connected && !screen.IsTyping && UnityEngine.Application.isFocused)
            {
                if(keyboard!=null)
                {
                    throttle=keyboard.wKey.isPressed||keyboard.upArrowKey.isPressed?1:0;
                    brake=keyboard.sKey.isPressed||keyboard.downArrowKey.isPressed?1:0;
                    steer=(keyboard.dKey.isPressed||keyboard.rightArrowKey.isPressed?1:0)-(keyboard.aKey.isPressed||keyboard.leftArrowKey.isPressed?1:0);
                    if(keyboard.escapeKey.wasPressedThisFrame) Disconnect();
                }
                if(gamepad!=null)
                {
                    throttle=Mathf.Max(throttle,gamepad.rightTrigger.ReadValue());
                    brake=Mathf.Max(brake,gamepad.leftTrigger.ReadValue());
                    if(Mathf.Abs(gamepad.leftStick.x.ReadValue())>.08f) steer=gamepad.leftStick.x.ReadValue();
                }
            }
            accumulated+=Mathf.Min(Time.unscaledDeltaTime,.1f);
            int catchup=0;
            while(accumulated>=1f/PrototypeRules.TickRate && catchup++<6)
            {
                accumulated-=1f/PrototypeRules.TickRate;
                session.Step(throttle,brake,steer);
            }
            var state=session.PredictedState;
            float s=(float)(state.DistanceMillimeters/1000.0),d=state.LateralMillimeters/1000f,speed=state.SpeedMillimetersPerSecond/1000f;
            Stage.RenderFrame(session.LatestWorld,session.PlayerId,s,d,session.Status==SessionStatus.Connected,Time.unscaledDeltaTime);
            smoothedDelta=Mathf.Lerp(smoothedDelta,Time.unscaledDeltaTime,.06f);
            telemetryTime+=Time.unscaledDeltaTime;
            if(telemetryTime>.2f)
            {
                telemetryTime=0;
                var world=session.LatestWorld;
                int count=world==null?0:world.Riders.Count;
                screen.SetTelemetry(speed,s,count);
                BrowserSocketTransport.Report(JsonUtility.ToJson(new Metrics {state=session.Status.ToString(),player=session.PlayerId,
                    tick=world==null?0:world.Tick,
                    ack=world==null?0:world.AcknowledgedInputSequence,
                    inputs=session.SentInputs,peers=count,fps=Mathf.RoundToInt(1/Mathf.Max(.001f,smoothedDelta)),
                    speed=speed,distance=s,correction=session.LastCorrectionMeters,sharedFixture=sharedFixture}));
            }
        }
        private void OnDestroy()
        {
            if(screen!=null) { screen.ConnectRequested-=Connect; screen.LeaveRequested-=Disconnect; }
            if(session!=null) {session.Changed-=StateChanged;session.Dispose();}
        }
    }
}
