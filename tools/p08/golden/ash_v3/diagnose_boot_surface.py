"""Isolate existing boot normal artifacts; restore materials after the render."""
import bpy
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera;restore=[]
for name in ['AshV2_BootLeather_Baked','AshV2_Rubber_Baked']:
    material=bpy.data.materials[name];node=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for link in list(node.inputs['Normal'].links):
        restore.append((material,link.from_socket,link.to_socket));material.node_tree.links.remove(link)
try:
    camera.location=(.68,-.37,.51);target=Vector((.286,-.071,.44));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.4
    scene.render.resolution_x=900;scene.render.resolution_y=900;scene.cycles.samples=24
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v3/private-boot-no-normal.png';bpy.ops.render.render(write_still=True)
finally:
    for material,source,target in restore:material.node_tree.links.new(source,target)
print('BOOT_NORMAL_DIAGNOSTIC_RESTORED_NO_SAVED_INPUT_CHANGES')
