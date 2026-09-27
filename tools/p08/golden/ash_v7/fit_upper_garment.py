"""Repair actual shoulder/collar skin pokes by moving only upper garment surfaces."""
import bpy,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];samples=[('RB_Idle',0),('RB_MenuHero',0),('RB_MenuHero',.5),('RB_MenuHero',1),('RB_Ride',0),('RB_LeanLeft',.5),('RB_LeanRight',.5),('RB_AttackLeft',.5),('RB_AttackRight',.5),('RB_KickLeft',.5),('RB_KickRight',.5),('RB_Hit',.5),('RB_Fall',0),('RB_Fall',.5),('RB_Fall',1),('RB_Run',.25),('RB_Remount',.5)]
roles={'AshV4_LeatherDetails_Baked','AshV4_TailoredLeather_Baked','AshV2_OchreThread_Baked','AshV2_AgedBrass_Baked','AshV3_Rubber_Baked'};reports=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];mesh=obj.data;ids=set(i for p in mesh.polygons if mesh.materials[p.material_index].name in roles for i in p.vertices if 1.425<mesh.vertices[i].co.z<1.605 and abs(mesh.vertices[i].co.x)<.32);original={i:mesh.vertices[i].co.copy() for i in ids};history=[]
 for iteration in range(6):
  corrections={};count=0
  for name,t in samples:
   action=bpy.data.actions[name];rig.animation_data.action=action;a,b=action.frame_range;frame=a+(b-a)*t;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();points=[v.co for v in m.vertices];skin=[tuple(p.vertices) for p in m.polygons if m.materials[p.material_index].name=='AshV6_Skin_Baked'];garment=[p for p in m.polygons if all(i in ids for i in p.vertices)];tree=BVHTree.FromPolygons(points,skin,all_triangles=False);gtree=BVHTree.FromPolygons(points,[tuple(p.vertices) for p in garment],all_triangles=False);pairs=gtree.overlap(tree);count+=len(pairs);indices=set(a for a,b in pairs)
   deform={b.name:b.matrix@b.bone.matrix_local.inverted() for b in rig.pose.bones};inverse={}
   for index in indices:
    face=garment[index];corners=[points[i] for i in face.vertices];center=sum(corners,Vector())/len(corners);tests=[center]
    for k,p in enumerate(corners):tests.extend([p,p.lerp(corners[(k+1)%len(corners)],.25),p.lerp(corners[(k+1)%len(corners)],.5),p.lerp(corners[(k+1)%len(corners)],.75),p.lerp(center,.5)])
    worst=Vector()
    for point in tests:
     near,normal,face_index,d=tree.find_nearest(point);signed=(point-near).dot(normal)
     if signed<.0008:
      delta=normal*(.0012-signed)
      if delta.length>worst.length:worst=delta
    if worst.length==0:
     near,normal,face_index,d=tree.find_nearest(center);worst=normal*.0010
    assert worst.length<.025,'Upper garment correction too large'
    for i in face.vertices:
     if i not in inverse:
      transform=Matrix(((0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)))
      for g in mesh.vertices[i].groups:transform+=deform[obj.vertex_groups[g.group].name]*g.weight
      inverse[i]=transform.to_3x3().inverted()
     delta=inverse[i]@worst
     if i not in corrections or delta.length>corrections[i].length:corrections[i]=delta
   ev.to_mesh_clear()
  history.append({'iteration':iteration,'skinIntersectionPairs':count,'upperGarmentVerticesMoved':len(corrections)})
  if not corrections:break
  for i,delta in corrections.items():
   assert (mesh.vertices[i].co+delta-original[i]).length<.03,'Upper garment fit exceeds bounded displacement'
   before=[k.data[i].co.copy() for k in mesh.shape_keys.key_blocks];mesh.vertices[i].co+=delta
   for key,co in zip(mesh.shape_keys.key_blocks,before):key.data[i].co=co+delta
  mesh.update()
 reports.append({'lod':level,'history':history,'maximumUpperGarmentDisplacement':max((mesh.vertices[i].co-original[i]).length for i in ids)})
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_UPPER_GARMENT_FIT '+json.dumps({'lods':reports,'skinGeometryOrWeightsChanged':False,'gloveBootGeometryOrWeightsChanged':False,'poseCount':17,'visualAccepted':False}))
