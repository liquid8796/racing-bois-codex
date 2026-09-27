using System.Collections.Generic;
using UnityEngine;
using RacingBois.Client.Application;

namespace RacingBois.Client.Presentation
{
    /// <summary>Visual fixture only. It does not decide collision, speed, damage or results.</summary>
    public sealed class RoadStageView : MonoBehaviour
    {
        public GameObject BarrierPrefab;
        public Material RoadMaterial, GroundMaterial, AccentMaterial, DarkMaterial, WhiteMaterial;
        public Camera ViewCamera;
        private readonly Dictionary<string, Transform> riderViews = new Dictionary<string, Transform>();
        private readonly List<Transform> roadside = new List<Transform>();
        private readonly List<Transform> marks = new List<Transform>();
        private readonly HashSet<string> activeRiders = new HashSet<string>();
        private readonly List<string> retiredRiders = new List<string>();
        private float cameraBlend;

        public void Build()
        {
            Part("Ground", PrimitiveType.Cube, new Vector3(0,-.18f,120), new Vector3(600,.2f,800), GroundMaterial);
            Part("Road", PrimitiveType.Cube, new Vector3(0,-.045f,120), new Vector3(14,.08f,700), RoadMaterial);
            for (int i=0;i<42;i++)
            {
                var mark=Part("Centerline",PrimitiveType.Cube,new Vector3(0,.006f,i*12),new Vector3(.16f,.012f,4),WhiteMaterial);
                marks.Add(mark.transform);
            }
            for (int side=-1;side<=1;side+=2)
            {
                Part("Edge",PrimitiveType.Cube,new Vector3(side*6.5f,.005f,120),new Vector3(.14f,.012f,700),WhiteMaterial);
                for (int i=0;i<20;i++)
                {
                    var barrier=Instantiate(BarrierPrefab,transform);
                    // This fixture scrolls the presentation origin; these instances move at runtime.
                    foreach(var child in barrier.GetComponentsInChildren<Transform>()) child.gameObject.isStatic=false;
                    barrier.name="RoadsideBarrier"; barrier.transform.position=new Vector3(side*8,.0f,i*18);
                    barrier.transform.rotation=Quaternion.Euler(0,90,0); roadside.Add(barrier.transform);
                }
                for(int i=0;i<10;i++)
                {
                    var block=Part("SceneryBlock",PrimitiveType.Cube,new Vector3(side*(23+i%3*8),3+i%4*2, i*38+30),
                        new Vector3(9+i%4,6+i%4*4,12),GroundMaterial);
                }
            }
        }
        private GameObject Part(string name, PrimitiveType shape, Vector3 position, Vector3 scale, Material material, Transform parent=null)
        {
            var obj=GameObject.CreatePrimitive(shape); obj.name=name;
            obj.transform.SetParent(parent == null ? transform : parent, false);
            obj.transform.localPosition=position; obj.transform.localScale=scale;
            obj.GetComponent<Renderer>().sharedMaterial=material;
            Destroy(obj.GetComponent<Collider>());
            return obj;
        }
        private Transform Rider(string id, bool local)
        {
            if(riderViews.TryGetValue(id,out var existing)) return existing;
            var root=new GameObject("Rider_"+id).transform; root.SetParent(transform);
            var body=Part("PrototypeBody",PrimitiveType.Cube,new Vector3(0,.8f,0),new Vector3(.55f,.35f,1.5f),local?AccentMaterial:WhiteMaterial,root);
            Part("Seat",PrimitiveType.Cube,new Vector3(0,1.05f,-.3f),new Vector3(.42f,.15f,.7f),DarkMaterial,root);
            foreach(float z in new[]{-.68f,.68f})
            {
                var wheel=Part("Wheel",PrimitiveType.Cylinder,new Vector3(0,.4f,z),new Vector3(.8f,.14f,.8f),DarkMaterial,root);
                wheel.transform.localRotation=Quaternion.Euler(0,0,90);
            }
            Part("RiderProxy",PrimitiveType.Capsule,new Vector3(0,1.42f,-.1f),new Vector3(.42f,.5f,.42f),local?AccentMaterial:WhiteMaterial,root);
            riderViews[id]=root; return root;
        }
        public void RenderFrame(WorldReadModel world, string localId, float localS, float localD, bool connected, float dt)
        {
            cameraBlend=Mathf.MoveTowards(cameraBlend,connected?1:0,dt*1.7f);
            float offset=connected?localS:0;
            activeRiders.Clear();
            if(connected && world!=null)
            {
                foreach(var riderState in world.Riders)
                {
                    activeRiders.Add(riderState.Id);
                    bool local=riderState.Id==localId;
                    var rider=Rider(riderState.Id,local);
                    var goal=new Vector3(local?localD:riderState.LateralMeters,0,local?0:riderState.LongitudinalMeters-localS);
                    rider.localPosition=local?goal:Vector3.Lerp(rider.localPosition,goal,1-Mathf.Exp(-dt*12));
                }
            }
            retiredRiders.Clear();
            foreach(var pair in riderViews)
                if(!connected||!activeRiders.Contains(pair.Key))retiredRiders.Add(pair.Key);
            foreach(var id in retiredRiders)
            {
                Destroy(riderViews[id].gameObject);
                riderViews.Remove(id);
            }
            for(int i=0;i<roadside.Count;i++)
            {
                var p=roadside[i].position;
                p.z=Mathf.Repeat((i%20)*18-offset+45,360)-45; roadside[i].position=p;
            }
            for(int i=0;i<marks.Count;i++)
            {
                var p=marks[i].position; p.z=Mathf.Repeat(i*12-offset+36,504)-36; marks[i].position=p;
            }
            var targetPosition=Vector3.Lerp(new Vector3(11,5,-11),new Vector3(localD*.7f,3.3f,-7.5f),cameraBlend);
            ViewCamera.transform.position=Vector3.Lerp(ViewCamera.transform.position,targetPosition,1-Mathf.Exp(-dt*5));
            var lookAt=Vector3.Lerp(new Vector3(0,.5f,12),new Vector3(localD*.8f,1.2f,15),cameraBlend);
            ViewCamera.transform.rotation=Quaternion.Slerp(ViewCamera.transform.rotation,Quaternion.LookRotation(lookAt-ViewCamera.transform.position),1-Mathf.Exp(-dt*5));
        }
    }
}
