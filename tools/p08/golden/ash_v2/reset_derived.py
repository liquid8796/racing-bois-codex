"""Discard only rebuildable Ash runtime copies, keeping authored source/actions."""
import bpy
from mathutils import Matrix
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for name in ['AshV2_L0_Skin','AshV2_L1_Skin','AshV2_L2_Skin','AshV2_HighResSource','Forward','Ground_L','Ground_R']:
    obj=bpy.data.objects.get(name)
    if obj:bpy.data.objects.remove(obj,do_unlink=True)
for material in list(bpy.data.materials):
    if material.name.startswith('RB_Bake_') and material.users==0:bpy.data.materials.remove(material)
bpy.data.collections['AshV2_Editable_Source'].hide_viewport=False
bpy.context.view_layer.update()
print('ASH_AUTHORED_SOURCE_RETAINED_DERIVED_COPIES_RESET')
