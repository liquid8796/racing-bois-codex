"""Original Racing Bois P03/P04 assets. Run through the pinned Blender MCP.

The recipe loads no legacy geometry, sprite, texture, sound, or animation.
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
palette = [(.95,.235,.055),(.038,.052,.071),(.14,.19,.24),(.63,.7,.73),
           (.84,.88,.79),(.024,.031,.04),(.28,.55,.64),(.99,.72,.25)]
metallic = [0.25,0.0,0.5,0.85,0.1,0.0,0.5,0.1]
smoothness = [.45,.2,.32,.65,.36,.18,.74,.55]
def texture(name, channels, color=True):
    image = bpy.data.images.new(name,256,256,alpha=True)
    if not color: image.colorspace_settings.name='Non-Color'
    pixels=[]
    for y in range(256):
        for x in range(256):
            tile=(y//128)*4+(x//64)
            pixels.extend(channels[tile])
    image.pixels=pixels
    image.filepath_raw=VEH+name+'.png'; image.file_format='PNG'; image.save()
    return image
base=texture('RB_RacePalette_BaseColor',[(*v,1) for v in palette])
cop_colors=list(palette); cop_colors[0]=(.035,.105,.23); cop_colors[4]=(.88,.88,.78)
cop_base=texture('RB_PolicePalette_BaseColor',[(*v,1) for v in cop_colors])
normal=texture('RB_RacePalette_Normal',[(.5,.5,1,1)]*8,False)
mask=texture('RB_RacePalette_MetallicSmoothness',[(metallic[i],1,0,smoothness[i]) for i in range(8)],False)
rough=texture('RB_RacePalette_Roughness',[(1-smoothness[i],)*3+(1,) for i in range(8)],False)
material=bpy.data.materials.new('RB_RacePalette'); material.use_nodes=True
n=material.node_tree.nodes; links=material.node_tree.links; shader=n.get('Principled BSDF')
for name,img,destination in [('Base',base,'Base Color')]:
    tex=n.new('ShaderNodeTexImage');tex.image=img;links.new(tex.outputs['Color'],shader.inputs[destination])
masknode=n.new('ShaderNodeTexImage');masknode.image=mask
sep=n.new('ShaderNodeSeparateColor');links.new(masknode.outputs['Color'],sep.inputs['Color'])
links.new(sep.outputs['Red'],shader.inputs['Metallic'])
roughnode=n.new('ShaderNodeTexImage');roughnode.image=rough;links.new(roughnode.outputs['Color'],shader.inputs['Roughness'])

def bv(v): return Vector((v[0],-v[2],v[1]))
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
        uv.uv.y=(row+.08+.84*uv.uv.y)/2
    o.data.uv_layers.active.name='UV0_IntentionalPaletteReuse'
    o.data.materials.clear();o.data.materials.append(material)
    if parent:
        world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world
    o['authored_from_scratch']=True;o['palette_tile']=tile
    return o
def box(name,pos,size,tile,parent=None,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=bv(pos));o=bpy.context.object
    o.dimensions=(size[0],size[2],size[1]);return finish(o,name,tile,parent,bevel)
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
    hub=rod(name+'_Rim',(pos[0]-width*.39,pos[1],pos[2]),(pos[0]+width*.39,pos[1],pos[2]),radius*.64,3,joint,16)
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
                bm=bmesh.new();bm.from_mesh(dupe.data)
                valid=all(e.is_manifold for e in bm.edges) and all(f.calc_area()>1e-10 for f in bm.faces)
                bm.free()
                if valid:
                    dupe['lod_retained_ratio']=candidate
                    break
            if not valid:raise RuntimeError('LOD topology could not be preserved: '+dupe.name)
        dupe.hide_render=True
    return dupmap[root]

assets=[]
def make_motorcycle():
    root=empty('RB_Motorcycle');lod=empty('RB_Moto_LOD0',root)
    body=[]
    def b(name,pos,size,tile,bevel=.015):o=box(name,pos,size,tile,lod,bevel);body.append(o);return o
    def r(*args,**kw):o=rod(*args,parent=lod,**kw);body.append(o);return o
    def e(*args,**kw):o=ellipsoid(*args,parent=lod,**kw);body.append(o);return o
    wheel('RB_Moto_L0_Wheel_Front',(0,.33,.72),.33,.19,lod)
    wheel('RB_Moto_L0_Wheel_Rear',(0,.35,-.72),.35,.23,lod)
    for side in [-1,1]:
        x=side*.16
        r('Frame_'+str(side),(x,.48,-.46),(x,.75,.30),.036,2)
        r('UpperFrame_'+str(side),(x,.68,-.62),(x,.81,.12),.03,3)
        r('Fork_'+str(side),(x,.33,.72),(x,.98,.48),.027,3)
        r('SwingArm_'+str(side),(x,.35,-.72),(x,.48,-.12),.035,2)
        r('Shock_'+str(side),(x,.42,-.6),(x,.78,-.35),.038,7)
        r('HandleGrip_'+str(side),(side*.19,1.06,.36),(side*.38,1.055,.28),.026,5)
        r('Exhaust_'+str(side),(side*.2,.40,-.07),(side*.29,.41,-.68),.055,3)
        b('FootPeg_'+str(side),(side*.25,.43,-.1),(.15,.045,.08),3)
    b('EngineBlock',(0,.51,-.05),(.33,.33,.32),2,.02)
    for y in [.43,.48,.53,.58]:b('EngineCoolingFin',(0,y,-.05),(.37,.016,.35),3,.004)
    e('SculptedTank',(0,.845,.04),(.44,.31,.64),0,segments=16,rings=8)
    b('Seat',(0,.81,-.42),(.35,.10,.55),1,.034)
    b('TailFairing',(0,.78,-.69),(.39,.19,.28),0,.024)
    b('RearLamp',(0,.81,-.845),(.21,.065,.04),0,.008)
    b('HeadlampHousing',(0,.97,.61),(.33,.18,.14),2,.025)
    b('Headlamp',(0,.98,.69),(.27,.10,.025),4,.008)
    b('FrontFender',(0,.66,.73),(.23,.055,.47),0,.02)
    b('NumberPlate',(0,.855,.75),(.25,.10,.028),4,.009)
    b('TankStripe',(0,.99,.04),(.065,.012,.34),4,.004)
    join_meshes(body,'RB_Moto_L0_Body',lod)
    for joint in list(lod.children):
        if 'Wheel_' in joint.name:join_meshes([c for c in joint.children if c.type=='MESH'],joint.name+'_Mesh',joint)
    lod_copy(lod,1,.52,'RB_Moto');lod_copy(lod,2,.23,'RB_Moto')
    assets.append((root,VEH,'ArtSource/Vehicles/RB_Motorcycle.blend'))
    return root

def make_rider():
    root=empty('RB_Rider');lod=empty('RB_Rider_LOD0',root)
    hip=empty('RB_Rider_L0_Hip',lod,(0,.94,0))
    pelvis=box('Pelvis',(0,.95,0),(.34,.25,.24),1,hip,.05)
    torso=empty('RB_Rider_L0_Torso',hip,(0,.17,0))
    # joint positions are local offsets; primitive helpers receive world coords.
    chest=box('Jacket',(0,1.23,0),(.47,.43,.27),0,torso,.065)
    back=box('JacketBackPanel',(0,1.23,-.145),(.30,.30,.026),1,torso,.015)
    stripe=box('JacketShoulderMark',(0,1.405,-.13),(.39,.042,.035),4,torso,.005)
    join_meshes([chest,back,stripe],'RB_Rider_L0_Torso_Mesh',torso)
    head=empty('RB_Rider_L0_Head',torso,(0,.42,0))
    helmet=ellipsoid('Helmet',(0,1.625,0),(.35,.38,.36),4,head,20,10)
    visor=ellipsoid('Visor',(0,1.64,.11),(.32,.145,.19),6,head,16,8)
    chin=box('ChinGuard',(0,1.515,.10),(.26,.085,.18),1,head,.03)
    join_meshes([helmet,visor,chin],'RB_Rider_L0_Head_Mesh',head)
    for side,label in [(-1,'L'),(1,'R')]:
        upper=empty('RB_Rider_L0_UpperArm_'+label,torso,(side*.26,.26,0))
        a=rod('JacketSleeve',(side*.26,1.37,0),(side*.33,1.08,0),.095,0,upper)
        pad=ellipsoid('ElbowPad',(side*.33,1.08,0),(.21,.19,.20),1,upper)
        join_meshes([a,pad],'RB_Rider_L0_UpperArm_'+label+'_Mesh',upper)
        fore=empty('RB_Rider_L0_Forearm_'+label,upper,(side*.07,-.29,0))
        arm=rod('Forearm',(side*.33,1.08,0),(side*.34,.82,.015),.075,1,fore)
        glove=box('Glove',(side*.34,.795,.02),(.15,.15,.16),5,fore,.04)
        join_meshes([arm,glove],'RB_Rider_L0_Forearm_'+label+'_Mesh',fore)
        thigh=empty('RB_Rider_L0_Thigh_'+label,hip,(side*.105,-.09,0))
        leg=rod('Trouser',(side*.105,.85,0),(side*.13,.49,.02),.105,1,thigh)
        knee=ellipsoid('KneePad',(side*.13,.47,.055),(.22,.20,.23),2,thigh)
        join_meshes([leg,knee],'RB_Rider_L0_Thigh_'+label+'_Mesh',thigh)
        shin=empty('RB_Rider_L0_Shin_'+label,thigh,(side*.025,-.38,.02))
        lower=rod('Shin',(side*.13,.47,.02),(side*.13,.14,0),.085,1,shin)
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
    width=1.82;length=4.4 if van else 4.15
    b('LowerBody',(0,.68,0),(width,.65,length),2 if van else 0,.10)
    b('Cabin',(0,1.2,-.26),(1.66,1.04 if van else .65,2.65 if van else 2.12),4 if van else 2,.12)
    b('Windshield',(0,1.36,.91 if van else .825),(1.43,.50 if van else .36,.035),6,.04)
    b('RearGlass',(0,1.37,-1.595 if van else -1.34),(1.38,.47 if van else .32,.035),6,.02)
    for side in [-1,1]:
        for z in [.42,-.56]:b('SideWindow',(side*.839,1.35,z),(.026,.43 if van else .33,.76),6,.012)
        b('DoorRail',(side*.919,.85,-.1),(.04,.038,2.6),3,.008)
        b('Mirror',(side*1.0,1.15,.68),(.15,.11,.17),1,.02)
        for z in [-1.30,1.30]:
            joint=wheel(name+'_L0_Wheel',(side*.83,.36,z),.36,.23,lod)
            pieces.extend([m for m in joint.children if m.type=='MESH'])
    b('FrontBumper',(0,.42,length/2+.015),(1.76,.13,.11),1,.025)
    b('RearBumper',(0,.42,-length/2-.015),(1.76,.13,.11),1,.025)
    for side in [-1,1]:
        b('Headlamp',(side*.60,.79,length/2+.01),(.42,.14,.045),4,.014)
        b('Taillamp',(side*.65,.77,-length/2-.015),(.29,.14,.045),0,.01)
    b('Grille',(0,.68,length/2+.015),(.65,.21,.06),1,.008)
    if van:
        b('CargoRoof',(0,1.82,-.43),(1.67,.12,2.69),4,.04)
        b('CargoStripe',(0,1.52,-1.622),(1.20,.12,.022),0,.004)
    else:b('HoodStripe',(0,1.014,1.48),(.25,.018,.87),4,.004)
    join_meshes(pieces,name+'_L0_Body',lod)
    for child in list(lod.children):
        if child.type=='EMPTY' and len(child.children)==0:bpy.data.objects.remove(child,do_unlink=True)
    lod_copy(lod,1,.5,name);lod_copy(lod,2,.20,name)
    assets.append((root,VEH,'ArtSource/Vehicles/'+name+'.blend'));return root

moto=make_motorcycle();rider=make_rider();coupe=make_car();van=make_car(True)
report={'authorship':'Original procedural hard-surface modeling, no game assets loaded',
        'blender_version':bpy.app.version_string,'coordinate_contract':'meters; exported Unity Y-up Z-forward',
        'palette_uv_policy':'Intentional repeated palette tile sampling between parts; uniquely packed islands within each primitive',
        'textures':{'base':256,'police_base':256,'normal':256,'metallic_smoothness':256,'roughness':256},'assets':[]}
for root,folder,source in assets:
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in descendants(root):o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=folder+root.name+'.fbx',use_selection=True,
        object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,
        bake_space_transform=True,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
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
