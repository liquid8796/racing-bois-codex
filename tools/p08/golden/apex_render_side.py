"""Run a saved candidate view through real Blender MCP; never edits meshes."""
import bpy, math, json
from mathutils import Vector
scene=bpy.context.scene
camera=scene.camera
camera.data.type='ORTHO';camera.data.ortho_scale=2.65
camera.data.lens=64
camera.location=(4,0,.7)
camera.rotation_euler=(Vector((0,0,.62))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.cycles.samples=16
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/iteration-01-side.png'
bpy.ops.render.render(write_still=True)
print('APEX_REVIEW_RENDER_SAVED '+scene.render.filepath)

