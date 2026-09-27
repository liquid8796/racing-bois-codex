using System;
using System.Collections.Generic;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    /// <summary>Transforms and effects follow immutable authority state; colliders here never decide gameplay.</summary>
    public sealed class RaceStageView : MonoBehaviour
    {
        public TrackRibbonView Road;
        public Camera ViewCamera;
        public GameObject MotorcyclePrefab, PoliceMotorcyclePrefab, RiderPrefab, CoupePrefab, VanPrefab, PedestrianPrefab;
        public GameObject PoliceRiderPrefab;
        public GameObject ClubPrefab;
        public AnimationClip[] RiderClips;
        public Material SparkMaterial;
        public bool UseExternalEffects;
        private readonly Dictionary<int,RiderVisual> riders=new Dictionary<int,RiderVisual>(GameplayRules.MaxRiders);
        private readonly Dictionary<int,TrafficVisual> traffic=new Dictionary<int,TrafficVisual>(GameplayRules.MaxTraffic);
        private readonly Dictionary<int,RiderVisual> pedestrians=new Dictionary<int,RiderVisual>(GameplayRules.MaxPedestrians);
        private readonly HashSet<int> activeRiders=new HashSet<int>(GameplayRules.MaxRiders), activeTraffic=new HashSet<int>(GameplayRules.MaxTraffic);
        private readonly HashSet<int> activePedestrians=new HashSet<int>(GameplayRules.MaxPedestrians);
        private readonly List<int> retired=new List<int>(GameplayRules.MaxRiders);
        private readonly Stack<RiderVisual> spareRiders=new Stack<RiderVisual>(GameplayRules.MaxRiders), sparePolice=new Stack<RiderVisual>(GameplayRules.MaxRiders);
        private readonly Stack<TrafficVisual> spareCoupes=new Stack<TrafficVisual>(GameplayRules.MaxTraffic), spareVans=new Stack<TrafficVisual>(GameplayRules.MaxTraffic);
        private readonly Stack<RiderVisual> sparePedestrians=new Stack<RiderVisual>(GameplayRules.MaxPedestrians);
        private MaterialPropertyBlock riderTint;
        private P08ActorContent actorContent;
        private bool renderSuspended;
        private readonly Stack<RiderVisual> familyScratch = new Stack<RiderVisual>(GameplayRules.MaxRiders);
        private readonly List<ParticleSystem> impactPool=new List<ParticleSystem>();
        private RiderVisual menuRider;
        private bool menuPreviewFraming, menuPreviewShowRider = true;
        private float menuPreviewTime;
        public readonly struct MenuPreviewState
        {
            public readonly int BikeIndex, CharacterIndex;
            public readonly bool ShowRider, ShowroomFraming;
            public readonly Vector3 CameraPosition;
            public readonly Quaternion CameraRotation;
            public readonly float CameraFieldOfView;
            public readonly bool HasCamera;
            public MenuPreviewState(int bikeIndex, int characterIndex, bool showRider, bool showroomFraming, Camera camera)
            {
                BikeIndex = bikeIndex; CharacterIndex = characterIndex; ShowRider = showRider; ShowroomFraming = showroomFraming;
                HasCamera = camera != null; CameraPosition = HasCamera ? camera.transform.position : Vector3.zero;
                CameraRotation = HasCamera ? camera.transform.rotation : Quaternion.identity; CameraFieldOfView = HasCamera ? camera.fieldOfView : 46;
            }
        }
        public bool MenuPreviewReady => !renderSuspended && actorContent != null && actorContent == ContentRegistry.Actors && menuRider != null;
        public int MenuPreviewBikeIndex => menuRider == null ? -1 : menuRider.BikeIndex;
        public int MenuPreviewCharacterIndex => menuRider == null ? -1 : menuRider.CharacterIndex;
        private int impactIndex;
        private long lastEventId,lastTick=-1;
        private bool wasActive, cameraInitialized;
        private float impactShake;
        private int riderPoolSize, trafficPoolSize, pedestrianPoolSize;
        public int PoolCreated { get; private set; }
        public int PoolReused { get; private set; }
        public int PoolRebalanced { get; private set; }
        public int RiderPoolSize => riderPoolSize;
        public int TrafficPoolSize => trafficPoolSize;
        public int PedestrianPoolSize => pedestrianPoolSize;
        public int ActiveRiderCount => riders.Count;
        public int ActiveTrafficCount => traffic.Count;
        public int ActivePedestrianCount => pedestrians.Count;
        public void Build()
        {
            if(menuRider!=null)return;
            riderTint=new MaterialPropertyBlock();
            Road.Build(TrackDefinition.Default);
            menuRider=CreateRider(-1,false);
            PlaceMenuRider();
            if(!UseExternalEffects)for(int i=0;i<8;i++)impactPool.Add(CreateImpact());
        }
        public MenuPreviewState CaptureMenuPreview()
            => new MenuPreviewState(menuRider == null ? 0 : menuRider.BikeIndex, menuRider == null ? 0 : menuRider.CharacterIndex, menuPreviewShowRider, menuPreviewFraming, ViewCamera);
        /// <summary>Cosmetic inspection only. Unloaded catalog identities and active races cannot change the menu actor.</summary>
        public bool SetMenuPreview(int bikeIndex, int characterIndex, bool showRider = true)
        {
            if (wasActive || !MenuPreviewReady || bikeIndex < 0 || bikeIndex >= ContentRegistry.Bikes.Count || characterIndex < 0 || characterIndex >= ContentRegistry.Riders.Count)
                return false;
            if (menuRider.BikeIndex != bikeIndex || menuRider.CharacterIndex != characterIndex)
            {
                menuRider.Bike.gameObject.SetActive(false); menuRider.Rider.gameObject.SetActive(false);
                DestroyOwned(menuRider.Bike.gameObject); DestroyOwned(menuRider.Rider.gameObject);
                menuRider = CreateRider(-1, false, bikeIndex, characterIndex);
                PlaceMenuRider();
            }
            bool changed = !menuPreviewFraming || menuPreviewShowRider != showRider;
            menuPreviewFraming = true; menuPreviewShowRider = showRider;
            menuRider.Bike.gameObject.SetActive(true); menuRider.Rider.gameObject.SetActive(showRider);
            if (changed) cameraInitialized = false;
            return true;
        }
        public bool RestoreMenuPreview(MenuPreviewState state)
        {
            if (!SetMenuPreview(state.BikeIndex, state.CharacterIndex, state.ShowRider)) return false;
            menuPreviewShowRider = state.ShowRider; menuPreviewFraming = state.ShowroomFraming;
            menuPreviewTime = 0; cameraInitialized = false;
            if(state.HasCamera&&ViewCamera!=null){ViewCamera.transform.SetPositionAndRotation(state.CameraPosition,state.CameraRotation);ViewCamera.fieldOfView=state.CameraFieldOfView;}
            return true;
        }
        private void PlaceMenuRider()
        {
            if (menuRider == null) return;
            menuRider.Bike.position = Road.Point(7, 2.4f);
            menuRider.Bike.rotation = Road.Heading(7) * Quaternion.Euler(0, -12, 0);
            menuRider.Rider.position = menuRider.Bike.position + menuRider.Bike.rotation * new Vector3(0, -.08f, -.32f);
            menuRider.Rider.rotation = menuRider.Bike.rotation;
            Pose(menuRider, RiderMode.Riding, 0, 0, 0, 0, false);
            menuRider.Weapon?.ResetPose();
        }
        private static void DisablePhysics(GameObject obj)
        {
            foreach(var collider in obj.GetComponentsInChildren<Collider>(true))collider.enabled=false;
            foreach(var child in obj.GetComponentsInChildren<Transform>(true))child.gameObject.isStatic=false;
        }
        private RiderVisual CreateRider(int id,bool police,int bikeIndex=0,int characterIndex=0)
        {
            var bikePrefab=police?PoliceMotorcyclePrefab:actorContent!=null?actorContent.Bikes[bikeIndex]:MotorcyclePrefab;
            var riderPrefab=police&&PoliceRiderPrefab!=null?PoliceRiderPrefab:actorContent!=null?actorContent.Riders[characterIndex]:RiderPrefab;
            var bike=Instantiate(bikePrefab,transform);
            var rider=Instantiate(riderPrefab,transform);
            bike.name="Bike_"+id;rider.name="Rider_"+id;DisablePhysics(bike);DisablePhysics(rider);
            var visual=new RiderVisual(bike.transform,rider.transform);
            var riderClips = RiderAnimationSet.Resolve(rider.transform, RiderClips);
            if(riderClips!=null&&riderClips.Length>0)
            {
                var animation=rider.AddComponent<RiderAnimationView>();
                if(animation.Initialize(rider.transform,riderClips))visual.Animation=animation;
            }
            visual.IsPolice=police;visual.BikeIndex=bikeIndex;visual.CharacterIndex=characterIndex;
            ApplyRiderIdentity(visual,id);
            visual.Weapon = rider.AddComponent<WeaponGripView>();
            visual.Weapon.Initialize(ClubPrefab,rider.transform);
            return visual;
        }
        private void ApplyRiderIdentity(RiderVisual visual,int id)
        {
            visual.Bike.name="Bike_"+id;visual.Rider.name="Rider_"+id;
            riderTint.Clear();
            if(actorContent==null&&id>0&&!visual.IsPolice)riderTint.SetColor("_BaseColor",Color.HSVToRGB((id%7)*.14f,.25f,1));
            foreach(var renderer in visual.TintRenderers)renderer.SetPropertyBlock(actorContent==null&&id>0&&!visual.IsPolice?riderTint:null);
        }
        private RiderVisual AcquireRider(int id,bool police,int bikeIndex,int characterIndex)
        {
            var pool=police?sparePolice:spareRiders;
            RiderVisual view=null;
            while(pool.Count>0)
            {
                var candidate=pool.Pop();
                if(candidate.BikeIndex==bikeIndex&&candidate.CharacterIndex==characterIndex){view=candidate;break;}
                familyScratch.Push(candidate);
            }
            while(familyScratch.Count>0)pool.Push(familyScratch.Pop());
            if(view!=null){PoolReused++;ApplyRiderIdentity(view,id);}
            else
            {
                if(riderPoolSize>=GameplayRules.MaxRiders)
                {
                    var other=police?spareRiders:sparePolice;
                    if(other.Count==0&&pool.Count==0)return null;
                    var obsolete=pool.Count>0?pool.Pop():other.Pop();DestroyOwned(obsolete.Bike.gameObject);DestroyOwned(obsolete.Rider.gameObject);
                    riderPoolSize--;PoolRebalanced++;
                }
                view=CreateRider(id,police,bikeIndex,characterIndex);riderPoolSize++;PoolCreated++;
            }
            view.Bike.gameObject.SetActive(true);view.Rider.gameObject.SetActive(true);
            view.Initialized=false;view.WheelAngle=0;
            foreach(var wheel in view.Wheels)wheel.localRotation=view.WheelRest[wheel];
            foreach(var bone in view.Bones)bone.Value.localRotation=view.Rest[bone.Key];
            if(view.Animation!=null)view.Animation.ResetPose();
            if(view.Weapon!=null)view.Weapon.ResetPose();
            return view;
        }
        private void ReleaseRider(RiderVisual view)
        {
            view.Initialized=false;view.Bike.gameObject.SetActive(false);view.Rider.gameObject.SetActive(false);
            (view.IsPolice?sparePolice:spareRiders).Push(view);
        }
        private TrafficVisual AcquireTraffic(int id,bool van)
        {
            var pool=van?spareVans:spareCoupes;TrafficVisual view;
            if(pool.Count>0){view=pool.Pop();PoolReused++;}
            else
            {
                if(trafficPoolSize>=GameplayRules.MaxTraffic)
                {
                    var other=van?spareCoupes:spareVans;
                    if(other.Count==0)return null;
                    DestroyOwned(other.Pop().Root.gameObject);trafficPoolSize--;PoolRebalanced++;
                }
                var obj=Instantiate(van?VanPrefab:CoupePrefab,transform);DisablePhysics(obj);
                view=new TrafficVisual(obj.transform,van);trafficPoolSize++;PoolCreated++;
            }
            view.Root.name="Traffic_"+id;view.Initialized=false;view.Root.gameObject.SetActive(true);return view;
        }
        private RiderVisual AcquirePedestrian(int id)
        {
            RiderVisual view;
            if(sparePedestrians.Count>0){view=sparePedestrians.Pop();PoolReused++;}
            else
            {
                if(pedestrianPoolSize>=GameplayRules.MaxPedestrians)return null;
                var obj=Instantiate(PedestrianPrefab,transform);DisablePhysics(obj);
                view=new RiderVisual(null,obj.transform);pedestrianPoolSize++;PoolCreated++;
            }
            view.Rider.name="Pedestrian_"+id;view.Initialized=false;view.Rider.gameObject.SetActive(true);
            foreach(var bone in view.Bones)bone.Value.localRotation=view.Rest[bone.Key];
            return view;
        }
        public void ResetInterpolation()
        {
            cameraInitialized=false;
            foreach(var view in riders.Values)view.Initialized=false;
            foreach(var view in pedestrians.Values)view.Initialized=false;
            foreach(var view in traffic.Values)view.Initialized=false;
        }
        public void RenderFrame(RaceWorldReadModel world,RaceRiderReadModel local,bool active,float dt,bool reducedMotion,bool actorsAlreadyInterpolated=false)
        {
            if(renderSuspended)return;
            if(active&&world!=null&&actorContent!=null&&(Road.CourseIndex!=world.CourseIndex||Road.LevelIndex!=world.Level))
            {
                if(!ContentRegistry.ReadyFor(world.CourseIndex))throw new InvalidOperationException("Race content is not loaded.");
                Road.ApplyContent(ContentRegistry.Route,world.Level);ResetInterpolation();
            }
            bool reset=active!=wasActive||(world!=null&&world.Tick<lastTick);
            if(reset){cameraInitialized=false;lastEventId=0;impactShake=0;}
            wasActive=active;
            if(menuRider!=null){menuRider.Bike.gameObject.SetActive(!active);menuRider.Rider.gameObject.SetActive(!active&&menuPreviewShowRider);}
            activeRiders.Clear();activeTraffic.Clear();activePedestrians.Clear();
            int riderCount=active&&world!=null?Mathf.Min(world.Riders.Count,GameplayRules.MaxRiders):0;
            int trafficCount=active&&world!=null?Mathf.Min(world.Traffic.Count,GameplayRules.MaxTraffic):0;
            int pedestrianCount=active&&world!=null?Mathf.Min(world.Pedestrians.Count,GameplayRules.MaxPedestrians):0;
            for(int i=0;i<riderCount;i++)activeRiders.Add(world.Riders[i].Id);
            for(int i=0;i<trafficCount;i++)activeTraffic.Add(world.Traffic[i].Id);
            for(int i=0;i<pedestrianCount;i++)activePedestrians.Add(world.Pedestrians[i].Id);
            // Return departed interest entries first, so replacements in this same frame can reuse them.
            RetireViews();
            if(active&&world!=null)
            {
                lastTick=world.Tick;
                for(int riderIndex=0;riderIndex<riderCount;riderIndex++)
                {
                    var published=world.Riders[riderIndex];
                    var item=published.Id==local.Id?local:published;
                    bool police=item.Kind==RiderKind.Police;
                    if(riders.TryGetValue(item.Id,out var view)&&(view.IsPolice!=police||view.BikeIndex!=item.BikeCatalogIndex||view.CharacterIndex!=item.CharacterCatalogIndex))
                    {
                        ReleaseRider(view);riders.Remove(item.Id);view=null;
                    }
                    if(view==null)
                    {
                        view=AcquireRider(item.Id,police,item.BikeCatalogIndex,item.CharacterCatalogIndex);if(view==null)continue;
                        riders.Add(item.Id,view);
                    }
                    RenderRider(view,item,dt,reset,actorsAlreadyInterpolated);
                }
                for(int trafficIndex=0;trafficIndex<trafficCount;trafficIndex++)
                {
                    var item=world.Traffic[trafficIndex];
                    if(traffic.TryGetValue(item.Id,out var view)&&view.IsVan!=item.IsVan)
                    {
                        ReleaseTraffic(view);traffic.Remove(item.Id);view=null;
                    }
                    if(view==null)
                    {
                        view=AcquireTraffic(item.Id,item.IsVan);if(view==null)continue;
                        traffic.Add(item.Id,view);
                    }
                    var point=Road.Point(item.LongitudinalMeters,item.LateralMeters);
                    view.Root.position=!view.Initialized||reset||actorsAlreadyInterpolated?point:Vector3.Lerp(view.Root.position,point,1-Mathf.Exp(-dt*18));
                    view.Root.rotation=Road.Heading(item.LongitudinalMeters)*Quaternion.Euler(0,item.SpeedMetersPerSecond<0?180:0,0);
                    view.Initialized=true;
                }
                for(int eventIndex=0;eventIndex<world.Events.Count;eventIndex++)
                {
                    var item=world.Events[eventIndex];
                    if(item.Id<=lastEventId)continue;lastEventId=item.Id;
                    if((item.Kind==RaceEventKind.Hit||item.Kind==RaceEventKind.Crash||item.Kind==RaceEventKind.Landed)&&
                        riders.TryGetValue(item.TargetId>0?item.TargetId:item.SourceId,out var target))
                    {
                        if(!UseExternalEffects&&impactPool.Count>0)
                        {
                            var fx=impactPool[impactIndex++%impactPool.Count];
                            fx.transform.position=target.Rider.position+Vector3.up*.65f;fx.Play();
                        }
                        if(item.TargetId==local.Id||item.SourceId==local.Id)impactShake=.16f;
                    }
                }
                for(int pedestrianIndex=0;pedestrianIndex<pedestrianCount;pedestrianIndex++)
                {
                    var item=world.Pedestrians[pedestrianIndex];
                    if(!pedestrians.TryGetValue(item.Id,out var view))
                    {
                        view=AcquirePedestrian(item.Id);if(view==null)continue;
                        pedestrians.Add(item.Id,view);
                    }
                    var position=Road.Point(item.LongitudinalMeters,item.LateralMeters,item.HeightMeters);
                    if(item.Mode==PedestrianMode.Stumbled)position.y-=.3f;
                    view.Rider.position=!view.Initialized||reset||actorsAlreadyInterpolated?position:Vector3.Lerp(view.Rider.position,position,1-Mathf.Exp(-dt*18));
                    view.Rider.rotation=Road.Heading(item.LongitudinalMeters)*Quaternion.Euler(0,item.IsCrossing?item.FacingSide*90:item.FacingSide<0?180:0,0);
                    view.Initialized=true;
                    foreach(var bone in view.Bones)bone.Value.localRotation=view.Rest[bone.Key];
                    if(item.Mode==PedestrianMode.Walking)
                    {
                        float swing=Mathf.Sin(item.StateTicks*.13f)*24;
                        Rotate(view,"Thigh_L",swing,0,0);Rotate(view,"Thigh_R",-swing,0,0);
                        Rotate(view,"UpperArm_L",-swing*.65f,0,-5);Rotate(view,"UpperArm_R",swing*.65f,0,5);
                    }
                    else if(item.Mode==PedestrianMode.Stumbled)
                    {
                        Rotate(view,"Hip",35,0,15);Rotate(view,"Thigh_L",-45,0,0);Rotate(view,"Thigh_R",-45,0,0);
                        Rotate(view,"Shin_L",70,0,0);Rotate(view,"Shin_R",70,0,0);Rotate(view,"UpperArm_L",-45,0,-30);
                    }
                    else Rotate(view,"UpperArm_R",0,0,130+Mathf.Sin(item.StateTicks*.06f)*12);
                }
            }
            UpdateCamera(local,active,dt,reducedMotion);
        }
        public void BeforeContentUnload()
        {
            renderSuspended=true;cameraInitialized=false;
            menuPreviewFraming=false;menuPreviewShowRider=true;menuPreviewTime=0;
            if(menuRider!=null){menuRider.Bike.gameObject.SetActive(false);menuRider.Rider.gameObject.SetActive(false);}
            activeRiders.Clear();activeTraffic.Clear();activePedestrians.Clear();RetireViews();
            Road.ClearContent();RenderSettings.skybox=null;
            if(ViewCamera!=null){ViewCamera.clearFlags=CameraClearFlags.SolidColor;ViewCamera.backgroundColor=new Color(.06f,.07f,.08f);}
        }
        public void ApplyContent(int course,int level)
        {
            if(!ContentRegistry.ReadyFor(course))throw new InvalidOperationException("Complete actor/route content is required.");
            var actors=ContentRegistry.Actors;
            if(actorContent!=actors)
            {
                ClearActorPool();actorContent=actors;
                MotorcyclePrefab=actors.Bikes[0];RiderPrefab=actors.Riders[0];PoliceMotorcyclePrefab=actors.PoliceBike;PoliceRiderPrefab=actors.PoliceRider;
                CoupePrefab=actors.Coupe;VanPrefab=actors.Van;PedestrianPrefab=actors.Pedestrian;ClubPrefab=actors.Club;RiderClips=actors.RiderClips;
                menuRider=CreateRider(-1,false);
            }
            var route=ContentRegistry.Route;Road.ApplyContent(route,level);
            RenderSettings.skybox=route.Skybox;RenderSettings.fog=true;RenderSettings.fogMode=FogMode.ExponentialSquared;
            RenderSettings.fogColor=route.FogColor;RenderSettings.fogDensity=route.FogDensity;
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat;RenderSettings.ambientLight=route.AmbientColor;
            if(RenderSettings.sun!=null){RenderSettings.sun.color=route.SunColor;RenderSettings.sun.intensity=route.SunIntensity;RenderSettings.sun.transform.rotation=Quaternion.Euler(route.SunEuler);}
            if(ViewCamera!=null){ViewCamera.clearFlags=CameraClearFlags.Skybox;ViewCamera.backgroundColor=route.FogColor;}
            PlaceMenuRider();
            renderSuspended=false;ResetInterpolation();
        }
        private void ClearActorPool()
        {
            var all=new HashSet<RiderVisual>();if(menuRider!=null)all.Add(menuRider);
            foreach(var value in riders.Values)all.Add(value);foreach(var value in pedestrians.Values)all.Add(value);
            foreach(var value in spareRiders)all.Add(value);foreach(var value in sparePolice)all.Add(value);foreach(var value in sparePedestrians)all.Add(value);
            foreach(var value in all){if(value.Bike!=null)DestroyOwned(value.Bike.gameObject);if(value.Rider!=null)DestroyOwned(value.Rider.gameObject);}
            foreach(var value in traffic.Values)DestroyOwned(value.Root.gameObject);foreach(var value in spareCoupes)DestroyOwned(value.Root.gameObject);foreach(var value in spareVans)DestroyOwned(value.Root.gameObject);
            riders.Clear();traffic.Clear();pedestrians.Clear();spareRiders.Clear();sparePolice.Clear();sparePedestrians.Clear();spareCoupes.Clear();spareVans.Clear();
            riderPoolSize=trafficPoolSize=pedestrianPoolSize=0;menuRider=null;
        }
        private void ReleaseTraffic(TrafficVisual view)
        {
            view.Initialized=false;view.Root.gameObject.SetActive(false);(view.IsVan?spareVans:spareCoupes).Push(view);
        }
        private void RetireViews()
        {
            retired.Clear();foreach(var pair in riders)if(!activeRiders.Contains(pair.Key))retired.Add(pair.Key);
            foreach(int id in retired){ReleaseRider(riders[id]);riders.Remove(id);}
            retired.Clear();foreach(var pair in traffic)if(!activeTraffic.Contains(pair.Key))retired.Add(pair.Key);
            foreach(int id in retired){ReleaseTraffic(traffic[id]);traffic.Remove(id);}
            retired.Clear();foreach(var pair in pedestrians)if(!activePedestrians.Contains(pair.Key))retired.Add(pair.Key);
            foreach(int id in retired)
            {
                var view=pedestrians[id];view.Initialized=false;view.Rider.gameObject.SetActive(false);
                sparePedestrians.Push(view);pedestrians.Remove(id);
            }
            retired.Clear();
        }
        private void RenderRider(RiderVisual view,RaceRiderReadModel state,float dt,bool reset,bool interpolated)
        {
            if(reset)
            {
                view.WheelAngle=0;
                if(view.Animation!=null)view.Animation.ResetPose();
                if(view.Weapon!=null)view.Weapon.ResetPose();
            }
            bool detached=state.Mode==RiderMode.Falling||state.Mode==RiderMode.Detached||state.Mode==RiderMode.Running||
                state.Mode==RiderMode.Remounting||state.Mode==RiderMode.Wrecked;
            float bikeS=detached?state.BikeLongitudinalMeters:state.LongitudinalMeters;
            float bikeD=detached?state.BikeLateralMeters:state.LateralMeters;
            float mounting=state.Mode==RiderMode.Remounting?Mathf.SmoothStep(0,1,state.ModeAgeTicks/(float)GameplayRules.RemountDurationTicks):0;
            float fallBlend=detached?1-mounting:0;
            Vector3 bikePoint=Road.Point(bikeS,bikeD,(detached?state.BikeHeightMeters:state.HeightMeters)+fallBlend*.48f);
            Quaternion bikeRotation=Road.Heading(bikeS)*Quaternion.Euler(0,0,detached?76*fallBlend:state.LeanDegrees);
            Vector3 riderPoint=detached?Road.Point(state.LongitudinalMeters,state.LateralMeters,state.HeightMeters):
                bikePoint+Road.Heading(bikeS)*new Vector3(0,-.08f,-.32f);
            if(state.Mode==RiderMode.Falling||state.Mode==RiderMode.Detached||state.Mode==RiderMode.Wrecked)riderPoint.y+=view.FallenRootOffset;
            if(state.Mode==RiderMode.Remounting)riderPoint=Vector3.Lerp(riderPoint,Road.Point(bikeS,bikeD)+Road.Heading(bikeS)*new Vector3(0,-.08f,-.32f),mounting);
            Quaternion riderRotation=Road.Heading(state.LongitudinalMeters)*Quaternion.Euler(0,0,detached?0:state.LeanDegrees*.65f);
            float blend=interpolated?1:1-Mathf.Exp(-dt*22);
            if(!view.Initialized||reset){view.Bike.position=bikePoint;view.Bike.rotation=bikeRotation;view.Rider.position=riderPoint;view.Rider.rotation=riderRotation;view.Initialized=true;}
            else
            {
                view.Bike.position=Vector3.Lerp(view.Bike.position,bikePoint,blend);view.Bike.rotation=Quaternion.Slerp(view.Bike.rotation,bikeRotation,blend);
                view.Rider.position=Vector3.Lerp(view.Rider.position,riderPoint,blend);view.Rider.rotation=Quaternion.Slerp(view.Rider.rotation,riderRotation,blend);
            }
            view.WheelAngle=Mathf.Repeat(view.WheelAngle+state.SpeedMetersPerSecond*dt/2.0f*360,360);
            foreach(var wheel in view.Wheels)wheel.localRotation=view.WheelRest[wheel]*view.BikeBasisInverse*Quaternion.Euler(view.WheelAngle,0,0)*view.BikeBasis;
            Pose(view,state.Mode,state.AttackSide,state.AttackAgeTicks,state.ModeAgeTicks,state.SpeedMetersPerSecond,state.AttackWeapon==WeaponKind.Kick,state.LeanDegrees);
            view.Weapon.Render(state.Weapon,state.Mode,state.AttackWeapon,state.AttackSide);
        }
        private static void Pose(RiderVisual view,RiderMode mode,int side,int age,int stateAge,float speed,bool kick,float lean=0)
        {
            if(view.Animation!=null)
            {
                view.Animation.Render(mode,side,age,stateAge,speed,kick,lean,Time.unscaledDeltaTime>0?Time.unscaledDeltaTime:1f/60);return;
            }
            foreach(var bone in view.Bones)bone.Value.localRotation=view.Rest[bone.Key];
            bool running=mode==RiderMode.Running;
            bool fallen=mode==RiderMode.Falling||mode==RiderMode.Detached||mode==RiderMode.Wrecked;
            // Rigid articulation is deliberately separate from the gameplay state machine.
            if(running)
            {
                float phase=stateAge*.26f,swing=Mathf.Sin(phase)*34;
                Rotate(view,"Thigh_L",swing,0,0);Rotate(view,"Thigh_R",-swing,0,0);
                Rotate(view,"Shin_L",Mathf.Max(0,-swing),0,0);Rotate(view,"Shin_R",Mathf.Max(0,swing),0,0);
                Rotate(view,"UpperArm_L",-swing,0,-8);Rotate(view,"UpperArm_R",swing,0,8);
                Rotate(view,"Torso",8,0,0);
            }
            else if(fallen)
            {
                Rotate(view,"Hip",0,0,Mathf.Min(82,stateAge*5+30));Rotate(view,"UpperArm_L",-55,0,-55);Rotate(view,"UpperArm_R",-25,0,45);
            }
            else
            {
                Rotate(view,"Hip",0,0,0);Rotate(view,"Torso",18,0,0);
                Rotate(view,"Thigh_L",-62,0,-7);Rotate(view,"Thigh_R",-62,0,7);
                Rotate(view,"Shin_L",90,0,0);Rotate(view,"Shin_R",90,0,0);
                Rotate(view,"UpperArm_L",-48,0,-8);Rotate(view,"UpperArm_R",-48,0,8);
                Rotate(view,"Forearm_L",-35,0,0);Rotate(view,"Forearm_R",-35,0,0);
                if(mode==RiderMode.Attacking)
                {
                    float extension=Mathf.Sin(Mathf.Clamp01(age/(float)GameplayRules.AttackDurationTicks)*Mathf.PI);
                    Rotate(view,side<0?"UpperArm_L":"UpperArm_R",-30,side*30*extension,side*85*extension);
                    Rotate(view,side<0?"Forearm_L":"Forearm_R",-35*(1-extension),0,0);
                    if(kick)Rotate(view,side<0?"Thigh_L":"Thigh_R",-55,0,side*75*extension);
                    Rotate(view,"Torso",12,side*25*extension,0);
                }
            }
            if(mode==RiderMode.Remounting)
            {
                float blend=Mathf.SmoothStep(0,1,stateAge/(float)GameplayRules.RemountDurationTicks);
                foreach(var bone in view.Bones)bone.Value.localRotation=Quaternion.Slerp(view.Rest[bone.Key],bone.Value.localRotation,blend);
            }
        }
        private static void Rotate(RiderVisual view,string name,float x,float y,float z)
        {
            if(!view.Joints.TryGetValue(name,out var joints))return;
            Quaternion pose=view.BasisInverse*Quaternion.Euler(x,y,z)*view.Basis;
            foreach(var bone in joints)bone.localRotation=view.Rest[bone.name]*pose;
        }
        private void UpdateCamera(RaceRiderReadModel local,bool active,float dt,bool reduced)
        {
            float s=active?local.LongitudinalMeters:7;
            var heading=Road.Heading(s);
            Vector3 anchor=active?Road.Point(s,local.LateralMeters,Mathf.Min(1.5f,local.HeightMeters)):Road.Point(7,2.4f);
            Vector3 position=active?anchor+heading*new Vector3(0,2.65f,-6.5f):anchor+new Vector3(3.0f,1.45f,2.9f);
            Vector3 look=active?Road.Point(s+17,local.LateralMeters*.5f,1.1f):anchor+Vector3.up*.9f;
            if(!active&&menuPreviewFraming&&MenuPreviewReady)
            {
                if(!reduced)menuPreviewTime+=Mathf.Clamp(dt,0,.1f);
                float angle=Mathf.Sin(menuPreviewTime*.18f)*5;
                position=anchor+heading*Quaternion.Euler(0,angle,0)*new Vector3(3.3f,menuPreviewShowRider?1.95f:1.35f,3.5f);
                Vector3 subject=anchor+Vector3.up*(menuPreviewShowRider?.85f:.58f);
                // The camera looks beside the actor so the real model occupies the right two thirds of the flat garage layout.
                Vector3 cameraRight=Quaternion.LookRotation(subject-position,Vector3.up)*Vector3.right;
                look=subject-cameraRight*1.15f;
            }
            position.y=Mathf.Max(position.y,Road.Point(s-7).y+1.5f);
            impactShake=Mathf.MoveTowards(impactShake,0,dt*.55f);
            if(!reduced&&active)position+=ViewCamera.transform.right*(Mathf.Sin(Time.unscaledTime*71)*impactShake);
            Quaternion rotation=Quaternion.LookRotation(look-position,Vector3.up);
            float blend=cameraInitialized?1-Mathf.Exp(-dt*7):1;
            ViewCamera.transform.SetPositionAndRotation(Vector3.Lerp(ViewCamera.transform.position,position,blend),Quaternion.Slerp(ViewCamera.transform.rotation,rotation,blend));
            ViewCamera.fieldOfView=Mathf.Lerp(ViewCamera.fieldOfView,active?(reduced?58:60+Mathf.Clamp01(local.SpeedMetersPerSecond/58)*8):menuPreviewFraming?40:46,1-Mathf.Exp(-dt*3));
            cameraInitialized=true;
        }
        private ParticleSystem CreateImpact()
        {
            var obj=new GameObject("Impact pool");obj.transform.SetParent(transform);
            var ps=obj.AddComponent<ParticleSystem>();ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            var main=ps.main;main.loop=false;main.playOnAwake=false;main.duration=.3f;main.startLifetime=.3f;main.startSpeed=3;
            main.startSize=.045f;main.startColor=new Color(1,.67f,.25f);main.gravityModifier=.5f;main.maxParticles=14;
            var emission=ps.emission;emission.rateOverTime=0;emission.SetBursts(new[]{new ParticleSystem.Burst(0,10)});
            var shape=ps.shape;shape.shapeType=ParticleSystemShapeType.Sphere;shape.radius=.25f;
            obj.GetComponent<ParticleSystemRenderer>().sharedMaterial=SparkMaterial;
            return ps;
        }
        private static void DestroyOwned(UnityEngine.Object value)
        {
            if(value==null)return;
            if(UnityEngine.Application.isPlaying)UnityEngine.Object.Destroy(value);else UnityEngine.Object.DestroyImmediate(value);
        }
        private sealed class RiderVisual
        {
            public WeaponGripView Weapon;
            public RiderAnimationView Animation;
            public readonly Transform Bike,Rider;
            public readonly float FallenRootOffset;
            // Captured before the weapon is attached, so tint never leaks onto club materials.
            public readonly Renderer[] TintRenderers;
            public bool IsPolice;
            public int BikeIndex,CharacterIndex;
            public readonly Quaternion Basis,BasisInverse,BikeBasis,BikeBasisInverse;
            public readonly Dictionary<string,Transform> Bones=new Dictionary<string,Transform>();
            public readonly Dictionary<string,Quaternion> Rest=new Dictionary<string,Quaternion>();
            public readonly Dictionary<string,List<Transform>> Joints=new Dictionary<string,List<Transform>>();
            public readonly List<Transform> Wheels=new List<Transform>();
            public readonly Dictionary<Transform,Quaternion> WheelRest=new Dictionary<Transform,Quaternion>();
            public bool Initialized;public float WheelAngle;
            public RiderVisual(Transform bike,Transform rider)
            {
                Bike=bike;Rider=rider;FallenRootOffset=RiderAnimationSet.ResolveFallenRootOffset(rider);
                TintRenderers=rider.GetComponentsInChildren<Renderer>(true);
                var model=rider.Find("Model");Basis=model==null?Quaternion.identity:model.localRotation;BasisInverse=Quaternion.Inverse(Basis);
                var bikeModel=bike==null?null:bike.Find("Model");BikeBasis=bikeModel==null?Quaternion.identity:bikeModel.localRotation;BikeBasisInverse=Quaternion.Inverse(BikeBasis);
                foreach(var part in rider.GetComponentsInChildren<Transform>(true))
                {
                    if(!Bones.ContainsKey(part.name)){Bones.Add(part.name,part);Rest.Add(part.name,part.localRotation);}
                    int lodMarker=part.name.IndexOf("_L",System.StringComparison.Ordinal);
                    if(lodMarker>=0&&part.name.Length>lodMarker+3&&char.IsDigit(part.name[lodMarker+2]))
                    {
                        int separator=part.name.IndexOf('_',lodMarker+2);
                        if(separator<0)continue;
                        string joint=part.name.Substring(separator+1);
                        if(!Joints.TryGetValue(joint,out var siblings)){siblings=new List<Transform>(3);Joints.Add(joint,siblings);}
                        siblings.Add(part);
                    }
                }
                if(bike!=null)foreach(var part in bike.GetComponentsInChildren<Transform>(true))
                    if(part.name.EndsWith("_Wheel_Front")||part.name.EndsWith("_Wheel_Rear")) {Wheels.Add(part);WheelRest.Add(part,part.localRotation);}
            }
        }
        private sealed class TrafficVisual
        {
            public readonly Transform Root;
            public readonly bool IsVan;
            public bool Initialized;
            public TrafficVisual(Transform root,bool van){Root=root;IsVan=van;}
        }
    }
}
