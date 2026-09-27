import bpy,json,bmesh
from mathutils import Matrix
rig=bpy.data.objects['RB_P06_Rider_Rig']
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
body=bpy.data.objects['AshV2_Body'];clothes=bpy.data.objects['AshV2_Clothes']
keys=[]
if body.data.shape_keys:
    for key in body.data.shape_keys.key_blocks:keys.append({'name':key.name,'value':key.value});key.value=0
bm=bmesh.new();bm.from_mesh(clothes.data)
neck=[tuple(v.co) for v in bm.verts if v.co.z>1.48 and abs(v.co.x)<.14]
bm.free()
print(json.dumps({'keys_before_reset':keys,'neck_bounds':[[min(p[a] for p in neck),max(p[a] for p in neck)] for a in range(3)],
                  'pose_reset':True,'cloth_verts':len(clothes.data.vertices),'cloth_polygons':len(clothes.data.polygons)}))
