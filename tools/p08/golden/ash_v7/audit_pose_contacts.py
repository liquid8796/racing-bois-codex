import bpy,json,math
from mathutils.bvhtree import BVHTree
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig']
samples=[('idle','RB_Idle',0),('menu-start','RB_MenuHero',0),('menu-mid','RB_MenuHero',.5),('menu-end','RB_MenuHero',1),('ride','RB_Ride',0),('lean-left','RB_LeanLeft',.5),('lean-right','RB_LeanRight',.5),('attack-left','RB_AttackLeft',.5),('attack-right','RB_AttackRight',.5),('kick-left','RB_KickLeft',.5),('kick-right','RB_KickRight',.5),('hit','RB_Hit',.5),('fall-start','RB_Fall',0),('fall-mid','RB_Fall',.5),('fall-end','RB_Fall',1),('run','RB_Run',.25),('remount','RB_Remount',.5)]
rows=[]
for name,action,t in samples:
 clip=bpy.data.actions[action];rig.animation_data.action=clip;a,b=clip.frame_range;frame=a+(b-a)*t;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();levels=[]
 for level in range(3):
  obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();points=[v.co.copy() for v in m.vertices];assert all(math.isfinite(x) for p in points for x in p)
  skin=[tuple(p.vertices) for p in m.polygons if m.materials[p.material_index].name=='AshV6_Skin_Baked'];ids=set(obj['v7_collar_vertices'])|set(obj['v7_facing_vertices']);collar=[tuple(p.vertices) for p in m.polygons if all(i in ids for i in p.vertices)]
  tree=BVHTree.FromPolygons(points,skin,all_triangles=False);ctree=BVHTree.FromPolygons(points,collar,all_triangles=False);distances=[]
  for i in ids:
   near,n,index,d=tree.find_nearest(points[i]);distances.append((points[i]-near).dot(n))
  intersections=ctree.overlap(tree)
  levels.append({'lod':level,'minimumSignedNeckDistance':min(distances),'verticesBelowSkin':sum(d<0 for d in distances),'collarSkinTriangleIntersections':len(intersections),'evaluatedVertices':len(points),'boundsMin':[min(p[k] for p in points) for k in range(3)],'boundsMax':[max(p[k] for p in points) for k in range(3)]});ev.to_mesh_clear()
 rows.append({'sample':name,'clip':action,'normalizedTime':t,'lods':levels})
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
print('ASH_V7_POSE_CONTACT_AUDIT '+json.dumps({'samples':rows,'count':len(rows),'finiteDeformationPassed':True,'contactPassed':all(l['minimumSignedNeckDistance']>=0 and l['collarSkinTriangleIntersections']==0 for r in rows for l in r['lods']),'visualAccepted':False}))
