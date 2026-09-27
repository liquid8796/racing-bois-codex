using System;
using System.IO;
using System.Linq;
using System.Runtime.ExceptionServices;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace RacingBois.Diagnostics.PoseEnvelopePreview.Editor
{
    public static class PosePreviewBuilder
    {
        public const string AssetRoot="Assets/RacingBois/Diagnostics/PoseEnvelopePreview";
        [Serializable] private sealed class Receipt
        {
            public int schema=1,errors,warnings;public bool passed,sourceBindingPassed,editorStateRestored,settingsChanged;
            public string attemptId,startedUtc,completedUtc,unityVersion,target="StandaloneWindows64",backend="Mono2x",result,failureCode,output,scene,sourceFingerprint,selectionSha256;
            public double buildSeconds;public PreviewFile[] sources,sourcesAfter,playerFiles;public string[] restorationErrors,changedDuringBuild;
            public string scope="Isolated real-prefab Windows pose comparison build. No game bootstrap, frozen Client edit, network call, art/comfort/performance acceptance.";
        }
        public static string Build(string selectionPath,string outputDirectory,string compileProofPath="docs/p10/pose-envelope-native-staging/compiled-sources.json")
        {
            var receipt=new Receipt{attemptId=Guid.NewGuid().ToString("N"),startedUtc=DateTime.UtcNow.ToString("O"),unityVersion=Application.unityVersion,result="Preparing"};
            PreviewBuildScope scope=null;ExceptionDispatchInfo failure=null;string output=null;
            try
            {
                Require(!EditorApplication.isCompiling&&!EditorApplication.isPlayingOrWillChangePlaymode&&!BuildPipeline.isBuildingPlayer,"editor_not_idle");
                PreviewBuildInputs.VerifyExecutingAssemblies(compileProofPath);var selection=PreviewBuildInputs.Selection(selectionPath);
                var bike=AssetDatabase.LoadAssetAtPath<GameObject>(selection.bike.path);var rider=AssetDatabase.LoadAssetAtPath<GameObject>(selection.rider.path);
                var pipeline=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(selection.pipeline.path);var fixture=AssetDatabase.LoadAssetAtPath<TextAsset>(selection.fixture.path);
                Require(bike!=null&&rider!=null&&pipeline!=null&&fixture!=null,"selected_assets_missing");
                Require(PrefabUtility.IsPartOfPrefabAsset(bike)&&PrefabUtility.IsPartOfPrefabAsset(rider),"actual_prefabs_required");
                Require(!bike.GetComponentsInChildren<MonoBehaviour>(true).Any(c=>c==null)&&!rider.GetComponentsInChildren<MonoBehaviour>(true).Any(c=>c==null),"missing_actor_script");
                foreach(var actor in new[]{bike,rider})
                {
                    var renderers=actor.GetComponentsInChildren<Renderer>(true);
                    Require(renderers.Length>0&&renderers.All(r=>r.sharedMaterials.Length>0&&r.sharedMaterials.All(m=>m!=null&&m.shader!=null)),"actor_material_or_renderer_missing");
                }
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone,BuildTarget.StandaloneWindows64),"windows_module_missing");
                Require(Directory.Exists(Path.Combine(EditorApplication.applicationContentsPath,"PlaybackEngines/windowsstandalonesupport/Variations/win64_player_nondevelopment_mono")),"mono_player_missing");
                string candidate=Path.GetFullPath(outputDirectory),boundary=Path.GetFullPath("Build/PoseEnvelopePreview")+Path.DirectorySeparatorChar;
                Require(candidate.StartsWith(boundary,StringComparison.OrdinalIgnoreCase)&&!Directory.Exists(candidate)&&!File.Exists(candidate),"fresh_preview_output_required");
                PreviewBuildInputs.InsideProject(PreviewBuildInputs.Relative(candidate));
                var original=SceneManager.GetActiveScene();var oldPipeline=GraphicsSettings.defaultRenderPipeline;var oldQuality=QualitySettings.renderPipeline;
                var backend=PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone);var apis=PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
                bool defaults=PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64),background=PlayerSettings.runInBackground;string product=PlayerSettings.productName;
                scope=new PreviewBuildScope();var projectSettings=new PreviewProjectSettingsScope();scope.Own("project_settings_memory_and_disk",projectSettings.Restore);
                output=candidate;Directory.CreateDirectory(output);receipt.output=PreviewBuildInputs.Relative(output);
                scope.Own("active_scene",()=>{Require(original.IsValid()&&original.isLoaded,"original_scene_unavailable");if(SceneManager.GetActiveScene()!=original)SceneManager.SetActiveScene(original);Require(SceneManager.GetActiveScene()==original,"active_scene_restore_failed");});
                var created=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);
                scope.Own("owned_scene",()=>{if(created.IsValid()&&created.isLoaded)Require(EditorSceneManager.CloseScene(created,true),"owned_scene_close_failed");});
                SceneManager.SetActiveScene(created);
                string generated=AssetRoot+"/Generated";if(!AssetDatabase.IsValidFolder(generated))AssetDatabase.CreateFolder(AssetRoot,"Generated");
                string owned=generated+"/"+receipt.attemptId;AssetDatabase.CreateFolder(generated,receipt.attemptId);
                var ownedPipeline=UnityEngine.Object.Instantiate(pipeline);ownedPipeline.name="PosePreviewPipeline";
                string ownedPipelinePath=owned+"/PosePreviewPipeline.asset";AssetDatabase.CreateAsset(ownedPipeline,ownedPipelinePath);pipeline=ownedPipeline;
                var host=new GameObject("Isolated pose envelope comparison - no game bootstrap");var runner=host.AddComponent<PoseEnvelopePreviewRunner>();
                runner.BikePrefab=bike;runner.RiderPrefab=rider;runner.Fixture=fixture;
                runner.GroundMaterial=Material(owned,"Ground",new Color(.24f,.27f,.31f));runner.ReferenceMaterial=Material(owned,"ConstructedReference",new Color(.8f,.28f,.07f));runner.RawTargetMaterial=Material(owned,"UnfilteredTarget",new Color(.05f,.9f,.75f));
                var camera=new GameObject("Explicit diagnostic camera").AddComponent<Camera>();camera.gameObject.AddComponent<AudioListener>();runner.ReviewCamera=camera;
                camera.nearClipPlane=.03f;camera.farClipPlane=600;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.38f,.47f,.57f);camera.fieldOfView=65;camera.aspect=16f/9;
                var sun=new GameObject("Diagnostic daylight").AddComponent<Light>();sun.type=LightType.Directional;sun.color=new Color(1,.93f,.84f);sun.intensity=1.6f;sun.shadows=LightShadows.Soft;sun.transform.rotation=Quaternion.Euler(38,-35,0);
                RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.52f,.56f,.63f);RenderSettings.fog=false;
                receipt.scene=owned+"/PosePreview.unity";Require(EditorSceneManager.SaveScene(created,receipt.scene),"scene_save_failed");
                if(oldPipeline!=pipeline)scope.Change("graphics_pipeline",()=>GraphicsSettings.defaultRenderPipeline=pipeline,()=>GraphicsSettings.defaultRenderPipeline=oldPipeline);
                if(oldQuality!=pipeline)scope.Change("quality_pipeline",()=>QualitySettings.renderPipeline=pipeline,()=>QualitySettings.renderPipeline=oldQuality);
                if(backend!=ScriptingImplementation.Mono2x)scope.Change("scripting_backend",()=>PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x),()=>PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,backend));
                if(defaults)scope.Change("default_apis",()=>PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false),()=>PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,defaults));
                if(!apis.SequenceEqual(new[]{GraphicsDeviceType.Direct3D11}))scope.Change("graphics_apis",()=>PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{GraphicsDeviceType.Direct3D11}),()=>PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,apis));
                if(!background)scope.Change("run_background",()=>PlayerSettings.runInBackground=true,()=>PlayerSettings.runInBackground=background);
                if(product!="Racing Bois Pose Comparison")scope.Change("product",()=>PlayerSettings.productName="Racing Bois Pose Comparison",()=>PlayerSettings.productName=product);
                projectSettings.UsePipelineAtEveryQuality(pipeline);
                var preprocessor=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("UnityEditor.Rendering.Universal.ShaderBuildPreprocessor")).FirstOrDefault(t=>t!=null);
                Require(preprocessor!=null,"installed_urp_preprocessor_missing");
                var gather=preprocessor.GetMethod("GatherShaderFeatures",System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.NonPublic);
                Require(gather!=null,"installed_urp_prefilter_contract_changed");gather.Invoke(null,new object[]{false});
                AssetDatabase.SaveAssetIfDirty(pipeline);projectSettings.PersistEffectiveSettings(Path.Combine(output,"BuildEvidence","effective"));
                receipt.selectionSha256=PreviewBuildInputs.Digest(selectionPath);receipt.sources=PreviewBuildInputs.Snapshot(receipt.scene,selectionPath,compileProofPath,selection,ownedPipelinePath);receipt.sourceFingerprint=PreviewBuildInputs.Fingerprint(receipt.sources);
                CaptureSettings(output,"before");
                receipt.result="Building";Write(output,receipt);
                var built=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{receipt.scene},target=BuildTarget.StandaloneWindows64,locationPathName=Path.Combine(output,"RacingBoisPosePreview.exe"),options=BuildOptions.StrictMode|BuildOptions.DetailedBuildReport|BuildOptions.CompressWithLz4HC});
                receipt.result=built.summary.result.ToString();receipt.errors=built.summary.totalErrors;receipt.warnings=built.summary.totalWarnings;receipt.buildSeconds=built.summary.totalTime.TotalSeconds;
                receipt.sourcesAfter=PreviewBuildInputs.Snapshot(receipt.scene,selectionPath,compileProofPath,selection,ownedPipelinePath);
                receipt.changedDuringBuild=receipt.sources.Select(r=>r.path).Union(receipt.sourcesAfter.Select(r=>r.path)).Where(path=>
                    receipt.sources.FirstOrDefault(r=>r.path==path)?.sha256!=receipt.sourcesAfter.FirstOrDefault(r=>r.path==path)?.sha256)
                    .Union(projectSettings.ChangedDuringBuild()).OrderBy(path=>path,StringComparer.Ordinal).ToArray();
                receipt.sourceBindingPassed=receipt.changedDuringBuild.Length==0&&receipt.sourceFingerprint==PreviewBuildInputs.Fingerprint(receipt.sourcesAfter);
                CaptureSettings(output,"after");
                Require(built.summary.result==BuildResult.Succeeded&&receipt.sourceBindingPassed,"build_or_source_binding_failed");
                File.WriteAllText(Path.Combine(output,"PosePreview.binding.json"),JsonUtility.ToJson(new PreviewBinding{sourceFingerprint=receipt.sourceFingerprint,fixtureSha256=selection.fixture.sha256,selectionSha256=receipt.selectionSha256,unityVersion=Application.unityVersion},true));
                receipt.playerFiles=Directory.GetFiles(output,"*",SearchOption.AllDirectories).Where(p=>Path.GetFileName(p)!="PosePreview.build.json").OrderBy(p=>p,StringComparer.Ordinal).Select(p=>new PreviewFile{path=Path.GetRelativePath(output,p).Replace('\\','/'),sha256=PreviewBuildInputs.Digest(p),bytes=new FileInfo(p).Length}).ToArray();receipt.passed=true;
            }
            catch(Exception error){receipt.failureCode=error.GetType().Name;failure=ExceptionDispatchInfo.Capture(error);}
            finally
            {
                receipt.settingsChanged=scope!=null&&scope.Changed;receipt.restorationErrors=scope==null?Array.Empty<string>():scope.Restore();receipt.editorStateRestored=receipt.restorationErrors.Length==0;
                if(!receipt.editorStateRestored){receipt.passed=false;if(failure==null)receipt.failureCode="restoration_failed";}
                receipt.completedUtc=DateTime.UtcNow.ToString("O");if(output!=null)Write(output,receipt);
            }
            if(failure!=null)failure.Throw();Require(receipt.editorStateRestored,"restoration_failed");return JsonUtility.ToJson(receipt,true);
        }
        private static Material Material(string folder,string name,Color color)
        {
            var shader=Shader.Find("Universal Render Pipeline/Lit");Require(shader!=null,"urp_shader_missing");var material=new Material(shader){name="Diagnostic "+name};
            material.SetColor("_BaseColor",color);material.SetFloat("_Metallic",0);material.SetFloat("_Smoothness",.2f);AssetDatabase.CreateAsset(material,folder+"/"+name+".mat");return material;
        }
        private static void Write(string output,Receipt receipt)=>File.WriteAllText(Path.Combine(output,"PosePreview.build.json"),JsonUtility.ToJson(receipt,true));
        private static void CaptureSettings(string output,string phase)
        {
            string folder=Path.Combine(output,"BuildEvidence",phase);Directory.CreateDirectory(folder);
            foreach(string name in new[]{"ProjectSettings","GraphicsSettings","QualitySettings"})
                File.Copy("ProjectSettings/"+name+".asset",Path.Combine(folder,name+".asset"),true);
        }
        private static void Require(bool valid,string code){if(!valid)throw new InvalidOperationException(code);}
    }
}
