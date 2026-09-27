"""Repair measured V2 chain and tank intersections without changing preserved mechanisms."""
import bpy,bmesh,json
from mathutils import Vector
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V2/RB_Golden_Spark_v2_editable.blend')
root=bpy.data.objects['RB_Golden_Spark_v2'];scene=bpy.context.scene
case=bpy.data.objects['V2 conjoined lobed crankcase'];tank=bpy.data.objects['V2 copper teardrop tank']

def difference(target,cutter):
    try:
        bpy.context.view_layer.objects.active=target
        modifier=target.modifiers.new('Measured mechanical clearance','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    finally:bpy.data.objects.remove(cutter,do_unlink=True)

# A rear-open chain passage preserves the original inboard drive-chain plane and countershaft location.
bpy.ops.mesh.primitive_cube_add(size=1,location=(.075,-.240,.405))
cutter=bpy.context.object;cutter.name='V2 owned chain passage cutter';cutter.dimensions=(.034,.220,.140)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
modifier=cutter.modifiers.new('Rounded machined slot corners','BEVEL');modifier.width=.006;modifier.segments=3
bpy.ops.object.modifier_apply(modifier=modifier.name)
difference(case,cutter)

def expanded_copy(name,ring_sides=0):
    source=bpy.data.objects[name];value=source.copy();value.data=source.data.copy();scene.collection.objects.link(value)
    value.name='V2 owned clearance cutter '+name
    if ring_sides:
        count=len(value.data.vertices);assert (count-2)%ring_sides==0
        for first in range(0,count-2,ring_sides):
            center=sum((value.data.vertices[first+j].co for j in range(ring_sides)),Vector())/ring_sides
            for j in range(ring_sides):
                vertex=value.data.vertices[first+j];vertex.co=center+(vertex.co-center)*1.32
    else:
        for vertex in value.data.vertices:vertex.co+=vertex.normal*.006
    value.data.update();return value

# Real cavities clear the original steering tube and upper clamp; frame rails receive shallow mounting saddles.
for name,sides in [('Steering head',28),('Upper triple clamp',0),('Upper black frame rail -1',14),('Upper black frame rail 1',14)]:
    difference(tank,expanded_copy(name,sides))

# Preserve the painted side chart; repair only UV-degenerate faces on new caps/cut walls and the solidified strap edge.
uv_repairs=[]
for obj in [case,tank,bpy.data.objects['V2 wrapped passenger strap']]:
    data=obj.data;data.calc_loop_triangles();uv=data.uv_layers.active;bad_faces=set()
    for triangle in data.loop_triangles:
        a,b,c=[uv.data[index].uv for index in triangle.loops]
        if abs((b.x-a.x)*(c.y-a.y)-(c.x-a.x)*(b.y-a.y))<=2e-12:bad_faces.add(triangle.polygon_index)
    for index in bad_faces:
        face=data.polygons[index];normal=face.normal
        axis=0 if abs(normal.x)>=max(abs(normal.y),abs(normal.z)) else 1 if abs(normal.y)>=abs(normal.z) else 2
        axes=[i for i in range(3) if i!=axis]
        origin=data.vertices[data.loops[face.loop_start].vertex_index].co
        for loop in face.loop_indices:
            point=data.vertices[data.loops[loop].vertex_index].co-origin
            # The tank's repaired cap/wall charts live in a copper-only strip of the existing original paint.
            uv.data[loop].uv=(.02+point[axes[0]]*.08,.50+point[axes[1]]*.08) if obj==tank else (point[axes[0]]*2,point[axes[1]]*2)
    uv_repairs.append({'object':obj.name,'reprojectedFaces':len(bad_faces)})
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()

bpy.context.view_layer.update()
root['clearanceRevision']=2
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_refined02.blend',compress=True)
print('SPARK_V2_CLEARANCE_REPAIR='+json.dumps({'source':bpy.data.filepath,'newChainPassage':True,'tankCavities':'Steering head, upper clamp, two frame rails; original mechanisms unchanged',
    'uvRepairs':uv_repairs,'visualAccepted':False,'exported':False}))
