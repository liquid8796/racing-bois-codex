"""Export an explicit standing default action; preserve the failed FBX variant."""
import bpy,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/'
rig=bpy.data.objects['RB_P06_Rider_Rig'];root=bpy.data.objects['RB_Golden_Ash_V2'];scene=bpy.context.scene
def bounds():
    depsgraph=bpy.context.evaluated_depsgraph_get();obj=bpy.data.objects['AshV2_L0_Skin'];mesh=obj.evaluated_get(depsgraph).to_mesh()
    low=[min(v.co[a] for v in mesh.vertices) for a in range(3)];high=[max(v.co[a] for v in mesh.vertices) for a in range(3)]
    obj.evaluated_get(depsgraph).to_mesh_clear();return {'min':low,'max':high,'size':[b-a for a,b in zip(low,high)]}
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();rest=bounds()
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update();idle=bounds()
bpy.ops.object.select_all(action='DESELECT')
selection=[root,rig]+[bpy.data.objects['AshV2_L'+str(level)+'_Skin'] for level in range(3)]+[bpy.data.objects[name] for name in ['Forward','Ground_L','Ground_R']]
for obj in selection:obj.select_set(True)
bpy.context.view_layer.objects.active=root
path=ROOT+'Assets/RacingBois/Art/P08/Golden/Ash/V2/RB_Golden_Ash_V2_DefaultIdle.fbx'
bpy.ops.export_scene.fbx(filepath=path,use_selection=True,object_types={'MESH','ARMATURE','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',use_mesh_modifiers=False,
                        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,bake_anim_force_startend_keying=True,
                        bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='AUTO')
bpy.context.view_layer.update()
print('ASH_DEFAULT_IDLE_EXPORT '+json.dumps({'variant':path,'standingRestBefore':rest,'standingIdleBefore':idle,'afterExport':bounds(),'activeActionAfter':rig.animation_data.action.name if rig.animation_data.action else None,'sourceNotSaved':True}))
