"""Render actual V7 geometry in reference-facing views through direct MCP."""
import bpy,json
from mathutils import Vector

scene=bpy.context.scene
assert bpy.data.filepath.endswith('/V7/RB_Golden_Apex_v7.blend') or bpy.data.filepath.endswith('\\V7\\RB_Golden_Apex_v7.blend')
scene.render.resolution_x=1500
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.cycles.samples=24
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.24,.25,.26,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.55
ground=bpy.data.materials['Studio_Only_Ground'].node_tree.nodes['Principled BSDF']
ground.inputs['Base Color'].default_value=(.28,.29,.30,1)
scene.camera.data.lens=70
for name,position,target,kind in [
    ('beauty',(-3.20,-3.55,1.80),(0,0,.61),'PERSP'),
    ('side',(-4,0,.80),(0,0,.61),'ORTHO'),
    ('front',(0,-4,1.03),(0,-.15,.62),'ORTHO'),
]:
    scene.camera.location=position
    scene.camera.rotation_euler=(Vector(target)-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera.data.type=kind
    scene.camera.data.ortho_scale=2.55 if name!='front' else 1.60
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/v7/apex-'+name+'.png'
    bpy.ops.render.render(write_still=True)
    print('RENDERED_V7 '+scene.render.filepath)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(json.dumps({'status':'rendered-candidate-not-accepted','mesh_objects':sum(1 for o in scene.objects if o.type=='MESH')}))
