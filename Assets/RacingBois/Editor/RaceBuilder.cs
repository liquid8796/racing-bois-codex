using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.UIElements;
using RacingBois.Client.Bootstrap;
using RacingBois.Client.Presentation;

namespace RacingBois.Authoring.Editor
{
    public static class RaceBuilder
    {
        public const string ScenePath="Assets/RacingBois/Scenes/Race.unity";
        private const string Root="Assets/RacingBois/";
        [MenuItem("Racing Bois/Gameplay/Setup Race")]
        public static void Setup()
        {
            RaceAssetBuilder.Setup();
            ClubAssetBuilder.Setup();
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var pipeline=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Root+"Settings/WebURP.asset");
            if(pipeline==null)throw new InvalidOperationException("Run Foundation setup first.");
            pipeline.shadowDistance=75;pipeline.msaaSampleCount=2;pipeline.mainLightShadowmapResolution=2048;
            GraphicsSettings.defaultRenderPipeline=pipeline;QualitySettings.renderPipeline=pipeline;EditorUtility.SetDirty(pipeline);
            PlayerSettings.bundleVersion="0.5.0";PlayerSettings.enableFrameTimingStats=true;
            // Native Brotli decoding is HTTPS-only in major browsers; LAN must also cold-load over ordinary HTTP.
            PlayerSettings.WebGL.compressionFormat=WebGLCompressionFormat.Gzip;
            PlayerSettings.WebGL.decompressionFallback=false;
            var cameraObject=new GameObject("Main Camera");cameraObject.tag="MainCamera";
            var camera=cameraObject.AddComponent<Camera>();cameraObject.AddComponent<AudioListener>();
            camera.backgroundColor=new Color(.49f,.65f,.7f);camera.clearFlags=CameraClearFlags.Skybox;
            camera.nearClipPlane=.12f;camera.farClipPlane=600;camera.fieldOfView=60;camera.allowHDR=false;
            var sky=AssetDatabase.LoadAssetAtPath<Material>(Root+"Materials/RaceSky.mat");
            if(sky==null){sky=new Material(Shader.Find("Skybox/Procedural"));AssetDatabase.CreateAsset(sky,Root+"Materials/RaceSky.mat");}
            sky.SetColor("_SkyTint",new Color(.5f,.64f,.75f));sky.SetColor("_GroundColor",new Color(.49f,.43f,.31f));
            sky.SetFloat("_Exposure",1.1f);sky.SetFloat("_AtmosphereThickness",.85f);EditorUtility.SetDirty(sky);RenderSettings.skybox=sky;
            var sun=new GameObject("Late afternoon sun").AddComponent<Light>();sun.type=LightType.Directional;
            sun.color=new Color(1,.86f,.66f);sun.intensity=1.7f;sun.shadows=LightShadows.Soft;sun.transform.rotation=Quaternion.Euler(34,-38,0);
            RenderSettings.sun=sun;RenderSettings.ambientMode=AmbientMode.Trilight;
            RenderSettings.ambientSkyColor=new Color(.59f,.67f,.77f);RenderSettings.ambientEquatorColor=new Color(.45f,.47f,.43f);
            RenderSettings.ambientGroundColor=new Color(.26f,.25f,.21f);
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.ExponentialSquared;RenderSettings.fogDensity=.0034f;RenderSettings.fogColor=new Color(.67f,.69f,.63f);
            var road=new GameObject("Canyon Run Ribbon").AddComponent<TrackRibbonView>();
            road.Asphalt=Material("RaceAsphalt",new Color(.13f,.15f,.16f),.2f);
            road.Shoulder=Material("RaceShoulder",new Color(.48f,.37f,.23f),.1f);
            road.Landscape=Material("RaceLandscape",new Color(.47f,.43f,.28f),.04f);
            road.Paint=Material("RacePaint",new Color(.87f,.87f,.72f),.15f);
            road.YellowPaint=Material("RaceYellow",new Color(1,.65f,.13f),.15f);
            road.Rock=Material("RaceSandstone",new Color(.56f,.35f,.2f),.05f);
            road.Foliage=Material("RaceScrub",new Color(.24f,.29f,.15f),.03f);
            road.SandstonePrefab=Prefab("RB_Sandstone");road.SageScrubPrefab=Prefab("RB_SageScrub");
            var stage=new GameObject("Race Presentation").AddComponent<RaceStageView>();stage.Road=road;stage.ViewCamera=camera;
            stage.MotorcyclePrefab=Prefab("RB_Motorcycle");stage.PoliceMotorcyclePrefab=Prefab("RB_PoliceMotorcycle");
            stage.RiderPrefab=Prefab("RB_Rider");stage.CoupePrefab=Prefab("RB_TrafficCoupe");stage.VanPrefab=Prefab("RB_TrafficVan");
            stage.PedestrianPrefab=Prefab("RB_Pedestrian");
            stage.ClubPrefab=Prefab("RB_Club");
            stage.SparkMaterial=Material("RaceSpark",new Color(1,.68f,.15f),.2f);
            var app=new GameObject("RacingBoisNetwork");var document=app.AddComponent<UIDocument>();
            document.panelSettings=AssetDatabase.LoadAssetAtPath<PanelSettings>(Root+"Settings/MainPanel.asset");
            document.visualTreeAsset=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(Root+"UI/Race.uxml");
            var bootstrap=app.AddComponent<RaceBootstrap>();bootstrap.Stage=stage;bootstrap.Document=document;
            EditorSceneManager.SaveScene(scene,ScenePath);EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
            AssetDatabase.SaveAssets();Debug.Log("RB_RACE_SETUP_COMPLETE");
        }
        private static GameObject Prefab(string name)
        {
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Prefabs/"+name+".prefab");
            if(prefab==null)throw new InvalidOperationException("Missing "+name);
            return prefab;
        }
        private static Material Material(string name,Color color,float smooth)
        {
            string path=Root+"Materials/"+name+".mat";var value=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(value==null){value=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(value,path);}
            value.SetColor("_BaseColor",color);value.SetFloat("_Smoothness",smooth);value.enableInstancing=true;EditorUtility.SetDirty(value);return value;
        }
        public static void BuildWeb()
        {
            if(!File.Exists(ScenePath))Setup();
            PlayerSettings.WebGL.compressionFormat=WebGLCompressionFormat.Gzip;
            PlayerSettings.WebGL.decompressionFallback=false;
            string output="Build/Web-Race";
            var arguments=Environment.GetCommandLineArgs();
            for(int i=0;i<arguments.Length-1;i++)if(arguments[i]=="-raceBuildOutput")output=arguments[i+1];
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes=new[]{ScenePath},locationPathName=output,target=BuildTarget.WebGL,options=BuildOptions.DetailedBuildReport
            });
            Directory.CreateDirectory("docs/p03p04/unity");
            File.WriteAllText("docs/p03p04/unity/build.json",JsonUtility.ToJson(new Receipt
            {
                result=report.summary.result.ToString(),bytes=(long)report.summary.totalSize,
                errors=report.summary.totalErrors,warnings=report.summary.totalWarnings,
                seconds=report.summary.totalTime.TotalSeconds,unityVersion=UnityEngine.Application.unityVersion,output=output
            },true));
            if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new InvalidOperationException("Race Web build failed.");
        }
        [Serializable] private sealed class Receipt
        {
            public string result,unityVersion,output;public long bytes;public int errors,warnings;public double seconds;
        }
    }
}
