"""Review final source LOD0 and repaired LOD2 without saving camera changes."""
import bpy
import json
from mathutils import Vector
scene = bpy.context.scene
root = bpy.data.objects['RB_Golden_Spark_v1']
camera = scene.camera
camera.location = (3.6, 3.4, 1.62)
camera.data.type = 'PERSP'
camera.data.lens = 81
camera.rotation_euler = (Vector((0, 0, .61)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.resolution_x = 1536
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
for level in (0, 2):
    for obj in root.children_recursive:
        if obj.type == 'MESH':
            obj.hide_render = '_L%d_' % level not in obj.name
    scene.render.filepath = 'D:/Project/Unity/racing-bois/docs/p08/golden/spark/v1/05-export-lod%d-quarter.png' % level
    bpy.ops.render.render(write_still=True)
for obj in root.children_recursive:
    if obj.type == 'MESH':
        obj.hide_render = '_L0_' not in obj.name
print('SPARK_EXPORT_RENDER=' + json.dumps({'lodsRendered': [0, 2], 'sourceSaved': False, 'visualAccepted': False}))
