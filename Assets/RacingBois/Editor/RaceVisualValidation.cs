using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using RacingBois.Client.Application;
using RacingBois.Client.Bootstrap;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Editor-only controlled initial conditions. Captures real shared-core combat and recovery, not a human-play receipt.</summary>
    public sealed class RaceVisualValidation
    {
        private static RaceVisualValidation current;
        private RaceBootstrap bootstrap;
        private RaceSession session;
        private GameplayWorld world;
        private RaceScreen screen;
        private string folder;
        private int frame;
        private double lastCapture;
        private readonly List<FrameRecord> timeline=new List<FrameRecord>();
        public static string Begin()
        {
            var bootstrap=UnityEngine.Object.FindAnyObjectByType<RaceBootstrap>();
            if(bootstrap==null||bootstrap.Session==null)throw new InvalidOperationException("Enter Race scene Play Mode first.");
            if(current!=null)throw new InvalidOperationException("Capture already running.");
            current=new RaceVisualValidation();current.Initialize(bootstrap);
            UnityEditor.EditorApplication.update+=current.Update;
            return current.folder;
        }
        private void Initialize(RaceBootstrap value)
        {
            bootstrap=value;bootstrap.enabled=false;session=bootstrap.Session;session.StartLocal(1996,0);
            screen=bootstrap.GetComponent<RaceScreen>();
            world=(GameplayWorld)typeof(RaceSession).GetField("localWorld",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(session);
            var player=RaceSimulation.FindRider(world,1);player.SpeedMillimetersPerSecond=25000;
            var other=RaceSimulation.AddPlayer(world,2);other.DistanceMillimeters=other.BikeDistanceMillimeters=0;
            other.LateralMillimeters=other.BikeLateralMillimeters=1300;other.SpeedMillimetersPerSecond=25000;
            var traffic=world.Traffic[0];traffic.Active=true;traffic.Id=3011;traffic.DistanceMillimeters=110000;
            traffic.WidthMillimeters=VehicleDimensions.CoupeWidth;traffic.LengthMillimeters=VehicleDimensions.CoupeLength;traffic.HeightMillimeters=VehicleDimensions.CoupeHeight;
            traffic.LateralMillimeters=0;traffic.SpeedMillimetersPerSecond=-12000;traffic.Oncoming=true;
            world.TrafficCount=1;
            folder=Path.GetFullPath("docs/p03p04/unity/visual-capture");Directory.CreateDirectory(folder);
            Time.captureFramerate=30;
        }
        private void Update()
        {
            if(!UnityEditor.EditorApplication.isPlaying){Finish(false);return;}
            if(UnityEditor.EditorApplication.timeSinceStartup-lastCapture<1.0/30)return;
            lastCapture=UnityEditor.EditorApplication.timeSinceStartup;
            for(int step=0;step<2;step++)
            {
                RaceSimulation.SetInput(world,2,new RaceInput(1000,0,0,-1));
                session.Step(world.Tick<300?1:0,0,0,1,false);
            }
            var rider=session.LocalRider;
            bootstrap.Stage.RenderFrame(session.LatestWorld,rider,true,1f/30,false);
            screen.Render(session.LatestWorld,rider,RaceSessionMode.Local);
            timeline.Add(new FrameRecord{frame=frame,tick=world.Tick,mode=rider.Mode.ToString(),s=rider.LongitudinalMeters,bikeS=rider.BikeLongitudinalMeters,health=rider.Health,bike=rider.BikeCondition});
            UnityEditor.EditorApplication.QueuePlayerLoopUpdate();
            foreach(var window in Resources.FindObjectsOfTypeAll<UnityEditor.EditorWindow>())if(window.GetType().Name=="GameView")window.Repaint();
            ScreenCapture.CaptureScreenshot(Path.Combine(folder,"frame-"+frame.ToString("D4")+".png"));
            frame++;
            if(frame>=360)
            {
                File.WriteAllText(Path.Combine(folder,"timeline.json"),JsonUtility.ToJson(new CaptureReport{setup="Controlled two-rider combat plus oncoming traffic at110m, seed1996. Inputs only afterinitialplacement.30fps simulation/render.",frames=timeline.ToArray()},true));
                Debug.Log("RB_VISUAL_CAPTURE_COMPLETE "+folder);Finish(true);
            }
        }
        private void Finish(bool completed){UnityEditor.EditorApplication.update-=Update;Time.captureFramerate=0;current=null;}
        [Serializable] private sealed class FrameRecord {public int frame;public long tick;public string mode;public float s,bikeS;public int health,bike;}
        [Serializable] private sealed class CaptureReport {public string setup;public FrameRecord[] frames;}
    }
}
