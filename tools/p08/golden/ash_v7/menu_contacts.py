import bpy,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_MenuHero'];bike=bpy.data.objects['RB_Golden_Apex_v8_r2'];old=bike.location.copy();bike.location=(-.30,-.25,0);scene.frame_set(1);bpy.context.view_layer.update();points=[];faces=[]
for o in bike.children_recursive:
 if o.type!='MESH' or '_L0_' not in o.name:continue
 start=len(points);points.extend([o.matrix_world@v.co for v in o.data.vertices]);faces.extend([tuple(start+i for i in p.vertices) for p in o.data.polygons])
tree=BVHTree.FromPolygons(points,faces,all_triangles=False);obj=bpy.data.objects['AshV7_L0_Skin'];rows=[]
for frame in [1,31,61]:
 scene.frame_set(frame);bpy.context.view_layer.update();ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();hands=[]
 for side in ['L','R']:
  palm=[];hand=rig.pose.bones['RB_P06_Rider_L0_Hand_'+side]
  for original in obj.data.vertices:
   weights={obj.vertex_groups[g.group].name:g.weight for g in original.groups};weight=weights.get('RB_P06_Rider_L0_Hand_'+side,0)
   if weight<.75:continue
   p=m.vertices[original.index].co;distance=(p-hand.head).length
   if not .045<distance<.105:continue
   q,n,index,d=tree.find_nearest(p);palm.append((p-q).dot(n))
  hands.append({'side':side,'palmRegionVertices':len(palm),'minimumSignedBikeDistance':min(palm),'verticesInsideBikeBeyond1mm':sum(d<-.001 for d in palm),'nearestAbsoluteContact':min(abs(d) for d in palm),'wrist':list(hand.head)})
 rows.append({'frame':frame,'hands':hands});ev.to_mesh_clear()
bike.location=old;rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
print('ASH_V7_MENU_CONTACTS '+json.dumps({'reference':'actual imported ApexR2 geometry, not final R3 acceptance','bikeRootInActorBlender':[-.30,-.25,0],'samples':rows,'visualAccepted':False}))
