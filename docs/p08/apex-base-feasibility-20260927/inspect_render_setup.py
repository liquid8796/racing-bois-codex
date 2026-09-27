import bpy
import json
from mathutils import Vector

def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

clay = material('INSPECTION neutral gray clay', (.32, .32, .32), .46)
floor = material('INSPECTION neutral gray floor', (.16, .16, .16), .75)
for scene in bpy.data.scenes:
    if not scene.name.startswith('Inspection_'):
        continue
    bpy.context.window.scene = scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new(scene.name + '_World')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.5, .5, .5, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.008))
    bpy.context.object.name = 'INSPECTION Floor ' + scene.name
    bpy.context.object.data.materials.append(floor)
    for name, pos, power, size in [('Key', (3, -4, 5), 600, 4), ('Fill', (-3, -1, 3), 350, 3), ('Rim', (1, 3, 4), 500, 3)]:
        data = bpy.data.lights.new(scene.name + name, 'AREA')
        data.energy = power
        data.shape = 'DISK'
        data.size = size
        obj = bpy.data.objects.new(scene.name + name, data)
        scene.collection.objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (Vector((0, 0, .55)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data = bpy.data.cameras.new(scene.name + '_Camera')
    data.type = 'ORTHO'
    data.ortho_scale = 2.65
    camera = bpy.data.objects.new(scene.name + '_Camera', data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (3, -4, 1.7)
    camera.rotation_euler = (Vector((0, 0, .55)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/_local/p08-apex-base-inspection-20260927/licensed-base-inspection.blend')
print(json.dumps({'scenes': [s.name for s in bpy.data.scenes], 'engine': 'CYCLES', 'device': 'CPU', 'threads': 4, 'samples': 24}))
