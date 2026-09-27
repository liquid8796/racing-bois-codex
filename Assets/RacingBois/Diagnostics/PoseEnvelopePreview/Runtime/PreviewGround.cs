using System.Collections.Generic;
using UnityEngine;

namespace RacingBois.Diagnostics.PoseEnvelopePreview
{
    internal sealed class PreviewGround
    {
        internal readonly GameObject Root;internal readonly Transform RawRiderMarker,RawBikeMarker;
        internal PreviewGround(PreviewProjection projection,PreviewEpisode episode,Material ground,Material reference,Material raw,Transform parent)
        {
            Root=new GameObject("Diagnostic ground and reference markers (not recorded collisions)");Root.transform.SetParent(parent,false);
            float start=Mathf.Min(episode.before.s,episode.after.s)-35,end=Mathf.Max(episode.before.s,episode.after.s)+165;
            var vertices=new List<Vector3>();var triangles=new List<int>();var uv=new List<Vector2>();
            int rows=Mathf.CeilToInt((end-start)/2),columns=12;
            for(int r=0;r<=rows;r++)for(int c=0;c<=columns;c++)
            {float s=Mathf.Lerp(start,end,r/(float)rows),d=-12+c*2;vertices.Add(projection.Point(s,d));uv.Add(new Vector2(d/2,s/2));}
            for(int r=0;r<rows;r++)for(int c=0;c<columns;c++)
            {int a=r*(columns+1)+c,b=a+1,d=a+columns+1,e=d+1;triangles.AddRange(new[]{a,e,b,a,d,e});}
            var mesh=new Mesh{name="Source TrackDefinition diagnostic ribbon"};mesh.SetVertices(vertices);mesh.SetTriangles(triangles,0);mesh.SetUVs(0,uv);mesh.RecalculateNormals();mesh.RecalculateBounds();
            var road=new GameObject("Untextured diagnostic ground");road.transform.SetParent(Root.transform,false);road.AddComponent<MeshFilter>().sharedMesh=mesh;road.AddComponent<MeshRenderer>().sharedMaterial=ground;
            for(int i=0;i<rows;i+=3)
            {
                float s=start+i*2;var marker=Primitive("Distance reference",PrimitiveType.Cube,reference);
                marker.position=projection.Point(s,0,.012f);marker.rotation=projection.Heading(s);marker.localScale=new Vector3(.10f,.015f,1.5f);
            }
            var block=Primitive("Constructed reference obstacle - no collision claim",PrimitiveType.Cube,reference);
            block.position=projection.Point(episode.after.s+1,episode.after.d+1.5f,.4f);block.rotation=projection.Heading(episode.after.s);block.localScale=new Vector3(.7f,.8f,.7f);
            RawRiderMarker=Primitive("Unfiltered presentation rider target marker",PrimitiveType.Sphere,raw);RawRiderMarker.localScale=Vector3.one*.12f;
            RawBikeMarker=Primitive("Unfiltered presentation bike target marker",PrimitiveType.Cube,raw);RawBikeMarker.localScale=Vector3.one*.12f;
        }
        private Transform Primitive(string name,PrimitiveType type,Material material)
        {
            var value=GameObject.CreatePrimitive(type);value.name=name;value.transform.SetParent(Root.transform,false);value.GetComponent<Collider>().enabled=false;value.GetComponent<Renderer>().sharedMaterial=material;return value.transform;
        }
        internal void SetTargets(PreviewTargets targets){RawRiderMarker.position=targets.Rider;RawBikeMarker.position=targets.Bike;}
        internal void Dispose()
        {
            foreach(var filter in Root.GetComponentsInChildren<MeshFilter>())if(filter.sharedMesh!=null&&filter.sharedMesh.name=="Source TrackDefinition diagnostic ribbon")UnityEngine.Object.Destroy(filter.sharedMesh);
            UnityEngine.Object.Destroy(Root);
        }
    }
}
