using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.UIElements;
using UnityEngine.TextCore.Text;
using UnityEngine.TextCore.LowLevel;
using RacingBois.Client.Bootstrap;
using RacingBois.Client.Presentation;

namespace RacingBois.Authoring.Editor
{
    public static class FoundationBuilder
    {
        private const string Root = "Assets/RacingBois/";
        public const string ScenePath = Root + "Scenes/Foundation.unity";
        [MenuItem("Racing Bois/Foundation/Setup Scene")]
        public static void Setup()
        {
            Directory.CreateDirectory(Root+"Settings"); Directory.CreateDirectory(Root+"Materials");
            Directory.CreateDirectory(Root+"Prefabs"); Directory.CreateDirectory(Root+"Scenes");
            AssetDatabase.Refresh();
            ConfigureSettings();
            EnsureVietnameseFont();
            var renderer=AssetDatabase.LoadAssetAtPath<UniversalRendererData>(Root+"Settings/WebRenderer.asset");
            if(renderer==null) { renderer=ScriptableObject.CreateInstance<UniversalRendererData>(); AssetDatabase.CreateAsset(renderer,Root+"Settings/WebRenderer.asset"); }
            var pipeline=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Root+"Settings/WebURP.asset");
            if(pipeline==null) { pipeline=UniversalRenderPipelineAsset.Create(renderer); AssetDatabase.CreateAsset(pipeline,Root+"Settings/WebURP.asset"); }
            pipeline.supportsHDR=false; pipeline.msaaSampleCount=2; pipeline.renderScale=1;
            pipeline.shadowDistance=65; pipeline.mainLightShadowmapResolution=1024; pipeline.useSRPBatcher=true;
            GraphicsSettings.defaultRenderPipeline=pipeline; QualitySettings.renderPipeline=pipeline;
            EditorUtility.SetDirty(pipeline);
            var barrier=CreateBarrierPrefab();
            var panel=AssetDatabase.LoadAssetAtPath<PanelSettings>(Root+"Settings/MainPanel.asset");
            if(panel==null) {panel=ScriptableObject.CreateInstance<PanelSettings>(); AssetDatabase.CreateAsset(panel,Root+"Settings/MainPanel.asset");}
            panel.themeStyleSheet=AssetDatabase.LoadAssetAtPath<ThemeStyleSheet>(Root+"UI/RacingBoisTheme.tss");
            panel.scaleMode=PanelScaleMode.ScaleWithScreenSize; panel.referenceResolution=new Vector2Int(1600,900);
            panel.match=1; EditorUtility.SetDirty(panel);
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var cameraObject=new GameObject("Main Camera"); cameraObject.tag="MainCamera";
            var camera=cameraObject.AddComponent<Camera>(); cameraObject.AddComponent<AudioListener>();
            camera.clearFlags=CameraClearFlags.SolidColor; camera.backgroundColor=new Color(.075f,.12f,.17f);
            camera.nearClipPlane=.15f; camera.farClipPlane=500; camera.fieldOfView=58; camera.allowHDR=false;
            camera.transform.position=new Vector3(11,5,-11); camera.transform.LookAt(new Vector3(0,.5f,12));
            var lightObject=new GameObject("Sun"); var light=lightObject.AddComponent<Light>();
            light.type=LightType.Directional; light.intensity=1.7f; light.color=new Color(1,.84f,.67f);
            light.shadows=LightShadows.Soft; lightObject.transform.rotation=Quaternion.Euler(40,-30,0);
            RenderSettings.ambientMode=AmbientMode.Flat; RenderSettings.ambientLight=new Color(.38f,.47f,.57f);
            RenderSettings.fog=true; RenderSettings.fogMode=FogMode.ExponentialSquared; RenderSettings.fogDensity=.009f;
            RenderSettings.fogColor=camera.backgroundColor;
            var stage=new GameObject("Road Stage").AddComponent<RoadStageView>();
            stage.BarrierPrefab=barrier; stage.ViewCamera=camera;
            stage.RoadMaterial=Material("Road",new Color(.085f,.1f,.11f),.18f);
            stage.GroundMaterial=Material("Environment",new Color(.14f,.22f,.24f),.05f);
            stage.AccentMaterial=Material("RiderOrange",new Color(1,.30f,.055f),.45f);
            stage.DarkMaterial=Material("Rubber",new Color(.018f,.025f,.03f),.05f);
            stage.WhiteMaterial=Material("WarmWhite",new Color(.83f,.82f,.72f),.25f);
            var app=new GameObject("RacingBoisNetwork");
            var document=app.AddComponent<UIDocument>(); document.panelSettings=panel;
            document.visualTreeAsset=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(Root+"UI/Foundation.uxml");
            var bootstrap=app.AddComponent<FoundationBootstrap>(); bootstrap.Stage=stage; bootstrap.Document=document;
            EditorSceneManager.SaveScene(scene,ScenePath);
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
            AssetDatabase.SaveAssets();
            Validate();
            Debug.Log("RB_FOUNDATION_SETUP_COMPLETE");
        }

        private static void ConfigureSettings()
        {
            PlayerSettings.productName="Racing Bois"; PlayerSettings.companyName="Racing Bois"; PlayerSettings.bundleVersion="0.1.0";
            PlayerSettings.colorSpace=ColorSpace.Linear; PlayerSettings.runInBackground=true;
            PlayerSettings.defaultScreenWidth=1600; PlayerSettings.defaultScreenHeight=900;
            PlayerSettings.WebGL.template="PROJECT:RacingBois";
            PlayerSettings.WebGL.compressionFormat=WebGLCompressionFormat.Brotli;
            PlayerSettings.WebGL.decompressionFallback=false; PlayerSettings.WebGL.dataCaching=true;
            PlayerSettings.WebGL.nameFilesAsHashes=true;
            PlayerSettings.WebGL.initialMemorySize=128; PlayerSettings.WebGL.maximumMemorySize=512;
            PlayerSettings.WebGL.threadsSupport=false;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.WebGL,false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.WebGL,new[]{GraphicsDeviceType.OpenGLES3});
            var settings=new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
            var input=settings.FindProperty("activeInputHandler"); if(input!=null) input.intValue=1;
            settings.ApplyModifiedPropertiesWithoutUndo();
            // Unity 6000.5 exposes this editor setting internally; signature verified by live reflection.
            var setDynamic=typeof(PlayerSettings).GetMethod("SetDynamicBatchingForPlatform",
                System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic);
            if(setDynamic!=null)
                foreach(var target in new[]{BuildTarget.StandaloneWindows64,BuildTarget.WebGL}) setDynamic.Invoke(null,new object[]{target,false});
        }

        private static Material Material(string name,Color color,float smoothness)
        {
            var path=Root+"Materials/"+name+".mat";
            var material=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(material==null) {material=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(material,path);}
            material.SetColor("_BaseColor",color);material.SetFloat("_Smoothness",smoothness);material.enableInstancing=true;
            EditorUtility.SetDirty(material);return material;
        }

        private static void EnsureVietnameseFont()
        {
            const string path=Root+"UI/Fonts/NotoSans-Regular SDF.asset";
            var font=AssetDatabase.LoadAssetAtPath<FontAsset>(path);
            var source=AssetDatabase.LoadAssetAtPath<Font>(Root+"UI/Fonts/NotoSans-Regular.ttf");
            if(source==null)throw new InvalidOperationException("Vietnamese font source missing");
            if(font!=null)
            {
                var serializedFont=new SerializedObject(font);
                serializedFont.FindProperty("m_SourceFontFile").objectReferenceValue=source;
                serializedFont.ApplyModifiedPropertiesWithoutUndo();
                font.atlasPopulationMode=AtlasPopulationMode.Dynamic;
                EditorUtility.SetDirty(font);AssetDatabase.SaveAssets();
                AssetDatabase.ImportAsset(Root+"UI/Foundation.uss",ImportAssetOptions.ForceUpdate);
                return;
            }
            font=FontAsset.CreateFontAsset(source,48,5,GlyphRenderMode.SDFAA,1024,1024,AtlasPopulationMode.Dynamic,true);
            font.name="NotoSans-Regular SDF";
            var characters=new System.Text.StringBuilder();
            for(int c=32;c<=126;c++)characters.Append((char)c);
            for(int c=0x00c0;c<=0x01bf;c++)characters.Append((char)c);
            for(int c=0x1ea0;c<=0x1ef9;c++)characters.Append((char)c);
            characters.Append("→←↑↓↗·…");
            string missing; font.TryAddCharacters(characters.ToString(),out missing);
            const string required="Cùng lên đường. Đường thử nền tảng kết nối máy chủ điều khiển xe tốc độ phanh trái phải Giảm chuyển động giao diện";
            if(required.Any(c=>!char.IsWhiteSpace(c)&&!font.HasCharacter(c)))throw new InvalidOperationException("Vietnamese glyph missing from font atlas");
            AssetDatabase.CreateAsset(font,path);
            foreach(var atlas in font.atlasTextures)AssetDatabase.AddObjectToAsset(atlas,font);
            AssetDatabase.AddObjectToAsset(font.material,font);
            EditorUtility.SetDirty(font);
            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(Root+"UI/Foundation.uss",ImportAssetOptions.ForceUpdate);
        }

        public static void BuildWeb()
        {
            if(!File.Exists(ScenePath))Setup();
            var report=UnityEditor.BuildPipeline.BuildPlayer(new UnityEditor.BuildPlayerOptions
            {
                scenes=new[]{ScenePath},locationPathName="Build/Web",target=BuildTarget.WebGL,
                options=BuildOptions.DetailedBuildReport
            });
            Directory.CreateDirectory("docs/p02/unity");
            File.WriteAllText("docs/p02/unity/cli-build.json",JsonUtility.ToJson(new BuildReceipt
            {
                result=report.summary.result.ToString(),bytes=(long)report.summary.totalSize,
                errors=report.summary.totalErrors,warnings=report.summary.totalWarnings,
                seconds=report.summary.totalTime.TotalSeconds,unityVersion=UnityEngine.Application.unityVersion
            },true));
            if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)
                throw new InvalidOperationException("Web build failed: "+report.summary.result);
        }
        [Serializable] private sealed class BuildReceipt
        {
            public string result;public long bytes;public int errors;public int warnings;public double seconds;public string unityVersion;
        }

        private static GameObject CreateBarrierPrefab()
        {
            string folder=Root+"Art/Props/Barrier/";
            foreach(string path in Directory.GetFiles(folder,"*.png"))
            {
                var importer=AssetImporter.GetAtPath(path.Replace('\\','/')) as TextureImporter;
                if(importer==null) continue;
                importer.maxTextureSize=path.Contains("BaseColor")?512:128;
                importer.mipmapEnabled=true; importer.textureCompression=TextureImporterCompression.Compressed;
                importer.sRGBTexture=path.Contains("BaseColor");
                if(path.Contains("Normal")) importer.textureType=TextureImporterType.NormalMap;
                importer.SaveAndReimport();
            }
            var modelImporter=(ModelImporter)AssetImporter.GetAtPath(folder+"RB_RoadBarrier.fbx");
            modelImporter.globalScale=1; modelImporter.bakeAxisConversion=true;
            modelImporter.importAnimation=false; modelImporter.importCameras=false; modelImporter.importLights=false;
            modelImporter.materialImportMode=ModelImporterMaterialImportMode.None;
            modelImporter.meshCompression=ModelImporterMeshCompression.Low;
            modelImporter.generateSecondaryUV=true;modelImporter.isReadable=false; modelImporter.SaveAndReimport();
            var material=Material("RB_Barrier",Color.white,.38f);
            material.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(folder+"RB_Barrier_BaseColor.png"));
            material.SetTexture("_BumpMap",AssetDatabase.LoadAssetAtPath<Texture2D>(folder+"RB_Barrier_Normal.png"));
            material.SetTexture("_MetallicGlossMap",AssetDatabase.LoadAssetAtPath<Texture2D>(folder+"RB_Barrier_MetallicSmoothness.png"));
            // URP multiplies mask alpha by this scalar; alpha already stores authored smoothness 0.38.
            material.SetFloat("_Smoothness",1f);
            material.EnableKeyword("_NORMALMAP");material.EnableKeyword("_METALLICSPECGLOSSMAP");
            var imported=AssetDatabase.LoadAssetAtPath<GameObject>(folder+"RB_RoadBarrier.fbx");
            var instance=(GameObject)PrefabUtility.InstantiatePrefab(imported);instance.name="RB_RoadBarrier";
            instance.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);instance.transform.localScale=Vector3.one;
            var lods=new LOD[3];float[] transitions={.45f,.18f,.03f};
            for(int i=0;i<3;i++)
            {
                var renderer=instance.GetComponentsInChildren<MeshRenderer>(true).Single(r=>r.name=="RB_Barrier_LOD"+i);
                renderer.sharedMaterial=material; renderer.gameObject.SetActive(true); renderer.enabled=true;
                lods[i]=new LOD(transitions[i],new Renderer[]{renderer});
            }
            var group=instance.GetComponent<LODGroup>();if(group==null)group=instance.AddComponent<LODGroup>();
            group.SetLODs(lods);group.RecalculateBounds();
            var collider=instance.AddComponent<BoxCollider>();collider.center=new Vector3(0,.45f,0);collider.size=new Vector3(2,.9f,.64f);
            foreach(var t in instance.GetComponentsInChildren<Transform>()) t.gameObject.isStatic=true;
            var prefab=PrefabUtility.SaveAsPrefabAsset(instance,Root+"Prefabs/RB_RoadBarrier.prefab");
            UnityEngine.Object.DestroyImmediate(instance);
            return prefab;
        }

        [MenuItem("Racing Bois/Foundation/Validate")]
        public static void Validate()
        {
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Prefabs/RB_RoadBarrier.prefab");
            if(prefab==null)throw new InvalidOperationException("Missing barrier prefab");
            var renderers=prefab.GetComponentsInChildren<MeshRenderer>(true);
            if(renderers.Length!=3||prefab.GetComponent<LODGroup>().lodCount!=3)throw new InvalidOperationException("LOD mismatch");
            if(prefab.GetComponentsInChildren<Collider>(true).Length!=1||prefab.GetComponent<BoxCollider>()==null)throw new InvalidOperationException("Collider policy mismatch");
            if(prefab.transform.position!=Vector3.zero||prefab.transform.localScale!=Vector3.one||prefab.transform.rotation!=Quaternion.identity)throw new InvalidOperationException("Root transform mismatch");
            foreach(var child in prefab.GetComponentsInChildren<Transform>(true))
                if(GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(child.gameObject)>0)throw new InvalidOperationException("Missing script on prefab");
            foreach(var r in renderers) if(r.sharedMaterial==null||r.sharedMaterial.shader==null)throw new InvalidOperationException("Missing material");
            var meshes=prefab.GetComponentsInChildren<MeshFilter>(true);
            var bounds=renderers.Single(r=>r.name=="RB_Barrier_LOD0").bounds;
            if(Vector3.Distance(bounds.size,new Vector3(2,.9f,.64f))>.01f)throw new InvalidOperationException("Imported unit/axis mismatch");
            if(meshes.Any(m=>m.sharedMesh==null||!m.sharedMesh.HasVertexAttribute(VertexAttribute.Normal)||!m.sharedMesh.HasVertexAttribute(VertexAttribute.Tangent)))
                throw new InvalidOperationException("Missing mesh normal/tangent");
            var triangles=meshes.Select(m=>(long)m.sharedMesh.GetIndexCount(0)/3).ToArray();
            var receipt=new ValidationReceipt{passed=true,unityVersion=UnityEngine.Application.unityVersion,
                prefab=AssetDatabase.GetAssetPath(prefab),lodCount=3,colliders=1,materialCount=renderers.Select(r=>r.sharedMaterial).Distinct().Count(),
                triangles=triangles,uv2=meshes.All(m=>m.sharedMesh.HasVertexAttribute(VertexAttribute.TexCoord1)),
                rootPosition=prefab.transform.position,rootRotation=prefab.transform.eulerAngles,rootScale=prefab.transform.localScale,
                lod0Size=bounds.size,missingScripts=0,normalsAndTangents=true};
            Directory.CreateDirectory("docs/p02/unity");
            File.WriteAllText("docs/p02/unity/asset-validation.json",JsonUtility.ToJson(receipt,true));
            if(!receipt.uv2)throw new InvalidOperationException("Missing lightmap UV");
            Debug.Log("RB_ASSET_VALIDATION_PASS "+string.Join("/",triangles));
        }
        [Serializable] private sealed class ValidationReceipt
        {
            public bool passed;public string unityVersion;public string prefab;public int lodCount;public int colliders;public int materialCount;
            public long[] triangles;public bool uv2;public Vector3 rootPosition;public Vector3 rootRotation;public Vector3 rootScale;
            public Vector3 lod0Size;public int missingScripts;public bool normalsAndTangents;
        }
    }
}
