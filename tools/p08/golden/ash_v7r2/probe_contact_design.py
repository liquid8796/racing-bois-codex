import bpy,json
from mathutils import Vector
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene
old_action=rig.animation_data.action;old_frame=scene.frame_current;old_sub=scene.frame_subframe
rows=[]
try:
    rig.animation_data.action=bpy.data.actions['RB_Fall']
    for frame in [1,9.25,19]:
        scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();obj=bpy.data.objects['AshV7_L0_Skin'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
        try:
            minima={};positions={}
            for v in m.vertices:
                weights=[(g.weight,obj.vertex_groups[g.group].name) for g in v.groups]
                name=max(weights)[1]
                region=name.replace('RB_P06_Rider_L0_','')
                p=ev.matrix_world@v.co
                if region not in minima or p.z<minima[region]:minima[region]=p.z;positions[region]=list(p)
            rows.append({'frame':frame,'dominantBoneRegionMinimumWorldZ':minima,'minimumPositions':positions})
        finally:ev.to_mesh_clear()
    hip=rig.data.bones['RB_P06_Rider_L0_Hip'];local_up=hip.matrix_local.to_3x3().inverted()@(rig.matrix_world.to_3x3().inverted()@Vector((0,0,1)))
    basis={'parent':hip.parent.name if hip.parent else None,'worldUpInHipLocal':list(local_up),'hipRestHead':list(hip.head_local)}
finally:
    rig.animation_data.action=old_action;scene.frame_set(old_frame,subframe=old_sub);bpy.context.view_layer.update()
print('V7R2_CONTACT_DESIGN '+json.dumps({'sourceSaved':False,'hipBasis':basis,'samples':rows,'scope':'Source pose bounds by dominant bone, not physical contact forces or acceptance.'}))
