"""Measure posed runtime skin surfaces against imported physical contact markers."""
import bpy,math,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig']
obj=bpy.data.objects['AshV3_L0_Skin'];evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
vertices=[obj.matrix_world@v.co for v in mesh.vertices]
bvh=BVHTree.FromPolygons(vertices,[tuple(t.vertices) for t in mesh.loop_triangles],all_triangles=True)
def hit(origin,direction,distance):
    p,n,i,d=bvh.ray_cast(origin,direction,distance)
    return None if p is None else {'point':list(p),'distance':d,'normal':list(n),'material':mesh.materials[mesh.loop_triangles[i].material_index].name}
report={'scope':'Actual evaluated runtime mesh rays; contact evidence only, not visual fidelity acceptance.','grips':{},'feet':{},'seat':[]}
def surface_distance(value):return value['distance']
for label,sign in [('L',1),('R',-1)]:
    center=bpy.data.objects['Contact_Grip_'+label].matrix_world.translation
    axis=Vector((sign*.875,.484,0)).normalized();forward=Vector((axis.y,-axis.x,0));up=Vector((0,0,1))
    rays=[]
    for along in [-.024,0,.024]:
        for angle in range(0,360,30):
            direction=up*math.cos(math.radians(angle))+forward*math.sin(math.radians(angle))
            rays.append({'along':along,'angle':angle,'hit':hit(center+axis*along,direction,.075)})
    report['grips'][label]={'radius':.019,'rays':rays}
    peg=bpy.data.objects['Contact_Foot_'+label].matrix_world.translation
    report['feet'][label]={'pegRadius':.014,'soleAbovePegCentre':hit(peg-Vector((0,0,.10)),Vector((0,0,1)),.20)}
seat=bpy.data.objects['Contact_Seat'].matrix_world.translation
bike_surfaces=[]
for reference in bpy.data.collections['ApexR2_ContactReferenceOnly'].objects:
    if reference.type!='MESH' or reference.hide_render:continue
    reference.data.calc_loop_triangles()
    surface=BVHTree.FromPolygons([reference.matrix_world@v.co for v in reference.data.vertices],[tuple(t.vertices) for t in reference.data.loop_triangles],all_triangles=True)
    bike_surfaces.append((reference.name,surface))
for x in [-.06,-.03,.03,.06]:
    origin=seat+Vector((x,0,-.12))
    garment=hit(origin,Vector((0,0,1)),.30);physical=[]
    for name,surface in bike_surfaces:
        p,n,i,d=surface.ray_cast(seat+Vector((x,0,.20)),Vector((0,0,-1)),.40)
        if p is not None:physical.append({'object':name,'point':list(p),'distance':d})
    physical.sort(key=surface_distance)
    nearest=physical[0] if physical else None
    report['seat'].append({'x':x,'garmentAboveMarker':garment,'actualBikeSurface':nearest,'garmentMinusSeatMeters':garment['point'][2]-nearest['point'][2] if garment and nearest else None})
evaluated.to_mesh_clear()
print('ASH_V3_ACTUAL_CONTACT_RAYS '+json.dumps(report))
