import bpy,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/'
def action_values(action):
 curves=[]
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:curves.append((curve.data_path,curve.array_index,curve.extrapolation,[(tuple(p.co),tuple(p.handle_left),tuple(p.handle_right),p.interpolation,p.handle_left_type,p.handle_right_type) for p in curve.keyframe_points]))
 return curves
def capture(version):
 rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
 for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
 bones=[(b.name,b.parent.name if b.parent else '',[tuple(row) for row in b.matrix_local],tuple(b.head_local),tuple(b.tail_local)) for b in rig.data.bones]
 actions={a.name:action_values(a) for a in bpy.data.actions if a.name.startswith('RB_')};contacts=[]
 for level in range(3):
  obj=bpy.data.objects['AshV'+str(version)+'_L'+str(level)+'_Skin'];mesh=obj.data;roles={i:set() for i in range(len(mesh.vertices))}
  for p in mesh.polygons:
   for i in p.vertices:roles[i].add(mesh.materials[p.material_index].name)
  points=[]
  for v in mesh.vertices:
   weights=sorted((obj.vertex_groups[g.group].name,g.weight) for g in v.groups)
   glove=any(('Finger_' in n or 'Hand_' in n) and w>.2 for n,w in weights) and any('CharcoalLeather' in r or 'LeatherDetails' in r for r in roles[v.index])
   boot=v.co.z<.32 and any('BootLeather' in r or 'Rubber' in r for r in roles[v.index])
   if glove or boot:points.append((tuple(v.co),weights))
  contacts.append(sorted(points))
 mesh=bpy.data.objects['AshV'+str(version)+'_L0_Skin'].data
 tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons if '_Skin_Baked' in mesh.materials[p.material_index].name],all_triangles=False)
 samples={}
 for name,x,z in [('nasalRoot',0,1.695),('nasalDorsum',0,1.680),('nasalTip',0,1.650),('chinProfile',0,1.590),('malar',.052,1.674),('submalar',.049,1.642),('upperLip',0,1.635),('lowerLip',0,1.620)]:
  p,n,index,d=tree.ray_cast(Vector((x,-.5,z)),Vector((0,1,0)),1);samples[name]=list(p) if p is not None else None
 return {'bones':bones,'actions':actions,'contacts':contacts,'landmarks':samples}
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend',load_ui=False,use_scripts=False);before=capture(5)
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',load_ui=False,use_scripts=False);after=capture(6)
assert before['bones']==after['bones'],'Rest rig changed'
gameplay_before={k:v for k,v in before['actions'].items() if k!='RB_MenuHero'}
gameplay_after={k:v for k,v in after['actions'].items() if k!='RB_MenuHero'}
assert gameplay_before==gameplay_after,'A gameplay action changed'
def preserve_menu(curves):return [c for c in curves if c[0]!='pose.bones["RB_P06_Rider_L0_Head"].rotation_quaternion']
assert preserve_menu(before['actions']['RB_MenuHero'])==preserve_menu(after['actions']['RB_MenuHero']),'A non-head menu curve changed'
assert before['contacts']==after['contacts'],'Glove or boot coordinates/weights changed'
hair=bpy.data.objects['Authored_AshV6_L0_FittedFringe'];shell=bpy.data.objects['Authored_AshV6_L0_HelmetShell'];rim=bpy.data.objects['Authored_AshV6_L0_RolledHelmetGasket']
def tree(obj):return BVHTree.FromPolygons([v.co for v in obj.data.vertices],[tuple(p.vertices) for p in obj.data.polygons],all_triangles=False)
hairtree=tree(hair);overlap={'hairShell':len(hairtree.overlap(tree(shell))),'hairRolledRim':len(hairtree.overlap(tree(rim)))}
rig=bpy.data.objects['RB_P06_Rider_Rig'];poses={}
for name in ['RB_Idle','RB_MenuHero']:
 rig.animation_data.action=bpy.data.actions[name];bpy.context.scene.frame_set(1);bpy.context.view_layer.update();head=rig.pose.bones['RB_P06_Rider_L0_Head'];rest=rig.data.bones[head.name];transform=head.matrix@rest.matrix_local.inverted();poses[name]={'headForwardBlender':list(transform.to_3x3()@Vector((0,-1,0))),'headOrigin':list(head.head)}
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1)
print('ASH_V6_PRESERVATION '+json.dumps({'passed':True,'bonesExact':len(before['bones']),'gameplayActionsExact':len(gameplay_before),'menuChangeLimitedTo':'4 Head rotation_quaternion curves','allOtherMenuCurvesExact':True,'contactVertexCounts':[len(v) for v in after['contacts']],'coordinatesAndWeightsExact':True,'indicesAllowedToRemap':True,'beforeLandmarks':before['landmarks'],'afterLandmarks':after['landmarks'],'hairIntersections':overlap,'headPoseDiagnostics':poses,'visualAccepted':False}))
