"""P06 patrol variant of our newly authored cafe-racer; inspected patrol-v1.png.
Base geometry reuse is intentional and not counted as an independent asset.
New hard panniers, beacon and fairing shoulders are authored below.
"""
# common.py is prepended by compose.py; no dynamic execution in Blender.
scene=begin('patrol')
palette=[((.69,.22,.035),.45,.26,'paint'),((.026,.032,.035),.65,.35,'brushed'),((.10,.12,.13),.78,.32,'brushed'),((.48,.52,.54),.90,.26,'brushed'),((.77,.70,.51),.1,.39,'paint'),((.018,.022,.025),0,.88,'rubber'),((.23,.105,.048),0,.7,'leather'),((.34,.25,.12),.82,.30,'brushed'),((.008,.021,.029),.48,.12,'paint'),((.63,.68,.63),.1,.12,'paint'),((.72,.24,.01),.1,.18,'paint'),((.48,.008,.006),.1,.18,'paint'),((.026,.032,.040),.6,.33,'brushed'),((.08,.058,.036),0,.8,'leather'),((.72,.62,.39),.75,.38,'brushed'),((.008,.012,.015),.3,.48,'rubber')]
palette[0]=((.74,.70,.57),.4,.30,'paint')
palette[4]=((.018,.045,.080),.25,.35,'paint')
palette[6]=((.025,.030,.033),0,.72,'leather')
palette[14]=((.005,.07,.65),.25,.14,'paint')
mat=atlas('RB_P06_PoliceMotorcycle',palette)
root=empty('RB_P06_PoliceMotorcycle');parts=[]
def B(*a,**kw):o=box(*a,mat=mat,**kw);parts.append(o);return o
def R(*a,**kw):o=rod(*a,mat=mat,**kw);parts.append(o);return o
def S(*a,**kw):o=sphere(*a,mat=mat,**kw);parts.append(o);return o
def T(*a,**kw):o=tube(*a,mat=mat,**kw);parts.append(o);return o
# Real-volume tank with smooth shoulder and tapered tail, twin original cream stripes.
S('Fuel tank',(0,.88,.19),(.46,.34,.66),0,segments=32,rings=16)
def shell_patch(name,front,back,rows,cols,tile):
    verts=[bv(p) for p in front+back];n=len(front);faces=[]
    for r in range(rows-1):
        for c in range(cols-1):
            i=r*cols+c;faces.extend([(i,i+1,i+1+cols,i+cols),(n+i+cols,n+i+cols+1,n+i+1,n+i)])
    edge=list(range(cols))+[r*cols+cols-1 for r in range(1,rows)]+list(range((rows-1)*cols+cols-2,(rows-1)*cols-1,-1))+[r*cols for r in range(rows-2,0,-1)]
    for i in range(len(edge)):a,b=edge[i],edge[(i+1)%len(edge)];faces.append((a,b,n+b,n+a))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);parts.append(finish(o,name,tile,mat))
for stripe in [-.075,.075]:
    front=[];back=[]
    for j in range(21):
        theta=-1.4+j*2.8/20
        for x in [stripe-.010,stripe+.010]:
            factor=math.sqrt(1-(x/.23)**2);front.append((x,.88+.1715*factor*math.cos(theta),.19+.3315*factor*math.sin(theta)));back.append((x,.88+.1703*factor*math.cos(theta),.19+.3303*factor*math.sin(theta)))
    shell_patch('Conforming cream stripe',front,back,21,2,4)
for side in [-1,1]:
    front=[];back=[]
    for j in range(9):
        a=-.52+j*.13
        for k in range(11):
            b=-.50+k*.10;x=.23*math.cos(a)*math.cos(b);y=.88+.17*math.sin(a);z=.15+.27*math.cos(a)*math.sin(b)
            front.append((side*(x+.003),y,z));back.append((side*(x+.001),y,z))
    shell_patch('Conforming rubber knee pad',front,back,9,11,15)
R('Fuel cap',(0,1.051,.29),(0,1.072,.29),.047,3,sides=24)
S('Bench seat',(0,.83,-.42),(.35,.13,.68),6,segments=28,rings=12)
for z in [-.68,-.60,-.52,-.44,-.36,-.28,-.20]:
    T('Seat stitched piping',[(-.156,.839,z),(-.12,.879,z),(0,.893,z),(.12,.879,z),(.156,.839,z)],.003,14,sides=5)
for x in [-.19,.19]:
    T('Tubular cradle',[(x,.84,-.62),(x,.77,-.28),(x,.43,-.22),(x,.35,.25),(x,.48,.45),(x,.93,.56)],.024,1)
    T('Subframe',[(x,.57,-.17),(x,.77,-.58),(x,.82,-.77)],.023,1)
    T('Seat rail',[(x,.76,-.08),(x,.765,-.75),(x*.7,.83,-.84)],.018,1)
    R('Swingarm',(x,.38,-.17),(x,.32,-.73),.031,2)
    R('Fork upper',(x*.75,.97,.57),(x*.75,.64,.67),.031,7,sides=16)
    R('Fork lower',(x*.75,.67,.67),(x*.75,.32,.80),.036,2,sides=16)
    R('Shock piston',(x,.70,-.57),(x,.37,-.73),.019,3)
    R('Shock body',(x,.66,-.59),(x,.45,-.69),.039,7)
    spiral=[]
    for i in range(61):
        t=i/60;spiral.append((x+.045*math.cos(t*math.tau*7),.66-.21*t,.59*-1-.10*t+.022*math.sin(t*math.tau*7)))
    T('Rear coil spring',spiral,.006,1,sides=5)
    R('Foot peg',(x,.35,-.1),(x*1.5,.35,-.1),.021,5)
# Engine: finned double cylinder block, machined cases, covers and exposed fasteners.
B('Crankcase',(0,.49,.03),(.35,.27,.37),2,bevel=.05)
for x in [-.19,.19]:
    R('Engine side cover',(x*.90,.47,.04),(x*1.13,.47,.04),.13,2,sides=24)
    for i in range(8):
        a=math.tau*i/8;R('Case fastener',(x*1.13,.47+.10*math.cos(a),.04+.10*math.sin(a)),(x*1.18,.47+.10*math.cos(a),.04+.10*math.sin(a)),.007,3,sides=6)
for x in [-.094,.094]:
    B('Cylinder barrel',(x,.68,.18),(.15,.23,.22),1,bevel=.013)
    for y in [.594,.623,.652,.681,.710,.739,.768]:B('Cooling fin',(x,y,.18),(.175,.012,.235),3,bevel=.002)
    B('Cylinder head',(x,.79,.18),(.17,.045,.23),2,bevel=.01)
    T('Header pipe',[(x,.72,.30),(x,.65,.40),(x,.49,.43),(x,.32,.34),(x,.30,.02),(x*.2+.25,.31,-.22)],.027,7,sides=12)
for y,z in [(.36,-.41),(.45,-.40)]:
    R('Brushed stacked silencer',(.24,y,z+.14),(.25,y+.06,z-.31),.055,3,sides=16)
    R('Exhaust dark bore',(.251,y+.061,z-.312),(.252,y+.065,z-.318),.039,15,sides=16)
    R('Exhaust collar',(.247,y+.043,z-.20),(.248,y+.050,z-.24),.057,7,sides=16)
B('Side cover',(0,.68,-.25),(.40,.20,.26),1,bevel=.023)
# Twin lamp nose, instruments, grips, brake/clutch levers and mirrors.
B('Front flyscreen backing',(0,.97,.68),(.35,.29,.065),1,bevel=.035)
S('Smoked flyscreen',(0,1.115,.642),(.35,.25,.027),8,segments=20,rings=10)
for x in [-.087,.087]:
    R('Headlamp shell',(x,.961,.694),(x,.961,.779),.092,1,sides=32)
    R('Headlamp metal rim',(x,.961,.778),(x,.961,.797),.087,3,sides=32)
    R('Headlamp lens',(x,.961,.797),(x,.961,.805),.075,9,sides=32)
    for dx in [-.04,-.02,0,.02,.04]:R('Lens flute',(x+dx,.911,.806),(x+dx,1.011,.806),.0018,4,sides=5)
    R('Instrument pod',(x,1.006,.46),(x,1.042,.46),.049,1,sides=20)
    R('Instrument glass',(x,1.042,.46),(x,1.045,.46),.043,8,sides=20)
for sign in [-1,1]:
    T('Handlebar',[(0,1.00,.51),(.16*sign,1.00,.51),(.25*sign,1.04,.46),(.35*sign,1.04,.40)],.016,2)
    R('Wrapped handgrip',(.28*sign,1.04,.44),(.39*sign,1.04,.37),.024,6,sides=16)
    T('Lever',[(.27*sign,1.03,.48),(.36*sign,1.02,.48),(.405*sign,1.02,.44)],.007,3)
    T('Mirror stalk',[(.26*sign,1.06,.47),(.32*sign,1.21,.48),(.38*sign,1.27,.47)],.009,1)
    S('Mirror black housing',(.385*sign,1.285,.469),(.10,.13,.025),1,segments=16,rings=8)
    S('Mirror silver glass',(.385*sign,1.285,.453),(.085,.11,.006),3,segments=16,rings=8)
    R('Indicator stem',(.15*sign,.92,.67),(.25*sign,.92,.67),.01,1)
    S('Amber front indicator',(.255*sign,.92,.68),(.066,.039,.05),10,segments=16,rings=8)
    S('Amber rear indicator',(.215*sign,.77,-.78),(.065,.04,.05),10,segments=16,rings=8)
B('Tail lamp',(0,.78,-.806),(.145,.055,.038),11,bevel=.018)
B('Tail plate',(0,.67,-.83),(.17,.10,.014),1,bevel=.006)
# Gracefully curved fenders as closed tube-swept shells, no paper-thin surfaces.
for z in [.80,-.73]:
    front=[];back=[]
    for j in range(17):
        a=-.74+j*1.48/16
        for x in [-.105,-.08,-.04,0,.04,.08,.105]:
            radius=.355-.021*(x/.105)**2;front.append((x,.32+radius*math.cos(a),z+radius*math.sin(a)));back.append((x,.32+(radius-.008)*math.cos(a),z+(radius-.008)*math.sin(a)))
    shell_patch('Continuous metal fender',front,back,17,7,1)
# New patrol-only equipment; the base design is the newly authored P06 motorcycle.
for side in [-1,1]:
    B('Patrol hard pannier',(side*.29,.65,-.53),(.21,.26,.39),4,bevel=.035)
    B('Pannier light reflective insert',(side*.400,.65,-.53),(.006,.085,.20),9,bevel=.006)
    B('Pannier lid seam',(side*.29,.735,-.53),(.213,.012,.393),1,bevel=.008)
    B('Pannier lock',(side*.405,.72,-.37),(.010,.025,.027),3,bevel=.004)
R('Rear beacon mast',(0,.86,-.76),(0,1.085,-.76),.016,1,sides=12)
R('Beacon dark base',(0,1.065,-.76),(0,1.09,-.76),.045,1,sides=16)
R('Blue patrol beacon',(0,1.09,-.76),(0,1.165,-.76),.037,14,sides=20)
S('Beacon rounded cap',(0,1.164,-.76),(.074,.028,.074),14,segments=20,rings=8)
S('Ivory fairing shoulders',(0,.966,.711),(.41,.31,.060),0,segments=24,rings=10)
body=join(parts,'RB_P06_PoliceMotorcycle_L0_Body',root)
wheel_objects=[]
for label,z in [('Front',.80),('Rear',-.73)]:
    pieces=[];pivot=(0,.32,z);joint=empty('RB_P06_PoliceMotorcycle_Wheel_'+label,root,pivot)
    pieces.append(torus('Tread tire',pivot,.248,.074,5,mat,segments=48,minor_segments=12))
    for x in [-.047,.047]:pieces.append(torus('Rim lip',(x,.32,z),.224,.016,7,mat,segments=36,minor_segments=6))
    pieces.append(rod('Wheel hub',(-.074,.32,z),(.074,.32,z),.048,2,mat,sides=20))
    for j in range(5):
        a=j*math.tau/5;pieces.append(rod('Cast wheel spoke',(0,.32+math.cos(a)*.044,z+math.sin(a)*.044),(0,.32+math.cos(a+.18)*.219,z+math.sin(a+.18)*.219),.021,7,mat,sides=6))
    for x in ([-.067,.067] if label=='Front' else [-.067]):
        pieces.append(torus('Vented brake rotor',(x,.32,z),.154,.014,3,mat,segments=36,minor_segments=6))
        for j in range(8):
            a=j*math.tau/8;pieces.append(rod('Rotor radial web',(x,.32+.06*math.cos(a),z+.06*math.sin(a)),(x,.32+.154*math.cos(a+.2),z+.154*math.sin(a+.2)),.010,3,mat,sides=5))
    wheel_objects.append(join(pieces,'RB_P06_PoliceMotorcycle_L0_'+label,joint,pivot))
for obj in [body]+wheel_objects:
    bpy.context.view_layer.objects.active=obj;mod=obj.modifiers.new('Web hero triangle budget','DECIMATE');mod.ratio=.68;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
for level,ratio in [(1,.44),(2,.17)]:
    for obj in [body]+wheel_objects:lod_copy(obj,obj.name.replace('_L0_','_L'+str(level)+'_'),ratio,obj.parent)
empty('SeatAnchor',root,(0,.89,-.30));empty('HandlebarLeft',root,(-.33,1.04,.40));empty('HandlebarRight',root,(.33,1.04,.40))
export(root,'RB_P06_PoliceMotorcycle');studio(target=(0,.65,0),camera_pos=(2.8,1.65,3.1));save_render('RB_P06_PoliceMotorcycle')
report={'concept':'ArtSource/Concepts/P06/patrol-v1.png','root':root.name,'lods':[],'atlas':1024,'materials':1,'front_z':.80,'rear_z':-.73,'wheel_radius':.322,'wheel_joints':[o.parent.name for o in wheel_objects],'uv_policy':'Smart-unwrapped individual surfaces reuse material tiles intentionally; no source image projection.'}
for level in range(3):
    meshes=[o for o in root.children_recursive if o.type=='MESH' and '_L'+str(level)+'_' in o.name]
    for o in meshes:o.data.calc_loop_triangles()
    report['lods'].append({'level':level,'triangles':sum(len(o.data.loop_triangles) for o in meshes),'renderers':len(meshes)})
print(json.dumps(report))

# Police rider is a palette variant of the original P06 rider geometry/rig.
police_rider_palette=[((.020,.045,.075),0,.67,'leather'),((.70,.66,.53),0,.54,'leather'),((.014,.026,.049),0,.85,'cloth'),((.029,.038,.047),0,.64,'leather'),((.75,.70,.55),0,.31,'paint'),((.01,.025,.044),.4,.09,'paint'),((.014,.017,.020),0,.8,'rubber'),((.36,.27,.12),.72,.30,'brushed'),((.025,.029,.032),0,.63,'leather'),((.022,.048,.080),0,.81,'cloth'),((.65,.63,.53),.1,.60,'cloth'),((.10,.105,.105),.7,.32,'brushed'),((.038,.036,.032),0,.7,'leather'),((.030,.036,.048),.1,.5,'leather'),((.016,.042,.073),.25,.32,'paint'),((.005,.008,.012),.1,.56,'rubber')]
atlas('RB_P06_PoliceRider',police_rider_palette,surface_source='RB_P06_Rider')
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P06/Hero/RB_P06_PoliceMotorcycle.blend')
print(json.dumps({'variant':'RB_P06_PoliceRider','geometrySource':'RB_P06_Rider.fbx','distinctGeometry':False,'palette':'navy jacket/pants, ivory shoulder/sleeve panels, dark gloves, ivory/navy helmet','concept':'ArtSource/Concepts/P06/patrol-v1.png'}))
