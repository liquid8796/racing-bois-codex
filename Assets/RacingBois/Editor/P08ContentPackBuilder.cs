using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Explicit pack roots keep actors shared, one route resident and music outside the Unity heap.</summary>
    public static class P08ContentPackBuilder
    {
        public const string Root = "Assets/RacingBois/Content/P08/";
        private const string Materials = "Assets/RacingBois/Materials/P08/Routes/";
        private const string P06 = "Assets/RacingBois/Prefabs/P06/";
        private const string P08 = "Assets/RacingBois/Prefabs/P08/";
        private static readonly string[][] Props = {
            new[]{"RB_P06_RockA","RB_P06_RockB","RB_P06_Sage","RB_P06_DryGrass","RB_P06_Guardrail","RB_P06_Chevron"},
            new[]{"RB_P08_CityWarehouse","RB_P08_CityCornerShop","RB_P08_CityStreetlamp","RB_P08_CityBusShelter","RB_P08_CityLoadingGantry","RB_P08_CityWaterTank"},
            new[]{"RB_P08_RidgeFir","RB_P08_RidgeGranite","RB_P08_RidgeStoneWall","RB_P08_RidgeTimberHut","RB_P08_RidgeSnowPole","RB_P08_RidgeGalleryArch"},
            new[]{"RB_P08_CoastPalm","RB_P08_CoastSurfShack","RB_P08_CoastBeacon","RB_P08_CoastBridgePier","RB_P08_CoastBoulder","RB_P08_CoastBroadleafShrub"},
            new[]{"RB_P08_OrchardAppleTree","RB_P08_OrchardBarn","RB_P08_OrchardSilo","RB_P08_OrchardFence","RB_P08_OrchardHayBale","RB_P08_OrchardProduceKiosk"}
        };
        private static readonly string[] RouteMusic = {"amber-apex","ridge-line-promise","concrete-comet","blue-hour-service","dust-signal"};
        private static readonly Color[] Fog = {new Color(.58f,.47f,.36f),new Color(.10f,.13f,.20f),new Color(.61f,.69f,.73f),new Color(.51f,.70f,.77f),new Color(.62f,.66f,.47f)};
        private static readonly Color[] Ground = {Color.white,new Color(.38f,.41f,.46f),new Color(.69f,.72f,.67f),new Color(.82f,.78f,.63f),new Color(.56f,.66f,.40f)};
        [Serializable] private sealed class AudioDelivery { public AudioEntry[] clips = null; }
        [Serializable] private sealed class AudioEntry { public string id = "", category = "", role = "", oggPath = "", oggSha256 = ""; public bool signalAuditPassed = false; }
        [Serializable] private sealed class BuildReceipt { public int schema=1; public bool passed; public string unityVersion, target, contentHash, output; public P08BundleEntry[] entries; public DependencyReceipt[] dependencies; public GoldenProductionGate.FileRef promotionManifest; }
        [Serializable] private sealed class DependencyReceipt { public string id; public string[] dependsOn; }

        public static void Setup() { PrepareRoutes(); PrepareActors(); Validate(); }
        public static void Prepare() => Setup();

        public static void PrepareRoutes()
        {
            var bindings = GoldenProductionBindings.Load(); bindings.ValidateConsumed(PackPrefabNames());
            Directory.CreateDirectory(Root); Directory.CreateDirectory(Materials);
            for (int i=0;i<5;i++)
            {
                var route=Upsert<P08RouteContent>(Root+"Route-"+i+".asset"); route.CourseIndex=i;
                route.Props=Props[i].Select(name=>bindings.Resolve(name,Prefab)).ToArray();
                route.Guardrail=bindings.Resolve("RB_P06_Guardrail",Prefab); route.Chevron=bindings.Resolve("RB_P06_Chevron",Prefab); route.UtilityPole=bindings.Resolve("RB_P06_UtilityPole",Prefab);
                route.Asphalt=Tinted("Asphalt",i,Color.white); route.Shoulder=Tinted("Gravel",i,i==0?Color.white:Ground[i]);
                route.Landscape=Tinted("Gravel",i,Ground[i],"Landscape");
                route.Paint=Require<Material>("Assets/RacingBois/Materials/RacePaint.mat"); route.YellowPaint=Require<Material>("Assets/RacingBois/Materials/RaceYellow.mat");
                route.Wire=Require<Material>("Assets/RacingBois/Materials/P06/RB_P06_Roadside.mat");
                route.Water=Flat("Water-"+i,new Color(.10f,.34f,.43f),.72f); route.Skybox=Sky(i);
                route.FogColor=Fog[i]; route.AmbientColor=i==1?new Color(.27f,.30f,.39f):Color.Lerp(Fog[i],Color.white,.25f);
                route.FogDensity=i==1?.0016f:i==2?.0018f:.0012f; route.SunIntensity=i==1?.55f:1.2f;
                route.SunColor=i==4?new Color(1,.89f,.72f):Color.white;
                route.SunEuler=i==1?new Vector3(12,-55,0):i==4?new Vector3(28,-42,0):new Vector3(38,-28,0);
                route.RouteMusicId=RouteMusic[i]; route.Validate(i); EditorUtility.SetDirty(route);
            }
            AssetDatabase.SaveAssets(); Debug.Log("RB_P08_ROUTE_CONTENT_READY");
        }

        public static void PrepareActors()
        {
            var bindings = GoldenProductionBindings.Load(); bindings.ValidateConsumed(PackPrefabNames());
            Directory.CreateDirectory(Root); var delivery=ReadAudio();
            var actor=Upsert<P08ActorContent>(Root+"Actors.asset");
            actor.Bikes=Enumerable.Range(0,BikeCatalog.Count).Select(i=>bindings.Resolve("RB_P08_Bike_"+i.ToString("D2"),Prefab)).ToArray();
            actor.Riders=Enumerable.Range(0,CharacterCatalog.Count).Select(i=>bindings.Resolve(CharacterCatalog.GetAt(i).ArtId,Prefab)).ToArray();
            actor.Portraits=Enumerable.Range(0,CharacterCatalog.Count*3).Select(i=>Portrait(i/3,i%3)).ToArray();
            actor.PoliceBike=bindings.Resolve("RB_P06_PoliceMotorcycle",Prefab); actor.PoliceRider=bindings.Resolve("RB_P06_PoliceRider",Prefab);
            actor.Coupe=bindings.Resolve("RB_P06_TrafficCoupe",Prefab); actor.Van=bindings.Resolve("RB_P06_TrafficVan",Prefab); actor.Pedestrian=bindings.Resolve("RB_Pedestrian",Prefab); actor.Club=bindings.Resolve("RB_Club",Prefab);
            actor.TrafficExtras=P08ArtBuilder.Entries().Where(x=>x.kind=="traffic").Select(x=>bindings.Resolve(x.name,Prefab)).ToArray();
            actor.RiderClips=AssetDatabase.LoadAllAssetsAtPath("Assets/RacingBois/Art/P06/Hero/RB_P06_Rider.fbx").OfType<AnimationClip>()
                .Where(c=>P06HeroAssetBuilder.ClipNames.Contains(c.name)).OrderBy(c=>c.name).ToArray();
            var library=Upsert<P08ContentLibrary>(Root+"Library.asset"); var bank=Upsert<RaceAudioBank>(Root+"AudioBank.asset");
            // Existing original short utility cues fill dedicated bank roles; full compositions are never serialized here.
            EditorUtility.CopySerialized(Require<RaceAudioBank>("Assets/RacingBois/Audio/P06/RB_P06_AudioBank.asset"),bank); bank.Music=null;
            var sfx=delivery.Where(c=>c.category=="sfx").ToArray();
            foreach(var entry in sfx) ImportSound(entry);
            AudioClip Clip(string id)=>Require<AudioClip>(sfx.Single(x=>x.id==id).oggPath);
            bank.EngineLow=Clip("street-single-engine"); bank.EngineHigh=Clip("boost-pressure"); bank.Tire=Clip("tire-asphalt-drift"); bank.Gravel=Clip("tire-gravel-drift");
            bank.Impact=Clip("glove-contact-light"); bank.Crash=Clip("crash-traffic-medium"); bank.WeaponClub=Clip("wood-grip-contact"); bank.WeaponFist=Clip("glove-contact-heavy"); bank.WeaponChain=Clip("chain-link-contact"); bank.WeaponSwing=Clip("glove-air-sweep");
            library.AudioBank=bank;
            library.Sfx=sfx.Where(x=>x.role!="reaction").Select(x=>new P08NamedClip{Id=x.id,Clip=Require<AudioClip>(x.oggPath)}).ToArray();
            library.Voices=sfx.Where(x=>x.role=="reaction").Select(x=>new P08NamedClip{Id=x.id,Clip=Require<AudioClip>(x.oggPath)}).ToArray(); actor.Library=library;
            var ids=new HashSet<string>(sfx.Select(x=>x.id),StringComparer.Ordinal);
            foreach(var role in P08AudioRoles.All) if(!ids.Contains(role.Id))throw new InvalidOperationException("Missing functional audio role "+role.Id);
            if(sfx.Length!=72)throw new InvalidOperationException("Expected 72 authored sound cues.");
            actor.Validate(); EditorUtility.SetDirty(actor); EditorUtility.SetDirty(library); EditorUtility.SetDirty(bank);
            AssetDatabase.SaveAssets(); Debug.Log("RB_P08_ACTOR_CONTENT_READY");
        }

        public static void Validate()
        {
            var bindings = GoldenProductionBindings.Load(); bindings.ValidateConsumed(PackPrefabNames());
            var actor=Require<P08ActorContent>(Root+"Actors.asset"); actor.Validate();
            for(int i=0;i<actor.Bikes.Length;i++) bindings.ValidateBound("RB_P08_Bike_"+i.ToString("D2"),actor.Bikes[i]);
            for(int i=0;i<actor.Riders.Length;i++) bindings.ValidateBound(CharacterCatalog.GetAt(i).ArtId,actor.Riders[i]);
            bindings.ValidateBound("RB_P06_PoliceMotorcycle",actor.PoliceBike); bindings.ValidateBound("RB_P06_PoliceRider",actor.PoliceRider);
            bindings.ValidateBound("RB_P06_TrafficCoupe",actor.Coupe); bindings.ValidateBound("RB_P06_TrafficVan",actor.Van);
            bindings.ValidateBound("RB_Pedestrian",actor.Pedestrian); bindings.ValidateBound("RB_Club",actor.Club);
            var traffic=P08ArtBuilder.Entries().Where(x=>x.kind=="traffic").ToArray();
            if(actor.TrafficExtras==null||actor.TrafficExtras.Length!=traffic.Length)throw new InvalidOperationException("Traffic pack count changed.");
            for(int i=0;i<traffic.Length;i++)bindings.ValidateBound(traffic[i].name,actor.TrafficExtras[i]);
            for(int i=0;i<5;i++)
            {
                var route=Require<P08RouteContent>(Root+"Route-"+i+".asset"); route.Validate(i);
                for(int j=0;j<Props[i].Length;j++)bindings.ValidateBound(Props[i][j],route.Props[j]);
                bindings.ValidateBound("RB_P06_Guardrail",route.Guardrail);bindings.ValidateBound("RB_P06_Chevron",route.Chevron);bindings.ValidateBound("RB_P06_UtilityPole",route.UtilityPole);
            }
            SharedFurniturePaths();
            var audio=ReadAudio(); if(audio.Count(x=>x.category=="music")!=25)throw new InvalidOperationException("Expected 25 streamed compositions/scores.");
            foreach(var route in RouteMusic)if(!audio.Any(x=>x.category=="music"&&x.id==route))throw new InvalidOperationException("Route music missing.");
            Debug.Log("RB_P08_CONTENT_VALIDATED");
        }
        public static void BuildEditor()=>Build(BuildTarget.StandaloneWindows64,"Build/Content-editor","editor");
        public static void BuildDesktop()=>Build(BuildTarget.StandaloneWindows64,"Build/Content-desktop","desktop");
        public static void BuildWeb()=>Build(BuildTarget.WebGL,"Build/Content","webgl");
        private static void Build(BuildTarget target,string output,string label)
        {
            var promotionIdentity = GoldenProductionBindings.ManifestIdentity();
            Validate(); Directory.CreateDirectory(output); var audio=ReadAudio();
            // Shared road furniture, markings and their surfaces are explicitly assigned to actors.
            // Their transitive dependencies cannot be duplicated in all five route bundles.
            var sharedRoots=new[]{Root+"Actors.asset"}.Concat(SharedFurniturePaths()).Concat(new[]{
                "Assets/RacingBois/Materials/RacePaint.mat","Assets/RacingBois/Materials/RaceYellow.mat","Assets/RacingBois/Materials/P06/RB_P06_Roadside.mat",
                "Assets/RacingBois/Materials/P06/RB_P06_Asphalt.mat","Assets/RacingBois/Materials/P06/RB_P06_Gravel.mat"}).ToArray();
            var common=AssetDatabase.GetDependencies(sharedRoots,true).Where(x=>!x.EndsWith(".cs",StringComparison.Ordinal)&&!x.EndsWith(".asmdef",StringComparison.Ordinal)&&!x.EndsWith(".dll",StringComparison.Ordinal)).Distinct().OrderBy(x=>x,StringComparer.Ordinal).ToArray();
            var builds=new List<AssetBundleBuild>{new AssetBundleBuild{assetBundleName="actors",assetNames=common}};
            for(int i=0;i<5;i++)builds.Add(new AssetBundleBuild{assetBundleName="route-"+i,assetNames=new[]{Root+"Route-"+i+".asset"}});
            var built=BuildPipeline.BuildAssetBundles(output,builds.ToArray(),BuildAssetBundleOptions.ChunkBasedCompression|BuildAssetBundleOptions.StrictMode,target);
            if(built==null)throw new InvalidOperationException("Content bundle build failed.");
            var entries=new List<P08BundleEntry>(); var dependencies=new List<DependencyReceipt>();
            foreach(var build in builds)
            {
                string id=build.assetBundleName,path=Path.Combine(output,id),sha=Digest(path);
                if(!BuildPipeline.GetCRCForAssetBundle(path,out uint crc))throw new InvalidOperationException("Bundle CRC unavailable.");
                string hashed=id+"-"+sha+".bundle"; File.Copy(path,Path.Combine(output,hashed),true);
                var deps=built.GetAllDependencies(id);if(deps.Any(d=>d!="actors")||(id=="actors"&&deps.Length!=0))throw new InvalidOperationException("Unexpected bundle dependency graph.");
                dependencies.Add(new DependencyReceipt{id=id,dependsOn=deps});
                entries.Add(new P08BundleEntry{id=id,url=hashed,sha256=sha,crc=crc,bytes=new FileInfo(path).Length,asset=(id=="actors"?Root+"Actors.asset":Root+"Route-"+id.Substring(6)+".asset").ToLowerInvariant(),kind=id=="actors"?"actors":"route",courseIndex=id=="actors"?-1:int.Parse(id.Substring(6))});
            }
            Directory.CreateDirectory(Path.Combine(output,"music"));
            foreach(var track in audio.Where(x=>x.category=="music"))
            {
                string sha=Digest(track.oggPath);if(!string.Equals(sha,track.oggSha256,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Music delivery fingerprint differs.");
                string relative="music/"+track.id+"-"+sha+".ogg";File.Copy(track.oggPath,Path.Combine(output,relative),true);
                entries.Add(new P08BundleEntry{id=track.id,url=relative,sha256=sha,bytes=new FileInfo(track.oggPath).Length,kind="music",courseIndex=-1,asset=""});
            }
            // Recheck acceptance, native source and the actual pack references after the build window.
            Validate();
            GoldenProductionBindings.RequireSameManifest(promotionIdentity);
            var manifest=new P08ContentManifest{schema=1,buildTarget=target.ToString(),contentHash=GameplayRules.ContentHash,actorsId="actors",bundles=entries.ToArray()};
            ContentManifestRules.Validate(manifest,GameplayRules.ContentHash,new Uri(Path.GetFullPath(output)+Path.DirectorySeparatorChar));
            File.WriteAllText(Path.Combine(output,"manifest.json"),JsonUtility.ToJson(manifest,true));
            Directory.CreateDirectory("docs/p08/streaming"); File.WriteAllText("docs/p08/streaming/"+label+"-build.json",JsonUtility.ToJson(new BuildReceipt{passed=true,unityVersion=UnityEngine.Application.unityVersion,target=target.ToString(),contentHash=GameplayRules.ContentHash,output=output,entries=entries.ToArray(),dependencies=dependencies.ToArray(),promotionManifest=promotionIdentity},true));
            Debug.Log("RB_P08_"+label.ToUpperInvariant()+"_PACKS_BUILT");
        }
        private static AudioEntry[] ReadAudio()
        {
            var data=JsonUtility.FromJson<AudioDelivery>(File.ReadAllText("docs/p08/media/audio-delivery.json"));
            if(data?.clips==null||data.clips.Length!=97||data.clips.Any(x=>!x.signalAuditPassed||!File.Exists(x.oggPath)))throw new InvalidOperationException("Audited audio delivery is incomplete.");
            return data.clips;
        }
        private static void ImportSound(AudioEntry entry)
        {
            var importer=AssetImporter.GetAtPath(entry.oggPath) as AudioImporter;if(importer==null)throw new InvalidOperationException("Audio importer missing.");
            importer.forceToMono=true;importer.loadInBackground=true;
            var settings=importer.defaultSampleSettings;settings.loadType=AudioClipLoadType.CompressedInMemory;settings.compressionFormat=AudioCompressionFormat.Vorbis;settings.quality=.75f;settings.sampleRateSetting=AudioSampleRateSetting.OptimizeSampleRate;
            settings.preloadAudioData=true;importer.defaultSampleSettings=settings;importer.SetOverrideSampleSettings("WebGL",settings);importer.SaveAndReimport();
        }
        private static Sprite Portrait(int character,int state)
        {
            string path="Assets/RacingBois/Art/P08/Portraits/RB_P08_Portrait_"+character.ToString("D2")+"_"+state.ToString("D2")+".png";
            var importer=AssetImporter.GetAtPath(path) as TextureImporter;if(importer==null)throw new InvalidOperationException("Portrait missing: "+path);
            importer.textureType=TextureImporterType.Sprite;importer.spriteImportMode=SpriteImportMode.Single;importer.mipmapEnabled=false;importer.isReadable=false;importer.maxTextureSize=512;importer.textureCompression=TextureImporterCompression.Compressed;importer.SaveAndReimport();
            return Require<Sprite>(path);
        }
        private static GameObject Prefab(string name)=>Require<GameObject>((name.StartsWith("RB_P08_",StringComparison.Ordinal)?P08:name.StartsWith("RB_P06_",StringComparison.Ordinal)?P06:"Assets/RacingBois/Prefabs/")+name+".prefab");
        private static string[] SharedFurniturePaths()
        {
            var first=Require<P08RouteContent>(Root+"Route-0.asset");
            var shared=new[]{first.Guardrail,first.Chevron,first.UtilityPole};
            if(shared.Any(x=>x==null))throw new InvalidOperationException("Shared route furniture is incomplete.");
            for(int i=1;i<5;i++)
            {
                var route=Require<P08RouteContent>(Root+"Route-"+i+".asset");
                if(!shared.SequenceEqual(new[]{route.Guardrail,route.Chevron,route.UtilityPole}))
                    throw new InvalidOperationException("Routes must reference the same accepted shared furniture.");
            }
            var paths=shared.Select(AssetDatabase.GetAssetPath).ToArray();
            if(paths.Any(x=>string.IsNullOrEmpty(x)||!x.EndsWith(".prefab",StringComparison.Ordinal)))throw new InvalidOperationException("Shared furniture must be persistent prefab assets.");
            return paths;
        }
        private static IEnumerable<string> PackPrefabNames()=>Enumerable.Range(0,BikeCatalog.Count).Select(i=>"RB_P08_Bike_"+i.ToString("D2"))
            .Concat(CharacterCatalog.All.Select(x=>x.ArtId)).Concat(Props.SelectMany(x=>x))
            .Concat(new[]{"RB_P06_Guardrail","RB_P06_Chevron","RB_P06_UtilityPole","RB_P06_PoliceMotorcycle","RB_P06_PoliceRider","RB_P06_TrafficCoupe","RB_P06_TrafficVan","RB_Pedestrian","RB_Club"})
            .Concat(P08ArtBuilder.Entries().Where(x=>x.kind=="traffic").Select(x=>x.name));
        private static T Require<T>(string path)where T:UnityEngine.Object=>AssetDatabase.LoadAssetAtPath<T>(path)??throw new InvalidOperationException("Content asset missing: "+path);
        private static T Upsert<T>(string path)where T:ScriptableObject
        {var value=AssetDatabase.LoadAssetAtPath<T>(path);if(value==null){value=ScriptableObject.CreateInstance<T>();AssetDatabase.CreateAsset(value,path);}return value;}
        private static Material Tinted(string surface,int course,Color tint,string semantic="")
        {string path=Materials+"Route-"+course+"-"+(semantic.Length==0?surface:semantic)+".mat";var source=Require<Material>("Assets/RacingBois/Materials/P06/RB_P06_"+surface+".mat");var value=AssetDatabase.LoadAssetAtPath<Material>(path);if(value==null){value=new Material(source);AssetDatabase.CreateAsset(value,path);}else value.CopyPropertiesFromMaterial(source);value.SetColor("_BaseColor",tint);value.enableInstancing=true;EditorUtility.SetDirty(value);return value;}
        private static Material Flat(string name,Color color,float smoothness)
        {string path=Materials+name+".mat";var value=AssetDatabase.LoadAssetAtPath<Material>(path);if(value==null){value=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(value,path);}value.SetColor("_BaseColor",color);value.SetFloat("_Smoothness",smoothness);value.enableInstancing=true;EditorUtility.SetDirty(value);return value;}
        private static Material Sky(int course)
        {string path=Materials+"Sky-"+course+".mat";var value=AssetDatabase.LoadAssetAtPath<Material>(path);if(value==null){value=new Material(Shader.Find("Skybox/Procedural"));AssetDatabase.CreateAsset(value,path);}value.SetColor("_SkyTint",Fog[course]);value.SetColor("_GroundColor",Ground[course]);value.SetFloat("_Exposure",course==1?.55f:1.05f);value.SetFloat("_AtmosphereThickness",course==1?.7f:1);EditorUtility.SetDirty(value);return value;}
        private static string Digest(string path){using(var sha=SHA256.Create())using(var stream=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
    }
}
