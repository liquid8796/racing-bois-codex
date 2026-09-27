"""Concept-led P08 identities; original P06 deformation skeleton and clips shared once."""
from mathutils import Quaternion
scene=p08_begin('riders');reports=[]
# The roster is filled only after each image has been generated and reviewed.
ROSTER={
    0:('ash',(.043,.044,.039),(.025,.027,.026),(.48,.29,.17),(.016,.012,.009),'armored','helmet-goggles'),
    1:('juno',(.047,.14,.15),(.027,.03,.03),(.40,.22,.12),(.025,.017,.014),'fitted','helmet-curly'),
    2:('mako',(.029,.043,.064),(.022,.027,.037),(.54,.36,.24),(.009,.01,.012),'armored','helmet-short'),
    3:('rook',(.18,.044,.035),(.027,.026,.024),(.64,.45,.32),(.20,.075,.034),'fitted','helmet-goggles'),
}
for index in SELECTED_INDICES:
    if index not in ROSTER:raise RuntimeError('No reviewed individual rider concept for '+str(index))
    slug,coat,trousers,skin,hair,cut,headwear=ROSTER[index]
    bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P06/Hero/RB_P06_Rider.blend',load_ui=False,use_scripts=False)
    scene=bpy.context.scene;name='RB_P08_Rider_'+str(index).zfill(2);root=bpy.data.objects['RB_P06_Rider'];root.name=name
    rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data_clear()
    for bone in rig.pose.bones:bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((1,0,0,0))
    for obj in list(bpy.data.objects):
        if obj!=root and obj!=rig:bpy.data.objects.remove(obj,do_unlink=True)
    palette=[(coat,0,.63,'leather'),((.033,.036,.04),0,.75,'leather'),(trousers,0,.83,'cloth'),((.11,.12,.13),.10,.48,'rubber'),(skin,0,.63,'leather'),((.025,.033,.045),.3,.14,'paint'),((.015,.019,.022),0,.78,'rubber'),((.38,.35,.30),.75,.35,'brushed'),(hair,0,.82,'cloth'),((.08,.075,.065),0,.80,'cloth'),((.70,.68,.61),0,.73,'cloth'),((.22,.25,.27),.7,.34,'brushed'),((.3,.075,.05),0,.68,'leather'),((.048,.035,.03),0,.72,'leather'),((.63,.65,.61),0,.46,'paint'),((.008,.01,.011),0,.88,'rubber')]
    palette[9]=(.49,.26,.064),0,.71,'leather'
    if index==1:palette[9]=(.67,.65,.55),0,.68,'leather'
    if index==2:palette[9]=(.64,.23,.055),0,.60,'leather'
    if index==3:palette[9]=(.038,.037,.033),0,.68,'leather'
    surface=name+'_Atlas';mat=atlas(surface,palette);pieces=[];prefix='RB_P06_Rider_L0_'
    def weight(obj,groups):
        for bone,value in groups.items():
            g=obj.vertex_groups.new(name=prefix+bone);g.add(list(range(len(obj.data.vertices))),value,'REPLACE')
        pieces.append(obj);return obj
    def S(label,pos,size,tile,bone,segments=20,rings=12):return weight(sphere(label,pos,size,tile,mat,segments,rings),{bone:1})
    def B(label,pos,size,tile,bone,bevel=.008):return weight(box(label,pos,size,tile,mat,bevel),{bone:1})
    def R(label,a,b,r,tile,bone,sides=10):return weight(rod(label,a,b,r,tile,mat,sides),{bone:1})
    def T(label,points,r,tile,bone,sides=6):return weight(tube(label,points,r,tile,mat,sides),{bone:1})
    def loft(label,rings,tile,lower,upper=None,joint=0,span=.1,sides=20):
        vertices=[];faces=[]
        for cx,y,cz,rx,rz in rings:
            for j in range(sides):a=j*math.tau/sides;vertices.append(bv((cx+rx*math.cos(a),y,cz+rz*math.sin(a))))
        for row in range(len(rings)-1):
            for j in range(sides):a=row*sides+j;b=row*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
        faces.extend([tuple(reversed(range(sides))),tuple((len(rings)-1)*sides+j for j in range(sides))])
        mesh=bpy.data.meshes.new(label);mesh.from_pydata(vertices,[],faces);mesh.update();obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);finish(obj,label,tile,mat)
        groups={}
        for vertex in mesh.vertices:
            t=max(0,min(1,(vertex.co.z-joint)/span+.5)) if upper else 0
            for bone,value in ({lower:1-t,upper:t} if upper else {lower:1}).items():
                if value<1e-8:continue
                if bone not in groups:groups[bone]=obj.vertex_groups.new(name=prefix+bone)
                groups[bone].add([vertex.index],value,'REPLACE')
        pieces.append(obj);return obj
    broad=1.03 if cut in ['armored','vest'] else .91 if cut in ['fitted','racing'] else 1.0
    loft('Tailored '+slug+' torso',[(0,.94,0,.151,.094),(0,1.02,0,.155,.103),(0,1.15,0,.169,.110),(0,1.28,0,.19*broad,.109),(0,1.375,0,.20*broad,.10),(0,1.418,0,.086,.066)],0,'Hip','Torso',1.02,.14,24)
    for side,sign in [('L',-1),('R',1)]:
        B('Tailored shoulder contrast', (sign*.167,1.361,.024),(.10,.073,.173),9,'Torso',.015)
        if index==0:T('Amber sleeve inset',[(sign*.257,1.31,.072),(sign*.251,1.17,.070),(sign*.247,.92,.052)],.013,9,'UpperArm_'+side,8)
    loft('Trousers pelvis',[(0,.84,0,.13,.083),(0,.89,0,.152,.104),(0,.96,0,.152,.098)],2,'Hip')
    for side,sign in [('L',-1),('R',1)]:
        x=.25*sign;leg=.1175*sign
        loft('Tailored sleeve '+side,[(x,1.38,0,.082,.078),(x,1.25,0,.075,.075),(x,1.09,0,.067,.067),(x,.99,.012,.063,.060),(x,.825,.02,.045,.043)],0,'Forearm_'+side,'UpperArm_'+side,1.09,.10)
        loft('Articulated trouser leg '+side,[(leg,.90,0,.102,.098),(leg,.73,0,.087,.087),(leg,.505,.015,.073,.073),(leg,.34,.007,.063,.065),(leg,.14,0,.048,.052)],2,'Shin_'+side,'Thigh_'+side,.505,.11)
        loft('Boot shaft '+side,[(leg,.12,0,.055,.060),(leg,.27,0,.060,.067)],6,'Shin_'+side)
        S('Boot toe '+side,(leg,.064,.074),(.140,.112,.239),6,'Foot_'+side)
        B('Boot sole '+side,(leg,.021,.064),(.145,.035,.263),15,'Foot_'+side,.013)
        for yy in [.14,.19]:B('Boot strap '+side,(leg,yy,.062),(.119,.019,.025),3,'Shin_'+side,.004)
        S('Glove palm '+side,(x,.786,.025),(.086,.098,.055),1,'Hand_'+side)
        for j in range(4):S('Glove finger '+side,(x+(j-1.5)*.019,.738,.028),(.017,.057,.023),1,'Hand_'+side,12,8)
        S('Glove thumb '+side,(x-sign*.048,.773,.026),(.025,.050,.03),1,'Hand_'+side,12,8)
        if cut in ['armored','racing']:
            S('Rigid shoulder protector '+side,(x,1.366,-.004),(.15,.087,.15),9 if index==2 else 3,'UpperArm_'+side)
            S('Knee protector '+side,(leg,.481,.069),(.129,.15,.043),3,'Shin_'+side)
        if cut in ['vest','utility']:
            B('Chest utility pocket '+side,(sign*.107,1.223,.108),(.14,.13,.027),9,'Torso',.015)
            B('Pocket flap '+side,(sign*.107,1.28,.119),(.15,.034,.015),0,'Torso',.006)
        T('Sleeve construction seam '+side,[(x+sign*.064,1.30,.041),(x+sign*.058,1.15,.043),(x+sign*.045,.87,.045)],.0018,10,'UpperArm_'+side)
        B('Trouser rear pocket '+side,(leg,.883,-.098),(.083,.08,.008),9,'Hip',.012)
    loft('Neck',[(0,1.398,0,.057,.055),(0,1.465,0,.057,.053)],4,'Head')
    loft('Jacket collar',[(0,1.394,0,.090,.075),(0,1.436,0,.078,.064)],0,'Head')
    T('Front zipper',[(0,.96,.105),(0,1.13,.115),(0,1.345,.104)],.0025,7,'Torso')
    # Sculpted facial volumes remain in the skinned renderer, visible in real-time cutscenes.
    loft('Sculpted facial planes',[(0,1.466,.035,.047,.044),(0,1.50,.017,.083,.088),(0,1.54,.006,.101,.103),(0,1.59,0,.113,.116),(0,1.645,-.005,.107,.111),(0,1.70,-.013,.097,.105),(0,1.75,-.017,.067,.080),(0,1.775,-.02,.015,.020)],4,'Head',sides=32)
    for sign in [-1,1]:S('Zygomatic cheek plane',(sign*.067,1.587,.101),(.066,.066,.025),4,'Head',20,12)
    for sign in [-1,1]:
        S('Ear',(sign*.115,1.592,.01),(.040,.075,.032),4,'Head',16,10)
        S('Ear inner fold',(sign*.129,1.596,.015),(.012,.041,.017),12,'Head',12,8)
        S('Eye socket shadow',(sign*.048,1.631,.113),(.067,.034,.012),13,'Head',20,10)
        S('Eye white',(sign*.048,1.629,.122),(.053,.020,.010),14,'Head',20,10)
        S('Iris',(sign*.048,1.629,.129),(.020,.020,.006),8,'Head',16,10)
        S('Pupil',(sign*.048,1.629,.132),(.009,.010,.003),15,'Head',12,8)
        S('Eye highlight',(sign*.045,1.634,.134),(.004,.004,.0015),14,'Head',10,6)
        T('Eyebrow',[(sign*.024,1.659,.119),(sign*.049,1.667,.119),(sign*.079,1.654,.109)],.006,8,'Head')
    S('Nose bridge',(0,1.608,.126),(.036,.072,.050),4,'Head',20,12)
    S('Nose tip',(0,1.585,.150),(.045,.033,.030),4,'Head',20,10)
    for sign in [-1,1]:S('Nostril',(sign*.015,1.578,.153),(.011,.008,.007),13,'Head',12,8)
    S('Upper lip',(0,1.548,.123),(.065,.012,.018),12,'Head',20,8)
    S('Lower lip',(0,1.538,.122),(.060,.011,.015),12,'Head',20,8)
    T('Mouth crease',[(-.032,1.543,.130),(0,1.541,.134),(.032,1.543,.130)],.0015,13,'Head',5)
    # Hair silhouette varies independently of cloth colour and fits concept headwear.
    S('Hair crown',(0,1.727,-.006),(.233,.095,.243),8,'Head',28,14)
    for sign in [-1,1]:S('Hair temple',(sign*.092,1.675,-.025),(.055,.093,.151),8,'Head',20,12)
    if headwear=='long':
        for sign in [-1,1]:S('Long side hair',(sign*.102,1.553,-.050),(.072,.30,.157),8,'Head',20,14)
        S('Hair back',(0,1.568,-.088),(.20,.30,.108),8,'Head',24,16)
    if headwear.startswith('helmet'):
        helmet_tile=10 if index in [0,1] else 1
        S('Open face helmet crown',(0,1.696,-.041),(.280,.232,.269),helmet_tile,'Head',32,20)
        for sign in [-1,1]:
            S('Helmet side cheek',(sign*.122,1.57,-.020),(.048,.17,.158),helmet_tile,'Head',24,14)
            S('Helmet cheek cushion',(sign*.108,1.573,.014),(.026,.146,.103),1,'Head',20,12)
            R('Helmet chinstrap buckle',(sign*.118,1.495,.020),(sign*.122,1.495,.045),.012,7,'Head',12)
        if headwear=='helmet-goggles':
            for sign in [-1,1]:
                B('Goggles raised housing',(sign*.064,1.757,.074),(.104,.068,.030),7,'Head',.017)
                B('Raised goggle lens',(sign*.064,1.757,.091),(.080,.043,.008),5,'Head',.013)
            T('Goggle leather strap',[(-.132,1.765,-.037),(-.12,1.766,.036),(0,1.752,.096),(.12,1.766,.036),(.132,1.765,-.037)],.009,1,'Head')
        if headwear=='helmet-curly':
            for j in range(12):
                a=j*math.tau/12;S('Curled ponytail strand',(.069*math.cos(a),1.49+.035*math.sin(a),-.136),(.065,.093,.080),8,'Head',14,10)
        for sign in [-1,1]:T('Visible hair fringe',[(sign*.092,1.70,.075),(sign*.08,1.665,.107),(sign*.06,1.679,.112)],.012,8,'Head')
    if headwear=='goggles':
        for sign in [-1,1]:
            B('Goggle housing',(sign*.056,1.631,.13),(.088,.052,.032),1,'Head',.012)
            B('Goggle glass',(sign*.056,1.631,.15),(.073,.034,.011),5,'Head',.008)
        R('Goggle bridge',(-.012,1.63,.148),(.012,1.63,.148),.008,1,'Head')
    mesh=join(pieces,name+'_L0_Skin',rig)
    for vertex in mesh.data.vertices:
        total=sum(g.weight for g in vertex.groups)
        for g in vertex.groups:mesh.vertex_groups[g.group].add([vertex.index],g.weight/total,'REPLACE')
    for level,ratio in [(1,.47),(2,.20)]:lod_copy(mesh,name+'_L'+str(level)+'_Skin',ratio,rig)
    for obj in [o for o in rig.children if o.type=='MESH']:
        mod=obj.modifiers.new('Original shared deformation rig','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
    export(root,name,False)
    expression_counts=[]
    for skin_mesh in [o for o in rig.children if o.type=='MESH']:
        skin_mesh.shape_key_add(name='Basis')
        happy=skin_mesh.shape_key_add(name='Happy');focused=skin_mesh.shape_key_add(name='Focused');happy_count=0;focus_count=0
        for vertex in skin_mesh.data.vertices:
            co=vertex.co;ux=-co.x;uy=co.z;uz=-co.y
            if 1.521<uy<1.558 and uz>.112 and abs(ux)<.045:
                happy.data[vertex.index].co.z+=.004+.012*(min(1,abs(ux)/.035)**2);happy_count+=1
            if 1.648<uy<1.675 and uz>.102 and .016<abs(ux)<.083:
                focused.data[vertex.index].co.z-=.008*(1-min(1,abs(ux)/.083));focus_count+=1
            if 1.529<uy<1.553 and uz>.113 and abs(ux)<.043:
                focused.data[vertex.index].co.x*=.95;focus_count+=1
        expression_counts.append({'mesh':skin_mesh.name,'happyVertices':happy_count,'focusedVertices':focus_count})
    # Export final production blendshapes without changing the audited rest topology.
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for obj in root.children_recursive:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=OUT+name+'.fbx',use_selection=True,object_types={'MESH','EMPTY','ARMATURE'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    studio(target=(0,.93,0),camera_pos=(1.7,1.16,3.1),resolution=(960,1200));scene.render.film_transparent=False;scene.cycles.samples=24
    source='ArtSource/P08/'+name+'.blend'
    scene.render.filepath=ROOT+'docs/p08/art/'+name+'-render.png';bpy.ops.render.render(write_still=True)
    portrait_records=[]
    scene.render.resolution_x=512;scene.render.resolution_y=512;scene.cycles.samples=24
    camera=scene.camera;camera.location=bv((.11,1.627,1.035));camera.rotation_euler=(bv((0,1.598,.018))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=75
    for state in [0,1,2]:
        for skin_mesh in [o for o in rig.children if o.type=='MESH']:
            skin_mesh.data.shape_keys.key_blocks['Happy'].value=1 if state==1 else 0
            skin_mesh.data.shape_keys.key_blocks['Focused'].value=1 if state==2 else 0
        head=rig.pose.bones[prefix+'Head'];head.rotation_quaternion=Quaternion((0,1,0),math.radians(-4 if state==1 else 2 if state==2 else 0))
        portrait='Assets/RacingBois/Art/P08/Portraits/RB_P08_Portrait_'+str(index).zfill(2)+'_'+str(state).zfill(2)+'.png'
        scene.render.filepath=ROOT+portrait;bpy.ops.render.render(write_still=True)
        portrait_records.append({'identityIndex':index,'state':state,'path':portrait,'width':512,'height':512,'source':source,'method':'Actual concept-led skinned model; original facial blendshape and head pose; consistent neutral studio; no generated portrait pasted into output.'})
    for skin_mesh in [o for o in rig.children if o.type=='MESH']:
        skin_mesh.data.shape_keys.key_blocks['Happy'].value=0;skin_mesh.data.shape_keys.key_blocks['Focused'].value=0
    rig.pose.bones[prefix+'Head'].rotation_quaternion=Quaternion((1,0,0,0))
    bpy.ops.wm.save_as_mainfile(filepath=ROOT+source)
    report=asset_report(root,'ArtSource/Concepts/P08/Riders/'+str(index).zfill(2)+'-'+slug+'-v1.png',surface,'rider',source)
    report['displayName']=slug.title();report['identityIndex']=index;report['sharedBoneCount']=15;report['newAnimationClips']=0;report['portraits']=portrait_records;report['expressionShapes']=expression_counts
    reports.append(report)
print(json.dumps({'batch':'riders','assets':reports,'conceptFirst':True}))
