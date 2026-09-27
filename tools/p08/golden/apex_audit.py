"""Fresh Blender geometry observations; no acceptance flag is inferred."""
import bpy, bmesh, math, json
from mathutils import Vector
root=bpy.data.objects['RB_Golden_Apex']
items=[];all_points=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    data=obj.data;data.calc_loop_triangles()
    bm=bmesh.new();bm.from_mesh(data)
    uv=data.uv_layers.active
    uv_zero=0;geometry_zero=0;minimum_area=1.0
    for tri in data.loop_triangles:
        if tri.area<1e-12:geometry_zero+=1
        p=[uv.data[i].uv for i in tri.loops]
        area=abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5
        minimum_area=min(minimum_area,area)
        if area<1e-12:uv_zero+=1
    if '_L0_' in obj.name:all_points.extend(obj.matrix_world@vertex.co for vertex in data.vertices)
    items.append({'name':obj.name,'triangles':len(data.loop_triangles),'vertices':len(data.vertices),'materials':[m.name for m in data.materials],'nonManifoldEdges':sum(not edge.is_manifold for edge in bm.edges),'zeroAreaTriangles':geometry_zero,'zeroAreaUVTriangles':uv_zero,'minUVTriangleArea':minimum_area,'localPosition':list(obj.location),'localScale':list(obj.scale),'parent':obj.parent.name})
    bm.free()
def semantic(point):return [point.x,point.z,-point.y]
markers={obj.name:semantic(root.matrix_world.inverted()@obj.matrix_world.translation) for obj in root.children_recursive if obj.type=='EMPTY'}
minimum=[min(p[i] for p in all_points) for i in range(3)];maximum=[max(p[i] for p in all_points) for i in range(3)]
print('APEX_GEOMETRY_AUDIT '+json.dumps({'meshes':items,'markersUnitySemantic':markers,'blenderBoundsMin':minimum,'blenderBoundsMax':maximum,'unitySemanticSize':[maximum[0]-minimum[0],maximum[2]-minimum[2],maximum[1]-minimum[1]],'qualityAcceptance':'pending independent visual and Unity inspection','uvReuse':'Full-field finish textures intentionally shared across manufactured components; analytic longitudinal/radial UVs, planar caps, separate projected panels. No palette swatches.'}))
