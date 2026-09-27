"""Original canyon prop meshes, following inspected canyon-concept-v1.png."""
import bpy
import bmesh
import math
import json
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'Assets/RacingBois/Art/Props/Canyon/'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
palette=[(.64,.36,.17,1),(.42,.22,.11,1),(.24,.28,.15,1),(.40,.43,.26,1)]
def texture(name,colors,size):
    im=bpy.data.images.new(name,size,size,alpha=True);pixels=[]
    if 'BaseColor' not in name:im.colorspace_settings.name='Non-Color'
    for y in range(size):
        for x in range(size):pixels.extend(colors[(y//(size//2))*2+x//(size//2)])
    im.pixels=pixels;im.filepath_raw=OUT+name+'.png';im.file_format='PNG';im.save();return im
base=texture('RB_Canyon_BaseColor',palette,128)
texture('RB_Canyon_Normal',[(.5,.5,1,1)]*4,32)
texture('RB_Canyon_MetallicSmoothness',[(0,1,0,.12)]*4,32)
texture('RB_Canyon_Roughness',[(.88,.88,.88,1)]*4,32)
material=bpy.data.materials.new('RB_CanyonPalette');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.88
node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=base
material.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
def bv(p):return(-p[0],-p[2],p[1])
def empty(name,parent=None):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=parent;return obj
def make_mesh(name,vertices,faces,tiles,parent):
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata([bv(p) for p in vertices],[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.parent=parent
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.03);bpy.ops.object.mode_set(mode='OBJECT')
    for face in mesh.polygons:
        tile=tiles[face.index]
        for index in face.loop_indices:
            uv=mesh.uv_layers.active.data[index].uv
            uv.x=(tile%2+.12+uv.x*.76)/2;uv.y=(tile//2+.12+uv.y*.76)/2
    mesh.materials.append(material);obj['authored_from_scratch']=True
    obj['concept_reference']='ArtSource/Concepts/P03P04/canyon-concept-v1.png'
    return obj
def rock(root,level):
    vertices=[];faces=[];tiles=[]
    sides=[8,6,5][level];layers=[4,3,2][level]
    for layer in range(layers):
        bottom=layer*1.04/layers;top=(layer+1)*1.04/layers
        span=1-layer*.12;offset=layer*.055
        start=len(vertices)
        for height,radius in [(bottom,span),(top,span*.94)]:
            for corner in range(sides):
                a=2*math.pi*corner/sides;variation=1+.055*math.sin(corner*4.5+layer*2)
                vertices.append((offset+math.cos(a)*.82*radius*variation,height+.025*math.cos(a+layer),math.sin(a)*.62*radius*variation))
        faces.extend([tuple(start+i for i in reversed(range(sides))),tuple(start+sides+i for i in range(sides))]);tiles.extend([1,0])
        for i in range(sides):faces.append((start+i,start+(i+1)%sides,start+(i+1)%sides+sides,start+i+sides));tiles.append(layer%2)
    minimum=min(p[1] for p in vertices);vertices=[(p[0],p[1]-minimum,p[2]) for p in vertices]
    return make_mesh('RB_Sandstone_L'+str(level)+'_Body',vertices,faces,tiles,root)
def scrub(root,level):
    vertices=[];faces=[];tiles=[]
    count=[18,10,5][level]
    for i in range(count):
        angle=i*2.399963;radius=.12+.21*((i%5)/4);height=.38+.30*((i%4)/3)
        base=Vector((math.cos(angle)*radius*.3,.03,math.sin(angle)*radius*.3))
        tip=Vector((math.cos(angle)*radius,height,math.sin(angle)*radius))
        side=Vector((math.cos(angle+math.pi/2),0,math.sin(angle+math.pi/2)))*(.095 if level<2 else .16)
        bulge=base.lerp(tip,.60)
        start=len(vertices);vertices.extend([tuple(base),tuple(bulge+side),tuple(bulge-side+Vector((0,.015,.035))),tuple(tip)])
        faces.extend([(start,start+2,start+1),(start,start+1,start+3),(start+1,start+2,start+3),(start+2,start,start+3)])
        tiles.extend([2+(i%2)]*4)
    return make_mesh('RB_SageScrub_L'+str(level)+'_Body',vertices,faces,tiles,root)
roots=[];report=[]
for name in ['RB_Sandstone','RB_SageScrub']:
    root=empty(name);roots.append(root);items=[]
    for level in range(3):
        obj=rock(root,level) if name=='RB_Sandstone' else scrub(root,level)
        obj.hide_render=level!=0;obj.data.calc_loop_triangles()
        bm=bmesh.new();bm.from_mesh(obj.data)
        issues={'nonmanifold':sum(1 for e in bm.edges if not e.is_manifold),
                'bad_winding':sum(1 for e in bm.edges if e.is_manifold and not e.is_contiguous),
                'degenerate':sum(1 for face in bm.faces if face.calc_area()<1e-10),
                'loose':sum(1 for v in bm.verts if not v.link_faces),'positive_volume':bm.calc_volume(signed=True)>0}
        bm.free();items.append({'lod':level,'triangles':len(obj.data.loop_triangles),'checks':issues})
        if any(issues[key] for key in ['nonmanifold','bad_winding','degenerate','loose']) or not issues['positive_volume']:raise RuntimeError('Invalid mesh '+obj.name)
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for obj in root.children:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=OUT+name+'.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False)
    report.append({'asset':name,'lods':items})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/Props/Canyon/RB_CanyonPack.blend')
world=bpy.data.worlds.new('CanyonReview');scene.world=world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[1].default_value=.7
scene.render.engine='CYCLES';scene.cycles.samples=16
roots[0].location.x=-1;roots[1].location.x=1
for name,position,energy in [('Key',(3,-4,5),800),('Rim',(-3,2,3),500)]:
    data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=position;data.energy=energy;data.size=4
    obj.rotation_euler=(Vector((0,0,.4))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('CanyonCamera');camera=bpy.data.objects.new('CanyonCamera',data);scene.collection.objects.link(camera)
camera.location=(4,-7,3.3);camera.rotation_euler=(Vector((0,0,.4))-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=58;scene.camera=camera
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True;scene.render.filepath=ROOT+'docs/p03/assets/canyon-props.png'
bpy.ops.render.render(write_still=True)
print(json.dumps({'passed':True,'concept':'ArtSource/Concepts/P03P04/canyon-concept-v1.png','assets':report}))
