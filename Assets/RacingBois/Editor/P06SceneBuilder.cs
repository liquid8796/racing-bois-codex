using System;
using System.IO;
using System.Linq;
using RacingBois.Client.Bootstrap;
using RacingBois.Client.Presentation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Upgrades the existing scene in place, preserving its original objects and URP metadata.</summary>
    public static class P06SceneBuilder
    {
        private const string Root="Assets/RacingBois/";
        public const string ScenePath=Root+"Scenes/Race.unity";
        [MenuItem("Racing Bois/P06/Configure Production Slice")]
        public static void Setup()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play before configuring P06.");
            if(EditorSceneManager.GetActiveScene().path!=ScenePath)EditorSceneManager.OpenScene(ScenePath);
            var stage=UnityEngine.Object.FindAnyObjectByType<RaceStageView>();
            var app=UnityEngine.Object.FindAnyObjectByType<RaceBootstrap>();
            if(stage==null||app==null)throw new InvalidOperationException("Existing gameplay scene missing.");
            stage.MotorcyclePrefab=Prefab("Motorcycle");stage.RiderPrefab=Prefab("Rider");
            var policeBike=OptionalPrefab("PoliceMotorcycle");var policeRider=OptionalPrefab("PoliceRider");
            if(policeBike!=null)stage.PoliceMotorcyclePrefab=policeBike;
            if(policeRider!=null)stage.PoliceRiderPrefab=policeRider;
            var coupe=OptionalPrefab("TrafficCoupe");var van=OptionalPrefab("TrafficVan");
            if(coupe!=null)stage.CoupePrefab=coupe;if(van!=null)stage.VanPrefab=van;
            stage.RiderClips=AssetDatabase.LoadAllAssetsAtPath(Root+"Art/P06/Hero/RB_P06_Rider.fbx").OfType<AnimationClip>().Where(c=>!c.name.StartsWith("__preview__",StringComparison.Ordinal)).ToArray();
            if(stage.RiderClips.Length!=12)throw new InvalidOperationException("Expected twelve rider actions.");
            stage.UseExternalEffects=true;
            var road=stage.Road;road.SandstonePrefab=Prefab("RockA");road.RockBPrefab=Prefab("RockB");
            road.SageScrubPrefab=Prefab("Sage");road.DryGrassPrefab=Prefab("DryGrass");
            road.GuardrailPrefab=Prefab("Guardrail");road.ChevronPrefab=Prefab("Chevron");road.UtilityPolePrefab=Prefab("UtilityPole");
            road.Asphalt=Material("Asphalt");road.Shoulder=Material("Gravel");road.Landscape=Material("Gravel");
            road.Rock=Material("Sandstone");road.Foliage=Material("Foliage");road.WireMaterial=Material("Roadside");road.ViewCamera=stage.ViewCamera;
            Directory.CreateDirectory(Root+"Settings/P06");Directory.CreateDirectory(Root+"Materials/P06");AssetDatabase.Refresh();
            var camera=stage.ViewCamera;camera.allowHDR=true;camera.farClipPlane=650;camera.nearClipPlane=.15f;
            var cameraData=camera.GetUniversalAdditionalCameraData();cameraData.renderPostProcessing=true;cameraData.dithering=true;
            cameraData.renderShadows=true;cameraData.requiresDepthTexture=false;cameraData.requiresColorTexture=false;
            var pipeline=GraphicsSettings.defaultRenderPipeline as UniversalRenderPipelineAsset;
            if(pipeline==null)throw new InvalidOperationException("P06 requires URP.");
            pipeline.supportsHDR=true;pipeline.renderScale=1;pipeline.msaaSampleCount=2;pipeline.shadowDistance=70;pipeline.mainLightShadowmapResolution=2048;
            var pipelineData=new SerializedObject(pipeline);var soft=pipelineData.FindProperty("m_SoftShadowsSupported");if(soft!=null)soft.boolValue=true;pipelineData.ApplyModifiedProperties();EditorUtility.SetDirty(pipeline);
            var sun=RenderSettings.sun;if(sun==null)throw new InvalidOperationException("Scene sun missing.");
            sun.transform.rotation=Quaternion.Euler(28,-36,0);sun.color=new Color(1,.86f,.67f);sun.intensity=1.75f;sun.shadows=LightShadows.Soft;sun.shadowBias=.05f;sun.shadowNormalBias=.25f;
            RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=new Color(.40f,.52f,.67f);
            RenderSettings.ambientEquatorColor=new Color(.39f,.40f,.35f);RenderSettings.ambientGroundColor=new Color(.23f,.19f,.14f);RenderSettings.ambientIntensity=1;
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.ExponentialSquared;RenderSettings.fogDensity=.0030f;RenderSettings.fogColor=new Color(.66f,.70f,.70f);
            var sky=LoadOrCreateMaterial("RB_P06_Sky","RacingBois/CanyonSky");sky.SetColor("_Zenith",new Color(.09f,.30f,.56f));sky.SetColor("_Horizon",new Color(.52f,.69f,.81f));EditorUtility.SetDirty(sky);RenderSettings.skybox=sky;
            RenderSettings.defaultReflectionMode=DefaultReflectionMode.Custom;RenderSettings.customReflectionTexture=CreateReflection();RenderSettings.reflectionIntensity=.8f;
            var volume=UnityEngine.Object.FindObjectsByType<Volume>().FirstOrDefault(v=>v.name=="P06 Color and Atmosphere");
            if(volume==null)volume=new GameObject("P06 Color and Atmosphere").AddComponent<Volume>();
            volume.isGlobal=true;volume.priority=0;
            const string volumePath=Root+"Settings/P06/ColorAndAtmosphere.asset";
            var profile=AssetDatabase.LoadAssetAtPath<VolumeProfile>(volumePath);
            if(profile==null){profile=ScriptableObject.CreateInstance<VolumeProfile>();AssetDatabase.CreateAsset(profile,volumePath);}
            var tone=Get<Tonemapping>(profile);tone.mode.Override(TonemappingMode.ACES);
            var color=Get<ColorAdjustments>(profile);color.postExposure.Override(.15f);color.contrast.Override(9);color.saturation.Override(-4);
            var bloom=Get<Bloom>(profile);bloom.threshold.Override(1.2f);bloom.intensity.Override(.13f);bloom.scatter.Override(.55f);
            var vignette=Get<Vignette>(profile);vignette.intensity.Override(.12f);vignette.smoothness.Override(.55f);
            volume.sharedProfile=profile;EditorUtility.SetDirty(profile);
            app.AudioBank=AssetDatabase.LoadAssetAtPath<RaceAudioBank>(Root+"Audio/P06/RB_P06_AudioBank.asset");
            if(app.AudioBank==null||!app.AudioBank.IsComplete)throw new InvalidOperationException("Import P06 audio bank before scene setup.");
            var radial=CreateRadial();app.DustMaterial=Particle("RB_P06_Dust",radial,false);
            app.SparkMaterial=Particle("RB_P06_Sparks",radial,true);app.SkidMaterial=Particle("RB_P06_Skid",Texture2D.whiteTexture,false);
            var quality=app.GetComponent<RaceVisualQuality>();if(quality==null)quality=app.gameObject.AddComponent<RaceVisualQuality>();
            quality.ViewCamera=camera;quality.PostProcess=volume;app.VisualQuality=quality;
            PlayerSettings.bundleVersion="0.6.0";PlayerSettings.enableFrameTimingStats=true;
            PlayerSettings.WebGL.compressionFormat=WebGLCompressionFormat.Gzip;PlayerSettings.WebGL.decompressionFallback=false;
            EditorUtility.SetDirty(stage);EditorUtility.SetDirty(road);EditorUtility.SetDirty(app);EditorUtility.SetDirty(quality);
            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};AssetDatabase.SaveAssets();
            Debug.Log("RB_P06_SCENE_CONFIGURED");
        }
        private static T Get<T>(VolumeProfile profile) where T:VolumeComponent
        {
            if(profile.TryGet<T>(out var found))return found;
            var item=profile.Add<T>(true);AssetDatabase.AddObjectToAsset(item,profile);return item;
        }
        private static GameObject OptionalPrefab(string name)=>AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Prefabs/P06/RB_P06_"+name+".prefab");
        private static GameObject Prefab(string name)=>OptionalPrefab(name)??throw new InvalidOperationException("Missing P06 prefab: "+name);
        private static Material Material(string name)=>AssetDatabase.LoadAssetAtPath<Material>(Root+"Materials/P06/RB_P06_"+name+".mat")??throw new InvalidOperationException("Missing P06 material: "+name);
        private static Material LoadOrCreateMaterial(string name,string shader)
        {
            string path=Root+"Materials/P06/"+name+".mat";var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(mat==null){var selected=Shader.Find(shader);if(selected==null)throw new InvalidOperationException("Missing shader "+shader);mat=new Material(selected);AssetDatabase.CreateAsset(mat,path);}
            return mat;
        }
        private static Material Particle(string name,Texture texture,bool additive)
        {
            var mat=LoadOrCreateMaterial(name,"RacingBois/SoftParticle");mat.SetTexture("_BaseMap",texture);mat.SetFloat("_DstBlend",additive?1:10);mat.renderQueue=3000;EditorUtility.SetDirty(mat);return mat;
        }
        private static Texture2D CreateRadial()
        {
            string path=Root+"Settings/P06/ParticleRadial.asset";var texture=AssetDatabase.LoadAssetAtPath<Texture2D>(path);if(texture!=null)return texture;
            texture=new Texture2D(64,64,TextureFormat.RGBA32,true,true){name="P06 radial particle",wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};var pixels=new Color[4096];
            for(int y=0;y<64;y++)for(int x=0;x<64;x++){float radius=new Vector2((x+.5f)/32-1,(y+.5f)/32-1).magnitude;float a=Mathf.Pow(Mathf.Clamp01(1-radius),2);pixels[y*64+x]=new Color(1,1,1,a);}
            texture.SetPixels(pixels);texture.Apply(true,true);AssetDatabase.CreateAsset(texture,path);return texture;
        }
        private static Cubemap CreateReflection()
        {
            string path=Root+"Settings/P06/CanyonReflection.asset";var cube=AssetDatabase.LoadAssetAtPath<Cubemap>(path);if(cube!=null)return cube;
            cube=new Cubemap(64,TextureFormat.RGBA32,true){name="P06 ambient reflection"};var pixels=new Color[4096];
            for(int face=0;face<6;face++)
            {
                for(int y=0;y<64;y++)for(int x=0;x<64;x++)
                {
                    float u=(x+.5f)/32-1,v=(y+.5f)/32-1;Vector3 d;
                    switch(face){case 0:d=new Vector3(1,-v,-u);break;case 1:d=new Vector3(-1,-v,u);break;case 2:d=new Vector3(u,1,v);break;case 3:d=new Vector3(u,-1,-v);break;case 4:d=new Vector3(u,-v,1);break;default:d=new Vector3(-u,-v,-1);break;}
                    d.Normalize();var color=Color.Lerp(new Color(.70f,.71f,.67f),new Color(.18f,.38f,.62f),Mathf.Pow(Mathf.Clamp01(d.y),.45f));
                    if(d.y<0)color=Color.Lerp(color,new Color(.33f,.25f,.15f),Mathf.Clamp01(-d.y*3));pixels[y*64+x]=color;
                }
                cube.SetPixels(pixels,(CubemapFace)face);
            }
            cube.Apply(true,true);AssetDatabase.CreateAsset(cube,path);return cube;
        }
    }
}
