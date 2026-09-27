"""Original production motorcycles built only from individually inspected concepts."""
scene=p08_begin('bikes');reports=[]
specs={
    1:('kestrel','Kestrel','naked',0,3,.41,.32,.61,1,18),
    2:('rift-250','Rift 250','compact',4,14,.40,.30,.55,1,3),
    3:('jackal','Jackal','scrambler',10,3,.45,.33,.64,1,18),
    4:('ember','Ember','classic',11,7,.48,.28,.64,2,20),
    5:('apex','Apex','full',4,12,.45,.33,.58,4,6),
    6:('corvus','Corvus','fighter',0,6,.48,.34,.58,4,5),
    7:('viper','Viper','hyper',10,12,.46,.33,.56,4,7),
    8:('rift-750-n','Rift 750 N','muscle',11,13,.50,.34,.57,4,6),
    9:('specter','Specter','stream',4,12,.45,.30,.67,4,5),
    10:('nightjar','Nightjar','tour',12,7,.48,.31,.64,2,5),
    11:('cinder-10','Cinder 10','endurance',0,13,.47,.33,.65,4,6),
    12:('rift-750','Rift 750','sharp',11,12,.44,.30,.61,4,5),
    13:('odyssey','Odyssey','heritage-tour',7,4,.48,.31,.64,2,5),
    14:('havoc','Havoc','brutal',10,12,.49,.32,.57,2,6),
}
palette=[((.15,.28,.39),.55,.28,'paint'),((.018,.026,.033),.65,.36,'brushed'),((.17,.19,.20),.78,.35,'brushed'),((.54,.58,.60),.90,.24,'brushed'),((.78,.76,.67),.35,.27,'paint'),((.015,.019,.020),0,.88,'rubber'),((.085,.05,.031),0,.68,'leather'),((.48,.32,.10),.85,.32,'brushed'),((.018,.03,.045),.4,.13,'paint'),((.72,.73,.65),.15,.13,'paint'),((.18,.25,.085),.25,.44,'paint'),((.27,.022,.035),.4,.25,'paint'),((.045,.065,.09),.45,.34,'paint'),((.08,.09,.09),.7,.4,'brushed'),((.66,.025,.018),.2,.28,'paint'),((.005,.009,.011),0,.92,'rubber')]
family='A' if max(SELECTED_INDICES)<=5 else 'B' if max(SELECTED_INDICES)<=10 else 'C'
if family=='B':
    palette[0]=((.036,.045,.06),.55,.35,'paint');palette[4]=((.54,.59,.64),.72,.28,'paint')
    palette[10]=((.035,.29,.105),.50,.25,'paint');palette[11]=((.025,.085,.44),.45,.27,'paint')
    palette[12]=((.026,.044,.115),.45,.32,'paint');palette[6]=((.21,.08,.31),.40,.30,'paint')
if family=='C':
    palette[0]=((.70,.28,.045),.42,.30,'paint');palette[11]=((.58,.025,.018),.45,.24,'paint')
    palette[12]=((.023,.027,.032),.5,.33,'paint');palette[10]=((.55,.44,.25),.25,.43,'paint');palette[7]=((.29,.11,.05),.74,.35,'brushed')
surface='RB_P08_Bikes'+family+'_Atlas'
# The family atlas was authored with bike01. Later members read that exact
# shared surface instead of rewriting textures while Unity imports the roster.
if SELECTED_INDICES==[1] or family!='A':mat=atlas(surface,palette)
else:
    mat=bpy.data.materials.new(surface);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;s=n.get('Principled BSDF')
    for kind,dest in [('BaseColor','Base Color'),('Roughness','Roughness')]:
        im=bpy.data.images.load(OUT+surface+'_'+kind+'.png',check_existing=True)
        if kind!='BaseColor':im.colorspace_settings.name='Non-Color'
        node=n.new('ShaderNodeTexImage');node.image=im;l.new(node.outputs['Color'],s.inputs[dest])
    node=n.new('ShaderNodeTexImage');node.image=bpy.data.images.load(OUT+surface+'_Normal.png',check_existing=True);node.image.colorspace_settings.name='Non-Color'
    normal=n.new('ShaderNodeNormalMap');l.new(node.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],s.inputs['Normal'])
    node=n.new('ShaderNodeTexImage');node.image=bpy.data.images.load(OUT+surface+'_MetallicSmoothness.png',check_existing=True);node.image.colorspace_settings.name='Non-Color'
    sep=n.new('ShaderNodeSeparateColor');l.new(node.outputs['Color'],sep.inputs['Color']);l.new(sep.outputs['Red'],s.inputs['Metallic'])

def bike_shell(name,sections,tile,parts,sides=24):
    # Rounded closed longitudinal shell; per-section widths give authored silhouettes.
    verts=[];faces=[]
    for z,y,width,height in sections:
        for j in range(sides):
            a=j*math.tau/sides;verts.append(bv((math.cos(a)*width*.5,y+math.sin(a)*height*.5,z)))
    for row in range(len(sections)-1):
        for j in range(sides):a=row*sides+j;b=row*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),tuple((len(sections)-1)*sides+j for j in range(sides))])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);parts.append(finish(obj,name,tile,mat));return obj

def B(p,name,pos,size,tile,bevel=.01):
    obj=box(name,pos,size,tile,mat,bevel)
    for polygon in obj.data.polygons:polygon.use_smooth=polygon.area<.006
    p.append(obj);return obj
def S(p,name,pos,size,tile,segments=24,rings=12):
    obj=sphere(name,pos,size,tile,mat,segments,rings);p.append(obj);return obj
def R(p,name,a,b,r,tile,sides=12):
    obj=rod(name,a,b,r,tile,mat,sides);p.append(obj);return obj
def T(p,name,points,r,tile,sides=8):
    obj=tube(name,points,r,tile,mat,sides);p.append(obj);return obj

def brake_disc(parts,pos):
    vertices=[];sides=48
    for x in [pos[0]-.003,pos[0]+.003]:
        for radius in [.116,.200]:
            for i in range(sides):
                a=i*math.tau/sides;vertices.append(bv((x,pos[1]+radius*math.cos(a),pos[2]+radius*math.sin(a))))
    faces=[]
    for i in range(sides):
        j=(i+1)%sides
        faces.extend([(i,j,sides+j,sides+i),(2*sides+i,3*sides+i,3*sides+j,2*sides+j),(i,2*sides+i,2*sides+j,j),(sides+i,sides+j,3*sides+j,3*sides+i)])
    mesh=bpy.data.meshes.new('Annular machined brake rotor');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Annular machined brake rotor',mesh);scene.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    parts.append(finish(obj,'Annular machined brake rotor',3,mat))
    for i in range(24):
        a=i*math.tau/24
        # Dark flush drill cues in the metal face are bounded original microgeometry.
        R(parts,'Brake rotor drilled recess cue',(pos[0]-.0035,pos[1]+.171*math.cos(a),pos[2]+.171*math.sin(a)),(pos[0]-.004,pos[1]+.171*math.cos(a),pos[2]+.171*math.sin(a)),.004,15,6)

def front_patch(parts,name,outline,z,thickness,tile):
    vertices=[bv((x,y,depth)) for depth in [z-thickness/2,z+thickness/2] for x,y in outline]
    n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    parts.append(finish(obj,name,tile,mat,.003));return obj

def subtract_box(obj,name,pos,size):
    cutter=box(name,pos,size,15,mat,.008)
    bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new(name,'BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name);bpy.data.objects.remove(cutter,do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)

def windshield(parts,top):
    # Curved closed thin screen, with its lower rim embedded in the upper cowl.
    rows=[(.66,1.085,.34),(.57,1.15,.33),(.46,1.23,.29),(.34,top,.23)]
    vertices=[];columns=13
    for back in [False,True]:
        for z,y,width in rows:
            for col in range(columns):
                t=col/(columns-1)*2-1
                vertices.append(bv((t*width/2,y+.018*(1-t*t),z+.035*(1-t*t)-(.007 if back else 0))))
    n=len(rows)*columns;faces=[]
    for r in range(len(rows)-1):
        for c in range(columns-1):
            i=r*columns+c;faces.extend([(i,i+1,i+1+columns,i+columns),(n+i+columns,n+i+columns+1,n+i+1,n+i)])
    edge=list(range(columns))+[r*columns+columns-1 for r in range(1,len(rows))]+list(range(n-2,n-columns-1,-1))+[r*columns for r in range(len(rows)-2,0,-1)]
    for i in range(len(edge)):a,b=edge[i],edge[(i+1)%len(edge)];faces.append((a,b,n+b,n+a))
    mesh=bpy.data.meshes.new('Curved attached windscreen');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Curved attached windscreen',mesh);scene.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    parts.append(finish(obj,'Curved attached windscreen',8,mat))
    for side in [-1,1]:
        T(parts,'Screen mounting rail',[(side*.17,1.085,.66),(side*.165,1.15,.57),(side*.145,1.23,.46),(side*.115,top,.34)],.008,1,6)
        R(parts,'Flush screen fixing',(side*.151,1.108,.642),(side*.151,1.108,.654),.006,3,6)

def fairing_panel(parts,side,full,paint,style):
    sections=[(-.25,.36,.80,.18),(-.07,.34,.86,.225),(.13,.36,.92,.247),(.33,.44,1.00,.263),(.51,.67,1.085,.245),(.70,.92,1.055,.18)]
    if style=='sharp':sections=[(-.29,.37,.75,.17),(-.10,.33,.85,.21),(.11,.39,.93,.255),(.34,.49,1.04,.269),(.56,.80,1.09,.241),(.72,.94,1.048,.175)]
    elif style=='stream':sections=[(-.24,.42,.79,.19),(-.04,.39,.89,.237),(.18,.44,.98,.257),(.41,.62,1.08,.252),(.63,.88,1.108,.211),(.74,.98,1.069,.17)]
    elif style=='endurance':sections=[(-.27,.34,.86,.192),(-.08,.33,.94,.243),(.17,.36,1.02,.266),(.38,.52,1.09,.27),(.62,.85,1.13,.223),(.74,.97,1.095,.18)]
    if not full:sections=[(-.16,.50,.81,.175),(.04,.44,.94,.22),(.27,.50,1.03,.25),(.51,.79,1.075,.24),(.70,.92,1.055,.18)]
    vertices=[];faces=[];rows=len(sections);columns=7
    for inner in [False,True]:
        for z,bottom,top,width in sections:
            for j in range(columns):
                t=j/(columns-1);x=side*(width+math.sin(t*math.pi)*.025-(.024 if inner else 0))
                vertices.append(bv((x,bottom+(top-bottom)*t,z)))
    n=rows*columns
    for r in range(rows-1):
        for c in range(columns-1):
            i=r*columns+c;faces.extend([(i,i+1,i+1+columns,i+columns),(n+i+columns,n+i+columns+1,n+i+1,n+i)])
    edge=list(range(columns))+[r*columns+columns-1 for r in range(1,rows)]+list(range((rows-1)*columns+columns-2,(rows-1)*columns-1,-1))+[r*columns for r in range(rows-2,0,-1)]
    for j in range(len(edge)):a,b=edge[j],edge[(j+1)%len(edge)];faces.append((a,b,n+b,n+a))
    mesh=bpy.data.meshes.new('Sculpted fairing shell');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Sculpted fairing shell',mesh);scene.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    obj=finish(obj,'Contoured vented fairing shell',paint,mat)
    if style=='hyper':
        for y in [.60,.705,.81]:
            subtract_box(obj,'Open cooling slot',(side*.27,y,.245),(.20,.044,.19))
            B(parts,'Recessed cooling slot',(side*.225,y,.245),(.008,.040,.18),15,.004)
    else:
        if style in ['sharp','full','stream']:
            outline=[(.655,.20),(.795,.195),(.875,.365),(.75,.40)]
            cutter=profile('Intake shaping cutter',outline,.20,15,mat,.004,side*.27)
            bpy.context.view_layer.objects.active=obj;modifier=obj.modifiers.new('True angled intake opening','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
            bpy.ops.object.modifier_apply(modifier=modifier.name);bpy.data.objects.remove(cutter,do_unlink=True)
            parts.append(profile('Inset intake cavity back',outline,.008,15,mat,.003,side*.207))
        else:
            subtract_box(obj,'Open recessed side intake',(side*.27,.76,.28),(.18,.13,.17))
            B(parts,'Recessed intake back',(side*.21,.76,.28),(.008,.12,.16),15,.003)
        for y in [.72,.75,.78,.81]:B(parts,'Intake recessed louver',(side*.234,y,.28),(.008,.006,.15),13,.001)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    finish(obj,'Contoured vented fairing shell',paint,mat);parts.append(obj)
    # Panel seams and narrow trim are actual edge details, not detached boxes.
    T(parts,'Fairing shoulder seam',[(side*.22,.90,-.02),(side*.257,.94,.24),(side*.257,1.015,.43),(side*.215,1.067,.60)],.0025,13,5)

for index in SELECTED_INDICES:
    if index not in specs:raise RuntimeError('This bike concept has not been reviewed: '+str(index))
    slug,label,style,paint,accent,tank_width,tank_height,tank_length,cylinders,spokes=specs[index]
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    name='RB_P08_Bike_'+str(index).zfill(2);root=empty(name);parts=[]
    concept='ArtSource/Concepts/P08/Bikes/'+str(index).zfill(2)+'-'+slug+'-v1.png'
    classic=style in ['naked','classic','scrambler','heritage-tour'];full=style in ['full','hyper','stream','endurance','sharp'];scrambler=style=='scrambler'
    modern_naked=style in ['fighter','muscle','brutal']
    # Tank shape, saddle and rear bodywork vary structurally with the design.
    length_scale=tank_length/.61 if index>5 else 1
    bike_shell('Sculpted '+label+' fuel tank',[(.15+(z-.15)*length_scale,y,w,h) for z,y,w,h in [(-.15,.85,.23,.16),(-.06,.91,tank_width,tank_height),(.22,.92,tank_width,tank_height),(.45,.84,.20,.17)]],paint,parts,12 if modern_naked or style=='sharp' else 24)
    R(parts,'Fuel filler',(0,1.065,.23),(0,1.087,.23),.043,3,24)
    parts.append(torus('Fuel filler sealing ring',(0,1.089,.23),.039,.003,13,mat,20,5,axis='Y'))
    if classic:
        S(parts,'Flat ribbed saddle',(0,.845,-.48),(.34,.13,.65),6 if scrambler else 5,28,12)
        for z in [-.73,-.64,-.55,-.46,-.37,-.28]:
            factor=max(.01,1-((z+.48)/.325)**2);extent=.17*math.sqrt(factor)
            cross=[(x*extent,.847+.066*math.sqrt(max(.001,factor-(x*extent/.17)**2)),z) for x in [-.88,-.55,0,.55,.88]]
            T(parts,'Saddle stitched rib',cross,.0025,7 if scrambler else 13,6)
        if style in ['classic','heritage-tour']:S(parts,'Separate raised passenger pad',(0,.885,-.67),(.32,.11,.27),6,20,10)
    else:
        bike_shell('Raised sculpted tail',[(-.91,.93,.16,.06),(-.76,.92,.28,.15),(-.46,.83,.32,.14),(-.31,.79,.26,.07)],paint,parts)
        S(parts,'Sculpted rider saddle',(0,.84,-.38),(.30,.09,.38),5,24,10)
        S(parts,'Rear sport seat pad',(0,.996,-.69),(.23,.055,.22),5,20,8)
        if style=='tour':
            S(parts,'Wide touring passenger pad',(0,.97,-.65),(.32,.12,.31),5,24,10)
            for x in [-.18,.18]:T(parts,'Touring rack side',[(x,.90,-.64),(x,1.04,-.74),(x,1.04,-.98)],.015,13)
            for z in [-.76,-.85,-.94]:R(parts,'Touring rack crossbar',(-.18,1.04,z),(.18,1.04,z),.012,13)
    if style=='heritage-tour':
        for side in [-1,1]:
            B(parts,'Travel saddlebag hardcase',(side*.325,.70,-.59),(.19,.39,.49),1,.055)
            B(parts,'Travel saddlebag copper insert',(side*.423,.71,-.59),(.015,.27,.39),paint,.037)
            R(parts,'Saddlebag mounting tube',(side*.27,.76,-.31),(side*.28,.88,-.82),.013,13)
            parts.append(profile('Cream tank side inset',[(.86,-.09),(1.026,-.042),(1.054,.22),(.941,.345),(.84,.22)],.014,4,mat,.02,side*.216))
        for x in [-.16,.16]:T(parts,'Rear travel carrier rail',[(x,.87,-.65),(x,1.018,-.81),(x,1.018,-.96)],.016,13)
        for z in [-.81,-.89,-.96]:R(parts,'Rear carrier crossrail',(-.16,1.018,z),(.16,1.018,z),.013,13)
    for side in [-1,1]:
        x=.17*side
        T(parts,'Tubular diamond frame',[(x,.79,-.56),(x,.42,-.28),(x,.33,.15),(x,.67,.46),(x,.98,.52),(x,.76,.34),(x,.76,-.3)],.023,1)
        R(parts,'Rear swing arm',(x,.38,-.17),(x,.322,-.73),.029 if classic else .044,2)
        R(parts,'Front telescopic fork',(side*.135,.97,.55),(side*.135,.322,.80),.031,3)
        R(parts,'Fork lower',(side*.135,.52,.745),(side*.135,.322,.80),.040,2)
        if classic:
            R(parts,'Twin rear shock',(x,.75,-.48),(x,.35,-.73),.035,3)
            for k in range(8):
                y=.40+k*.034;z=-.70+k*.023
                parts.append(torus('Shock coil band',(x,y,z),.04,.006,1,mat,12,5,axis='Y'))
        R(parts,'Footpeg',(x,.36,-.12),(side*.29,.36,-.12),.021,5)
        T(parts,'Handlebar',[(0,1.035,.43),(side*.20,1.04,.45),(side*.32,1.055,.39)],.015,3)
        R(parts,'Grip',(side*.29,1.05,.41),(side*.39,1.05,.37),.023,5,16)
        T(parts,'Brake lever',[(side*.26,1.04,.46),(side*.35,1.032,.46),(side*.405,1.03,.405)],.007,3)
        T(parts,'Mirror stem',[(side*.26,1.06,.46),(side*.30,1.18,.49),(side*.36,1.235,.49)],.009,1)
        S(parts,'Mirror shell',(side*.37,1.24,.49),(.105,.10,.028),1,16,8)
        S(parts,'Mirror reflective face',(side*.37,1.24,.472),(.084,.08,.009),3,16,8)
    # Independently authored one/two/four-cylinder powertrains.
    B(parts,'Engine crankcase',(0,.48,.06),(.32,.26,.35),2,.045)
    for side in [-1,1]:
        R(parts,'Machined side cover',(side*.155,.48,.04),(side*.195,.48,.04),.118,3 if classic else 7,24)
        for j in range(8):
            a=j*math.tau/8;R(parts,'Case hex fastener',(side*.196,.48+.095*math.cos(a),.04+.095*math.sin(a)),(side*.203,.48+.095*math.cos(a),.04+.095*math.sin(a)),.006,13,6)
    for cylinder in range(cylinders):
        x=(cylinder-(cylinders-1)*.5)*(.125 if cylinders<3 else .078)
        barrel=B(parts,'Cylinder barrel',(x,.69,.16),(.12 if cylinders<3 else .073,.23,.19),1,.008)
        if style=='brutal':
            barrel.location=bv((0,.66,-.04 if cylinder==0 else .23));barrel.rotation_euler.x=math.radians(-24 if cylinder==0 else 24)
        for y in [.59,.625,.66,.695,.73,.765]:B(parts,'Cooling fin',(x,y,.16),(.15 if cylinders<3 else .082,.010,.21),3,.001)
        T(parts,'Exhaust header',[(x,.74,.26),(x,.63,.40),(x,.40,.36),(x,.31,.16),(.24,.35,-.25)],.023,7,10)
    B(parts,'Radiator',(0,.66,.43),(.31,.24,.045),13,.008)
    for y in [.58,.62,.66,.70,.74]:B(parts,'Radiator louver',(0,y,.458),(.29,.009,.012),3,.001)
    if scrambler:
        for y in [.63,.76]:
            R(parts,'High scrambler exhaust',(.25,y,-.22),(.27,y+.045,-.81),.057,3,20)
            R(parts,'Exhaust outlet',(.27,y+.045,-.815),(.27,y+.045,-.829),.041,15,16)
            R(parts,'Heat shield',(.279,y+.018,-.32),(.289,y+.045,-.71),.062,13,16)
        for side in [-1,1]:
            T(parts,'Side protection frame',[(side*.20,.49,.29),(side*.27,.73,.29),(side*.27,.81,.04),(side*.20,.53,-.08)],.019,3)
        B(parts,'Bash guard',(0,.31,.04),(.41,.055,.40),3,.024)
    elif style=='brutal':
        for y in [.53,.69]:
            R(parts,'Twin raised muffler',(.24,y,-.30),(.27,y+.045,-.85),.066,3,24)
            R(parts,'Twin muffler dark outlet',(.27,y+.045,-.852),(.27,y+.045,-.860),.047,15,20)
    elif full and style!='stream':
        R(parts,'Underseat silencer',(0,.84,-.62),(0,.88,-.92),.071,3,20)
        R(parts,'Underseat outlet',(0,.88,-.923),(0,.88,-.932),.05,15,20)
    else:
        for side in ([1,-1] if style in ['classic','stream'] else [1]):
            R(parts,'Brushed upswept silencer',(side*.24,.35,-.22),(side*.265,.42,-.83),.056,3,20)
            R(parts,'Silencer outlet',(side*.265,.42,-.835),(side*.265,.42,-.846),.040,15,16)
    if classic:
        R(parts,'Round headlight shell',(0,.98,.65),(0,.98,.81),.122,1,32)
        R(parts,'Polished headlight rim',(0,.98,.81),(0,.98,.831),.118,3,32)
        R(parts,'Prismatic headlight lens',(0,.98,.832),(0,.98,.843),.103,9,32)
        for x in [-.078,-.052,-.026,0,.026,.052,.078]:
            half=math.sqrt(.099*.099-x*x);R(parts,'Headlight lens flute',(x,.98-half,.846),(x,.98+half,.846),.0016,3,5)
        if scrambler:
            for x in [-.074,-.037,0,.037,.074]:R(parts,'Lamp cage vertical',(x,.892,.856),(x,1.067,.856),.0035,1,6)
            for y in [.92,.958,.996,1.034]:R(parts,'Lamp cage horizontal',(-.09,y,.858),(.09,y,.858),.0035,1,6)
        if style=='heritage-tour':
            bike_shell('Short touring flyscreen',[(.57,1.02,.29,.027),(.48,1.15,.27,.025),(.38,1.24,.21,.022)],8,parts,20)
            B(parts,'Horizontal headlamp LED bar',(0,.985,.851),(.171,.025,.010),9,.003)
        R(parts,'Single gauge',(0,1.045,.45),(0,1.095,.45),.057,1,20)
        R(parts,'Gauge glass',(0,1.095,.45),(0,1.10,.45),.049,8,20)
        for side in [-1,1]:
            panel=profile('Triangular side cover',[(.60,-.38),(.80,-.32),(.76,-.04),(.62,-.08)],.02,paint,mat,.015,side*.195);parts.append(panel)
    elif modern_naked:
        B(parts,'Exposed broad modern radiator',(0,.67,.45),(.40,.31,.055),13,.01)
        for side in [-1,1]:
            parts.append(profile('Angular radiator shroud',[(.62,.39),(.91,.46),(.98,.27),(.83,.10)],.045,paint,mat,.012,side*.235))
            parts.append(profile('Shroud accent blade',[(.68,.43),(.87,.45),(.90,.40),(.73,.38)],.047,accent,mat,.004,side*.24))
        if style=='fighter':
            for x in [-.089,.089]:
                R(parts,'Twin projector housing',(x,.98,.67),(x,.98,.82),.087,1,24)
                R(parts,'Twin projector metal rim',(x,.98,.82),(x,.98,.838),.080,3,24)
                R(parts,'Twin projector glass',(x,.98,.839),(x,.98,.85),.063,9,24)
            parts.append(profile('Angular flyscreen',[(1.03,.62),(1.15,.59),(1.11,.72),(1.02,.76)],.30,paint,mat,.008))
        elif style=='brutal':
            bike_shell('Muscular angular single lamp cowl',[(.59,1.075,.24,.20),(.72,1.03,.28,.22),(.84,1.01,.23,.145)],paint,parts,12)
            B(parts,'Recessed rectangular LED lamp',(0,1.017,.848),(.187,.070,.014),15,.019)
            B(parts,'Horizontal LED lens',(0,1.025,.858),(.158,.023,.008),9,.006)
        else:
            bike_shell('Pointed naked-bike cowl',[(.58,1.00,.23,.18),(.74,.97,.25,.15),(.84,.95,.08,.035)],paint,parts,12)
            for side in [-1,1]:
                bezel=B(parts,'Compact lamp inset',(side*.062,.973,.771),(.063,.102,.018),15,.008);bezel.rotation_euler.y=side*.22
                lamp=B(parts,'Angled compact headlamp',(side*.062,.973,.785),(.042,.077,.012),9,.005);lamp.rotation_euler.y=side*.22
        B(parts,'Compact digital instruments',(0,1.095,.36),(.19,.07,.12),1,.012)
        B(parts,'Smoked instrument glass',(0,1.135,.36),(.16,.01,.10),8,.003)
    else:
        # Closed side panels and nose volumes leave the front wheel and steering area open.
        lower=[(.36,-.26),(.32,.26),(.46,.49),(.86,.59),(1.055,.63),(1.10,.48),(.91,.10),(.77,-.15)]
        if not full:lower=[(.49,-.17),(.42,.28),(.58,.46),(.91,.59),(1.06,.63),(1.10,.50),(.92,.08),(.82,-.16)]
        for side in [-1,1]:
            fairing_panel(parts,side,full,paint,style)
            parts.append(profile('Contrasting lower fairing',[(.35,-.26),(.33,.28),(.53,.43),(.50,.07)],.018,accent,mat,.005,side*.235))
            if style=='stream':
                parts.append(profile('Flowing midnight overlay',[(.45,-.20),(.57,.19),(.77,.42),(.85,.35),(.73,.08),(.61,-.08)],.014,accent,mat,.008,side*.277))
            for z,y in [(-.10,.54),(.08,.86),(.48,1.045)]:
                R(parts,'Flush fairing hex fixing',(side*.267,y,z),(side*.273,y,z),.005,13,6)
        # Nose tapers into the side shells; lamps are flush polygonal inserts.
        bike_shell('Sculpted connected sport nose',[(.48,1.04,.42,.20),(.62,1.045,.44,.21),(.76,1.005,.41,.15),(.83,.977,.44,.18)],paint,parts,24)
        top=1.32 if style=='tour' else 1.27 if style=='endurance' else 1.255
        windshield(parts,top)
        if style=='endurance':
            for x in [-.09,.09]:
                R(parts,'Recessed round endurance bezel',(x,.991,.824),(x,.991,.846),.075,15,32)
                R(parts,'Endurance prismatic lamp',(x,.991,.846),(x,.991,.851),.061,9,32)
                for offset in [-.035,0,.035]:
                    half=math.sqrt(.057*.057-offset*offset)
                    R(parts,'Headlight fluted lens',(x+offset,.991-half,.852),(x+offset,.991+half,.852),.0015,3,5)
        else:
            for side in [-1,1]:
                outline=[(side*.025,.95),(side*.172,.955),(side*.186,1.020),(side*.063,1.014)]
                if side<0:outline.reverse()
                front_patch(parts,'Flush angular headlamp bezel',outline,.837,.009,15)
                lens=[(side*.041,.962),(side*.157,.966),(side*.166,1.005),(side*.069,1.001)]
                if side<0:lens.reverse()
                front_patch(parts,'Inset angular headlamp lens',lens,.844,.006,9)
                R(parts,'Lamp optic projector',(side*.105,.985,.846),(side*.105,.985,.850),.018,3,20)
        T(parts,'Nose centre seam',[(0,1.095,.61),(0,1.065,.74),(0,.94,.83)],.002,13,5)
        B(parts,'Instrument binnacle',(0,1.055,.34),(.22,.095,.13),1,.015)
    # Closed curved fender sections; high scrambler fender is visibly distinct.
    for rear,z in [(False,.80),(True,-.73)]:
        y=.76 if scrambler and not rear else .65
        bike_shell('Raised front mudguard' if scrambler and not rear else 'Curved mudguard',[(z-.23,y-.09,.16,.035),(z,y,.22,.035),(z+.23,y-.09,.16,.035)],paint,parts,12)
    B(parts,'Rear tail lamp',(0,.87 if not classic else .80,-.879),(.18,.055,.026),14,.008)
    B(parts,'Rear registration plate',(0,.69,-.89),(.16,.11,.015),13,.005)
    for side in [-1,1]:
        S(parts,'Front amber indicator',(side*.235,.92,.67),(.054,.037,.05),7,12,8)
        S(parts,'Rear amber indicator',(side*.19,.80,-.77),(.054,.035,.046),7,12,8)
    B(parts,'Front brake caliper',(-.10,.395,.956),(.066,.095,.09),7,.012)
    body=join(parts,name+'_L0_Body',root);wheels=[]
    for label_wheel,z in [('Front',.80),('Rear',-.73)]:
        wheel_parts=[];pivot=(0,.322,z);joint=empty(name+'_Wheel_'+label_wheel,root,pivot)
        wheel_parts.append(torus('Road tire',pivot,.247,.075,5,mat,48,10,'X'))
        for j in range(36):
            a=j*math.tau/36
            for side in [-1,1]:
                points=[]
                for k in range(4):
                    x=side*(.018+k*.015);radius=.247+math.sqrt(max(.001,.075*.075-x*x));angle=a+side*k*.018
                    points.append((x,.322+radius*math.cos(angle),z+radius*math.sin(angle)))
                T(wheel_parts,'Shallow directional tire channel',points,.0021,15,5)
        for x in [-.05,.05]:wheel_parts.append(torus('Rim lip',(x,.322,z),.219,.018,3 if classic else 1,mat,36,6,'X'))
        wheel_parts.append(rod('Wheel hub',(-.075,.322,z),(.075,.322,z),.048,2,mat,20))
        for j in range(spokes):
            a=j*math.tau/spokes
            wheel_parts.append(rod('Wheel spoke',(0,.322+math.cos(a)*.045,z+math.sin(a)*.045),(0,.322+math.cos(a+.12)*.215,z+math.sin(a+.12)*.215),.007 if classic else .023,3 if classic else 1,mat,6))
        for x in ([-.075,.075] if full and label_wheel=='Front' else [-.075]):
            brake_disc(wheel_parts,(x,.322,z))
            for j in range(10):
                a=j*math.tau/10;wheel_parts.append(rod('Brake disc radial web',(x,.322+.06*math.cos(a),z+.06*math.sin(a)),(x,.322+.155*math.cos(a+.20),z+.155*math.sin(a+.20)),.009,3,mat,5))
        wheels.append(join(wheel_parts,name+'_L0_'+label_wheel,joint,pivot))
    for obj in [body]+wheels:
        obj.data.calc_loop_triangles()
        if len(obj.data.loop_triangles)>10000:
            bpy.context.view_layer.objects.active=obj;m=obj.modifiers.new('Motorcycle authored LOD budget','DECIMATE');m.ratio=10000/len(obj.data.loop_triangles);m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name)
        for level,ratio in [(1,.44),(2,.16)]:lod_copy(obj,obj.name.replace('_L0_','_L'+str(level)+'_'),ratio,obj.parent)
    empty('SeatAnchor',root,(0,.89,-.30));empty('HandlebarLeft',root,(-.33,1.04,.40));empty('HandlebarRight',root,(.33,1.04,.40))
    export(root,name)
    studio(target=(0,.65,0),camera_pos=(2.8,1.6,3.1),resolution=(1280,960))
    scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.22,.25,.29,1);scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.85
    scene.render.film_transparent=False;scene.cycles.samples=24
    source='ArtSource/P08/'+name+'.blend';bpy.ops.wm.save_as_mainfile(filepath=ROOT+source)
    scene.render.filepath=ROOT+'docs/p08/art/'+name+'-render.png';bpy.ops.render.render(write_still=True)
    report=asset_report(root,concept,surface,'bike',source);report['displayName']=label;report['catalogIndex']=index
    reports.append(report)
print(json.dumps({'batch':'bikes','assets':reports,'conceptFirst':True}))
