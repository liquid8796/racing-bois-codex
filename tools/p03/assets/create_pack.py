"""Original Racing Bois P03/P04 assets. Run through the pinned Blender MCP.

The recipe loads no legacy geometry, sprite, texture, sound, or animation.
Concept revision: ArtSource/Concepts/P03P04/*-concept-v1.png, inspected before
this revision. Concepts guide forms and color, not texture projection.
Coordinates in authoring helpers are meters, Unity X right / Y up / Z forward.
"""
import bpy
import bmesh
import math
import json
from mathutils import Vector

ROOT = 'D:/Project/Unity/racing-bois/'
VEH = ROOT + 'Assets/RacingBois/Art/Vehicles/'
CHAR = ROOT + 'Assets/RacingBois/Art/Characters/'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24

# Deliberately shared palette UVs across modular surfaces. Each primitive is
# uniquely smart-unwrapped inside its tile; the overlap between repeated parts
# is intentional. No photos or existing game imagery is used.
palette = [(.75,.26,.055),(.045,.049,.055),(.105,.12,.14),(.62,.65,.65),
           (.83,.80,.70),(.018,.021,.023),(.035,.082,.095),(.48,.30,.12),
           (.075,.25,.27),(.042,.075,.135),(.57,.31,.065),(.56,.02,.018),
           (.013,.029,.07),(.97,.38,.025),(.86,.83,.73),(.01,.014,.018)]
metallic = [0.25,0.0,0.5,0.85,0.1,0.0,0.15,0.7,0.35,0.0,0.0,0.0,0.2,0.0,0.05,0.1]
smoothness = [.45,.24,.32,.65,.36,.18,.78,.5,.5,.14,.25,.52,.8,.5,.38,.2]
def texture(name, channels, color=True):
    image = bpy.data.images.new(name,256,256,alpha=True)
    if not color: image.colorspace_settings.name='Non-Color'
    pixels=[]
    for y in range(256):
        for x in range(256):
            tile=(y//64)*4+(x//64)
            pixels.extend(channels[tile])
    image.pixels=pixels
    image.filepath_raw=VEH+name+'.png'; image.file_format='PNG'; image.save()
    return image
base=texture('RB_RacePalette_BaseColor',[(*v,1) for v in palette])
cop_colors=list(palette); cop_colors[0]=(.035,.105,.23); cop_colors[4]=(.88,.88,.78)
cop_base=texture('RB_PolicePalette_BaseColor',[(*v,1) for v in cop_colors])
normal=texture('RB_RacePalette_Normal',[(.5,.5,1,1)]*16,False)
mask=texture('RB_RacePalette_MetallicSmoothness',[(metallic[i],1,0,smoothness[i]) for i in range(16)],False)
rough=texture('RB_RacePalette_Roughness',[(1-smoothness[i],)*3+(1,) for i in range(16)],False)
material=bpy.data.materials.new('RB_RacePalette'); material.use_nodes=True
n=material.node_tree.nodes; links=material.node_tree.links; shader=n.get('Principled BSDF')
for name,img,destination in [('Base',base,'Base Color')]:
    tex=n.new('ShaderNodeTexImage');tex.image=img;links.new(tex.outputs['Color'],shader.inputs[destination])
masknode=n.new('ShaderNodeTexImage');masknode.image=mask
sep=n.new('ShaderNodeSeparateColor');links.new(masknode.outputs['Color'],sep.inputs['Color'])
links.new(sep.outputs['Red'],shader.inputs['Metallic'])
roughnode=n.new('ShaderNodeTexImage');roughnode.image=rough;links.new(roughnode.outputs['Color'],shader.inputs['Roughness'])

def bv(v): return Vector((-v[0],-v[2],v[1]))
def clean_mesh(mesh,weld=True):
    bm=bmesh.new();bm.from_mesh(mesh)
    if weld:bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
    boundary=[edge for edge in bm.edges if edge.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    wire=[edge for edge in bm.edges if edge.is_wire]
    if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
    loose=[vertex for vertex in bm.verts if not vertex.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
def empty(name,parent=None,position=(0,0,0)):
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.location=bv(position)
    if parent: o.parent=parent
    return o
def finish(o,name,tile,parent=None,bevel=0):
    o.name=name;bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if bevel:
        mod=o.modifiers.new('Authored edge bevel','BEVEL');mod.width=bevel;mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    clean_mesh(o.data)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.04)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Keep every sample at least eight pixels from a palette edge at base mip.
    col=tile%4; row=tile//4
    for uv in o.data.uv_layers.active.data:
        uv.uv.x=(col+.14+.72*uv.uv.x)/4
        uv.uv.y=(row+.14+.72*uv.uv.y)/4
    o.data.uv_layers.active.name='UV0_IntentionalPaletteReuse'
    o.data.materials.clear();o.data.materials.append(material)
    if parent:
        world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world
    o['authored_from_scratch']=True;o['palette_tile']=tile
    return o
def box(name,pos,size,tile,parent=None,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=bv(pos));o=bpy.context.object
    o.dimensions=(size[0],size[2],size[1]);return finish(o,name,tile,parent,bevel)
def profile(name,outline,width,tile,parent=None,bevel=.008,center_x=0):
    # A closed custom side profile, rather than a stretched cube silhouette.
    vertices=[bv((x,y,z)) for x in [center_x-width/2,center_x+width/2] for y,z in outline]
    count=len(outline)
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces.extend((i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count))
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    return finish(o,name,tile,parent,bevel)
def panel(name,points,offset,tile,parent):
    vertices=[bv(point) for point in points]+[bv(Vector(point)+Vector(offset)) for point in points]
    count=len(points)
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces.extend((i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count))
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    return finish(o,name,tile,parent)
def rod(name,a,b,radius,tile,parent=None,vertices=12):
    av,bvec=bv(a),bv(b);delta=bvec-av
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=delta.length,location=(av+bvec)/2)
    o=bpy.context.object;o.rotation_euler=delta.to_track_quat('Z','Y').to_euler()
    return finish(o,name,tile,parent)
def ellipsoid(name,pos,size,tile,parent=None,segments=16,rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=bv(pos))
    o=bpy.context.object;o.scale=(size[0]/2,size[2]/2,size[1]/2)
    return finish(o,name,tile,parent)
def wheel(name,pos,radius,width,parent):
    joint=empty(name,parent,pos)
    # local visual is a closed torus and a closed axle: both have manifold surfaces.
    bpy.ops.mesh.primitive_torus_add(major_segments=20,minor_segments=8,major_radius=radius-width*.40,minor_radius=width*.40,location=bv(pos),rotation=(0,math.pi/2,0))
    tire=finish(bpy.context.object,name+'_Tire',5,joint)
    bpy.ops.mesh.primitive_torus_add(major_segments=16,minor_segments=6,major_radius=radius*.64,minor_radius=.021,location=bv(pos),rotation=(0,math.pi/2,0))
    finish(bpy.context.object,name+'_Rim',3,joint)
    for i in range(5):
        angle=i*2*math.pi/5
        inner=(pos[0],pos[1]+math.cos(angle)*radius*.12,pos[2]+math.sin(angle)*radius*.12)
        outer=(pos[0],pos[1]+math.cos(angle)*radius*.65,pos[2]+math.sin(angle)*radius*.65)
        rod(name+'_Spoke',inner,outer,.024,3,joint,6)
    cap=rod(name+'_Hub',(pos[0]-width*.45,pos[1],pos[2]),(pos[0]+width*.45,pos[1],pos[2]),radius*.18,2,joint)
    return joint
def join_meshes(objects,name,parent):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    result=bpy.context.object;result.name=name
    # Collapse duplicate material slots to the one shared palette.
    result.data.materials.clear();result.data.materials.append(material)
    for p in result.data.polygons:p.material_index=0
    world=result.matrix_world.copy();result.parent=parent;result.matrix_world=world
    return result
def descendants(root):return list(root.children_recursive)
def valid_mesh(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    result=all(edge.is_manifold for edge in bm.edges) and all(face.calc_area()>1e-10 for face in bm.faces)
    bm.verts.ensure_lookup_table();unseen=set(vertex.index for vertex in bm.verts)
    while unseen:
        pending=[bm.verts[next(iter(unseen))]];indices=set();faces=set()
        while pending:
            at=pending.pop()
            if at.index in indices:continue
            indices.add(at.index);unseen.discard(at.index);faces.update(at.link_faces)
            pending.extend(edge.other_vert(at) for edge in at.link_edges if edge.other_vert(at).index not in indices)
        volume=0
        for face in faces:
            first=face.verts[0].co
            for i in range(1,len(face.verts)-1):volume+=first.dot(face.verts[i].co.cross(face.verts[i+1].co))/6
        if volume<=1e-12:result=False
    bm.free();return result
def simplify_components(obj,source,ratio):
    # Thin glass/stripes and closed tiny hard-surface details are preserved;
    # decimate substantial islands independently, avoiding island collapse.
    name=obj.name;parent=obj.parent;obj.data=source.data.copy()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
    pieces=[obj]+[item for item in bpy.context.selected_objects if item!=obj]
    for part in pieces:
        original=part.data.copy();original.calc_loop_triangles()
        if len(original.loop_triangles)<36:continue
        bpy.context.view_layer.objects.active=part
        for candidate in [ratio,.35,.5,.65,.8,1]:
            if candidate<ratio:continue
            part.data=original.copy()
            mod=part.modifiers.new('Topology-preserving component LOD','DECIMATE');mod.ratio=candidate
            bpy.ops.object.modifier_apply(modifier=mod.name);clean_mesh(part.data,False)
            if valid_mesh(part.data):break
    result=join_meshes(pieces,name,parent)
    if not valid_mesh(result.data):raise RuntimeError('Component LOD invalid: '+name)
    return result
def lod_copy(root,index,ratio,prefix):
    dupmap={}
    sources=[root]+descendants(root)
    for source in sources:
        dupe=source.copy()
        if source.type=='MESH':dupe.data=source.data.copy()
        scene.collection.objects.link(dupe);dupmap[source]=dupe
        dupe.name=source.name.replace('_L0_','_L'+str(index)+'_').replace('_LOD0','_LOD'+str(index))
    for source,dupe in dupmap.items():
        if source.parent in dupmap:dupe.parent=dupmap[source.parent]
        else:dupe.parent=source.parent
        if dupe.type=='MESH':
            bpy.context.view_layer.objects.active=dupe
            # Tiny closed detail islands must not collapse into invalid edges.
            # Increase retained geometry only for meshes that fail topology QA.
            for candidate in [ratio,.28,.33,.38,.43,.48,.50]:
                if candidate<ratio:continue
                dupe.data=source.data.copy()
                modifier=dupe.modifiers.new('LOD simplification','DECIMATE');modifier.ratio=candidate
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                clean_mesh(dupe.data,False)
                valid=valid_mesh(dupe.data)
                if valid:
                    dupe['lod_retained_ratio']=candidate
                    break
            if not valid:dupe=simplify_components(dupe,source,ratio)
        dupe.hide_render=True
    return dupmap[root]

assets=[]
def make_motorcycle():
    root=empty('RB_Motorcycle');lod=empty('RB_Moto_LOD0',root)
    body=[]
    def b(name,pos,size,tile,bevel=.015):o=box(name,pos,size,tile,lod,bevel);body.append(o);return o
    def r(*args,**kw):o=rod(*args,parent=lod,**kw);body.append(o);return o
    def e(*args,**kw):o=ellipsoid(*args,parent=lod,**kw);body.append(o);return o
    def p(*args,**kw):o=profile(*args,parent=lod,**kw);body.append(o);return o
    wheel('RB_Moto_L0_Wheel_Front',(0,.33,.72),.33,.19,lod)
    wheel('RB_Moto_L0_Wheel_Rear',(0,.35,-.72),.35,.23,lod)
    for side in [-1,1]:
        x=side*.16
        r('Frame_'+str(side),(x,.48,-.46),(x,.75,.30),.036,2)
        r('UpperFrame_'+str(side),(x,.68,-.62),(x,.81,.12),.03,3)
        r('Fork_'+str(side),(x,.33,.72),(x,.98,.48),.033,7)
        r('SwingArm_'+str(side),(x,.35,-.72),(x,.48,-.12),.035,2)
        r('Shock_'+str(side),(x,.42,-.6),(x,.78,-.35),.038,7)
        r('HandleGrip_'+str(side),(side*.19,1.06,.36),(side*.38,1.055,.28),.026,5)
        b('FootPeg_'+str(side),(side*.25,.43,-.1),(.15,.045,.08),3)
        r('MirrorStem_'+str(side),(side*.32,1.05,.32),(side*.40,1.16,.35),.009,3,vertices=6)
        b('Mirror_'+str(side),(side*.42,1.17,.36),(.11,.052,.065),1,.012)
    for y in [.43,.55]:
        r('RightShortExhaust',(.25,y,-.15),(.29,y,-.76),.060,3)
        r('ExhaustOutlet',(.29,y,-.755),(.29,y,-.78),.045,15)
    b('EngineBlock',(0,.51,-.05),(.33,.33,.32),2,.02)
    for y in [.43,.48,.53,.58]:b('EngineCoolingFin',(0,y,-.05),(.37,.016,.35),3,.004)
    p('AngularAmberTank',[(.73,-.24),(.91,-.25),(1.01,-.12),(1.01,.14),(.91,.32),(.76,.29)],.43,0,bevel=.027)
    p('IvoryTankStripe',[(.914,-.251),(1.014,-.12),(1.014,.14),(1.007,.14),(1.007,-.12),(.907,-.251)],.045,4,bevel=0)
    b('Seat',(0,.81,-.42),(.35,.10,.55),1,.034)
    b('TailFairing',(0,.78,-.69),(.39,.19,.28),1,.024)
    b('RearLamp',(0,.81,-.845),(.21,.065,.04),11,.008)
    for x in [-.091,.091]:
        r('RoundLampHousing',(x,.99,.60),(x,.99,.745),.099,1,vertices=16)
        r('RoundIvoryHeadlamp',(x,.99,.744),(x,.99,.767),.077,4,vertices=16)
    p('AngularGraphiteCowl',[(1.055,.60),(1.165,.51),(1.19,.53),(1.11,.70)],.355,2,bevel=.008)
    b('FrontFender',(0,.66,.73),(.23,.055,.47),1,.02)
    for side in [-1,1]:b('FrontIndicator',(side*.245,1.005,.62),(.10,.045,.065),13,.012)
    join_meshes(body,'RB_Moto_L0_Body',lod)
    for joint in list(lod.children):
        if 'Wheel_' in joint.name:join_meshes([c for c in joint.children if c.type=='MESH'],joint.name+'_Mesh',joint)
    lod_copy(lod,1,.52,'RB_Moto');lod_copy(lod,2,.23,'RB_Moto')
    assets.append((root,VEH,'ArtSource/Vehicles/RB_Motorcycle.blend'))
    return root

def make_rider():
    root=empty('RB_Rider');lod=empty('RB_Rider_LOD0',root)
    hip=empty('RB_Rider_L0_Hip',lod,(0,.94,0))
    pelvis=box('Pelvis',(0,.95,0),(.34,.25,.24),9,hip,.05)
    torso=empty('RB_Rider_L0_Torso',hip,(0,.17,0))
    # joint positions are local offsets; primitive helpers receive world coords.
    chest=box('Jacket',(0,1.23,0),(.47,.43,.27),1,torso,.065)
    back=box('JacketBackPanel',(0,1.23,-.145),(.30,.30,.026),1,torso,.015)
    stripe=box('JacketShoulderMark',(0,1.405,-.13),(.39,.042,.035),0,torso,.005)
    zipline=rod('JacketZip',(0,1.085,.141),(0,1.393,.141),.008,3,torso,6)
    collar=ellipsoid('JacketCollar',(0,1.46,0),(.24,.12,.24),1,torso,12,6)
    join_meshes([chest,back,stripe,zipline,collar],'RB_Rider_L0_Torso_Mesh',torso)
    head=empty('RB_Rider_L0_Head',torso,(0,.42,0))
    helmet=ellipsoid('Helmet',(0,1.625,0),(.35,.38,.36),4,head,20,10)
    visor=ellipsoid('Visor',(0,1.64,.11),(.32,.145,.19),12,head,16,8)
    chin=box('ChinGuard',(0,1.515,.10),(.26,.085,.18),1,head,.03)
    headparts=[helmet,visor,chin]
    outer=[];inner=[]
    for step in range(13):
        angle=math.radians(-75+step*10)
        outer.append((1.625+.194*math.cos(angle),.184*math.sin(angle)))
        inner.append((1.625+.187*math.cos(angle),.177*math.sin(angle)))
    for x in [-.028,.028]:headparts.append(profile('HelmetAmberStripe',outer+list(reversed(inner)),.018,0,head,0,x))
    join_meshes(headparts,'RB_Rider_L0_Head_Mesh',head)
    for side,label in [(-1,'L'),(1,'R')]:
        upper=empty('RB_Rider_L0_UpperArm_'+label,torso,(side*.26,.26,0))
        a=rod('JacketSleeve',(side*.26,1.37,0),(side*.33,1.08,0),.095,1,upper)
        pad=ellipsoid('ElbowPad',(side*.33,1.08,0),(.21,.19,.20),1,upper)
        shoulder=ellipsoid('AmberShoulder',(side*.27,1.35,0),(.21,.19,.21),0,upper)
        band1=rod('IvorySleeveBand',(side*.293,1.267,0),(side*.3,1.24,0),.097,4,upper)
        band2=rod('IvorySleeveBand',(side*.309,1.207,0),(side*.316,1.18,0),.097,4,upper)
        join_meshes([a,pad,shoulder,band1,band2],'RB_Rider_L0_UpperArm_'+label+'_Mesh',upper)
        fore=empty('RB_Rider_L0_Forearm_'+label,upper,(side*.07,-.29,0))
        arm=rod('Forearm',(side*.33,1.08,0),(side*.34,.82,.015),.075,1,fore)
        glove=box('Glove',(side*.34,.795,.02),(.15,.15,.16),10,fore,.04)
        join_meshes([arm,glove],'RB_Rider_L0_Forearm_'+label+'_Mesh',fore)
        thigh=empty('RB_Rider_L0_Thigh_'+label,hip,(side*.105,-.09,0))
        leg=rod('Trouser',(side*.105,.85,0),(side*.13,.49,.02),.105,9,thigh)
        knee=ellipsoid('KneePad',(side*.13,.47,.055),(.22,.20,.23),2,thigh)
        join_meshes([leg,knee],'RB_Rider_L0_Thigh_'+label+'_Mesh',thigh)
        shin=empty('RB_Rider_L0_Shin_'+label,thigh,(side*.025,-.38,.02))
        lower=rod('Shin',(side*.13,.47,.02),(side*.13,.14,0),.085,9,shin)
        boot=box('Boot',(side*.13,.10,.075),(.19,.19,.34),5,shin,.035)
        join_meshes([lower,boot],'RB_Rider_L0_Shin_'+label+'_Mesh',shin)
    pelvis.name='RB_Rider_L0_Hip_Mesh'
    lod_copy(lod,1,.5,'RB_Rider');lod_copy(lod,2,.23,'RB_Rider')
    assets.append((root,CHAR,'ArtSource/Characters/RB_Rider.blend'))
    return root

def make_car(van=False):
    name='RB_TrafficVan' if van else 'RB_TrafficCoupe';root=empty(name);lod=empty(name+'_LOD0',root)
    pieces=[]
    def b(label,pos,size,tile,bevel=.03):
        o=box(name+'_L0_'+label,pos,size,tile,lod,bevel);pieces.append(o);return o
    width=1.95 if van else 1.85;length=4.5 if van else 4.4
    def p(label,outline,span,tile,bevel=.012):
        o=profile(name+'_L0_'+label,outline,span,tile,lod,bevel);pieces.append(o);return o
    def pane(label,points,offset,tile=6):
        o=panel(name+'_L0_'+label,points,offset,tile,lod);pieces.append(o);return o
    # Open-bottom wheel arches are part of the closed body profile; they are
    # modeled geometry, not a dark decal hiding a solid body through the wheel.
    arches=[(.34,1.81),(.52,1.74),(.68,1.60),(.75,1.40),(.68,1.20),(.52,1.06),(.34,.99),
            (.34,-.99),(.52,-1.06),(.68,-1.20),(.75,-1.40),(.68,-1.60),(.52,-1.74),(.34,-1.81)]
    if van:
        p('IvoryDeliveryShell',[(.34,-2.25),(2.17,-2.25),(2.22,-1.95),(2.22,1.35),(1.32,2.15),(1.20,2.25),(.34,2.25)]+arches,width,4,.028)
        pane('WideWindshield',[(-.84,1.38,2.107),(.84,1.38,2.107),(.84,2.10,1.463),(-.84,2.10,1.463)],(0,.005,.009))
        for side in [-1,1]:
            pane('CabWindow',[(side*.98,1.36,.54),(side*.98,2.08,.54),(side*.98,2.08,1.32),(side*.98,1.36,1.985)],(side*.008,0,0))
            b('AmberBeltStripe',(side*.980,1.085,0),(.025,.17,4.42),0,.004)
            b('CharcoalSill',(side*.982,.45,0),(.04,.30,1.97),1,.018)
            for z in [-2.04,2.04]:b('SillEnd',(side*.982,.45,z),(.04,.30,.38),1,.014)
            b('CargoPanelUpper',(side*.980,1.94,-.90),(.020,.025,2.42),14,.004)
            b('DoorHandle',(side*.997,1.29,.56),(.045,.065,.18),1,.012)
            b('RearLamp',(side*.80,1.01,-2.275),(.11,.42,.035),11,.01)
        b('RearBelt',(0,1.085,-2.263),(1.91,.17,.035),0,.003)
        b('FrontBelt',(0,1.085,2.263),(1.91,.17,.035),0,.003)
        b('RearDoorSeam',(0,1.47,-2.267),(.02,1.4,.023),2,.002)
        b('RearDoorHandle',(0,1.08,-2.285),(.12,.17,.035),1,.012)
        for x in [-.72,-.36,0,.36,.72]:b('RoofMarker',(x,2.255,1.17),(.075,.07,.14),13,.012)
    else:
        p('PetrolTealWedge',[(.34,-2.2),(.95,-2.2),(1.01,-1.2),(.94,.95),(.84,2.2),(.34,2.2)]+arches,width,8,.028)
        # Cabin narrows toward the roof, so the side glass follows a sloped plane.
        cross=[(-1.19,.89,.86,.94,.97),(-.53,.87,.73,.95,1.36),(.46,.87,.73,.95,1.36),(1.09,.87,.85,.94,.97)]
        verts=[]
        for z,wb,wt,yb,yt in cross:verts.extend([(-wb,yb,z),(wb,yb,z),(wt,yt,z),(-wt,yt,z)])
        vertices=[bv(v) for v in verts];faces=[(3,2,1,0),(12,13,14,15)]
        for section in range(3):
            for edge in range(4):faces.append((section*4+edge,section*4+(edge+1)%4,(section+1)*4+(edge+1)%4,(section+1)*4+edge))
        mesh=bpy.data.meshes.new('CoupeRoofMesh');mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new('CoupeRoof',mesh);scene.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        pieces.append(finish(obj,name+'_L0_SlopedRoof',8,lod,.012))
        pane('SlopedWindshield',[(-.833,1.012,1.047),(.833,1.012,1.047),(.709,1.332,.498),(-.709,1.332,.498)],(0,.005,.008))
        pane('RearGlass',[(-.836,1.014,-1.138),(-.707,1.33,-.570),(.707,1.33,-.570),(.836,1.014,-1.138)],(0,.005,-.008))
        for side in [-1,1]:
            pane('DoorWindow',[(side*.859,1.006,.980),(side*.743,1.326,.44),(side*.743,1.326,-.24),(side*.859,1.006,-.24)],(side*.008,0,0))
            pane('QuarterWindow',[(side*.859,1.006,-.31),(side*.743,1.326,-.31),(side*.743,1.326,-.50),(side*.859,1.006,-1.055)],(side*.008,0,0))
            b('DoorHandle',(side*.939,.913,-.38),(.027,.050,.16),1,.008)
            b('RockerRail',(side*.933,.39,0),(.04,.13,1.97),1,.010)
            b('AmberIndicator',(side*.944,.76,1.51),(.025,.065,.13),13,.006)
        b('RearSpoiler',(0,1.001,-2.02),(1.77,.055,.19),8,.012)
    for side in [-1,1]:
        b('Mirror',(side*(1.07 if van else .995),1.48 if van else 1.05,1.5 if van else .87),(.17,.21 if van else .11,.16),1,.02)
        for z in [-1.40,1.40]:
            joint=wheel(name+'_L0_Wheel',(side*(.90 if van else .86),.35,z),.35,.23,lod)
            pieces.extend([m for m in joint.children if m.type=='MESH'])
    b('FrontBumper',(0,.50,length/2+.015),(width,.26,.11),1,.025)
    b('RearBumper',(0,.50,-length/2-.015),(width,.26,.11),1,.025)
    for side in [-1,1]:
        b('Headlamp',(side*.64,.86 if van else .76,length/2+.015),(.36,.23 if van else .13,.045),4,.010)
        b('LampDivider',(side*.64,.86 if van else .76,length/2+.042),(.013,.21 if van else .12,.012),3,.001)
        b('Indicator',(side*.86,.86 if van else .76,length/2+.018),(.12,.23 if van else .13,.04),13,.008)
        if not van:b('Taillamp',(side*.62,.79,-length/2-.015),(.51,.18,.045),11,.01)
    b('Grille',(0,.86 if van else .75,length/2+.018),(.91,.25 if van else .15,.06),1,.008)
    for y in ([.80,.87,.94] if van else [.72,.77]):b('GrilleBar',(0,y,length/2+.053),(.87,.018,.016),2,.002)
    join_meshes(pieces,name+'_L0_Body',lod)
    for child in list(lod.children):
        if child.type=='EMPTY' and len(child.children)==0:bpy.data.objects.remove(child,do_unlink=True)
    lod_copy(lod,1,.5,name);lod_copy(lod,2,.20,name)
    assets.append((root,VEH,'ArtSource/Vehicles/'+name+'.blend'));return root

moto=make_motorcycle();rider=make_rider();coupe=make_car();van=make_car(True)
report={'authorship':'Original procedural hard-surface modeling, no game assets loaded',
        'iteration':'Concept-guided revision after initial graybox',
        'concepts':['motorcycle-concept-v1.png','rider-concept-v1.png','coupe-concept-v1.png','van-concept-v1.png'],
        'blender_version':bpy.app.version_string,'coordinate_contract':'meters; exported Unity Y-up Z-forward',
        'palette_uv_policy':'Intentional repeated palette tile sampling between parts; uniquely packed islands within each primitive',
        'textures':{'base':256,'police_base':256,'normal':256,'metallic_smoothness':256,'roughness':256},'assets':[]}
for root,folder,source in assets:
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in descendants(root):o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=folder+root.name+'.fbx',use_selection=True,
        object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    asset={'name':root.name,'fbx':folder+root.name+'.fbx','lods':[],'issues':[]}
    for lod in root.children:
        if '_LOD' not in lod.name:continue
        meshes=[o for o in descendants(lod) if o.type=='MESH'];triangles=0
        for mesh in meshes:
            mesh.data.calc_loop_triangles();triangles+=len(mesh.data.loop_triangles)
            bm=bmesh.new();bm.from_mesh(mesh.data)
            nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
            loose=sum(1 for v in bm.verts if not v.link_faces)
            degenerate=sum(1 for face in bm.faces if face.calc_area()<1e-10)
            volume=bm.calc_volume(signed=True)
            bm.free()
            uvbad=sum(1 for uv in mesh.data.uv_layers.active.data if min(uv.uv)<0 or max(uv.uv)>1)
            if nonmanifold or loose or degenerate or volume<=0 or uvbad:
                asset['issues'].append({'mesh':mesh.name,'nonmanifold':nonmanifold,'loose':loose,'degenerate':degenerate,'signed_volume':volume,'uv_out_of_bounds':uvbad})
        asset['lods'].append({'name':lod.name,'mesh_count':len(meshes),'triangles':triangles})
    report['assets'].append(asset)
    # Each .blend includes its named production collection and the shared source
    # pack, allowing recipe reruns and all procedural material inputs to be kept.
    bpy.ops.wm.save_as_mainfile(filepath=ROOT+source)

# Neutral source scene and a review composition; sources were saved before the
# layout offset below, so their root transforms remain identity.
moto.location=bv((-1.15,0,0));rider.location=bv((.45,0,.1))
coupe.location=bv((3.35,0,-.5));van.location=bv((-4.45,0,-.85))
world=bpy.data.worlds.new('RB_PackStudio');scene.world=world;world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.095,.12,.16,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.45
ground=box('ReviewGround',(0,-.055,0),(30,.1,24),1,None,0)
for name,loc,energy,size in [('Key',(4,8,7),2200,8),('Rim',(-5,6,-5),2600,7)]:
    data=bpy.data.lights.new(name,'AREA');light=bpy.data.objects.new(name,data);scene.collection.objects.link(light)
    light.location=bv(loc);data.energy=energy;data.shape='DISK';data.size=size
    light.rotation_euler=(bv((0,.8,0))-light.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('PackReview');camera=bpy.data.objects.new('PackReview',camera_data)
scene.collection.objects.link(camera);camera.location=bv((9,7,12));camera.rotation_euler=(bv((0,.8,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.lens=48
scene.camera=camera;scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=ROOT+'docs/p03/assets/original-pack.png'
scene.view_settings.view_transform='AgX'
bpy.ops.render.render(write_still=True)
print(json.dumps(report))
