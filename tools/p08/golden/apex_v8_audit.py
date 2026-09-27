"""Saved V8 structural observations. No concept-fidelity score is generated."""
import bpy, bmesh, json
from mathutils import Vector
root=bpy.data.objects['RB_Golden_Apex_v8']
items=[];points=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    data=obj.data;data.calc_loop_triangles()
    bm=bmesh.new();bm.from_mesh(data)
    uv=data.uv_layers.active
    zero_geo=sum(t.area<1e-12 for t in data.loop_triangles)
    zero_uv=0
    for t in data.loop_triangles:
        p=[uv.data[i].uv for i in t.loops]
        if abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5<1e-12:zero_uv+=1
    if '_L0_' in obj.name:points.extend(obj.matrix_world@v.co for v in data.vertices)
    items.append({'name':obj.name,'triangles':len(data.loop_triangles),'vertices':len(data.vertices),
        'nonManifoldEdges':sum(not e.is_manifold for e in bm.edges),'zeroAreaTriangles':zero_geo,
        'zeroAreaUVTriangles':zero_uv,'materials':[m.name for m in data.materials],
        'parent':obj.parent.name,'localPosition':list(obj.location),'localScale':list(obj.scale)})
    bm.free()
minimum=[min(p[i] for p in points) for i in range(3)]
maximum=[max(p[i] for p in points) for i in range(3)]
markers={obj.name:[obj.location.x,obj.location.z,obj.location.y] for obj in root.children_recursive if obj.type=='EMPTY'}
print('APEX_V8_GEOMETRY_AUDIT '+json.dumps({'meshes':items,'blenderBoundsMin':minimum,'blenderBoundsMax':maximum,
    'unityIntendedSize':[maximum[0]-minimum[0],maximum[2]-minimum[2],maximum[1]-minimum[1]],
    'markersIntendedUnitySemantic':markers,'coordinateRecipe':'Blender=(semanticX,semanticForward,semanticUp); FBX -Z forward/Y up; root must prove Unity +Z, left -X, right +X together.',
    'acceptance':'Not accepted; structural observations never prove 100 percent visual fidelity.',
    'uvPolicy':'Purposeful full-field finish textures share component UV charts intentionally; unique decal unwrap not claimed.'}))
