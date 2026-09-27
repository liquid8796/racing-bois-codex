using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using RacingBois.Gameplay.Definitions;
using UnityEngine;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    /// <summary>Opt-in, bounded, no-network camera comparison. No game bootstrap or mutable gameplay object is created.</summary>
    public sealed class PoseEnvelopePreviewRunner:MonoBehaviour
    {
        public GameObject BikePrefab,RiderPrefab;public Camera ReviewCamera;public TextAsset Fixture;
        public Material GroundMaterial,ReferenceMaterial,RawTargetMaterial;
        private PreviewConfiguration config;private PreviewRunReport report;private PreviewFixture fixture;private PreviewCaptureRecorder captures;
        private PreviewActorRig actor;private PreviewGround ground;private PreviewProjection projection;
        private PreviewEnvelopeDriver rider,bike;private PreviewEpisode episode;private StreamWriter samples;
        private readonly List<string> warnings=new List<string>();
        private double began,segmentAt,lastFrameAt,nextSampleAt,lastSampleAt=-1,correctionAt;
        private int episodeIndex,variant,sequence;private bool active,finished,encoding,corrected,beforeCaptured,midCaptured,settledCaptured,initialized,nextSegment;
        private Vector3 previousCameraOffset;private float riderBound;private bool poseChanged;private PreviewPose currentPose;private PreviewTargets targets;
        private static readonly string[] Variants={"unfiltered","envelope40","comparison20"};

        private void Awake()
        {
            try
            {
                config=PreviewConfiguration.Parse(Environment.GetCommandLineArgs());if(!config.Enabled){enabled=false;return;}
                if(Application.isEditor||Application.platform!=RuntimePlatform.WindowsPlayer||Type.GetType("Mono.Runtime")==null)
                    throw new InvalidOperationException("native_windows_mono_required");
                string bindingPath=Path.GetFullPath(Path.Combine(Application.dataPath,"..","PosePreview.binding.json"));
                if(!File.Exists(bindingPath)||new FileInfo(bindingPath).Length>16384)throw new InvalidOperationException("preview_binding_missing");
                var binding=JsonUtility.FromJson<PreviewBinding>(File.ReadAllText(bindingPath));
                if(binding==null||binding.schema!=1||binding.backend!="Mono2x"||binding.sourceFingerprint!=config.ExpectedFingerprint||Fixture==null||
                    PreviewCaptureRecorder.Digest(Fixture.bytes)!=binding.fixtureSha256)throw new InvalidOperationException("preview_binding_mismatch");
                fixture=JsonUtility.FromJson<PreviewFixture>(Fixture.text);ValidateFixture(fixture);
                if(BikePrefab==null||RiderPrefab==null||ReviewCamera==null||GroundMaterial==null||ReferenceMaterial==null||RawTargetMaterial==null)
                    throw new InvalidOperationException("preview_scene_inputs_missing");
                Directory.CreateDirectory(config.Output);began=Time.realtimeSinceStartupAsDouble;
                samples=new StreamWriter(new FileStream(Path.Combine(config.Output,"samples.jsonl"),FileMode.CreateNew,FileAccess.Write,FileShare.Read),new UTF8Encoding(false));
                report=new PreviewRunReport{startedUtc=DateTime.UtcNow.ToString("O"),sourceFingerprint=binding.sourceFingerprint,bindingSha256=PreviewCaptureRecorder.DigestFile(bindingPath),
                    fixtureSha256=binding.fixtureSha256,selectionSha256=binding.selectionSha256,unityVersion=Application.unityVersion,platform=Application.platform.ToString(),backend=binding.backend,
                    include20=config.Include20,monoDetected=true,samplesFile="samples.jsonl",graphicsDevice=SystemInfo.graphicsDeviceName,graphicsApi=SystemInfo.graphicsDeviceType.ToString(),
                    screenWidth=Screen.width,screenHeight=Screen.height,graphicsUvStartsAtTop=SystemInfo.graphicsUVStartsAtTop};
                File.WriteAllText(Path.Combine(config.Output,"reconstruction.json"),Fixture.text);
                Application.logMessageReceived+=OnLog;Application.runInBackground=true;Application.targetFrameRate=60;QualitySettings.vSyncCount=0;
                actor=new PreviewActorRig(BikePrefab,RiderPrefab,transform);captures=new PreviewCaptureRecorder(config.Output,began);
                active=true;BeginSegment();WriteReport();
            }
            catch(Exception error){if(report!=null)Finish(false,error.GetType().Name);else{Debug.LogError("RB_POSE_PREVIEW_SETUP_FAILED "+error.GetType().Name);Application.Quit(2);}}
        }
        private void Update()
        {
            if(!active||finished)return;
            try
            {
                double now=Time.realtimeSinceStartupAsDouble;if(now-began>PreviewConfiguration.MaximumRunSeconds){Finish(false,"wall_clock_limit");return;}
                if(captures.Failure!=null){Finish(false,captures.Failure);return;}
                if(encoding)
                {
                    if(captures.Pending==0){captures.EncodeOne();if(captures.EncodingComplete)Finish(true,"");}
                    return;
                }
                if(nextSegment){BeginSegment();nextSegment=false;now=Time.realtimeSinceStartupAsDouble;}
                float dt=Mathf.Clamp((float)(now-lastFrameAt),0,.1f);lastFrameAt=now;
                double segment=now-segmentAt;bool firstCorrection=false;
                if(!corrected&&beforeCaptured&&segment>=.9){corrected=true;correctionAt=now;firstCorrection=true;}
                double after=corrected?now-correctionAt:-1;
                currentPose=corrected?episode.after.Continue(after):episode.before;
                targets=projection.Target(currentPose);
                var scope=new PresentationContinuityScope(episode.sessionEpoch,episode.raceEpoch,"diagnostic-no-network",episode.riderId,false,1,(float)episode.rawPredictionCorrectionMeters);
                bool observedDetachedCorrection=scope.DetachedCorrectionSince(0,PreviewProjection.Detached((RiderMode)episode.after.mode));
                bool rebase=firstCorrection&&(poseChanged||observedDetachedCorrection);
                rider.Sample(targets.Rider,targets.RiderRotation,now,riderBound,rebase,!initialized);
                bike.Sample(targets.Bike,targets.BikeRotation,now,100,rebase,!initialized);
                actor.Apply(currentPose,rider,bike,dt);ground.SetTargets(targets);
                FollowCamera(currentPose,dt,!initialized);initialized=true;
                if(now>=nextSampleAt)
                {
                    int missed=Math.Max(0,(int)((now-nextSampleAt)*60));double late=now-nextSampleAt;nextSampleAt+=(missed+1)/60d;
                    AddSample(now,segment,after,missed,late);
                }
                if(!beforeCaptured&&segment>=.45){Capture("before",after);beforeCaptured=true;}
                if(firstCorrection)Capture("correction",0);
                if(corrected&&!midCaptured&&after>=.15){Capture("mid",after);midCaptured=true;}
                if(corrected&&!settledCaptured&&after>=.8){Capture("settled",after);settledCaptured=true;}
                if(corrected&&after>=1.25)
                {
                    variant++;
                    if(variant>=(config.Include20?3:2)){variant=0;episodeIndex++;}
                    if(episodeIndex==fixture.episodes.Length){encoding=true;samples.Flush();}
                    else nextSegment=true;
                }
            }
            catch(Exception error){Finish(false,error.GetType().Name);}
        }
        private void BeginSegment()
        {
            episode=fixture.episodes[episodeIndex];projection=new PreviewProjection(episode,actor.FallenRootOffset);ground?.Dispose();
            ground=new PreviewGround(projection,episode,GroundMaterial,ReferenceMaterial,RawTargetMaterial,transform);
            rider=new PreviewEnvelopeDriver(variant);bike=new PreviewEnvelopeDriver(variant);actor.Reset();
            segmentAt=lastFrameAt=Time.realtimeSinceStartupAsDouble;nextSampleAt=segmentAt;
            corrected=beforeCaptured=midCaptured=settledCaptured=initialized=false;previousCameraOffset=Vector3.zero;
            riderBound=Mathf.Clamp(Mathf.Max(Mathf.Abs(episode.before.speed),Mathf.Abs(episode.after.speed))+10,10,100);
            poseChanged=PreviewProjection.Detached((RiderMode)episode.before.mode)!=PreviewProjection.Detached((RiderMode)episode.after.mode);
        }
        private void FollowCamera(PreviewPose pose,float dt,bool initialize)
        {
            projection.Camera(pose,out var position,out var rotation,out float fov);
            Vector3 previous=ReviewCamera.transform.position;
            if(!initialize&&variant!=0)
            {previous-=previousCameraOffset;if(rider.Began)previous+=rider.Shift;}
            if(initialize||rider.Reset)previous=position;
            float blend=initialize||rider.Reset?1:1-Mathf.Exp(-dt*7);
            ReviewCamera.transform.SetPositionAndRotation(Vector3.Lerp(previous,position,blend)+(variant==0?Vector3.zero:rider.Offset),Quaternion.Slerp(ReviewCamera.transform.rotation,rotation,blend));
            ReviewCamera.fieldOfView=initialize?fov:Mathf.Lerp(ReviewCamera.fieldOfView,fov,1-Mathf.Exp(-dt*3));
            previousCameraOffset=variant==0?Vector3.zero:rider.Offset;
        }
        private void AddSample(double now,double segment,double after,int missed,double late)
        {
            if(sequence>=10000)throw new InvalidOperationException("sample_limit");
            double gap=lastSampleAt<0?0:now-lastSampleAt;lastSampleAt=now;report.maximumSampleGapSeconds=Math.Max(report.maximumSampleGapSeconds,gap);report.missedSampleSlots+=missed;
            var row=new PreviewFrame{sequence=++sequence,unityFrame=Time.frameCount,episodeIndex=episode.originalIndex,variant=Variants[variant],stage=corrected?"after":"before",
                wallSeconds=now-began,segmentSeconds=segment,afterSeconds=after,sampleDeltaSeconds=gap,sampleLatenessSeconds=late,missedSampleSlots=missed,
                mode=currentPose.mode,modeAge=currentPose.modeAge,originalRawPredictionCorrectionMeters=episode.rawPredictionCorrectionMeters,
                unfilteredRiderTarget=targets.Rider,unfilteredBikeTarget=targets.Bike,unfilteredRiderRotation=targets.RiderRotation,unfilteredBikeRotation=targets.BikeRotation,
                renderedRider=actor.Rider.position,renderedBike=actor.Bike.position,renderedRiderRotation=actor.Rider.rotation,renderedBikeRotation=actor.Bike.rotation,
                cameraPosition=ReviewCamera.transform.position,cameraRotation=ReviewCamera.transform.rotation,riderOffset=rider.Offset,bikeOffset=bike.Offset,
                riderDisplayError=Vector3.Distance(targets.Rider,actor.Rider.position),bikeDisplayError=Vector3.Distance(targets.Bike,actor.Bike.position),
                cameraRiderDepth=ReviewCamera.transform.InverseTransformPoint(actor.Rider.position).z,riderRemaining=rider.Remaining,bikeRemaining=bike.Remaining,
                riderReset=rider.ResetReason,bikeReset=bike.ResetReason,riderHardResets=rider.HardResets,bikeHardResets=bike.HardResets};
            samples.WriteLine(JsonUtility.ToJson(row));report.samples=sequence;if(sequence%60==0){samples.Flush();WriteReport();}
        }
        private void Capture(string stage,double after)=>captures.Request(ReviewCamera,episode,Variants[variant],stage,after,actor.Rider.position,actor.Bike.position);
        private void OnLog(string message,string stack,LogType type)
        {
            if(report==null)return;
            if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors++;
            if(type==LogType.Warning){report.warnings++;if(warnings.Count<16)warnings.Add(message.Length>240?message.Substring(0,240):message);}
        }
        private void WriteReport()
        {report.wallSeconds=Time.realtimeSinceStartupAsDouble-began;report.warningMessages=warnings.ToArray();report.captures=captures==null?Array.Empty<PreviewCapture>():captures.Captures;File.WriteAllText(Path.Combine(config.Output,"run.json"),JsonUtility.ToJson(report,true));}
        private void Finish(bool success,string failure)
        {
            if(finished)return;if(success&&report.errors>0){success=false;failure="engine_errors";}
            finished=true;report.completed=success;report.status=success?"CAPTURED":"FAILED";report.failureCode=failure;report.finishedUtc=DateTime.UtcNow.ToString("O");
            samples?.Flush();samples?.Dispose();samples=null;report.samplesSha256=PreviewCaptureRecorder.DigestFile(Path.Combine(config.Output,"samples.jsonl"));
            WriteReport();Application.logMessageReceived-=OnLog;Application.Quit(success?0:2);
        }
        private void OnApplicationQuit(){if(active&&!finished)Finish(false,"interrupted");}
        private static void ValidateFixture(PreviewFixture value)
        {
            if(value==null||value.schema!=1||value.episodes==null||value.episodes.Length!=4)throw new InvalidOperationException("four_trace_cases_required");
            foreach(var e in value.episodes)
            {
                if(string.IsNullOrEmpty(e.id)||e.id.IndexOfAny(new[]{'/','\\',':','.'})>=0||e.course<0||e.course>4||e.level<0||e.level>4)throw new InvalidOperationException("fixture_identity_invalid");
                foreach(var p in new[]{e.before,e.after})if(p==null||p.mode<0||p.mode>10||!float.IsFinite(p.s+p.d+p.h+p.bikeS+p.bikeD+p.bikeH+p.speed+p.bikeSpeed+p.lean)||p.modeAge<0)throw new InvalidOperationException("fixture_pose_invalid");
            }
        }
    }
}
