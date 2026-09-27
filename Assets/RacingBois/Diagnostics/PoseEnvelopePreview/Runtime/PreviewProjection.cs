using RacingBois.Gameplay.Definitions;
using UnityEngine;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    public readonly struct PreviewTargets
    {
        public readonly Vector3 Rider,Bike;public readonly Quaternion RiderRotation,BikeRotation;
        public PreviewTargets(Vector3 rider,Vector3 bike,Quaternion riderRotation,Quaternion bikeRotation)
        {Rider=rider;Bike=bike;RiderRotation=riderRotation;BikeRotation=bikeRotation;}
    }
    /// <summary>Source-bound reconstruction of current stage target/camera formulas, in actual Unity value types.</summary>
    public sealed class PreviewProjection
    {
        private readonly TrackDefinition track;public Vector3 Origin{get;}
        public PreviewProjection(PreviewEpisode episode)
        {track=TrackDefinition.ForCourse(episode.course,episode.level);Origin=AbsolutePoint(episode.after.s,0,0);}
        private Vector3 AbsolutePoint(float s,float d,float h)
        {var p=track.Sample((long)(s*1000));return new Vector3(p.CenterX+p.ForwardZ*d,p.CenterY+h,p.CenterZ-p.ForwardX*d);}
        public Vector3 Point(float s,float d=0,float h=0)=>AbsolutePoint(s,d,h)-Origin;
        public Quaternion Heading(float s)
        {var p=track.Sample((long)(s*1000));return Quaternion.LookRotation(new Vector3(p.ForwardX,p.GradePermille/1000f,p.ForwardZ).normalized,Vector3.up);}
        public static bool Detached(RiderMode mode)=>mode==RiderMode.Falling||mode==RiderMode.Detached||mode==RiderMode.Running||mode==RiderMode.Remounting||mode==RiderMode.Wrecked;
        public PreviewTargets Target(PreviewPose pose)
        {
            var mode=(RiderMode)pose.mode;bool detached=Detached(mode);
            float s=detached?pose.bikeS:pose.s,d=detached?pose.bikeD:pose.d;
            float mounting=mode==RiderMode.Remounting?Mathf.SmoothStep(0,1,pose.modeAge/(float)GameplayRules.RemountDurationTicks):0;
            float fall=detached?1-mounting:0;
            var bike=Point(s,d,(detached?pose.bikeH:pose.h)+fall*.48f);
            var rider=detached?Point(pose.s,pose.d,pose.h):bike+Heading(s)*new Vector3(0,-.08f,-.32f);
            if(mode==RiderMode.Falling||mode==RiderMode.Detached||mode==RiderMode.Wrecked)rider.y-=.55f;
            if(mode==RiderMode.Remounting)rider=Vector3.Lerp(rider,Point(s,d)+Heading(s)*new Vector3(0,-.08f,-.32f),mounting);
            return new PreviewTargets(rider,bike,Heading(pose.s)*Quaternion.Euler(0,0,detached?0:pose.lean*.65f),Heading(s)*Quaternion.Euler(0,0,detached?76*fall:pose.lean));
        }
        public void Camera(PreviewPose pose,out Vector3 position,out Quaternion rotation,out float fov)
        {
            var anchor=Point(pose.s,pose.d,Mathf.Min(1.5f,pose.h));position=anchor+Heading(pose.s)*new Vector3(0,2.65f,-6.5f);
            var look=Point(pose.s+17,pose.d*.5f,1.1f);position.y=Mathf.Max(position.y,Point(pose.s-7).y+1.5f);
            rotation=Quaternion.LookRotation(look-position,Vector3.up);fov=60+Mathf.Clamp01(pose.speed/58)*8;
        }
    }
}
