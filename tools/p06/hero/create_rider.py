"""Original P06 skinned rider, authored after rider-v1.png inspection."""
# common.py is prepended by compose.py; no dynamic execution in Blender.
from mathutils import Quaternion,Matrix
scene=begin('rider')
for previous in list(bpy.data.actions):
    if previous.name.startswith('RB_'):bpy.data.actions.remove(previous)
palette=[((.033,.037,.039),0,.67,'leather'),((.32,.17,.045),0,.54,'leather'),((.012,.020,.034),0,.85,'cloth'),((.065,.073,.079),0,.64,'leather'),((.75,.70,.55),0,.31,'paint'),((.01,.025,.044),.4,.09,'paint'),((.014,.017,.020),0,.8,'rubber'),((.36,.27,.12),.72,.30,'brushed'),((.13,.065,.02),0,.63,'leather'),((.1,.125,.15),0,.81,'cloth'),((.62,.60,.50),.1,.60,'cloth'),((.10,.105,.105),.7,.32,'brushed'),((.038,.036,.032),0,.7,'leather'),((.16,.105,.035),.1,.5,'leather'),((.7,.30,.025),.25,.32,'paint'),((.005,.008,.012),.1,.56,'rubber')]
mat=atlas('RB_P06_Rider',palette)
root=empty('RB_P06_Rider');pieces=[];prefix='RB_P06_Rider_L0_'
spec=[('Hip',(0,.89,0),(0,1.02,0),None),('Torso',(0,1.02,0),(0,1.41,0),'Hip'),('Head',(0,1.41,0),(0,1.69,0),'Torso')]
for side,x in [('L',-.25),('R',.25)]:
    spec.extend([('UpperArm_'+side,(x,1.375,0),(x,1.09,0),'Torso'),('Forearm_'+side,(x,1.09,0),(x,.825,.02),'UpperArm_'+side),('Hand_'+side,(x,.825,.02),(x,.745,.025),'Forearm_'+side),('Thigh_'+side,(x*.47,.90,0),(x*.47,.505,.015),'Hip'),('Shin_'+side,(x*.47,.505,.015),(x*.47,.115,0),'Thigh_'+side),('Foot_'+side,(x*.47,.115,0),(x*.47,.075,.155),'Shin_'+side)])
data=bpy.data.armatures.new('RB_P06_Rider_GenericRig');rig=bpy.data.objects.new('RB_P06_Rider_Rig',data);scene.collection.objects.link(rig);rig.parent=root;bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,head,tail,parent in spec:
    bone=data.edit_bones.new(prefix+name);bone.head=bv(head);bone.tail=bv(tail)
    if parent:bone.parent=data.edit_bones[prefix+parent]
    bone.use_deform=True
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
def weight(o,weights):
    for bone,value in weights.items():
        group=o.vertex_groups.new(name=prefix+bone);group.add(list(range(len(o.data.vertices))),value,'REPLACE')
    pieces.append(o);return o
def S(name,pos,size,tile,bone,segments=20,rings=10):return weight(sphere(name,pos,size,tile,mat,segments,rings),{bone:1})
def B(name,pos,size,tile,bone,bevel=.008):return weight(box(name,pos,size,tile,mat,bevel),{bone:1})
def R(name,a,b,r,tile,bone,sides=10):return weight(rod(name,a,b,r,tile,mat,sides),{bone:1})
def T(name,points,r,tile,bone,sides=6):return weight(tube(name,points,r,tile,mat,sides),{bone:1})
def loft(name,rings,tile,weight_spec,sides=20):
    verts=[];faces=[]
    for cx,y,cz,rx,rz in rings:
        for j in range(sides):a=j*math.tau/sides;verts.append(bv((cx+rx*math.cos(a),y,cz+rz*math.sin(a))))
    for k in range(len(rings)-1):
        for j in range(sides):a=k*sides+j;b=k*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),tuple((len(rings)-1)*sides+j for j in range(sides))]);mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);finish(o,name,tile,mat)
    groups={}
    for v in mesh.vertices:
        values={weight_spec[0]:1} if len(weight_spec)==1 else blend(v.co.z,weight_spec[0],weight_spec[1],weight_spec[2],weight_spec[3])
        for bone,w in values.items():
            if bone not in groups:groups[bone]=o.vertex_groups.new(name=prefix+bone)
            groups[bone].add([v.index],w,'REPLACE')
    pieces.append(o);return o
def blend(y,joint,above,below,span=.07):
    t=max(0,min(1,(y-joint)/span+.5));return {above:t,below:1-t}
# Continuous torso and limb surfaces with intermediate loops for deformation.
loft('Tailored jacket',[(0,.935,0,.154,.093),(0,.98,0,.165,.104),(0,1.05,0,.157,.103),(0,1.13,0,.166,.109),(0,1.22,0,.187,.118),(0,1.31,0,.205,.108),(0,1.38,0,.19,.095),(0,1.415,0,.103,.066)],0,(1.015,'Torso','Hip',.16),24)
loft('Jeans pelvis',[(0,.84,0,.13,.085),(0,.89,0,.153,.108),(0,.96,0,.157,.103)],2,('Hip',),20)
for side,sign in [('L',-1),('R',1)]:
    x=.25*sign;leg=.1175*sign
    loft('Jacket sleeve '+side,[(x,1.385,0,.083,.077),(x,1.33,0,.089,.084),(x,1.25,0,.078,.078),(x,1.16,0,.067,.070),(x,1.11,0,.071,.069),(x,1.075,0,.068,.066),(x,1.025,.006,.068,.064),(x,.94,.012,.057,.055),(x,.86,.018,.049,.045),(x,.825,.02,.048,.043)],0,(1.09,'UpperArm_'+side,'Forearm_'+side,.09),20)
    loft('Denim leg '+side,[(leg,.91,0,.105,.10),(leg,.83,0,.105,.098),(leg,.72,0,.093,.088),(leg,.61,.007,.079,.079),(leg,.545,.013,.072,.074),(leg,.505,.015,.074,.073),(leg,.47,.013,.073,.071),(leg,.40,.010,.068,.067),(leg,.30,.006,.061,.064),(leg,.20,.002,.054,.058),(leg,.135,0,.048,.052)],2,(.505,'Thigh_'+side,'Shin_'+side,.10),20)
    S('Shoulder amber pad '+side,(x,1.359,0),(.180,.121,.178),1,'UpperArm_'+side)
    S('Shoulder armor '+side,(x,1.385,.01),(.128,.082,.135),3,'UpperArm_'+side,16,8)
    # Two cream leather stripes around each bicep, weighted to upper arm.
    for y in [1.226,1.198]:loft('Ivory sleeve band '+side,[(x,y-.008,0,.078,.079),(x,y+.008,0,.081,.081)],10,('UpperArm_'+side,),20)
    S('Elbow protection '+side,(x,1.071,-.055),(.115,.14,.041),3,'Forearm_'+side,16,8)
    S('Knee protection '+side,(leg,.473,.073),(.128,.151,.038),3,'Shin_'+side,20,10)
    for yy in [.58,.599,.618]:
        T('Knee stretch ribs '+side,[(leg-.057,yy,.064),(leg,yy+.007,.082),(leg+.057,yy,.064)],.005,3,'Thigh_'+side)
    # Boot body/cuff, tailored heel and toe, raised instep stitch strips.
    loft('Boot shaft '+side,[(leg,.12,0,.055,.061),(leg,.19,0,.061,.065),(leg,.27,0,.065,.071),(leg,.285,0,.066,.073)],6,('Shin_'+side,),20)
    S('Boot toe '+side,(leg,.066,.074),(.139,.118,.245),6,'Foot_'+side,24,10)
    B('Boot rubber sole '+side,(leg,.023,.061),(.144,.040,.267),15,'Foot_'+side,.015)
    B('Shin boot armor '+side,(leg,.204,.065),(.080,.106,.027),3,'Shin_'+side,.014)
    for yy in [.125,.15]:T('Boot instep rib '+side,[(leg-.051,yy,.030),(leg,yy+.009,.068),(leg+.051,yy,.030)],.004,7,'Shin_'+side)
    B('Boot ankle buckle '+side,(leg+sign*.061,.12,.016),(.016,.041,.036),7,'Shin_'+side,.004)
    # Gloved hands and fingers are closed geometry, one skinned renderer after join.
    S('Glove palm '+side,(x,.786,.021),(.092,.098,.057),1,'Hand_'+side,20,10)
    S('Glove knuckle guard '+side,(x,.789,.047),(.074,.048,.020),3,'Hand_'+side,16,8)
    for j in range(4):
        dx=(j-1.5)*.020
        S('Gloved finger '+side,(x+dx,.738,.027),(.018,.065-.004*abs(j-1),.023),1,'Hand_'+side,12,8)
    S('Thumb '+side,(x-sign*.052,.775,.031),(.025,.059,.030),1,'Hand_'+side,12,8)
    # Stitching/seams and zipper pockets add readable construction without textures copied from concept.
    T('Jacket flank seam '+side,[(sign*.145,.968,.073),(sign*.142,1.075,.085),(sign*.17,1.25,.075),(sign*.16,1.35,.062)],.0019,7,'Torso')
    T('Chest pocket zipper '+side,[(sign*.115,1.245,.108),(sign*.12,1.14,.104)],.0025,7,'Torso')
    B('Rear jeans pocket '+side,(leg,.882,-.094),(.086,.092,.010),9,'Hip',.01)
# Center zip, collar and clean helmet with curved visor shell.
T('Jacket center zipper',[(0,.96,.106),(0,1.08,.109),(0,1.24,.121),(0,1.355,.097)],.003,7,'Torso')
for yy in [1.002,1.034,1.066,1.098,1.13,1.162,1.194,1.226,1.258,1.29,1.322]:B('Zip teeth',(0,yy,.115),(.012,.003,.004),11,'Torso',.001)
loft('Raised leather collar',[(0,1.386,0,.09,.075),(0,1.436,0,.086,.069)],0,('Head',),24)
S('Helmet shell',(0,1.602,.0),(.286,.375,.316),4,'Head',32,20)
def helmet_patch(name,theta0,theta1,phi0,phi1,tile,rows,cols,offset=.003):
    front=[];back=[]
    for r in range(rows):
        theta=theta0+(theta1-theta0)*r/(rows-1)
        for c in range(cols):
            phi=phi0+(phi1-phi0)*c/(cols-1)
            for array,off in [(front,offset),(back,offset-.001)]:array.append(bv(((.143+off)*math.cos(theta)*math.sin(phi),1.602+(.1875+off)*math.sin(theta),(.158+off)*math.cos(theta)*math.cos(phi))))
    verts=front+back;n=len(front);faces=[]
    for r in range(rows-1):
        for c in range(cols-1):i=r*cols+c;faces.extend([(i,i+1,i+1+cols,i+cols),(n+i+cols,n+i+cols+1,n+i+1,n+i)])
    edge=list(range(cols))+[r*cols+cols-1 for r in range(1,rows)]+list(range((rows-1)*cols+cols-2,(rows-1)*cols-1,-1))+[r*cols for r in range(rows-2,0,-1)]
    for i in range(len(edge)):a,b=edge[i],edge[(i+1)%len(edge)];faces.append((a,b,n+b,n+a))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);finish(o,name,tile,mat);weight(o,{'Head':1})
helmet_patch('Navy shield visor',-.24,.42,-1.19,1.19,5,8,25,.004)
for a,b in [(-.20,-.065),(.065,.20)]:helmet_patch('Amber helmet crown stripe',.46,2.95,a,b,14,26,3,.002)
helmet_patch('Helmet chin vent',-.83,-.51,-.28,.28,15,4,9,.004)
for sign in [-1,1]:
    R('Helmet visor pivot',(sign*.138,1.636,.048),(sign*.151,1.636,.048),.029,3,'Head',20)
    R('Helmet pivot bolt',(sign*.151,1.636,.048),(sign*.153,1.636,.048),.013,11,'Head',16)
mesh=join(pieces,'RB_P06_Rider_L0_Skin',rig)
# Join bakes rest transforms. Normalize every vertex; retain at most two smooth influence weights.
for v in mesh.data.vertices:
    weights=[(g.group,g.weight) for g in v.groups if g.weight>0]
    total=sum(w for _,w in weights)
    if total<=0:raise RuntimeError('Unweighted rider vertex')
    for g,w in weights:mesh.vertex_groups[g].add([v.index],w/total,'REPLACE')
bpy.context.view_layer.objects.active=mesh
budget=mesh.modifiers.new('Web hero triangle budget','DECIMATE');budget.ratio=.72;budget.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=budget.name)
for level,ratio in [(1,.48),(2,.20)]:lod_copy(mesh,'RB_P06_Rider_L'+str(level)+'_Skin',ratio,rig)
for obj in [o for o in rig.children if o.type=='MESH']:
    # Unity's standard SkinnedMeshRenderer uses linear blend skinning; keep
    # the source review deformation algorithm identical to production.
    mod=obj.modifiers.new('Generic deformation rig','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
# Authored action rotations in Unity world convention -> Blender -> local bone basis.
basis=Matrix(((-1,0,0),(0,0,-1),(0,1,0))).to_4x4()
def bone_rotation(name,xyz):
    rx,ry,rz=[math.radians(v) for v in xyz]
    # Explicit Unity handedness reflection is incorporated by the same model basis used by runtime.
    rot=Matrix.Rotation(rz,4,'Z')@Matrix.Rotation(ry,4,'Y')@Matrix.Rotation(rx,4,'X')
    transformed=basis@rot@basis.inverted();rest=data.bones[prefix+name].matrix_local.to_4x4()
    return (rest.inverted()@transformed@rest).to_quaternion()
def riding():return {'Torso':(35,0,0),'Thigh_L':(-62,0,-7),'Thigh_R':(-62,0,7),'Shin_L':(90,0,0),'Shin_R':(90,0,0),'UpperArm_L':(-95,-10,0),'UpperArm_R':(-95,10,0),'Forearm_L':(-20,0,0),'Forearm_R':(-20,0,0)}
def get_pose(kind,t,sign=1):
    p=riding();f=math.sin(t*math.pi);suffix='L' if sign<0 else 'R'
    if kind=='Lean':p['Torso']=(35,0,10*sign);p['Head']=(0,-6*sign,-4*sign)
    elif kind=='Attack':p['UpperArm_'+suffix]=(-30,sign*30*f,sign*85*f);p['Forearm_'+suffix]=(-35*(1-f),0,0);p['Torso']=(12,sign*25*f,0)
    elif kind=='Kick':p['Thigh_'+suffix]=(-55,0,sign*75*f);p['Shin_'+suffix]=(90*(1-f*.6),0,0)
    elif kind=='Hit':p['Torso']=(18-16*f,0,12*f);p['Head']=(-15*f,10*f,0)
    elif kind=='Fall':
        f=math.sin(t*math.pi*.5);p={'Hip':(15*f,0,82*f),'Torso':(-25*f,0,0),'UpperArm_L':(-55,0,-55*f),'UpperArm_R':(-25,0,45*f),'Thigh_L':(-20*f,0,-20*f),'Thigh_R':(20*f,0,15*f),'Shin_L':(45*f,0,0),'Shin_R':(20*f,0,0)}
    elif kind=='Run':
        swing=math.sin(t*math.tau)*34;p={'Torso':(8,0,0),'Thigh_L':(swing,0,0),'Thigh_R':(-swing,0,0),'Shin_L':(max(0,-swing)*1.5,0,0),'Shin_R':(max(0,swing)*1.5,0,0),'UpperArm_L':(-swing,0,-8),'UpperArm_R':(swing,0,8),'Forearm_L':(-55,0,0),'Forearm_R':(-55,0,0),'Head':(-3,0,0)}
    elif kind=='Remount':p={key:tuple(a*(t*t*(3-2*t)) for a in value) for key,value in p.items()}
    elif kind=='Idle':p={}
    return p
def make_action(name,duration,kind,loop=False,sign=1):
    rig.animation_data_create();action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    frames=max(2,round(duration*30));action['loop']=loop;action['root_motion']=False
    for frame in range(frames+1):
        t=frame/frames;values=get_pose(kind,t,sign)
        for bone in rig.pose.bones:
            short=bone.name[len(prefix):];bone.rotation_mode='QUATERNION';bone.rotation_quaternion=bone_rotation(short,values.get(short,(0,0,0)));bone.keyframe_insert(data_path='rotation_quaternion',frame=frame+1,group=short)
    return {'name':name,'frames':[1,frames+1],'seconds':duration,'loop':loop,'rootMotion':False}
actions=[]
actions.append(make_action('RB_Ride',1,'Ride',True))
for side,sign in [('Left',-1),('Right',1)]:
    actions.append(make_action('RB_Lean'+side,1,'Lean',True,sign));actions.append(make_action('RB_Attack'+side,.5,'Attack',False,sign));actions.append(make_action('RB_Kick'+side,.55,'Kick',False,sign))
for name,duration,loop in [('Hit',.35,False),('Fall',.6,False),('Run',.8,True),('Remount',.8,False),('Idle',1,True)]:actions.append(make_action('RB_'+name,duration,name,loop))
rig.animation_data.action=None
for bone in rig.pose.bones:bone.rotation_quaternion=Quaternion((1,0,0,0))
scene.render.fps=30;scene.frame_start=1;scene.frame_end=31
export(root,'RB_P06_Rider',True)
studio(target=(0,.95,0),camera_pos=(1.8,1.22,3.1),resolution=(1000,1200));save_render('RB_P06_Rider')
report={'concept':'ArtSource/Concepts/P06/rider-v1.png','root':root.name,'rig':rig.name,'rigType':'Generic skinned','rootMotion':False,'bonePrefix':prefix,'bones':[name for name,_,_,_ in spec],'actions':actions,'lods':[],'materials':1,'textureMax':1024,'restHeightMeters':1.79}
for level in range(3):
    o=bpy.data.objects['RB_P06_Rider_L'+str(level)+'_Skin'];o.data.calc_loop_triangles();report['lods'].append({'level':level,'triangles':len(o.data.loop_triangles),'renderers':1})
print(json.dumps(report))
