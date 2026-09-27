import bpy,json
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend',load_ui=False,use_scripts=False)
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.data.objects['RB_Golden_Ash_V5'].name='RB_Golden_Ash_V6'
for obj in bpy.data.objects:
    if obj.name.startswith('AshV5_L'):obj.name=obj.name.replace('AshV5_L','AshV6_L',1)
bpy.data.collections['AshV5_Equipment'].name='AshV6_Equipment'
obj=bpy.data.objects['AshV6_L0_Skin'];mesh=obj.data
roles=[]
for mat in mesh.materials:
    ids=set(i for p in mesh.polygons if mesh.materials[p.material_index]==mat for i in p.vertices)
    if not ids:continue
    xyz=[mesh.vertices[i].co for i in ids]
    roles.append({'name':mat.name,'vertices':len(ids),'min':[min(p[k] for p in xyz) for k in range(3)],'max':[max(p[k] for p in xyz) for k in range(3)]})
faces=[tuple(p.vertices) for p in mesh.polygons if mesh.materials[p.material_index].name=='AshV4_Skin_Baked' and max(mesh.vertices[i].co.z for i in p.vertices)>1.55]
tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],faces,all_triangles=False)
samples=[]
for z in [1.580,1.590,1.605,1.620,1.635,1.650,1.665,1.680,1.695,1.710,1.725]:
    for x in [0,.02,.04,.06,.08]:
        p,n,index,d=tree.ray_cast(Vector((x,-.5,z)),Vector((0,1,0)),1)
        if p is not None:samples.append({'x':x,'z':z,'frontY':p.y})
equipment=[]
for part in bpy.data.collections['AshV6_Equipment'].objects:
    if not part.name.startswith('AshV6_L0'):continue
    points=[v.co for v in part.data.vertices]
    equipment.append({'name':part.name,'min':[min(p[k] for p in points) for k in range(3)],'max':[max(p[k] for p in points) for k in range(3)]})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_REST_PROBE '+json.dumps({'roles':roles,'faceGrid':samples,'equipment':equipment,'rigBones':len(rig.data.bones)}))
