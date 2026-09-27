"""Fit collar to the swept neck surface using actual preserved animation poses."""
import bpy,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene
samples=[('RB_Idle',0),('RB_MenuHero',0),('RB_MenuHero',.5),('RB_MenuHero',1),('RB_Ride',0),('RB_LeanLeft',.5),('RB_LeanRight',.5),('RB_AttackLeft',.5),('RB_AttackRight',.5),('RB_KickLeft',.5),('RB_KickRight',.5),('RB_Hit',.5),('RB_Fall',0),('RB_Fall',.5),('RB_Fall',1),('RB_Run',.25),('RB_Remount',.5)]
reports=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];mesh=obj.data;ids=list(obj['v7_collar_vertices']);original={i:mesh.vertices[i].co.copy() for i in ids};history=[]
 for iteration in range(5):
  corrections={};worst=1
  for name,t in samples:
   action=bpy.data.actions[name];rig.animation_data.action=action;a,b=action.frame_range;f=a+(b-a)*t;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=evaluated.to_mesh();tree=BVHTree.FromPolygons([v.co for v in m.vertices],[tuple(p.vertices) for p in m.polygons if m.materials[p.material_index].name=='AshV6_Skin_Baked'],all_triangles=False)
   bone=rig.pose.bones['RB_P06_Rider_L0_Torso'];inverse=(bone.matrix@bone.bone.matrix_local.inverted()).to_3x3().inverted()
   for i in ids:
    point=m.vertices[i].co;near,normal,face,d=tree.find_nearest(point);signed=(point-near).dot(normal);worst=min(worst,signed)
    if signed<.0008:
     delta=inverse@(normal*(.0011-signed))
     if i not in corrections or delta.length>corrections[i].length:corrections[i]=delta
   evaluated.to_mesh_clear()
  history.append({'iteration':iteration,'minimumBefore':worst,'verticesCorrected':len(corrections)})
  if not corrections:break
  for i,delta in corrections.items():
   assert (mesh.vertices[i].co+delta-original[i]).length<.021,'Swept collar displacement too large'
   before=[k.data[i].co.copy() for k in mesh.shape_keys.key_blocks];mesh.vertices[i].co+=delta
   for key,co in zip(mesh.shape_keys.key_blocks,before):key.data[i].co=co+delta
  mesh.update()
 reports.append({'lod':level,'history':history,'maximumRestDisplacement':max((mesh.vertices[i].co-original[i]).length for i in ids)})
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_SWEPT_COLLAR_FIT '+json.dumps({'lods':reports,'actualPoseCount':17,'onlyCollarGeometryEdited':True,'visualAccepted':False}))
