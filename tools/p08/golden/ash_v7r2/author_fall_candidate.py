import bpy,json,math,array
from mathutils import Vector,Quaternion,Matrix
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend',load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];fall=bpy.data.actions['RB_Fall'];lods=[bpy.data.objects['AshV7_L'+str(i)+'_Skin'] for i in range(3)]
parts=['Hip','Torso','Head','UpperArm_L','Forearm_L','Hand_L','UpperArm_R','Forearm_R','Hand_R','Thigh_L','Shin_L','Foot_L','Thigh_R','Shin_R','Foot_R']
directions={'Torso':(-.12,-.18,.976),'Head':(.55,-.04,.834),'UpperArm_L':(-.18,-.65,-.58),'Forearm_L':(-.40,-.12,.90),'Hand_L':(-.25,-.10,.96),'UpperArm_R':(.25,-.65,-.72),'Forearm_R':(.55,-.20,.81),'Hand_R':(.3,-.1,.95),'Thigh_L':(.06,-.34,-.94),'Shin_L':(0,.32,-.95),'Foot_L':(-.35,-.90,-.20),'Thigh_R':(.30,-.62,-.72),'Shin_R':(.03,.70,-.72),'Foot_R':(.10,-.95,-.28)}
def action_values(action):
    values=[]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:values.append((curve.data_path,curve.array_index,curve.extrapolation,[(tuple(p.co),tuple(p.handle_left),tuple(p.handle_right),p.interpolation,p.handle_left_type,p.handle_right_type) for p in curve.keyframe_points]))
    return values
def immutable_state():
    meshes=[]
    for obj in lods:
        m=obj.data;meshes.append((tuple(tuple(v.co) for v in m.vertices),tuple((tuple(p.vertices),p.material_index,p.use_smooth) for p in m.polygons),tuple(tuple((g.group,g.weight) for g in v.groups) for v in m.vertices),tuple((key.name,tuple(tuple(v.co) for v in key.data)) for key in m.shape_keys.key_blocks),tuple(tuple(v.uv) for v in m.uv_layers[0].data),tuple(mat.name for mat in m.materials)))
    bones=tuple((b.name,b.parent.name if b.parent else '',tuple(tuple(row) for row in b.matrix_local),tuple(b.head_local),tuple(b.tail_local)) for b in rig.data.bones)
    return meshes,bones
immutable_before=immutable_state();actions_before={a.name:action_values(a) for a in bpy.data.actions if a.name.startswith('RB_')};assert len(actions_before)==13 and tuple(fall.frame_range)==(1.,19.)
hip=rig.pose.bones['RB_P06_Rider_L0_Hip'];assert hip.parent is None
rest=hip.bone.matrix_local.to_quaternion();world_up=hip.bone.matrix_local.to_3x3().inverted()@Vector((0,0,1))
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def mesh_bounds(regions=False):
    rows=[]
    for level,obj in enumerate(lods):
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
        try:
            values=array.array('f',[0])*(len(m.vertices)*3);m.vertices.foreach_get('co',values);row=ev.matrix_world[2]
            heights=[row[0]*values[i]+row[1]*values[i+1]+row[2]*values[i+2]+row[3] for i in range(0,len(values),3)]
            assert all(math.isfinite(v) for v in values)
            groups={}
            if regions:
                for i,v in enumerate(m.vertices):
                    name=max((g.weight,obj.vertex_groups[g.group].name) for g in v.groups)[1].replace('RB_P06_Rider_L0_','')
                    groups[name]=min(groups.get(name,10),heights[i])
            rows.append({'lod':level,'minimumWorldZ':min(heights),'maximumWorldZ':max(heights),'regionMinimumWorldZ':groups})
        finally:ev.to_mesh_clear()
    return rows
base=[];rig.animation_data.action=fall
for frame in range(1,20):
    scene.frame_set(frame);bpy.context.view_layer.update()
    base.append({p.name:(p.location.copy(),p.rotation_quaternion.copy(),p.scale.copy()) for p in rig.pose.bones})
rig.animation_data.action=None;key_rows=[];target_values=[];previous={}
for frame in range(1,20):
    for p in rig.pose.bones:p.location,p.rotation_quaternion,p.scale=base[frame-1][p.name]
    bpy.context.view_layer.update();t=(frame-1)/18.;body=Quaternion((0,1,0),math.radians(90*smooth(t)));blend=smooth((t-.05)/.70)
    if frame>1:
        hip.rotation_quaternion=rest.inverted()@body@rest;bpy.context.view_layer.update()
        for part in parts[1:]:
            p=rig.pose.bones['RB_P06_Rider_L0_'+part];old_location=p.location.copy();old_scale=p.scale.copy();current=p.matrix.copy()
            delta=(p.tail-p.head).normalized().rotation_difference((body@Vector(directions[part])).normalized());target=delta@current.to_quaternion();rotation=current.to_quaternion().slerp(target,blend)
            p.matrix=Matrix.Translation(p.head)@rotation.to_matrix().to_4x4();p.location=old_location;p.scale=old_scale;bpy.context.view_layer.update()
        uncorrected=mesh_bounds();minimum=min(row['minimumWorldZ'] for row in uncorrected)
        clearance=.004+(.019277578219771385-.004)*(1-smooth((frame-1)/2.0));offset=clearance-minimum
        hip.location+=world_up*offset;bpy.context.view_layer.update()
    else:offset=0
    values={}
    for part in parts:
        p=rig.pose.bones['RB_P06_Rider_L0_'+part];q=p.rotation_quaternion.copy()
        if part in previous and q.dot(previous[part])<0:q.negate()
        previous[part]=q;values[part]=(tuple(p.location),tuple(q))
    target_values.append(values);key_rows.append({'frame':frame,'authoredWorldVerticalCorrection':offset,'hipWorldHead':list(hip.head),'lods':mesh_bounds()})
curve_lookup={}
for layer in fall.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:curve_lookup[(curve.data_path,curve.array_index)]=curve
allowed=set();modified=[]
for part in parts:
    path='pose.bones["RB_P06_Rider_L0_'+part+'"].rotation_quaternion'
    for axis in range(4):
        allowed.add((path,axis));curve=curve_lookup[(path,axis)]
        for key in curve.keyframe_points:
            frame=int(round(key.co.x));assert abs(key.co.x-frame)<1e-6 and 1<=frame<=19
            key.co.y=target_values[frame-1][part][1][axis];key.handle_left_type='AUTO_CLAMPED';key.handle_right_type='AUTO_CLAMPED'
        curve.update();modified.append((path,axis))
path='pose.bones["RB_P06_Rider_L0_Hip"].location'
for axis in [1,2]:
    allowed.add((path,axis));curve=curve_lookup[(path,axis)]
    for key in curve.keyframe_points:
        frame=int(round(key.co.x));key.co.y=target_values[frame-1]['Hip'][0][axis];key.handle_left_type='AUTO_CLAMPED';key.handle_right_type='AUTO_CLAMPED'
    curve.update();modified.append((path,axis))
assert tuple(fall.frame_range)==(1.,19.)
assert immutable_before==immutable_state(),'Immutable mesh, UV, weight or rest rig changed'
actions_after={a.name:action_values(a) for a in bpy.data.actions if a.name.startswith('RB_')}
assert {k:v for k,v in actions_before.items() if k!='RB_Fall'}=={k:v for k,v in actions_after.items() if k!='RB_Fall'},'Other action changed'
assert [v for v in actions_before['RB_Fall'] if (v[0],v[1]) not in allowed]==[v for v in actions_after['RB_Fall'] if (v[0],v[1]) not in allowed],'Unauthorized Fall curve changed'
rig.animation_data.action=fall;dense=[]
for step in range(145):
    frame=1+step/8.;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
    dense.append({'frame':frame,'normalizedTime':(frame-1)/18.,'hipWorldHead':list(hip.head),'lods':mesh_bounds(regions=step%8==0)})
worst=min(row['minimumWorldZ'] for sample in dense for row in sample['lods']);maximum_up=max(dense[i]['hipWorldHead'][2]-dense[i-1]['hipWorldHead'][2] for i in range(1,len(dense)))
passed=worst>=0
source=ROOT+'ArtSource/P08/Golden/Ash/V7R2/RB_Golden_Ash_V7R2.blend'
if passed:
    rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=source,compress=True)
print('V7R2_AUTHORED_FALL '+json.dumps({'passedSourceFloorGate':passed,'saved':passed,'source':source if passed else None,'clip':'RB_Fall','durationSeconds':.75,'fps':24,'otherActionsExact':12,'geometryUvWeightsRestRigExact':True,'modifiedCurveChannels':modified,'allOtherFallChannelsExact':True,'firstPosePreserved':True,'worstDenseWorldZ':worst,'maximumHipRiseBetweenSubframes':maximum_up,'keys':key_rows,'dense':dense,'nativePending':True,'visualAccepted':False}))
