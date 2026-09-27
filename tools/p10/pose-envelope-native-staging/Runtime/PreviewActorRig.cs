using System;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using UnityEngine;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    internal sealed class PreviewActorRig
    {
        internal readonly Transform Rider,Bike;private readonly RiderAnimationView animation;
        internal PreviewActorRig(GameObject bikePrefab,GameObject riderPrefab,Transform parent)
        {
            var bike=UnityEngine.Object.Instantiate(bikePrefab,parent,false);var rider=UnityEngine.Object.Instantiate(riderPrefab,parent,false);
            Bike=bike.transform;Rider=rider.transform;bike.name="Diagnostic real Apex";rider.name="Diagnostic real Ash";
            foreach(var obj in new[]{bike,rider})
            {
                foreach(var collider in obj.GetComponentsInChildren<Collider>(true))collider.enabled=false;
                foreach(var body in obj.GetComponentsInChildren<Rigidbody>(true)){body.isKinematic=true;body.useGravity=false;}
                foreach(var child in obj.GetComponentsInChildren<Transform>(true))child.gameObject.isStatic=false;
                foreach(var lod in obj.GetComponentsInChildren<LODGroup>(true))lod.ForceLOD(0);
                foreach(var skin in obj.GetComponentsInChildren<SkinnedMeshRenderer>(true))skin.updateWhenOffscreen=true;
            }
            animation=rider.AddComponent<RiderAnimationView>();
            if(!animation.Initialize(Rider,RiderAnimationSet.Resolve(Rider,null)))throw new InvalidOperationException("authored_rider_animation_missing");
        }
        internal void Reset(){animation.ResetPose();}
        internal void Apply(PreviewPose pose,PreviewEnvelopeDriver rider,PreviewEnvelopeDriver bike,float dt)
        {
            Rider.SetPositionAndRotation(rider.Position,rider.Rotation);Bike.SetPositionAndRotation(bike.Position,bike.Rotation);
            animation.Render((RiderMode)pose.mode,pose.attackSide,pose.attackAge,pose.modeAge,pose.speed,pose.kick,pose.lean,dt);
        }
    }
}
