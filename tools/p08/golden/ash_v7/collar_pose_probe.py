"""Actual deformed collar/neck distance over the requested 17 pose samples."""
import bpy,json,math
from mathutils.bvhtree import BVHTree
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];obj=bpy.data.objects['AshV7_L0_Skin']
samples=[('idle','RB_Idle',0),('menu-start','RB_MenuHero',0),('menu-mid','RB_MenuHero',.5),('menu-end','RB_MenuHero',1),('ride','RB_Ride',0),('lean-left','RB_LeanLeft',.5),('lean-right','RB_LeanRight',.5),('attack-left','RB_AttackLeft',.5),('attack-right','RB_AttackRight',.5),('kick-left','RB_KickLeft',.5),('kick-right','RB_KickRight',.5),('hit','RB_Hit',.5),('fall-start','RB_Fall',0),('fall-mid','RB_Fall',.5),('fall-end','RB_Fall',1),('run','RB_Run',.25),('remount','RB_Remount',.5)]
rows=[]
def by_distance(row):return row['signedDistance']
for name,action,t in samples:
 clip=bpy.data.actions[action];rig.animation_data.action=clip;start,end=clip.frame_range;f=start+(end-start)*t;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=evaluated.to_mesh()
 faces=[tuple(p.vertices) for p in m.polygons if m.materials[p.material_index].name=='AshV6_Skin_Baked'];tree=BVHTree.FromPolygons([v.co for v in m.vertices],faces,all_triangles=False);distances=[];bad=[]
 for index in obj['v7_collar_vertices']:
  v=m.vertices[index];p,n,face,d=tree.find_nearest(v.co);signed=(v.co-p).dot(n);distances.append(signed)
  if signed<-.001:bad.append({'vertex':index,'signedDistance':signed,'restPosition':list(obj.data.vertices[index].co),'posedPosition':list(v.co),'nearest':list(p)})
 rows.append({'sample':name,'clip':action,'normalizedTime':t,'minimumSignedNeckDistance':min(distances),'verticesDeeperThan1mm':len(bad),'worst':sorted(bad,key=by_distance)[:4]});evaluated.to_mesh_clear()
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
print('ASH_V7_COLLAR_POSES '+json.dumps({'samples':rows,'count':len(rows),'scope':'Nearest surface signed distances on real deformed skin; visual and triangle contact review still required.'}))
