import bpy
import bmesh
import math
import json
from mathutils import Vector

# New original Racing Bois prop. No original-game geometry or texture is loaded.
ROOT = 'D:/Project/Unity/racing-bois'
EXPORT = ROOT + '/Assets/RacingBois/Art/Props/Barrier/'
SOURCE = ROOT + '/ArtSource/Props/RB_RoadBarrier.blend'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.render.engine = 'CYCLES'
scene.cycles.samples = 8

material = bpy.data.materials.new('RB_Barrier_PaintedConcrete')
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
shader.inputs['Roughness'].default_value = 0.62
shader.inputs['Metallic'].default_value = 0.0
texcoord = nodes.new('ShaderNodeTexCoord')
separate = nodes.new('ShaderNodeSeparateXYZ')
links.new(texcoord.outputs['Generated'], separate.inputs[0])
xmul = nodes.new('ShaderNodeMath'); xmul.operation = 'MULTIPLY'; xmul.inputs[1].default_value = 6.0
zmul = nodes.new('ShaderNodeMath'); zmul.operation = 'MULTIPLY'; zmul.inputs[1].default_value = -1.2
links.new(separate.outputs['X'], xmul.inputs[0]); links.new(separate.outputs['Z'], zmul.inputs[0])
add = nodes.new('ShaderNodeMath'); add.operation = 'ADD'
links.new(xmul.outputs[0], add.inputs[0]); links.new(zmul.outputs[0], add.inputs[1])
fract = nodes.new('ShaderNodeMath'); fract.operation = 'FRACT'; links.new(add.outputs[0], fract.inputs[0])
step = nodes.new('ShaderNodeMath'); step.operation = 'GREATER_THAN'; step.inputs[1].default_value = 0.5
links.new(fract.outputs[0], step.inputs[0])
mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MIX'
mix.inputs[1].default_value = (0.8, 0.105, 0.02, 1)
mix.inputs[2].default_value = (0.83, 0.82, 0.72, 1)
links.new(step.outputs[0], mix.inputs[0]); links.new(mix.outputs[0], shader.inputs['Base Color'])

profile = [(-.32,0),(.32,0),(.32,.18),(.14,.52),(.10,.9),(-.10,.9),(-.14,.52),(-.32,.18)]
verts = [(x,y,z) for x in [-1.0,1.0] for y,z in profile]
faces = [tuple(reversed(range(8))),tuple(range(8,16))]
faces += [(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
mesh = bpy.data.meshes.new('RB_Barrier_LOD0_Mesh')
mesh.from_pydata(verts,[],faces); mesh.update()
obj = bpy.data.objects.new('RB_Barrier_LOD0',mesh); scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj; obj.select_set(True)
bm = bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
obj.data.materials.append(material)
bevel = obj.modifiers.new('Edge bevel','BEVEL'); bevel.width=.025; bevel.segments=3
bpy.ops.object.modifier_apply(modifier=bevel.name)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025)
bpy.ops.object.mode_set(mode='OBJECT')
obj.data.uv_layers.active.name = 'UV0'

base = bpy.data.images.new('RB_Barrier_BaseColor',512,512,alpha=False)
texture = nodes.new('ShaderNodeTexImage'); texture.image=base; nodes.active=texture
scene.render.bake.use_pass_direct=False; scene.render.bake.use_pass_indirect=False; scene.render.bake.use_pass_color=True
scene.render.bake.margin=8
bpy.ops.object.bake(type='DIFFUSE')
base.filepath_raw=EXPORT+'RB_Barrier_BaseColor.png'; base.file_format='PNG'; base.save()
links.new(texture.outputs['Color'],shader.inputs['Base Color'])

normal = bpy.data.images.new('RB_Barrier_Normal',128,128,alpha=False)
normal.colorspace_settings.name='Non-Color'
normal.pixels=[v for i in range(128*128) for v in (.5,.5,1,1)]
normal.filepath_raw=EXPORT+'RB_Barrier_Normal.png'; normal.file_format='PNG'; normal.save()
mask = bpy.data.images.new('RB_Barrier_MetallicSmoothness',128,128,alpha=True)
mask.colorspace_settings.name='Non-Color'
mask.pixels=[v for i in range(128*128) for v in (0,1,0,.38)]
mask.filepath_raw=EXPORT+'RB_Barrier_MetallicSmoothness.png'; mask.file_format='PNG'; mask.save()
rough = bpy.data.images.new('RB_Barrier_Roughness',128,128,alpha=False)
rough.colorspace_settings.name='Non-Color'; rough.pixels=[v for i in range(128*128) for v in (.62,.62,.62,1)]
rough.filepath_raw=ROOT+'/ArtSource/Props/RB_Barrier_Roughness.png'; rough.file_format='PNG'; rough.save()

root=bpy.data.objects.new('RB_RoadBarrier',None); scene.collection.objects.link(root); obj.parent=root
lods=[obj]
for index,ratio in [(1,.5),(2,.2)]:
    duplicate=obj.copy(); duplicate.data=obj.data.copy(); duplicate.name='RB_Barrier_LOD'+str(index)
    scene.collection.objects.link(duplicate); duplicate.parent=root
    bpy.context.view_layer.objects.active=duplicate
    decimate=duplicate.modifiers.new('LOD simplification','DECIMATE'); decimate.ratio=ratio
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    duplicate.hide_render=True; lods.append(duplicate)
for lod in lods:
    lod.data.calc_loop_triangles()
    lod['authored_from_scratch']=True
    lod['source_recipe']='tools/blender/create_barrier.py'

bpy.ops.object.select_all(action='DESELECT')
root.select_set(True)
for lod in lods: lod.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=EXPORT+'RB_RoadBarrier.fbx',use_selection=True,
    object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,
    bake_space_transform=True,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')

world=bpy.data.worlds.new('RB_StudioWorld'); scene.world=world; world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.11,.14,.18,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.5
for name,location,energy,size in [('Key',(1,-3,4),650,4),('Rim',(-2,2,3),800,3)]:
    data=bpy.data.lights.new(name,'AREA'); light=bpy.data.objects.new(name,data)
    scene.collection.objects.link(light); light.location=location; data.energy=energy; data.shape='DISK'; data.size=size
    light.rotation_euler=(Vector((0,0,.4))-light.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('ReviewCamera'); camera=bpy.data.objects.new('ReviewCamera',camera_data)
scene.collection.objects.link(camera); camera.location=(3,-4,2.3)
camera.rotation_euler=(Vector((0,0,.4))-camera.location).to_track_quat('-Z','Y').to_euler(); camera_data.lens=50
scene.camera=camera; scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=ROOT+'/docs/p02/blender/barrier-render.png'
scene.render.film_transparent=True
bpy.ops.wm.save_as_mainfile(filepath=SOURCE)
bpy.ops.render.render(write_still=True)
print(json.dumps({'asset':'RB_RoadBarrier','source':SOURCE,'export':EXPORT+'RB_RoadBarrier.fbx',
    'dimensions_m':list(obj.dimensions),'root_location':list(root.location),'root_scale':list(root.scale),
    'lod_triangles':[len(l.data.loop_triangles) for l in lods],
    'uv_policy':'Smart packed unique surface islands; LOD copies intentionally share same atlas',
    'materials':1,'texture_sizes':{'base_color':512,'normal':128,'metallic_smoothness':128},
    'source_assets_loaded':0,'blender_version':bpy.app.version_string}))
