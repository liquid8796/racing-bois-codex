import bpy,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend')
path=ROOT+'_local/p08-ash-v7r1-staging/RB_Golden_Ash_V7R1.fbx'
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];root=bpy.data.objects['RB_Golden_Ash_V7']
lods=[bpy.data.objects['AshV7_L'+str(i)+'_Skin'] for i in range(3)]
selection=[root,rig]+lods+[bpy.data.objects[n] for n in ['Forward','Ground_L','Ground_R']]
old_action=rig.animation_data.action;old_frame=scene.frame_current;old_sub=scene.frame_subframe
old_active=bpy.context.view_layer.objects.active;old_selected=list(bpy.context.selected_objects)
hidden=[(obj,obj.hide_get(),obj.hide_render) for obj in selection]
bone_matrices=[(bone,bone.matrix_basis.copy()) for bone in rig.pose.bones]
shape_values=[(key,key.value) for obj in lods for key in obj.data.shape_keys.key_blocks]
try:
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    for key,value in shape_values:key.value=0
    bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
    for obj in selection:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.fbx(filepath=path,use_selection=True,object_types={'MESH','ARMATURE','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
        use_mesh_modifiers=False,use_triangles=False,add_leaf_bones=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,
        bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='STRIP')
finally:
    rig.animation_data.action=old_action
    for bone,matrix in bone_matrices:bone.matrix_basis=matrix
    for key,value in shape_values:key.value=value
    scene.frame_set(old_frame,subframe=old_sub)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in old_selected:obj.select_set(True)
    for obj,hide,render in hidden:obj.hide_set(hide);obj.hide_render=render
    bpy.context.view_layer.objects.active=old_active;bpy.context.view_layer.update()
print('V7R1_RADIUS_EXPORT '+json.dumps({'path':path,'use_triangles':False,'sourceSavedBySeparateUvOnlyRecipe':True,'nativePending':True,'visualAccepted':False}))
