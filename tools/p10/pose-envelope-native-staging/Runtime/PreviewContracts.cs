using System;
using RacingBois.Gameplay.Definitions;
using UnityEngine;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    [Serializable] public sealed class PreviewPose
    {
        public float s,d,h,bikeS,bikeD,bikeH,speed,bikeSpeed,lean;
        public int mode,modeAge,attackSide,attackAge; public bool kick;
        public PreviewPose Continue(double seconds)
        {
            var value=(PreviewPose)MemberwiseClone();float t=(float)Math.Max(0,seconds);
            value.s+=speed*t;value.bikeS+=(PreviewProjection.Detached((RiderMode)mode)?Math.Max(0,bikeSpeed):speed)*t;
            value.modeAge+=Math.Max(0,(int)(seconds*60));value.attackAge+=Math.Max(0,(int)(seconds*60));return value;
        }
    }
    [Serializable] public sealed class PreviewEpisode
    {
        public string id; public int originalIndex,course,level,authorityBeforeMode,authorityAfterMode,forecastBeforeMode,forecastAfterMode,sessionEpoch,raceEpoch,riderId;
        public double traceAt,rawPredictionCorrectionMeters,recordedPresentedDeltaMeters;
        public PreviewPose before,after;
    }
    [Serializable] public sealed class PreviewFixture
    { public int schema;public string trace,traceSha256,scope,reconstruction,timing;public PreviewEpisode[] episodes; }
    [Serializable] public sealed class PreviewBinding
    { public int schema=1;public string sourceFingerprint,fixtureSha256,selectionSha256,unityVersion,backend="Mono2x"; }
    [Serializable] public sealed class PreviewFrame
    {
        public int sequence,unityFrame,episodeIndex,missedSampleSlots,mode,modeAge,riderHardResets,bikeHardResets;
        public string variant,stage,riderReset,bikeReset;
        public double wallSeconds,segmentSeconds,afterSeconds,sampleDeltaSeconds,sampleLatenessSeconds,riderRemaining,bikeRemaining,originalRawPredictionCorrectionMeters;
        public Vector3 unfilteredRiderTarget,unfilteredBikeTarget,renderedRider,renderedBike,cameraPosition,riderOffset,bikeOffset;
        public Quaternion unfilteredRiderRotation,unfilteredBikeRotation,renderedRiderRotation,renderedBikeRotation,cameraRotation;
        public float riderDisplayError,bikeDisplayError,cameraRiderDepth;
    }
    [Serializable] public sealed class PreviewCapture
    {
        public string episode,variant,stage,file,sha256;public int unityFrame,width,height;public long bytes;
        public double requestWallSeconds,afterSeconds,readbackCompletedWallSeconds; public Vector3 rider,bike,camera;
        public bool variedPixels;
    }
    [Serializable] public sealed class PreviewRunReport
    {
        public int schema=1,targetSampleHz=60,samples,missedSampleSlots,errors,warnings;
        public string status="RUNNING",failureCode="",startedUtc,finishedUtc,sourceFingerprint,bindingSha256,fixtureSha256,selectionSha256,unityVersion,platform,backend,graphicsDevice,graphicsApi;
        public int screenWidth,screenHeight;public bool graphicsUvStartsAtTop;
        public double wallSeconds,maximumSampleGapSeconds;public bool include20,monoDetected,completed,nativeVisualAccepted;
        public string[] warningMessages;public PreviewCapture[] captures;public string samplesFile,samplesSha256;
        public string scope="Isolated real Unity camera comparison using actual selected prefabs and RiderAnimationView. Reconstructed pose-pair continuation; no server, game bootstrap, full WAN playback, performance or visual acceptance.";
    }
}
