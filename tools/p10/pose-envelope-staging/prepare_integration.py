"""Stage hash-guarded renderer changes; never writes live Client source."""
from pathlib import Path
import difflib
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'Candidate'
OUT.mkdir(exist_ok=True)
baseline=json.loads((HERE/'production-before.json').read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert all(sha(ROOT/path)==digest for path,digest in baseline['sources'].items()),'Frozen source changed'
def replace(text,old,new):
    assert text.count(old)==1,old[:80]
    return text.replace(old,new)
stage_path='Assets/RacingBois/Client/Presentation/RaceStageView.cs'
stage=(ROOT/stage_path).read_text(encoding='utf-8-sig')
stage=replace(stage,'        private float impactShake;', '''        private float impactShake;
        private PresentationContinuityScope previousContinuityScope;
        private bool usedNetworkContinuity, cameraUsedVisualOffset, localVisualRebased, localVisualReset;
        private Vector3 localVisualOffset, localBikeVisualOffset, localVisualShift, previousCameraVisualOffset;
        public float LocalVisualCorrectionMeters => localVisualOffset.magnitude;
        public float LocalBikeVisualCorrectionMeters => localBikeVisualOffset.magnitude;
        public double LocalVisualCorrectionRemainingSeconds { get; private set; }
        public VisualPoseResetReason LocalVisualResetReason { get; private set; }
        public int LocalVisualHardResetCount { get; private set; }
        public int LocalVisualReconciliationCount { get; private set; }''')
stage=replace(stage,'bool actorsAlreadyInterpolated=false)','bool actorsAlreadyInterpolated=false,PresentationContinuityScope continuity=default)')
stage=replace(stage,'            if(renderSuspended)return;', '''            if(renderSuspended)return;
            localVisualOffset=localBikeVisualOffset=localVisualShift=Vector3.zero;
            localVisualRebased=localVisualReset=false;LocalVisualResetReason=VisualPoseResetReason.None;LocalVisualCorrectionRemainingSeconds=0;
            bool useContinuity=actorsAlreadyInterpolated&&continuity.IsValid;
            double visualNow=Time.realtimeSinceStartupAsDouble;''')
stage=replace(stage,'            bool reset=active!=wasActive||(world!=null&&world.Tick<lastTick);', '''            bool reset=active!=wasActive||(world!=null&&world.Tick<lastTick)||useContinuity!=usedNetworkContinuity||
                (useContinuity&&!continuity.SameIdentity(previousContinuityScope));
            previousContinuityScope=continuity;usedNetworkContinuity=useContinuity;''')
stage=replace(stage,'RenderRider(view,item,dt,reset,actorsAlreadyInterpolated);','RenderRider(view,item,dt,reset,actorsAlreadyInterpolated,useContinuity&&item.Id==local.Id,continuity,visualNow);')
stage=replace(stage,'UpdateCamera(local,active,dt,reducedMotion);','UpdateCamera(local,active,dt,reducedMotion,useContinuity,continuity.Frozen);')
stage=replace(stage,'private void RenderRider(RiderVisual view,RaceRiderReadModel state,float dt,bool reset,bool interpolated)',
    'private void RenderRider(RiderVisual view,RaceRiderReadModel state,float dt,bool reset,bool interpolated,bool localContinuity,PresentationContinuityScope continuity,double now)')
old='''            float blend=interpolated?1:1-Mathf.Exp(-dt*22);
            if(!view.Initialized||reset){view.Bike.position=bikePoint;view.Bike.rotation=bikeRotation;view.Rider.position=riderPoint;view.Rider.rotation=riderRotation;view.Initialized=true;}
            else
            {
                view.Bike.position=Vector3.Lerp(view.Bike.position,bikePoint,blend);view.Bike.rotation=Quaternion.Slerp(view.Bike.rotation,bikeRotation,blend);
                view.Rider.position=Vector3.Lerp(view.Rider.position,riderPoint,blend);view.Rider.rotation=Quaternion.Slerp(view.Rider.rotation,riderRotation,blend);
            }'''
new='''            float blend=interpolated?1:1-Mathf.Exp(-dt*22);
            if(localContinuity)
            {
                bool initialize=!view.Initialized||reset||!view.UsedVisualContinuity;
                bool poseChanged=view.VisualDetached!=detached||(!initialize&&continuity.DetachedCorrectionSince(view.VisualCorrectionRevision,detached));
                float riderSpeedBound=Mathf.Clamp(Mathf.Max(Mathf.Abs(view.PreviousVisualSpeed),Mathf.Abs(state.SpeedMetersPerSecond))+10,10,100);
                view.BikeEnvelope.Sample(bikePoint,bikeRotation,now,100,poseChanged,continuity.Frozen,initialize,out var shownBike,out var shownBikeRotation);
                view.RiderEnvelope.Sample(riderPoint,riderRotation,now,riderSpeedBound,poseChanged,continuity.Frozen,initialize,out var shownRider,out var shownRiderRotation);
                view.Bike.SetPositionAndRotation(shownBike,shownBikeRotation);view.Rider.SetPositionAndRotation(shownRider,shownRiderRotation);
                localVisualOffset=view.RiderEnvelope.Offset;localBikeVisualOffset=view.BikeEnvelope.Offset;
                localVisualShift=view.RiderEnvelope.RawTargetShift;localVisualRebased=view.RiderEnvelope.BeganReconciliation;
                localVisualReset=view.RiderEnvelope.ResetThisSample;
                LocalVisualResetReason=view.RiderEnvelope.ResetReason;
                LocalVisualHardResetCount=view.RiderEnvelope.HardResetCount+view.BikeEnvelope.HardResetCount;
                LocalVisualCorrectionRemainingSeconds=Math.Max(view.RiderEnvelope.RemainingSeconds,view.BikeEnvelope.RemainingSeconds);
                if(localVisualRebased)LocalVisualReconciliationCount++;
                view.UsedVisualContinuity=true;view.Initialized=true;
            }
            else
            {
                view.UsedVisualContinuity=false;
                if(!view.Initialized||reset){view.Bike.position=bikePoint;view.Bike.rotation=bikeRotation;view.Rider.position=riderPoint;view.Rider.rotation=riderRotation;view.Initialized=true;}
                else
                {
                    view.Bike.position=Vector3.Lerp(view.Bike.position,bikePoint,blend);view.Bike.rotation=Quaternion.Slerp(view.Bike.rotation,bikeRotation,blend);
                    view.Rider.position=Vector3.Lerp(view.Rider.position,riderPoint,blend);view.Rider.rotation=Quaternion.Slerp(view.Rider.rotation,riderRotation,blend);
                }
            }
            view.VisualDetached=detached;view.PreviousVisualSpeed=state.SpeedMetersPerSecond;view.VisualCorrectionRevision=continuity.CorrectionRevision;'''
stage=replace(stage,old,new)
stage=replace(stage,'private void UpdateCamera(RaceRiderReadModel local,bool active,float dt,bool reduced)',
    'private void UpdateCamera(RaceRiderReadModel local,bool active,float dt,bool reduced,bool online,bool frozen)')
stage=replace(stage,'            float s=active?local.LongitudinalMeters:7;', '''            if(active&&online&&frozen&&cameraInitialized)return;
            if(localVisualReset)cameraInitialized=false;
            float s=active?local.LongitudinalMeters:7;''')
stage=replace(stage,'''            float blend=cameraInitialized?1-Mathf.Exp(-dt*7):1;
            ViewCamera.transform.SetPositionAndRotation(Vector3.Lerp(ViewCamera.transform.position,position,blend),Quaternion.Slerp(ViewCamera.transform.rotation,rotation,blend));''',
'''            bool useOffset=active&&online;
            if(useOffset!=cameraUsedVisualOffset){cameraInitialized=false;previousCameraVisualOffset=Vector3.zero;}
            Vector3 previous=ViewCamera.transform.position;
            if(cameraInitialized&&useOffset)
            {
                previous-=previousCameraVisualOffset;
                if(localVisualRebased)previous+=localVisualShift;
            }
            float blend=cameraInitialized?1-Mathf.Exp(-dt*7):1;
            Vector3 shown=Vector3.Lerp(previous,position,blend)+(useOffset?localVisualOffset:Vector3.zero);
            ViewCamera.transform.SetPositionAndRotation(shown,Quaternion.Slerp(ViewCamera.transform.rotation,rotation,blend));
            previousCameraVisualOffset=useOffset?localVisualOffset:Vector3.zero;cameraUsedVisualOffset=useOffset;''')
stage=replace(stage,'            public WeaponGripView Weapon;', '''            public readonly UnityVisualPoseEnvelope RiderEnvelope=new UnityVisualPoseEnvelope(),BikeEnvelope=new UnityVisualPoseEnvelope();
            public bool UsedVisualContinuity,VisualDetached;
            public long VisualCorrectionRevision;
            public float PreviousVisualSpeed;
            public WeaponGripView Weapon;''')
bootstrap_path='Assets/RacingBois/Client/Bootstrap/RaceBootstrap.cs'
bootstrap=(ROOT/bootstrap_path).read_text(encoding='utf-8-sig')
bootstrap=replace(bootstrap,'Stage.RenderFrame(world,local,renderingRace,dt,screen.ReducedMotion,useMultiplayer);',
'''var continuity=useMultiplayer&&multiplayer.Room!=null?
                    new PresentationContinuityScope(multiplayer.PresentationSessionEpoch,multiplayer.Room.RaceEpoch,multiplayer.Room.RoomId,multiplayer.RiderId,
                        multiplayer.PresentationFrozen||multiplayer.IsReconnecting||multiplayer.IsSuspended,multiplayer.PresentationCorrectionRevision,multiplayer.LastCorrectionMeters):default;
                Stage.RenderFrame(world,local,renderingRace,dt,screen.ReducedMotion,useMultiplayer,continuity);''')
session_path='Assets/RacingBois/Client/Application/MultiplayerSession.cs'
session=(ROOT/session_path).read_text(encoding='utf-8-sig')
session=replace(session,'        public string SessionId => PlayerId;', '''        public string SessionId => PlayerId;
        /// <summary>Lease identity for resetting renderer-only continuity; grants no authority.</summary>
        public int PresentationSessionEpoch => sessionEpoch;''')
session=replace(session,'        public float LastCorrectionMeters { get; private set; }', '''        public float LastCorrectionMeters { get; private set; }
        /// <summary>Changes only for a measured equal-target prediction correction, not ordinary snapshots.</summary>
        public long PresentationCorrectionRevision { get; private set; }''')
session=replace(session,'            MaximumCorrectionMeters = 0;','            MaximumCorrectionMeters = 0; PresentationCorrectionRevision = 0;')
messages_path='Assets/RacingBois/Client/Application/MultiplayerSession.Messages.cs'
messages=(ROOT/messages_path).read_text(encoding='utf-8-sig')
messages=replace(messages,'                MaximumCorrectionMeters = Math.Max(MaximumCorrectionMeters, LastCorrectionMeters);',
    '                MaximumCorrectionMeters = Math.Max(MaximumCorrectionMeters, LastCorrectionMeters);\n                PresentationCorrectionRevision++;')
rows=[];patch=[]
for path,text in [(stage_path,stage),(bootstrap_path,bootstrap),(session_path,session),(messages_path,messages)]:
    destination=OUT/Path(path).name;destination.write_text(text,encoding='utf-8',newline='\n')
    rows.append({'target':path,'beforeSha256':sha(ROOT/path),'candidate':destination.relative_to(ROOT).as_posix(),'candidateSha256':sha(destination)})
    patch.extend(difflib.unified_diff((ROOT/path).read_text(encoding='utf-8-sig').splitlines(True),text.splitlines(True),fromfile=path,tofile=destination.relative_to(ROOT).as_posix()))
for name in ['VisualPoseEnvelope.cs','UnityVisualPoseEnvelope.cs','PresentationContinuityScope.cs']:
    rows.append({'target':'Assets/RacingBois/Client/Presentation/'+name,'beforeSha256':None,'candidate':(HERE/name).relative_to(ROOT).as_posix(),'candidateSha256':sha(HERE/name)})
(HERE/'candidate-manifest.json').write_text(json.dumps({'schema':1,'productionApplied':False,'files':rows},indent=2)+'\n')
(HERE/'review.diff').write_text(''.join(patch))
assert all(sha(ROOT/path)==digest for path,digest in baseline['sources'].items())
print('Staged4 modified files +3 new presentation files;163 frozen source paths unchanged.')
