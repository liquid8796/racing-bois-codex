using UnityEngine;
using NVector=System.Numerics.Vector3;
using NRotation=System.Numerics.Quaternion;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    internal sealed class PreviewEnvelopeDriver
    {
        private readonly UnityVisualPoseEnvelope baseline=new UnityVisualPoseEnvelope();
        private readonly VisualPoseEnvelope20Comparison slower=new VisualPoseEnvelope20Comparison();
        private readonly int variant;
        internal Vector3 Position,Offset,Shift;internal Quaternion Rotation;internal bool Began,Reset;
        internal double Remaining;internal string ResetReason;internal int HardResets;
        internal PreviewEnvelopeDriver(int variant){this.variant=variant;}
        internal void Sample(Vector3 p,Quaternion q,double now,float speed,bool changed,bool initialize)
        {
            if(variant==0){Position=p;Rotation=q;Offset=Shift=Vector3.zero;Began=false;Reset=initialize;Remaining=0;ResetReason=initialize?"Initialization":"None";return;}
            var position=new NVector(p.x,p.y,p.z);var rotation=new NRotation(q.x,q.y,q.z,q.w);
            if(variant==1)
            {
                baseline.Sample(p,q,now,speed,changed,false,initialize,out Position,out Rotation);
                Offset=baseline.Offset;Shift=baseline.RawTargetShift;Began=baseline.BeganReconciliation;Reset=baseline.ResetThisSample;
                Remaining=baseline.RemainingSeconds;ResetReason=baseline.ResetReason.ToString();HardResets=baseline.HardResetCount;
            }
            else
            {
                slower.Sample(position,rotation,now,speed,changed,reset:initialize);Position=Unity(slower.Position);Rotation=Unity(slower.Rotation);
                Offset=Unity(slower.PositionOffset);Shift=Unity(slower.RawTargetShift);Began=slower.BeganReconciliation;Reset=slower.ResetThisSample;
                Remaining=slower.RemainingSeconds;ResetReason=slower.ResetReason.ToString();HardResets=slower.HardResetCount;
            }
        }
        private static Vector3 Unity(NVector p)=>new Vector3(p.X,p.Y,p.Z);
        private static Quaternion Unity(NRotation q)=>new Quaternion(q.X,q.Y,q.Z,q.W);
    }
}
