"""Separate menu-only pose; preserve all twelve gameplay actions and rig rest."""
import bpy,math,json
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';PREFIX='RB_P06_Rider_L0_';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig']
previous_menu=bpy.data.actions.get('RB_MenuHero')
if previous_menu:
    assert previous_menu.get('scope','')=='Main menu only; standing beside ApexR2, tail/tank hands','Do not replace an unrelated action'
    rig.animation_data.action=None;bpy.data.actions.remove(previous_menu)
def action_values(action):
    values=[]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    values.append((curve.data_path,curve.array_index,curve.extrapolation,
                        [(tuple(p.co),tuple(p.handle_left),tuple(p.handle_right),p.interpolation,p.handle_left_type,p.handle_right_type) for p in curve.keyframe_points]))
    return values
gameplay_actions={a.name:action_values(a) for a in bpy.data.actions if a.name.startswith('RB_')}
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in rig.pose.bones}
local_fingers={b.name:b.matrix_basis.copy() for b in rig.pose.bones if 'Finger_' in b.name}
yaw=Matrix.Rotation(math.radians(-65),4,'Z');lower=Matrix.Translation(Vector((0,0,-.017)))
standing={name:lower@yaw@matrix for name,matrix in base.items()}
bike=bpy.data.objects['RB_Golden_Apex_v8_r2'];old_bike=bike.location.copy();bike.location=(-.30,-.25,0);bpy.context.view_layer.update()
vertices=[];faces=[]
for o in bike.children_recursive:
    if o.type!='MESH' or '_L0_' not in o.name:continue
    start=len(vertices);vertices.extend([o.matrix_world@v.co for v in o.data.vertices]);faces.extend([tuple(start+i for i in p.vertices) for p in o.data.polygons])
bike_tree=BVHTree.FromPolygons(vertices,faces,all_triangles=False)

def limb(a,end,l1,l2,hint):
    delta=end-a;d=delta.length
    if d>l1+l2-.0002:raise RuntimeError('Menu limb exceeds physical length '+str(d-l1-l2))
    axis=delta.normalized();projection=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-projection*projection))
    side=hint-a-axis*(hint-a).dot(axis)
    if side.length<.0001:side=axis.orthogonal()
    return a+axis*projection+side.normalized()*height

def segment(name,start,end):
    bone=rig.data.bones[PREFIX+name];reference=standing[bone.name].to_quaternion()
    rotation=(reference@Vector((0,1,0))).rotation_difference((end-start).normalized())@reference
    rig.pose.bones[bone.name].matrix=Matrix.Translation(start)@rotation.to_matrix().to_4x4();bpy.context.view_layer.update()

def palm_frame(label,point,normal):
    sign=1 if label=='L' else -1;hand=rig.data.bones[PREFIX+'Hand_'+label]
    across=(rig.data.bones[PREFIX+'Finger_Index_1_'+label].head_local-rig.data.bones[PREFIX+'Finger_Pinky_1_'+label].head_local).normalized()
    long=(rig.data.bones[PREFIX+'Finger_Middle_1_'+label].head_local-hand.head_local).normalized()
    across=(across-long*across.dot(long)).normalized();old_normal=across.cross(long).normalized()
    wanted=Vector((-.84,-.54 if label=='L' else .54,0));wanted=(wanted-normal*wanted.dot(normal)).normalized()
    new_normal=normal*sign;new_across=wanted.cross(new_normal).normalized()
    source_basis=Matrix((across,long,old_normal)).transposed();desired_basis=Matrix((new_across,wanted,new_normal)).transposed()
    rotation=desired_basis@source_basis.transposed()
    contact_from_wrist=long*.073-old_normal*(sign*.010)
    wrist=point-rotation@contact_from_wrist+normal*.003
    return wrist,rotation.to_quaternion()

targets={}
for label,grid in [('L',[(-.18,-.28),(-.20,-.24),(-.18,-.20)]),('R',[(x,y) for y in [.43,.47,.39,.51] for x in [-.23,-.25,-.21]])]:
    shoulder=standing[PREFIX+'UpperArm_'+label].translation;maximum=rig.data.bones[PREFIX+'UpperArm_'+label].length+rig.data.bones[PREFIX+'Forearm_'+label].length
    valid=[]
    for x,y in grid:
        point,normal,index,d=bike_tree.ray_cast(Vector((x,y,1.7)),Vector((0,0,-1)),1.3)
        if point is None or normal.z<.48:continue
        wrist,rotation=palm_frame(label,point,normal);reach=(wrist-shoulder).length
        if reach<maximum-.001:valid.append((point,normal,wrist,rotation,reach,normal.z))
    assert valid,'No reachable real menu surface for '+label
    # Prefer an upward support surface; no arbitrary floating contact target.
    best=valid[0]
    for value in valid[1:]:
        if value[5]>best[5]+.05:best=value
    targets[label]=best

rig.animation_data.action=None
action=bpy.data.actions.new('RB_MenuHero');action.use_fake_user=True;action['loop']=True;action['root_motion']=False;action['scope']='Main menu only; standing beside ApexR2, tail/tank hands'
rig.animation_data.action=action
for frame,breath in [(1,0),(31,.0015),(61,0)]:
    scene.frame_set(frame)
    for bone in rig.pose.bones:
        bone.matrix=standing[bone.name];bpy.context.view_layer.update()
    bpy.context.view_layer.update()
    # Foot targets stay on the original rotated idle support plane despite
    # the small relaxed hip drop; every limb keeps its original bone length.
    for label,sign in [('L',1),('R',-1)]:
        thigh=rig.pose.bones[PREFIX+'Thigh_'+label];a=thigh.head.copy();ankle=(yaw@base[PREFIX+'Foot_'+label]).translation
        hint=(yaw@base[PREFIX+'Shin_'+label]).translation+Vector((-.025,0,0))
        knee=limb(a,ankle,rig.data.bones[PREFIX+'Thigh_'+label].length,rig.data.bones[PREFIX+'Shin_'+label].length,hint)
        segment('Thigh_'+label,a,knee);segment('Shin_'+label,knee,ankle);rig.pose.bones[PREFIX+'Foot_'+label].matrix=yaw@base[PREFIX+'Foot_'+label]
    head=rig.pose.bones[PREFIX+'Head'];head.matrix=Matrix.Translation(head.head)@Matrix.Rotation(math.radians(25),4,'Z')@head.matrix.to_quaternion().to_matrix().to_4x4()
    torso=rig.pose.bones[PREFIX+'Torso'];torso.location.y+=breath;bpy.context.view_layer.update()
    for label,sign in [('L',1),('R',-1)]:
        point,normal,wrist,rotation,reach,up=targets[label]
        upper=rig.pose.bones[PREFIX+'UpperArm_'+label];shoulder=upper.head.copy()
        hint=shoulder+Vector((.15,-.04 if label=='L' else .10,-.24))
        elbow=limb(shoulder,wrist,rig.data.bones[PREFIX+'UpperArm_'+label].length,rig.data.bones[PREFIX+'Forearm_'+label].length,hint)
        segment('UpperArm_'+label,shoulder,elbow);segment('Forearm_'+label,elbow,wrist)
        rest=rig.data.bones[PREFIX+'Hand_'+label]
        rig.pose.bones[rest.name].matrix=Matrix.Translation(wrist)@(rotation@rest.matrix_local.to_quaternion()).to_matrix().to_4x4()
    for name,matrix in local_fingers.items():rig.pose.bones[name].matrix_basis=matrix
    bpy.context.view_layer.update()
    for bone in rig.pose.bones:
        bone.rotation_mode='QUATERNION';bone.keyframe_insert(data_path='location',frame=frame,group=bone.name)
        bone.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=bone.name);bone.keyframe_insert(data_path='scale',frame=frame,group=bone.name)
for name,values in gameplay_actions.items():assert action_values(bpy.data.actions[name])==values,'Gameplay action keys changed'
scene.frame_set(1);bike.location=old_bike;bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_MENU_POSE '+json.dumps({'clip':'RB_MenuHero','frames':[1,61],'loop':True,'rootMotion':False,
    'standingActorOffsetFromBikeUnity':[-.30,0,-.25],'previewBikeRootInActorBlender':[-.30,-.25,0],
    'contacts':{label:{'surface':list(data[0]),'normal':list(data[1]),'wrist':list(data[2]),'armReachMetres':data[4]} for label,data in targets.items()},
    'gameplayActionCountPreserved':len(gameplay_actions),'canonicalR2ReferenceOnly':True,'R3ContactsStillRequired':True,'visualAccepted':False}))
