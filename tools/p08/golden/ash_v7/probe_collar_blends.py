import bpy,json
from mathutils.bvhtree import BVHTree
obj=bpy.data.objects['AshV7_L0_Skin'];rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene
ids=list(obj['v7_collar_vertices']);saved={i:[(obj.vertex_groups[g.group].name,g.weight) for g in obj.data.vertices[i].groups] for i in ids};head=obj.vertex_groups['RB_P06_Rider_L0_Head'];torso=obj.vertex_groups['RB_P06_Rider_L0_Torso'];rows=[]
for weight in [0,.2,.35,.5,.65,.8]:
 for i in ids:
  for g in list(obj.data.vertices[i].groups):obj.vertex_groups[g.group].remove([i])
  torso.add([i],1-weight,'REPLACE')
  if weight:head.add([i],weight,'REPLACE')
 obj.data.update();minimum=1;failed=0
 for name,t in [('RB_MenuHero',0),('RB_Ride',0),('RB_Remount',.5),('RB_Fall',.5),('RB_Run',.25)]:
  action=bpy.data.actions[name];rig.animation_data.action=action;a,b=action.frame_range;f=a+(b-a)*t;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=evaluated.to_mesh();faces=[tuple(p.vertices) for p in m.polygons if m.materials[p.material_index].name=='AshV6_Skin_Baked'];tree=BVHTree.FromPolygons([v.co for v in m.vertices],faces,all_triangles=False)
  for i in ids:
   v=m.vertices[i].co;p,n,index,d=tree.find_nearest(v);signed=(v-p).dot(n);minimum=min(minimum,signed);failed+=signed<-.001
  evaluated.to_mesh_clear()
 rows.append({'headWeight':weight,'worstNeckDistance':minimum,'samplesBelowMinus1mm':failed})
for i,weights in saved.items():
 for g in list(obj.data.vertices[i].groups):obj.vertex_groups[g.group].remove([i])
 for name,w in weights:obj.vertex_groups[name].add([i],w,'REPLACE')
obj.data.update();rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
print('ASH_V7_COLLAR_BLEND_SWEEP '+json.dumps({'candidates':rows,'originalWeightsRestored':True,'sourceSaved':False}))
