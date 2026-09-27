"""Read-only comparison with the current Unity geometry-area gate."""
import bpy,json
rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin'];obj.data.calc_loop_triangles();counts={};minimum=1
    for triangle in obj.data.loop_triangles:
        a,b,c=[obj.data.vertices[i].co for i in triangle.vertices]
        value=(b-a).cross(c-a).length_squared;minimum=min(minimum,value)
        if value<=1e-16:
            name=obj.data.materials[triangle.material_index].name;counts[name]=counts.get(name,0)+1
    rows.append({'level':level,'crossSquaredMinimum':minimum,'atOrBelowUnityThreshold':sum(counts.values()),'materials':counts})
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene;old_action=rig.animation_data.action;old_frame=scene.frame_current;finger=[]
for clip in ['RB_Idle','RB_Ride','RB_AttackLeft']:
    rig.animation_data.action=bpy.data.actions[clip];scene.frame_set(8);bpy.context.view_layer.update()
    finger.append({'clip':clip,'indexLAngles':[rig.pose.bones['RB_P06_Rider_L0_Finger_Index_'+str(i)+'_L'].rotation_quaternion.angle for i in [1,2,3]]})
rig.animation_data.action=old_action;scene.frame_set(old_frame);bpy.context.view_layer.update()
print('ASH_UNITY_THRESHOLD_PROBE '+json.dumps({'threshold':1e-16,'meshes':rows,'fingerCurveProbe':finger,'sourceFileUnchanged':True}))
