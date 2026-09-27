import bpy,bmesh,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
rows=[]
for level in range(3):
 body=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];parts=[bpy.data.objects['AshV7_L'+str(level)+'_'+suffix] for suffix in ['Equipment','Glass','CollarFacing']]
 facing=parts[2];bm=bmesh.new();bm.from_mesh(facing.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(facing.data);bm.free();face_positions={tuple(v.co) for v in facing.data.vertices}
 for obj in parts:
  m=obj.data;m.calc_loop_triangles()
  for tri in m.loop_triangles:
   a,b,c=[m.vertices[i].co for i in tri.vertices];assert (b-a).cross(c-a).length_squared>1e-16,obj.name+' physical'
   a,b,c=[m.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a;assert abs(ab.x*ac.y-ab.y*ac.x)>1e-14,obj.name+' UV'
  for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
 for key in body.data.shape_keys.key_blocks:key.value=0
 bpy.ops.object.select_all(action='DESELECT');body.hide_set(False);body.select_set(True)
 for obj in parts:obj.hide_set(False);obj.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.object.join();body['v7_facing_vertices']=[v.index for v in body.data.vertices if tuple(v.co) in face_positions]
 assert len(body['v7_facing_vertices'])==len(face_positions)
 used={p.material_index for p in body.data.polygons}
 for i in range(len(body.data.materials)-1,-1,-1):
  if i not in used:body.active_material_index=i;bpy.ops.object.material_slot_remove()
 body.hide_render=level!=0;body.hide_set(level!=0);body.data.calc_loop_triangles();rows.append({'lod':level,'vertices':len(body.data.vertices),'triangles':len(body.data.loop_triangles),'materials':[m.name for m in body.data.materials]})
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_ASSEMBLED '+json.dumps({'lods':rows,'separateTransparentMaterial':'AshV7_AmberGlass_Baked','visualAccepted':False}))
