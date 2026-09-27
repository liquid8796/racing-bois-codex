"""New casual spectator, authored after inspecting pedestrian-concept-v1.png."""
import bpy
import bmesh
import math
import json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'Assets/RacingBois/Art/Characters/'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
colors=[(.79,.75,.61,1),(.28,.34,.26,1),(.035,.075,.13,1),(.46,.27,.085,1),(.60,.39,.25,1),(.045,.027,.014,1),(.055,.053,.044,1),(.13,.16,.10,1)]
def image(name,values,color=True):
    tex=bpy.data.images.new(name,128,128,alpha=True)
    if not color:tex.colorspace_settings.name='Non-Color'
    pixels=[]
    for y in range(128):
        for x in range(128):pixels.extend(values[(y//64)*4+x//32])
    tex.pixels=pixels;tex.filepath_raw=OUT+name+'.png';tex.file_format='PNG';tex.save();return tex
base=image('RB_Pedestrian_BaseColor',colors)
image('RB_Pedestrian_Normal',[(.5,.5,1,1)]*8,False)
image('RB_Pedestrian_MetallicSmoothness',[(0,1,0,.20)]*8,False)
image('RB_Pedestrian_Roughness',[(.8,.8,.8,1)]*8,False)
material=bpy.data.materials.new('RB_PedestrianPalette');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.8
tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=base
material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
def bv(v):return Vector((-v[0],-v[2],v[1]))
def empty(name,parent=None,position=(0,0,0)):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=parent;obj.location=bv(position);return obj
def clean(mesh):
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
def finish(obj,name,tile,parent,bevel=0):
    obj.name=name;bpy.context.view_layer.objects.active=obj;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if bevel:
        mod=obj.modifiers.new('Soft silhouette edges','BEVEL');mod.width=bevel;mod.segments=1;bpy.ops.object.modifier_apply(modifier=mod.name)
    clean(obj.data);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.03);bpy.ops.object.mode_set(mode='OBJECT')
    for entry in obj.data.uv_layers.active.data:
        entry.uv.x=(tile%4+.14+.72*entry.uv.x)/4;entry.uv.y=(tile//4+.10+.80*entry.uv.y)/2
    obj.data.materials.append(material);world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world;return obj
def box(name,position,size,tile,parent,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=bv(position));obj=bpy.context.object;obj.dimensions=(size[0],size[2],size[1]);return finish(obj,name,tile,parent,bevel)
def sphere(name,position,size,tile,parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=bv(position));obj=bpy.context.object;obj.scale=(size[0]/2,size[2]/2,size[1]/2);return finish(obj,name,tile,parent)
def rod(name,a,b,r,tile,parent):
    delta=bv(b)-bv(a);bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=r,depth=delta.length,location=(bv(a)+bv(b))/2)
    obj=bpy.context.object;obj.rotation_euler=delta.to_track_quat('Z','Y').to_euler();return finish(obj,name,tile,parent)
def join(parts,name,parent):
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts:part.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    obj.data.materials.clear();obj.data.materials.append(material)
    for polygon in obj.data.polygons:polygon.material_index=0
    return obj
def valid(mesh):
    bm=bmesh.new();bm.from_mesh(mesh);result=all(edge.is_manifold and edge.is_contiguous for edge in bm.edges) and all(face.calc_area()>1e-10 for face in bm.faces)
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
root=empty('RB_Pedestrian');lod=empty('RB_Ped_LOD0',root)
hip=empty('RB_Ped_L0_Hip',lod,(0,.92,0));box('RB_Ped_L0_Hip_Mesh',(0,.93,0),(.32,.23,.24),2,hip,.035)
torso=empty('RB_Ped_L0_Torso',hip,(0,.16,0))
parts=[box('SageShirt',(0,1.22,0),(.42,.43,.25),1,torso,.045),box('IvoryVestBack',(0,1.22,-.133),(.40,.43,.035),0,torso,.012)]
for side in [-1,1]:
    parts.append(box('VestFront',(side*.128,1.22,.132),(.165,.42,.033),0,torso,.008))
    for y in [1.12,1.29]:parts.append(box('VestPocket',(side*.129,y,.156),(.115,.085,.025),0,torso,.005))
join(parts,'RB_Ped_L0_Torso_Mesh',torso)
head=empty('RB_Ped_L0_Head',torso,(0,.40,0))
parts=[rod('Neck',(0,1.43,0),(0,1.53,0),.07,4,head),sphere('AdultFace',(0,1.62,.01),(.255,.29,.25),4,head),
       sphere('ShortDarkHair',(0,1.718,-.005),(.27,.12,.26),5,head),box('Nose',(0,1.62,.14),(.041,.048,.037),4,head,.009)]
for side in [-1,1]:
    parts.append(sphere('Ear',(side*.125,1.625,0),(.042,.073,.043),4,head))
    parts.append(box('Eye',(side*.047,1.666,.123),(.028,.014,.012),5,head,.003))
parts.append(box('Mouth',(0,1.571,.127),(.049,.012,.009),5,head,.002))
join(parts,'RB_Ped_L0_Head_Mesh',head)
for side,label in [(-1,'L'),(1,'R')]:
    upper=empty('RB_Ped_L0_UpperArm_'+label,torso,(side*.24,.26,0))
    a=rod('SageSleeve',(side*.24,1.34,0),(side*.295,1.16,0),.085,1,upper)
    b=rod('UpperArmSkin',(side*.295,1.16,0),(side*.31,1.07,0),.065,4,upper)
    join([a,b],'RB_Ped_L0_UpperArm_'+label+'_Mesh',upper)
    fore=empty('RB_Ped_L0_Forearm_'+label,upper,(side*.07,-.27,0))
    a=rod('ForearmSkin',(side*.31,1.07,0),(side*.33,.81,.015),.06,4,fore)
    b=box('Hand',(side*.33,.775,.025),(.105,.13,.11),4,fore,.025)
    join([a,b],'RB_Ped_L0_Forearm_'+label+'_Mesh',fore)
    thigh=empty('RB_Ped_L0_Thigh_'+label,hip,(side*.10,-.09,0))
    rod('RB_Ped_L0_Thigh_'+label+'_Mesh',(side*.10,.83,0),(side*.12,.46,.01),.092,2,thigh)
    shin=empty('RB_Ped_L0_Shin_'+label,thigh,(side*.02,-.37,.01))
    a=rod('DenimShin',(side*.12,.46,.01),(side*.12,.12,0),.074,2,shin)
    b=box('OchreSneaker',(side*.12,.07,.069),(.165,.12,.30),3,shin,.023)
    c=box('IvorySole',(side*.12,.025,.069),(.17,.035,.305),0,shin,.012)
    join([a,b,c],'RB_Ped_L0_Shin_'+label+'_Mesh',shin)
for level,ratio in [(1,.52),(2,.25)]:
    copied={}
    for original in [lod]+list(lod.children_recursive):
        obj=original.copy();scene.collection.objects.link(obj);obj.name=original.name.replace('_L0_','_L'+str(level)+'_').replace('_LOD0','_LOD'+str(level));copied[original]=obj
        if original.type=='MESH':
            for retained in [ratio,.35,.52,.68,.82,1]:
                if retained<ratio:continue
                obj.data=original.data.copy();bpy.context.view_layer.objects.active=obj
                mod=obj.modifiers.new('LOD detail reduction','DECIMATE');mod.ratio=retained;bpy.ops.object.modifier_apply(modifier=mod.name)
                if valid(obj.data):break
        obj.hide_render=True
    for original,obj in copied.items():obj.parent=copied[original.parent] if original.parent in copied else original.parent
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for obj in root.children_recursive:obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=OUT+'RB_Pedestrian.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/Characters/RB_Pedestrian.blend')
lods=[]
for group in root.children:
    triangles=0;checks=[]
    for obj in group.children_recursive:
        if obj.type=='MESH':obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles);checks.append(valid(obj.data))
    lods.append({'name':group.name,'triangles':triangles,'passed':all(checks)})
world=bpy.data.worlds.new('PedReview');scene.world=world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[1].default_value=.7
scene.render.engine='CYCLES';scene.cycles.samples=16
data=bpy.data.lights.new('Key','AREA');light=bpy.data.objects.new('Key',data);scene.collection.objects.link(light);light.location=(3,-4,5);data.energy=600;data.size=4;light.rotation_euler=(Vector((0,0,.9))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('PedCamera');camera=bpy.data.objects.new('PedCamera',data);scene.collection.objects.link(camera);camera.location=(2.3,-4.4,2.1);camera.rotation_euler=(Vector((0,0,.92))-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=60;scene.camera=camera
scene.render.resolution_x=720;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.filepath=ROOT+'docs/p03/assets/pedestrian.png';bpy.ops.render.render(write_still=True)
print(json.dumps({'asset':'RB_Pedestrian','concept':'ArtSource/Concepts/P03P04/pedestrian-concept-v1.png','authorship':'New mesh primitives based on own articulated rig proportions; no legacy content','lods':lods}))
