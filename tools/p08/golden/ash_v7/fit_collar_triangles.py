"""Resolve real between-vertex collar intersections across preserved pose samples."""
import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];samples=[('RB_Idle',0),('RB_MenuHero',0),('RB_MenuHero',.5),('RB_MenuHero',1),('RB_Ride',0),('RB_LeanLeft',.5),('RB_LeanRight',.5),('RB_AttackLeft',.5),('RB_AttackRight',.5),('RB_KickLeft',.5),('RB_KickRight',.5),('RB_Hit',.5),('RB_Fall',0),('RB_Fall',.5),('RB_Fall',1),('RB_Run',.25),('RB_Remount',.5)]
reports=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];mesh=obj.data;ids=set(obj['v7_collar_vertices'])|set(obj['v7_facing_vertices']);original={i:mesh.vertices[i].co.copy() for i in ids};history=[]
 for iteration in range(7):
  corrections={};pair_count=0;minimum=1
  for name,t in samples:
   action=bpy.data.actions[name];rig.animation_data.action=action;a,b=action.frame_range;frame=a+(b-a)*t;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();points=[v.co for v in m.vertices];skin=[tuple(p.vertices) for p in m.polygons if m.materials[p.material_index].name=='AshV6_Skin_Baked'];collar=[p for p in m.polygons if all(i in ids for i in p.vertices)];tree=BVHTree.FromPolygons(points,skin,all_triangles=False);ctree=BVHTree.FromPolygons(points,[tuple(p.vertices) for p in collar],all_triangles=False);pairs=ctree.overlap(tree);pair_count+=len(pairs);indices=set(a for a,b in pairs)
   bone=rig.pose.bones['RB_P06_Rider_L0_Torso'];inverse=(bone.matrix@bone.bone.matrix_local.inverted()).to_3x3().inverted()
   for index in indices:
    face=collar[index];corners=[points[i] for i in face.vertices];center=sum(corners,Vector())/len(corners);tests=[center]
    for k,p in enumerate(corners):tests.extend([p.lerp(corners[(k+1)%len(corners)],.25),p.lerp(corners[(k+1)%len(corners)],.5),p.lerp(corners[(k+1)%len(corners)],.75),p.lerp(center,.5)])
    worst_delta=Vector()
    for point in tests:
     near,normal,face_index,d=tree.find_nearest(point);signed=(point-near).dot(normal);minimum=min(minimum,signed)
     if signed<.0008:
      delta=inverse@(normal*(.0012-signed))
      if delta.length>worst_delta.length:worst_delta=delta
    if worst_delta.length==0:
     # Very narrow edge crossing not hit by the finite samples: use the
     # nearest triangle centroid normal and a bounded clearance increment.
     near,normal,face_index,d=tree.find_nearest(center);worst_delta=inverse@(normal*.0008)
    assert worst_delta.length<.008,'Unbounded collar triangle correction'
    for i in face.vertices:
     if i not in corrections or worst_delta.length>corrections[i].length:corrections[i]=worst_delta.copy()
   ev.to_mesh_clear()
  history.append({'iteration':iteration,'intersectionPairs':pair_count,'verticesMoved':len(corrections),'minimumInteriorSample':minimum})
  if not corrections:break
  for i,delta in corrections.items():
   assert (mesh.vertices[i].co+delta-original[i]).length<.017,'Excessive collar-only refinement'
   before=[k.data[i].co.copy() for k in mesh.shape_keys.key_blocks];mesh.vertices[i].co+=delta
   for key,co in zip(mesh.shape_keys.key_blocks,before):key.data[i].co=co+delta
  mesh.update()
 reports.append({'lod':level,'history':history,'additionalMaximumDisplacement':max((mesh.vertices[i].co-original[i]).length for i in ids)})
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_TRIANGLE_CLEARANCE '+json.dumps({'lods':reports,'poseSamples':17,'visualAccepted':False}))
