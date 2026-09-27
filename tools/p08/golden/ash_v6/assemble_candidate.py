import bpy,json,math
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
rows=[]
for level in range(3):
 equipment=bpy.data.objects['AshV6_L'+str(level)+'_Equipment'];mesh=equipment.data;mesh.calc_loop_triangles();bad=[];uvbad=[]
 for tri in mesh.loop_triangles:
  a,b,c=[mesh.vertices[i].co for i in tri.vertices]
  if (b-a).cross(c-a).length_squared<=1e-16:bad.append(tri.index)
  a,b,c=[mesh.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a
  if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uvbad.append(tri.index)
 rows.append({'lod':level,'triangles':len(mesh.loop_triangles),'physicalFailures':bad,'uvFailures':uvbad})
print('ASH_V6_PREMERGE '+json.dumps(rows))
assert all(not r['physicalFailures'] and not r['uvFailures'] for r in rows),'Actual equipment triangles or primary UVs failed'
for level in range(3):
 obj=bpy.data.objects['AshV6_L'+str(level)+'_Skin'];equipment=bpy.data.objects['AshV6_L'+str(level)+'_Equipment']
 for key in obj.data.shape_keys.key_blocks:key.value=0
 for modifier in list(equipment.modifiers):equipment.modifiers.remove(modifier)
 bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);equipment.hide_set(False);obj.select_set(True);equipment.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
 # Remove now-unused old head-material slots; body material references retain
 # their identity and order. Avoid exporting meaningless empty submeshes.
 used={p.material_index for p in obj.data.polygons}
 for i in range(len(obj.data.materials)-1,-1,-1):
  if i not in used:obj.active_material_index=i;bpy.ops.object.material_slot_remove()
 obj.hide_render=level!=0;obj.hide_set(level!=0);obj['v6_equipment_merged']=True
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_ASSEMBLED '+json.dumps({'lodSkins':3,'newAtlasMaterials':3,'skinMaterial':'AshV6_Skin_Baked','noGameplayOrBoneEdits':True,'visualAccepted':False}))
