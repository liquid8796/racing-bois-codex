"""Fix diagnostic profile framing; does not change the character mesh."""
import bpy
from mathutils import Vector
scene=bpy.context.scene
assert 'Ash/AnatomyV1/' in bpy.data.filepath.replace('\\','/')
scene.camera.data.ortho_scale=.52
scene.camera.location=(3,-.025,1.60)
scene.camera.rotation_euler=(Vector((0,-.025,1.60))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/recovery/ash-anatomy-profile.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('PROFILE_FRAMING_CORRECTED '+scene.render.filepath)
