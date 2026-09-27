"""P08 environment kits. Only a reviewed concept may select its corresponding batch."""
scene=p08_begin(BATCH);reports=[]
concepts={'neon':'neon-district-v1.png','ridge':'ridge-pass-v1.png','coast':'coastal-line-v1.png','orchard':'orchard-road-v1.png'}
concept='ArtSource/Concepts/P08/Environments/'+concepts[BATCH]
surface='RB_P08_'+BATCH.title()+'_Atlas'
palette=[((.30,.32,.31),0,.88,'concrete'),((.07,.23,.24),.35,.40,'paint'),((.045,.055,.060),.70,.42,'brushed'),((.42,.44,.42),.84,.32,'brushed'),((.62,.44,.19),0,.73,'wood'),((.10,.18,.16),0,.90,'foliage'),((.035,.06,.065),.15,.15,'paint'),((.70,.57,.32),0,.38,'paint'),((.21,.18,.13),0,.91,'wood'),((.08,.27,.29),.25,.32,'paint'),((.40,.13,.055),0,.74,'paint'),((.69,.67,.57),0,.82,'concrete'),((.19,.23,.18),0,.85,'foliage'),((.62,.61,.54),0,.80,'concrete'),((.84,.65,.20),.2,.34,'paint'),((.027,.037,.031),0,.90,'rubber')]
if BATCH=='ridge':
    palette[0]=((.35,.37,.36),0,.87,'concrete');palette[1]=((.24,.16,.085),0,.86,'wood');palette[5]=((.10,.17,.07),0,.89,'foliage');palette[10]=((.58,.055,.025),0,.6,'paint')
elif BATCH=='coast':
    palette[0]=((.53,.50,.39),0,.9,'concrete');palette[1]=((.075,.31,.34),0,.67,'paint');palette[5]=((.20,.31,.065),0,.88,'foliage');palette[10]=((.69,.075,.037),0,.62,'paint')
elif BATCH=='orchard':
    palette[1]=((.40,.105,.038),0,.84,'wood');palette[4]=((.52,.36,.14),0,.93,'wood');palette[5]=((.16,.28,.06),0,.88,'foliage');palette[10]=((.57,.022,.008),0,.3,'paint')
mat=atlas(surface,palette)

def start(name):
    return empty('RB_P08_'+name),[]

def B(parts,name,pos,size,tile=0,bevel=.015):
    o=box(name,pos,size,tile,mat,bevel)
    for face in o.data.polygons:face.use_smooth=face.area<.025
    parts.append(o);return o

def R(parts,name,a,b,r,tile=2,sides=10):
    o=rod(name,a,b,r,tile,mat,sides);parts.append(o);return o

def S(parts,name,pos,size,tile=0,segments=16,rings=8):
    o=sphere(name,pos,size,tile,mat,segments,rings);parts.append(o);return o

def done(root,parts,kind='scenery',collider=True):
    bpy.context.view_layer.update()
    minimum=min((o.matrix_world@Vector(c)).z for o in parts for c in o.bound_box)
    for o in parts:o.location.z-=minimum
    if kind=='foliage':
        total=sum(len(o.data.polygons) for o in parts)
        if total>3000:
            for o in parts:
                if len(o.data.polygons)<24:continue
                bpy.context.view_layer.objects.active=o
                modifier=o.modifiers.new('Foliage web geometry budget','DECIMATE');modifier.ratio=.42;modifier.use_collapse_triangulate=True
                bpy.ops.object.modifier_apply(modifier=modifier.name)
    authored_lods(parts,root.name,root)
    reports.append(asset_report(root,concept,surface,kind,'ArtSource/P08/RB_P08_'+BATCH+'.blend',collider))

def leaf(parts,name,start,end,width,tile=5):
    direction=Vector(end)-Vector(start);side=direction.cross(Vector((0,1,0))).normalized()
    verts=[];faces=[];rings=9
    for index in range(rings):
        t=index/(rings-1);middle=Vector(start)+direction*t+Vector((0,math.sin(t*math.pi)*width*.8,0))
        radius=max(.006,math.sin(t*math.pi)*width)
        for offset in [side*radius,Vector((0,.018,0)),-side*radius,Vector((0,-.018,0))]:verts.append(bv(middle+offset))
    for index in range(rings-1):
        for j in range(4):a=index*4+j;b=index*4+(j+1)%4;faces.append((a,b,b+4,a+4))
    faces.extend([(3,2,1,0),tuple((rings-1)*4+j for j in range(4))])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);parts.append(finish(o,name,tile,mat))

if BATCH=='neon':
    root,p=start('CityWarehouse')
    B(p,'Concrete warehouse shell',(0,4.4,0),(8,8.8,5.2),0,.04)
    B(p,'Roof overhang',(0,8.88,0),(8.4,.22,5.6),13,.03)
    for x in [-3.75,3.75]:B(p,'Concrete pilaster',(x,4.4,2.65),(.34,8.8,.20),13,.02)
    B(p,'Steel rolling door',(0,2,2.66),(3.7,3.9,.10),2,.018)
    for y in [.25+i*.23 for i in range(16)]:B(p,'Door corrugation',(0,y,2.725),(3.63,.05,.03),3,.003)
    for x in [-2.5,0,2.5]:
        B(p,'Window lintel',(x,6.87,2.69),(1.8,.15,.20),13)
        B(p,'Window recess',(x,6,2.655),(1.8,1.6,.05),2)
        B(p,'Warm window glazing',(x,6,2.69),(1.6,1.39,.03),7,.005)
        for dx in [-.4,0,.4]:B(p,'Window mullion',(x+dx,6,2.72),(.047,1.43,.04),2,.001)
        B(p,'Window crossbar',(x,6,2.72),(1.65,.047,.04),2,.001)
    for x in [-3,-1,1,3]:R(p,'Roof rail post',(x,8.95,2.4),(x,9.7,2.4),.035)
    R(p,'Roof safety rail',(-3.8,9.7,2.4),(3.8,9.7,2.4),.035)
    for x,h in [(-2,10.2),(2,9.7)]:R(p,'Roof vent',(x,8.9,-.4),(x,h,-.4),.24,3,16)
    for x in [-2.8,2.8]:B(p,'Hazard curb',(x,.35,2.85),(1.5,.7,.28),14)
    done(root,p)
    root,p=start('CityCornerShop')
    B(p,'Shop building',(0,3.1,0),(7,6.2,5),0,.045)
    for x in [-2.35,0,2.35]:
        B(p,'Upper recessed frame',(x,4.65,2.53),(1.7,1.5,.08),8)
        B(p,'Upper glass',(x,4.65,2.58),(1.45,1.25,.04),7,.003)
        B(p,'Upper mullion',(x,4.65,2.61),(.08,1.3,.035),2,.003)
    B(p,'Teal shop fascia',(0,2.85,2.75),(7.3,.62,.40),1,.025)
    B(p,'Amber sign border',(0,3.05,2.98),(6.8,.045,.024),7,.002)
    B(p,'Awning',(0,2.53,3.01),(7.6,.16,1.4),9,.035)
    B(p,'Awning luminous strip',(0,2.46,3.63),(7.15,.034,.045),14,.001)
    for x in [-2.3,.8]:
        B(p,'Storefront frame',(x,1.28,2.54),(2.45,2.3,.09),2)
        B(p,'Storefront glass',(x,1.32,2.60),(2.15,2.02,.025),6,.004)
        for y in [.55,1.03,1.51]:B(p,'Interior display shelf',(x,y,2.63),(1.9,.03,.04),7,.001)
    B(p,'Entry door',(2.65,1.2,2.58),(1.0,2.25,.10),1)
    B(p,'Door glazing',(2.65,1.4,2.65),(.75,1.5,.025),6)
    R(p,'Door handle',(2.98,.95,2.72),(2.98,1.4,2.72),.018,3)
    for x in [-3.5,3.5]:B(p,'Corner column',(x,1.2,2.66),(.25,2.4,.25),13)
    done(root,p)
    root,p=start('CityStreetlamp')
    B(p,'Footing',(0,.16,0),(.48,.32,.48),0)
    R(p,'Fluted lamp mast',(0,.28,0),(0,7,0),.075,2,16)
    p.append(tube('Curved outreach',[(0,6.6,0),(0,7.12,.45),(0,7.24,1.12),(0,7.10,1.9)],.058,3,mat,10))
    B(p,'Lamp housing',(0,7.02,1.88),(.36,.18,.72),2,.045)
    B(p,'Amber diffuser',(0,6.923,1.88),(.28,.018,.58),14,.01)
    B(p,'Street banner',(0,4.9,.17),(.82,1.55,.025),1,.002)
    for y in [4.22,5.65]:R(p,'Banner arm',(-.47,y,.11),(.47,y,.11),.025,3)
    done(root,p)
    root,p=start('CityBusShelter')
    B(p,'Shelter paving',(0,.055,0),(4.3,.11,1.95),13,.025)
    for x in [-1.95,1.95]:
        for z in [-.76,.76]:R(p,'Shelter upright',(x,.1,z),(x,2.8,z),.045,2)
    B(p,'Shelter roof',(0,2.8,0),(4.4,.18,2.15),2,.035)
    B(p,'Roof rim',(0,2.91,0),(4.5,.06,2.25),3,.015)
    B(p,'Rear smoked panel',(0,1.45,-.79),(3.8,2.3,.032),6,.003)
    B(p,'Route poster',(-1.4,1.4,-.765),(.75,1.6,.012),7,.001)
    for z in [-.53,-.34,-.15]:B(p,'Bench slat',(.3,.5,z),(2.6,.08,.14),4,.01)
    for x in [-.8,1.35]:
        R(p,'Bench foot',(x,.1,-.36),(x,.53,-.36),.035)
        R(p,'Bench back support',(x,.4,-.57),(x,1.15,-.57),.025)
    for y in [.85,1.04]:B(p,'Bench back slat',(.3,y,-.59),(2.6,.13,.055),4,.01)
    done(root,p)
    root,p=start('CityLoadingGantry')
    for x in [-4.5,4.5]:
        for z in [-1.7,1.7]:
            B(p,'Gantry leg',(x,5,z),(.38,10,.38),2,.025)
            B(p,'Gantry base',(x,.3,z),(1.05,.6,1.05),14)
        R(p,'Leg bracing',(x,.8,-1.7),(x,8.4,1.7),.08,3)
        R(p,'Leg bracing',(x,.8,1.7),(x,8.4,-1.7),.08,3)
    for z in [-1.7,1.7]:
        B(p,'Overhead beam',(0,10,z),(10.5,.8,.42),2)
        R(p,'Truss rail',(-5,11.2,z),(5,11.2,z),.07,3)
        for x in [-4,-2,0,2,4]:R(p,'Truss diagonal',(x,10.2,z),(x+1,11.2,z),.06,3)
    B(p,'Hoist trolley',(1.4,9.45,0),(1.5,.6,3.6),9,.03)
    for x in [1.1,1.7]:R(p,'Hoist cable',(x,9.1,0),(x,5.8,0),.013,3,6)
    p.append(torus('Cargo hook',(1.4,5.63,0),.2,.055,3,mat,24,6,axis='Z'))
    done(root,p)
    root,p=start('CityWaterTank')
    for x in [-1.4,1.4]:
        for z in [-1.4,1.4]:R(p,'Tank leg',(x,0,z),(x,4.3,z),.09,2)
    for z in [-1.4,1.4]:
        R(p,'Cross brace',(-1.4,.4,z),(1.4,3.8,z),.045,3)
        R(p,'Cross brace',(1.4,.4,z),(-1.4,3.8,z),.045,3)
    R(p,'Water reservoir',(0,3.7,0),(0,6.55,0),1.75,0,32)
    for y in [3.8,4.3,5.95,6.5]:p.append(torus('Tank strap',(0,y,0),1.765,.045,3,mat,32,6,axis='Y'))
    S(p,'Dished lid',(0,6.57,0),(3.56,.38,3.56),3,24,8)
    R(p,'Vent',(0,6.65,0),(0,7.1,0),.10,2)
    for x in [-.25,.25]:R(p,'Ladder rail',(x,.1,1.95),(x,6.9,1.95),.025,3)
    for y in [.25+i*.32 for i in range(20)]:R(p,'Ladder rung',(-.25,y,1.95),(.25,y,1.95),.018,3,6)
    done(root,p)
elif BATCH=='ridge':
    root,p=start('RidgeFir')
    # Closed pointed needle sprays preserve a fine irregular outline; no rock-like spheres.
    for lod in range(3):
        p=[];rng=random.Random(803);tiers=10 if lod==0 else 8 if lod==1 else 6;branches=9 if lod==0 else 7 if lod==1 else 5
        R(p,'Fir trunk',(0,0,0),(0,7.8,0),.14,8,10 if lod==0 else 7)
        for level in range(tiers):
            y=1.0+level*(6.2/max(1,tiers-1));radius=2.1*(1-level/max(1,tiers-1))+.21
            for j in range(branches):
                angle=j*math.tau/branches+level*.71+rng.uniform(-.07,.07);dx=math.cos(angle);dz=math.sin(angle)
                end=(dx*radius,y-.16+level*.025,dz*radius)
                R(p,'Fir branch',(0,y+.23,0),end,.025*(1-level*.07),8,6)
                twigs=4 if lod==0 else 3 if lod==1 else 2
                for t in range(twigs):
                    along=.30+.68*t/max(1,twigs-1);centre=Vector((dx*radius*along,y+.16-.22*along,dz*radius*along))
                    for fan in [-1,0,1]:
                        spray_angle=angle+fan*.49;length=(.46 if lod==0 else .55 if lod==1 else .65)*(1-level*.05)
                        direction=Vector((math.cos(spray_angle),-.19,math.sin(spray_angle))).normalized();width=.105 if lod==0 else .15 if lod==1 else .20
                        sideways=Vector((-math.sin(spray_angle),0,math.cos(spray_angle)));up=Vector((0,.020,0))
                        verts=[bv(centre),bv(centre+direction*length*.52+sideways*width),bv(centre+direction*length),bv(centre+direction*length*.52-sideways*width),bv(centre+direction*length*.48+up),bv(centre+direction*length*.48-up)]
                        faces=[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)]
                        mesh=bpy.data.meshes.new('Pointed fir needle spray');mesh.from_pydata(verts,[],faces);mesh.update();obj=bpy.data.objects.new('Pointed fir needle spray',mesh);scene.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
                        p.append(finish(obj,'Pointed fir needle spray',5 if (j+t)%3 else 12,mat))
        body=join(p,root.name+'_L'+str(lod)+'_Body',root);body.hide_render=lod>0
    export(root,root.name)
    for obj in root.children_recursive:
        if obj.type=='MESH':obj.hide_render=True
    reports.append(asset_report(root,concept,surface,'foliage','ArtSource/P08/RB_P08_ridge.blend',False))
    root,p=start('RidgeGranite')
    rng=random.Random(808)
    for i,(pos,size) in enumerate([((0,2,0),(5,4.2,3.5)),((1.6,.8,.4),(2.1,1.8,2.4)),((-1.65,.65,.8),(1.9,1.5,2.2))]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1,location=bv(pos));o=bpy.context.object
        for v in o.data.vertices:
            perturb=1+rng.uniform(-.11,.11);v.co*=perturb
        o.scale=(size[0]/2,size[2]/2,size[1]/2);p.append(finish(o,'Faceted granite mass '+str(i),0,mat))
    done(root,p)
    root,p=start('RidgeStoneWall')
    rng=random.Random(811)
    for row in range(4):
        for col in range(7):
            x=(col-3)*.67+(row%2)*.15
            B(p,'Dry stone block',(x,.18+row*.33,0),(.61+rng.uniform(-.04,.04),.30,.61+rng.uniform(-.05,.05)),0,.07)
    for x in [-2.58,2.58]:
        for y in [.2,.57,.94,1.31]:B(p,'Wall end pier',(x,y,0),(.72,.34,.76),13,.055)
        B(p,'Pier cap',(x,1.54,0),(.9,.16,.88),11,.04)
    done(root,p)
    root,p=start('RidgeTimberHut')
    B(p,'Stone plinth',(0,.35,0),(5.4,.7,4.4),0,.09)
    for y in [.85+i*.3 for i in range(8)]:
        for z in [-2,2]:R(p,'Horizontal timber wall',(-2.5,y,z),(2.5,y,z),.18,1,10)
        for x in [-2.4,2.4]:R(p,'End wall timber',(x,y,-2.15),(x,y,2.15),.18,8,10)
    for x in [-1,1]:
        B(p,'Cabin window surround',(x,2.0,2.21),(1.05,1.15,.13),4)
        B(p,'Cabin window glass',(x,2,2.29),(.84,.91,.035),6)
        for dx in [-.23,.23]:B(p,'Window shutter',(x+dx,2,2.32),(.05,.95,.035),1)
    B(p,'Cabin door',(0,1.6,-2.21),(1.05,1.9,.13),1)
    p.append(profile('Pitched timber roof',[(2.95,-2.5),(4.25,0),(2.95,2.5),(2.78,2.5),(4.04,0),(2.78,-2.5)],5.8,8,mat,.025))
    for x in [-2.65,-1.95,-1.25,-.55,.15,.85,1.55,2.25]:
        R(p,'Roof rib front',(x,4.26,0),(x,2.96,2.51),.04,1)
        R(p,'Roof rib rear',(x,4.26,0),(x,2.96,-2.51),.04,1)
    B(p,'Stone chimney',(1.5,4.15,-.7),(.65,1.85,.65),0,.05)
    B(p,'Chimney cap',(1.5,5.14,-.7),(.85,.18,.85),13)
    for x in [-2.45,0,2.45]:R(p,'Porch post',(x,.7,2.85),(x,1.75,2.85),.065,1)
    for y in [1,1.68]:R(p,'Porch rail',(-2.6,y,2.85),(2.6,y,2.85),.065,4)
    done(root,p)
    root,p=start('RidgeSnowPole')
    R(p,'Snow depth pole',(0,0,0),(0,2.4,0),.045,11,12)
    for y in [.2,.8,1.4,2.0]:R(p,'Red reflective segment',(0,y,0),(0,y+.3,0),.047,10,12)
    S(p,'Pole cap',(0,2.4,0),(.103,.1,.103),10,12,6)
    done(root,p)
    root,p=start('RidgeGalleryArch')
    # Open roof gallery: 14.45m clear width / 6.3m clear height.
    for x in [-7.7,7.7]:
        for z in [-4,0,4]:B(p,'Gallery pier',(x,3.4,z),(.95,6.8,1.15),0,.06)
        B(p,'Gallery side lintel',(x,6.75,0),(1.05,1.05,9.3),13,.05)
    B(p,'Gallery roof',(0,7.18,0),(16.4,.48,9.7),0,.05)
    for z in [-4,0,4]:B(p,'Roof cross beam',(0,6.6,z),(15.4,.40,.8),13,.04)
    for x in [-7.9,7.9]:B(p,'Foundation runner',(x,.18,0),(1.25,.36,9.6),13,.025)
    done(root,p,'landmark',False)
elif BATCH=='coast':
    root,p=start('CoastPalm')
    trunk=[(math.sin(t/7)*.45,t*.9,0) for t in range(9)]
    p.append(tube('Wind curved palm trunk',trunk,.17,8,mat,12))
    for i in range(25):
        y=i*.28;p.append(torus('Palm bark scar',(math.sin(y/6.3)*.45,y,0),.17,.012,4,mat,12,4,axis='Y'))
    crown=(.41,7.2,0)
    for j in range(12):
        a=j*math.tau/12;length=2.5+(j%3)*.3
        end=(crown[0]+math.cos(a)*length,6.35+(j%2)*.45,math.sin(a)*length)
        R(p,'Palm frond spine',crown,end,.028,4,6)
        for k in range(1,9):
            t=k/9;mid=Vector(crown).lerp(Vector(end),t)+Vector((0,math.sin(t*math.pi)*.6,0))
            for side in [-1,1]:
                tip=mid+Vector((math.cos(a+side*.8)*.8, -.2, math.sin(a+side*.8)*.8))
                leaf(p,'Closed palm leaflet',mid,tip,.075,5 if j%3 else 12)
    done(root,p,'foliage',False)
    root,p=start('CoastSurfShack')
    B(p,'Raised shack floor',(0,.38,0),(5.3,.25,3.9),8,.025)
    for x in [-2.25,2.25]:
        for z in [-1.55,1.55]:R(p,'Shack support',(x,0,z),(x,3.5,z),.10,4)
    for x in [-2.45+i*.35 for i in range(15)]:B(p,'Teal rear plank',(x,1.9,-1.6),(.32,2.85,.10),1,.008)
    for z in [-1.4+i*.3 for i in range(10)]:B(p,'Side weatherboard',(-2.4,1.85,z),(.11,2.8,.27),1,.008)
    B(p,'Open front counter',(0,1.25,1.65),(4.85,.16,.62),4,.025)
    B(p,'Counter apron',(0,.85,1.6),(4.8,.65,.11),1,.008)
    p.append(profile('Shack sloped roof',[(3.3,-2.3),(3.7,2.3),(3.88,2.3),(3.48,-2.3)],5.8,3,mat,.01))
    for x in [-2.6+i*.4 for i in range(14)]:R(p,'Roof folded rib',(x,3.52,-2.1),(x,3.89,2.1),.025,2,6)
    for x in [-1.6,0,1.6]:
        R(p,'Stool stem',(x,.4,2.4),(x,.95,2.4),.055,8)
        R(p,'Stool seat',(x,.94,2.4),(x,1.04,2.4),.25,4,16)
    for x in [-1.6,-.8,0,.8,1.6]:S(p,'String lamp',(x,3.13,1.87),(.07,.10,.07),14,10,6)
    done(root,p)
    root,p=start('CoastBeacon')
    R(p,'Beacon foundation',(0,0,0),(0,.55,0),1.55,0,24)
    for i in range(6):R(p,'Navigation tower band',(0,.55+i*.8,0),(0,1.35+i*.8,0),.72-i*.045,10 if i%2 else 11,24)
    R(p,'Beacon lamp housing',(0,5.35,0),(0,6.0,0),.49,6,20)
    R(p,'Beacon warm lens',(0,5.53,0),(0,5.91,0),.50,14,20)
    R(p,'Beacon roof',(0,6.0,0),(0,6.15,0),.63,2,20)
    for y in [.65,5.25]:
        p.append(torus('Circular maintenance rail',(0,y+.85,0),1.12 if y<1 else .9,.027,3,mat,24,6,axis='Y'))
        for j in range(8):
            a=j*math.tau/8;r=1.12 if y<1 else .9;R(p,'Beacon rail post',(math.cos(a)*r,y,math.sin(a)*r),(math.cos(a)*r,y+.85,math.sin(a)*r),.022,3,6)
    done(root,p)
    root,p=start('CoastBridgePier')
    B(p,'Bridge pier foot',(0,.35,0),(3.2,.7,2.8),13,.05)
    p.append(profile('Tapered bridge pier',[(.7,-.85),(.7,.85),(6.2,.6),(6.2,-.6)],2.25,0,mat,.025))
    B(p,'Pier cap',(0,6.3,0),(9.4,.8,2.0),13,.04)
    B(p,'Bridge deck module',(0,6.92,0),(11,.45,3.3),0,.03)
    for x in [-5,-3,-1,1,3,5]:B(p,'Bridge railing post',(x,7.66,1.44),(.16,1.05,.18),13)
    for y in [7.48,8.0]:B(p,'Bridge railing',(0,y,1.44),(10.8,.11,.16),13)
    done(root,p,'landmark',False)
    root,p=start('CoastBoulder')
    rng=random.Random(821)
    for i,(pos,size) in enumerate([((0,1.25,0),(4.2,2.5,3.3)),((1.3,.48,.9),(1.5,1.1,1.55))]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1,location=bv(pos));o=bpy.context.object
        for v in o.data.vertices:v.co*=1+rng.uniform(-.065,.065)
        o.scale=(size[0]/2,size[2]/2,size[1]/2);p.append(finish(o,'Salt weathered coastal mass '+str(i),0,mat))
    done(root,p)
    root,p=start('CoastBroadleafShrub')
    for j in range(12):
        a=j*math.tau/12;length=.72+(j%3)*.16
        startpos=(math.cos(a)*.08,.06,math.sin(a)*.08);end=(math.cos(a)*length,.55+(j%3)*.23,math.sin(a)*length)
        leaf(p,'Broad coastal leaf',startpos,end,.22,5 if j%2 else 12)
        R(p,'Leaf midrib',startpos,end,.009,4,6)
    done(root,p,'foliage',False)
elif BATCH=='orchard':
    root,p=start('OrchardAppleTree')
    R(p,'Apple tree trunk',(0,0,0),(0,2.6,0),.16,8,12)
    rng=random.Random(842)
    for j in range(7):
        a=j*math.tau/7;end=(math.cos(a)*1.4,2.8+(j%3)*.22,math.sin(a)*1.4)
        R(p,'Apple tree fork',(0,1.65,0),end,.067,8,8)
        for k in range(5):
            pos=(end[0]+rng.uniform(-.55,.55),end[1]+rng.uniform(-.15,.65),end[2]+rng.uniform(-.55,.55))
            S(p,'Leaf cluster',pos,(1.0,.8,1.0),5 if k%2 else 12,10,6)
        for k in range(4):
            pos=(end[0]+rng.uniform(-.5,.5),end[1]+rng.uniform(-.4,.2),end[2]+rng.uniform(-.5,.5))
            S(p,'Original apple fruit',pos,(.11,.12,.11),10,10,6)
    done(root,p,'foliage',False)
    root,p=start('OrchardBarn')
    p.append(profile('Gabled barn volume',[(0,-4),(5,-4),(7.5,0),(5,4),(0,4)],9,1,mat,.04))
    for x in [-4.4+i*.44 for i in range(21)]:
        B(p,'Front vertical barn board',(x,2.4,4.025),(.39,4.65,.07),1,.006)
    p.append(profile('Barn pitched roof',[(5,-4.5),(7.75,0),(5,4.5),(4.86,4.5),(7.56,0),(4.86,-4.5)],9.8,8,mat,.02))
    for x in [-4.6+i*.55 for i in range(18)]:
        R(p,'Roof batten',(x,5.02,4.52),(x,7.77,0),.03,3,6)
        R(p,'Roof batten',(x,5.02,-4.52),(x,7.77,0),.03,3,6)
    for x in [-1.3,1.3]:
        B(p,'Barn double door',(x,1.65,4.09),(2.5,3.3,.1),8,.01)
        for dx in [-1.13,1.13]:B(p,'Door upright',(x+dx,1.65,4.16),(.11,3.15,.045),11,.004)
        R(p,'Door diagonal',(x-1.1,.17,4.16),(x+1.1,3.12,4.16),.05,11,6)
    B(p,'Hayloft window',(0,5.55,3.17),(1.05,1.0,.08),6)
    done(root,p)
    root,p=start('OrchardSilo')
    R(p,'Silo foundation',(0,0,0),(0,.35,0),2.15,0,32)
    R(p,'Grain silo',(0,.35,0),(0,9.5,0),1.95,13,32)
    for y in [.55+i*.58 for i in range(16)]:p.append(torus('Silo reinforcing hoop',(0,y,0),1.97,.027,3,mat,32,6,axis='Y'))
    S(p,'Domed silo roof',(0,9.53,0),(3.94,1.2,3.94),3,32,12)
    for x in [-.22,.22]:R(p,'Silo ladder side',(x,.2,2.02),(x,10.0,2.02),.024,2)
    for y in [.25+i*.34 for i in range(28)]:R(p,'Silo ladder rung',(-.22,y,2.02),(.22,y,2.02),.018,2,6)
    done(root,p)
    root,p=start('OrchardFence')
    for x in [-2.2,2.2]:B(p,'Fence square post',(x,.7,0),(.21,1.4,.23),8,.02)
    for y in [.45,1.12]:B(p,'Weathered fence rail',(0,y,.025),(4.8,.17,.13),4,.015)
    for x in [-2.2,2.2]:
        for y in [.45,1.12]:R(p,'Fence nail',(x,y,.1),(x,y,.113),.012,3,8)
    done(root,p)
    root,p=start('OrchardHayBale')
    R(p,'Round hay bale',(-.55,.78,0),(.55,.78,0),.76,4,32)
    for x in [-.39,.39]:p.append(torus('Bale twine',(x,.78,0),.765,.012,8,mat,32,5,axis='X'))
    for radius in [.15,.29,.43,.57,.70]:
        for x in [-.558,.558]:p.append(torus('Wound straw ring',(x,.78,0),radius,.011,7,mat,24,4,axis='X'))
    done(root,p)
    root,p=start('OrchardProduceKiosk')
    B(p,'Kiosk base',(0,.1,0),(3.8,.2,2.5),8,.02)
    for x in [-1.7,1.7]:
        for z in [-1.05,1.05]:B(p,'Kiosk timber post',(x,1.55,z),(.16,3.0,.16),4)
    p.append(profile('Kiosk pitched roof',[(2.88,-1.5),(3.72,0),(2.88,1.5),(2.73,1.5),(3.54,0),(2.73,-1.5)],4.2,8,mat,.02))
    B(p,'Produce counter',(0,1.15,.6),(3.5,.15,1.0),4,.02)
    for x in [-1.1,0,1.1]:
        B(p,'Produce crate',(x,1.39,.6),(.96,.36,.74),8,.018)
        for dx in [-.26,0,.26]:
            for z in [.38,.65,.91]:S(p,'Market apple',(x+dx,1.61,z),(.19,.18,.18),10,10,6)
    B(p,'Kiosk blank chalk sign',(1.15,2.16,-.94),(.84,1.05,.055),15,.012)
    done(root,p)
else:
    raise RuntimeError('No reviewed recipe implemented for '+BATCH)
save_pack(BATCH,reports)
