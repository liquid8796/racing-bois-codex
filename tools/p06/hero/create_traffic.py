"""New coupe/van from inspected P03/P04 2D concepts, no imported old meshes."""
scene=begin('traffic')
palette=[((.065,.235,.255),.52,.30,'paint'),((.022,.027,.029),.1,.69,'rubber'),((.13,.16,.18),.80,.34,'brushed'),((.5,.54,.57),.90,.26,'brushed'),((.72,.68,.54),.4,.35,'paint'),((.012,.025,.033),.25,.12,'paint'),((.018,.021,.024),0,.85,'rubber'),((.62,.64,.57),.3,.16,'paint'),((.50,.18,.03),.1,.31,'paint'),((.64,.25,.018),.1,.19,'paint'),((.43,.012,.008),.1,.17,'paint'),((.38,.40,.37),.8,.35,'brushed'),((.02,.04,.05),.1,.18,'paint'),((.13,.15,.15),.7,.46,'brushed'),((.8,.75,.62),.15,.28,'paint'),((.008,.011,.014),0,.9,'rubber')]
mat=atlas('RB_P06_Traffic',palette)
def profile(name,outline,width,tile,bevel=.012,centerx=0):
    vertices=[bv((x,y,z)) for x in [centerx-width/2,centerx+width/2] for y,z in outline];n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n));mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);finish(o,name,tile,mat,bevel)
    for face in o.data.polygons:face.use_smooth=face.area<.025
    return o
def panel(name,points,offset,tile):
    verts=[bv(p) for p in points]+[bv(Vector(p)+Vector(offset)) for p in points];n=len(points);faces=[tuple(reversed(range(n))),tuple(range(n,n*2))];faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n));mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);return finish(o,name,tile,mat)
reports=[]
for van in [False,True]:
    name='RB_P06_TrafficVan' if van else 'RB_P06_TrafficCoupe';root=empty(name);parts=[];paint=4 if van else 0;width=1.98 if van else 1.86;half=width/2;wheel_y=.35 if van else .335;wheel_z=1.40 if van else 1.35;radius=.35 if van else .335
    outline=[(.35,2.22),(.87,2.22),(.96,1.2),(.98,-1.2),(.88,-2.22),(.35,-2.22)]
    # Bottom returns rear->front with real open wheel arches in the body silhouette.
    for center in [-wheel_z,wheel_z]:
        for i in range(13):a=math.pi-i*math.pi/12;outline.append((wheel_y+(radius+.025)*math.sin(a),center+(radius+.025)*math.cos(a)))
    parts.append(profile('Sculpted lower body',outline,width,paint,.018))
    if van:
        cabin=[(.84,-2.20),(2.18,-2.18),(2.23,-1.98),(2.23,.84),(2.10,1.13),(1.28,1.77),(.96,2.16)]
        parts.append(profile('Panel van coachwork',cabin,width,paint,.025))
        parts.append(box('Van nose joining panel',(0,.934,2.16),(width,.155,.13),paint,mat,.012))
        parts.append(panel('Broad front windscreen',[(-.895,1.34,1.75),(.895,1.34,1.75),(.865,2.08,1.15),(-.865,2.08,1.15)],(0,.005,.008),5))
        for sign in [-1,1]:
            x=sign*(half+.006)
            parts.append(panel('Van front door glass',[(x,1.36,.80),(x,1.36,1.67),(x,2.07,1.095),(x,2.13,.80)],(sign*.008,0,0),5))
            parts.append(box('Orange van body stripe',(x,1.14,-.25),(.011,.15,3.65),8,mat,.001))
            parts.append(box('Lower body cladding',(x,.56,-.1),(.012,.21,3.9),1,mat,.003))
            for z in [-.58,.79]:parts.append(tube('Sliding door seam',[(x,1.01,z),(x,2.09,z),(x,2.145,z+.08)],.004,13,mat,5))
            parts.append(tube('Coachwork press line',[(x,1.42,-2.07),(x,2.06,-2.07),(x,2.13,-1.98),(x,2.13,.59),(x,2.06,.67)],.003,14,mat,5))
            parts.append(box('Door handle',(x+sign*.017,1.23,.95),(.040,.035,.13),1,mat,.009))
            for z in [-1.20,-.3,.6]:parts.append(box('Roof pressed stiffener',(sign*.48,2.239,z),(.12,.016,.63),14,mat,.006))
        for x in [-.70,-.35,0,.35,.70]:parts.append(box('Roof amber marker',(x,2.242,.90),(.07,.035,.066),9,mat,.008))
        parts.append(box('Rear orange stripe',(0,1.13,-2.234),(1.87,.15,.01),8,mat,.001))
        parts.append(tube('Rear split door seam',[(0,.96,-2.23),(0,2.12,-2.23)],.004,13,mat,5))
        for x in [-.88,.88]:
            parts.append(box('Vertical van taillight',(x,1.10,-2.246),(.115,.36,.027),10,mat,.010))
            for y in [1.51,1.96]:parts.append(box('Rear hinge',(x,y,-2.244),(.048,.070,.016),3,mat,.004))
    else:
        cabin=[(.925,-1.40),(1.325,-.72),(1.36,-.58),(1.36,.42),(1.30,.57),(.94,1.18)]
        parts.append(profile('Coupe roof pillars',cabin,1.64,paint,.012))
        parts.append(panel('Sloping windshield',[(-.807,.975,1.168),(.807,.975,1.168),(.760,1.30,.58),(-.760,1.30,.58)],(0,.004,.005),5))
        parts.append(panel('Rear glass',[(-.79,.98,-1.35),(-.74,1.30,-.76),(.74,1.30,-.76),(.79,.98,-1.35)],(0,.004,-.004),5))
        for sign in [-1,1]:
            x=sign*.826
            parts.append(panel('Main coupe side window',[(x,.99,-.32),(x,.99,1.06),(x,1.29,.54),(x,1.307,-.32)],(sign*.006,0,0),5))
            parts.append(panel('Rear quarter glass',[(x,.99,-1.25),(x,.99,-.38),(x,1.305,-.38),(x,1.30,-.70)],(sign*.006,0,0),5))
            parts.append(tube('Door seam',[(sign*.936,.76,-.43),(sign*.936,.94,-.43),(sign*.936,.94,1.04)],.0025,13,mat,5))
            parts.append(box('Flush coupe door handle',(sign*.946,.866,-.33),(.019,.033,.112),1,mat,.005))
            parts.append(box('Beltline protective strip',(sign*.944,.64,0),(.018,.042,3.75),1,mat,.004))
            parts.append(box('Rear coupe lamp',(sign*.71,.815,-2.238),(.28,.145,.026),10,mat,.008))
            parts.append(box('Rear reversing lamp',(sign*.61,.815,-2.254),(.10,.06,.008),7,mat,.002))
        parts.append(box('Subtle rear deck spoiler',(0,.976,-2.00),(1.70,.038,.19),paint,mat,.015))
    # Front and rear fascia components, grille slats, headlight lenses and wipers.
    for z in ([2.25,-2.27] if van else [2.20,-2.20]):parts.append(box('Rounded traffic bumper',(0,.45,z),(width+.03,.21,.10),1,mat,.026))
    parts.append(box('Dark front grille',(0,.765,2.223),(1.11,.175,.035),15,mat,.013))
    for y in [.705,.74,.775,.81]:parts.append(box('Grille horizontal louver',(0,y,2.246),(1.04,.012,.012),13,mat,.002))
    for sign in [-1,1]:
        x=sign*(half-.18);parts.append(box('Headlight bezel',(x,.783,2.240),(.27,.185,.034),1,mat,.017))
        parts.append(box('Headlight glass',(x,.783,2.262),(.235,.148,.015),7,mat,.014))
        for dx in [-.074,-.025,.025,.074]:parts.append(box('Headlight lens prism',(x+dx,.783,2.269),(.002,.128,.002),14,mat,.0003))
        parts.append(box('Amber front indicator',(sign*(half-.015),.785,2.24),(.073,.145,.030),9,mat,.010))
        parts.append(box('Traffic wing mirror',(sign*(half+.065),1.55 if van else 1.04,.92 if van else .82),(.17,.16 if van else .105,.14),1,mat,.027))
        parts.append(tube('Windscreen wiper',[(sign*.05,1.35 if van else .995,1.77 if van else 1.15),(sign*.62,1.41 if van else 1.02,1.705 if van else 1.105)],.007,1,mat,6))
    # Wheel recess liners, tires, inset cast rims and clear hubs.
    for sign in [-1,1]:
        for z in [-wheel_z,wheel_z]:
            x=sign*(half-.03);pos=(x,wheel_y,z)
            parts.append(torus('Road tire',pos,radius-.072,.072,6,mat,segments=28,minor_segments=8))
            parts.append(torus('Alloy rim',(x+sign*.065,wheel_y,z),radius*.68,.020,3,mat,segments=24,minor_segments=6))
            parts.append(rod('Wheel center hub',(x,wheel_y,z),(x+sign*.082,wheel_y,z),.061,2,mat,12))
            for j in range(5):
                a=j*math.tau/5;parts.append(rod('Wheel spoke',(x+sign*.07,wheel_y+.051*math.cos(a),z+.051*math.sin(a)),(x+sign*.07,wheel_y+radius*.67*math.cos(a+.12),z+radius*.67*math.sin(a+.12)),.018,3,mat,5))
            # Dark depth behind the body arch keeps suspension recess readable.
            parts.append(rod('Arch shadow',(sign*(half-.12),wheel_y,z),(sign*(half-.14),wheel_y,z),radius*.91,15,mat,20))
    body=join(parts,name+'_L0_Body',root)
    body.data.calc_loop_triangles();initial=len(body.data.loop_triangles)
    if initial>5600:
        bpy.context.view_layer.objects.active=body;mod=body.modifiers.new('Traffic web budget','DECIMATE');mod.ratio=5600/initial;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    for level,ratio in [(1,.43),(2,.17)]:lod_copy(body,name+'_L'+str(level)+'_Body',ratio,root)
    empty(name+'_FrontMarker',root,(0,.6,2.25));empty(name+'_RearMarker',root,(0,.6,-2.27))
    export(root,name)
    reports.append({'name':name,'concept':'ArtSource/Concepts/P03P04/'+('van' if van else 'coupe')+'-concept-v1.png','lods':[],'colliderSize':[2.31,2.29,4.64] if van else [2.16,1.36,4.54]})
    for level in range(3):
        o=bpy.data.objects[name+'_L'+str(level)+'_Body'];o.data.calc_loop_triangles();reports[-1]['lods'].append({'level':level,'triangles':len(o.data.loop_triangles),'renderers':1})
    for obj in root.children_recursive:obj.hide_render=obj.type=='MESH' and '_L0_' not in obj.name
    if van:
        for obj in bpy.data.objects['RB_P06_TrafficCoupe'].children_recursive:obj.hide_render=True
    studio(target=(0,1 if van else .65,0),camera_pos=(5.3,3.0,6.0),resolution=(1280,850));save_render(name)
print(json.dumps({'assets':reports,'sharedMaterial':'RB_P06_Traffic','textures':{'base':1024,'normal_mask_roughness':512},'geometryReuseFromPriorPhases':False}))
