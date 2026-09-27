"""Stage a reviewable renderer-only integration; never writes Assets or starts Unity."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
source=ROOT/'Assets/RacingBois/Client/Presentation/RaceStageView.cs'
text=source.read_text(encoding='utf-8');original=text
def replace(old,new):
    global text
    if text.count(old)!=1:raise RuntimeError('Renderer anchor missing/ambiguous: '+old[:80])
    text=text.replace(old,new)
replace('        private float impactShake;', '''        private float impactShake;
        private Vector3 localVisualOffset, localBikeVisualOffset, localVisualShift, previousCameraVisualOffset;
        private bool localVisualRebased, cameraUsedVisualOffset;
        public float LocalVisualCorrectionMeters => localVisualOffset.magnitude;
        public float LocalBikeVisualCorrectionMeters => localBikeVisualOffset.magnitude;
        public int LocalVisualReconciliationCount { get; private set; }
        public bool TryGetRenderedActorPose(int id,out Vector3 rider,out Vector3 bike)
        {
            if(riders.TryGetValue(id,out var view)&&view.Initialized)
            {rider=view.Rider.position;bike=view.Bike.position;return true;}
            rider=bike=Vector3.zero;return false;
        }''')
replace('bool actorsAlreadyInterpolated=false)', 'bool actorsAlreadyInterpolated=false,bool presentationFrozen=false)')
replace('            if(renderSuspended)return;', '''            if(renderSuspended)return;
            localVisualOffset=localBikeVisualOffset=localVisualShift=Vector3.zero;localVisualRebased=false;''')
replace('RenderRider(view,item,dt,reset,actorsAlreadyInterpolated);','RenderRider(view,item,dt,reset,actorsAlreadyInterpolated,item.Id==local.Id,presentationFrozen);')
replace('UpdateCamera(local,active,dt,reducedMotion);','UpdateCamera(local,active,dt,reducedMotion,actorsAlreadyInterpolated);')
replace('private void RenderRider(RiderVisual view,RaceRiderReadModel state,float dt,bool reset,bool interpolated)',
        'private void RenderRider(RiderVisual view,RaceRiderReadModel state,float dt,bool reset,bool interpolated,bool isLocal,bool frozen)')
old='''            float blend=interpolated?1:1-Mathf.Exp(-dt*22);
            if(!view.Initialized||reset){view.Bike.position=bikePoint;view.Bike.rotation=bikeRotation;view.Rider.position=riderPoint;view.Rider.rotation=riderRotation;view.Initialized=true;}
            else
            {
                view.Bike.position=Vector3.Lerp(view.Bike.position,bikePoint,blend);view.Bike.rotation=Quaternion.Slerp(view.Bike.rotation,bikeRotation,blend);
                view.Rider.position=Vector3.Lerp(view.Rider.position,riderPoint,blend);view.Rider.rotation=Quaternion.Slerp(view.Rider.rotation,riderRotation,blend);
            }'''
new='''            float blend=interpolated?1:1-Mathf.Exp(-dt*22);
            if(interpolated&&isLocal)
            {
                bool initialize=!view.Initialized||reset||!view.UsedVisualReconciliation;
                bool changed=view.VisualMode!=state.Mode;
                view.BikeContinuity.Sample(bikePoint,bikeRotation,dt,changed,frozen,initialize,out var shownBike,out var shownBikeRotation);
                view.RiderContinuity.Sample(riderPoint,riderRotation,dt,changed,frozen,initialize,out var shownRider,out var shownRiderRotation);
                view.Bike.SetPositionAndRotation(shownBike,shownBikeRotation);view.Rider.SetPositionAndRotation(shownRider,shownRiderRotation);
                localVisualOffset=view.RiderContinuity.Offset;localBikeVisualOffset=view.BikeContinuity.Offset;
                localVisualShift=view.RiderContinuity.RawTargetShift;localVisualRebased=view.RiderContinuity.BeganReconciliation;
                if(localVisualRebased)LocalVisualReconciliationCount++;
                view.UsedVisualReconciliation=true;view.Initialized=true;
            }
            else
            {
                view.UsedVisualReconciliation=false;
                if(!view.Initialized||reset){view.Bike.position=bikePoint;view.Bike.rotation=bikeRotation;view.Rider.position=riderPoint;view.Rider.rotation=riderRotation;view.Initialized=true;}
                else
                {
                    view.Bike.position=Vector3.Lerp(view.Bike.position,bikePoint,blend);view.Bike.rotation=Quaternion.Slerp(view.Bike.rotation,bikeRotation,blend);
                    view.Rider.position=Vector3.Lerp(view.Rider.position,riderPoint,blend);view.Rider.rotation=Quaternion.Slerp(view.Rider.rotation,riderRotation,blend);
                }
            }
            view.VisualMode=state.Mode;'''
replace(old,new)
replace('private void UpdateCamera(RaceRiderReadModel local,bool active,float dt,bool reduced)',
        'private void UpdateCamera(RaceRiderReadModel local,bool active,float dt,bool reduced,bool online)')
replace('''            float blend=cameraInitialized?1-Mathf.Exp(-dt*7):1;
            ViewCamera.transform.SetPositionAndRotation(Vector3.Lerp(ViewCamera.transform.position,position,blend),Quaternion.Slerp(ViewCamera.transform.rotation,rotation,blend));''',
'''            bool useVisualOffset=active&&online;
            if(useVisualOffset!=cameraUsedVisualOffset){cameraInitialized=false;previousCameraVisualOffset=Vector3.zero;}
            Vector3 previous=ViewCamera.transform.position;
            if(cameraInitialized&&useVisualOffset)
            {
                // Rebase the camera's raw filter coordinate, then apply the same local
                // display offset. A correction must not leave the camera20m ahead of its actor.
                previous-=previousCameraVisualOffset;
                if(localVisualRebased)previous+=localVisualShift;
            }
            float blend=cameraInitialized?1-Mathf.Exp(-dt*7):1;
            Vector3 shown=Vector3.Lerp(previous,position,blend)+(useVisualOffset?localVisualOffset:Vector3.zero);
            ViewCamera.transform.SetPositionAndRotation(shown,Quaternion.Slerp(ViewCamera.transform.rotation,rotation,blend));
            previousCameraVisualOffset=useVisualOffset?localVisualOffset:Vector3.zero;cameraUsedVisualOffset=useVisualOffset;''')
replace('''            public WeaponGripView Weapon;''','''            public readonly UnityVisualTransformReconciler BikeContinuity=new UnityVisualTransformReconciler(),RiderContinuity=new UnityVisualTransformReconciler();
            public bool UsedVisualReconciliation;
            public RiderMode VisualMode;
            public WeaponGripView Weapon;''')
output=HERE/'UnityStage';output.mkdir(exist_ok=True)
(output/'RaceStageView.cs').write_text(text,encoding='utf-8')
bootstrap=ROOT/'Assets/RacingBois/Client/Bootstrap/RaceBootstrap.cs'
line='Stage.RenderFrame(world,local,renderingRace,dt,screen.ReducedMotion,useMultiplayer);'
assert bootstrap.read_text(encoding='utf-8').count(line)==1
(HERE/'bootstrap-callsite.txt').write_text('Replace only this presentation call after review:\n'+line+'\nWith:\n'+line.replace('useMultiplayer);','useMultiplayer,useMultiplayer&&multiplayer.PresentationFrozen);')+'\n')
receipt={'source':source.relative_to(ROOT).as_posix(),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'staged':(output/'RaceStageView.cs').relative_to(ROOT).as_posix(),'stagedSha256':hashlib.sha256((output/'RaceStageView.cs').read_bytes()).hexdigest(),'bootstrapSourceSha256':hashlib.sha256(bootstrap.read_bytes()).hexdigest(),'productionWritten':False,'nativeUnityExecuted':False}
(HERE/'integration-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
