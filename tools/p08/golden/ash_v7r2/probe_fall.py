import bpy,json,array,math
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend',load_ui=False,use_scripts=False)
rig=bpy.data.objects['RB_P06_Rider_Rig'];action=bpy.data.actions['RB_Fall'];scene=bpy.context.scene
old_action=rig.animation_data.action;old_frame=scene.frame_current;old_sub=scene.frame_subframe
curves=[]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                curves.append({'path':curve.data_path,'axis':curve.array_index,'keyframes':[[float(p.co.x),float(p.co.y),p.interpolation] for p in curve.keyframe_points]})
start,end=action.frame_range;rows=[]
try:
    rig.animation_data.action=action
    for sample in range(int(round((end-start)*4))+1):
        frame=start+sample*.25;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();lod_rows=[]
        for level in range(3):
            obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
            try:
                data=array.array('f',[0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',data)
                row=ev.matrix_world[2];heights=[row[0]*data[i]+row[1]*data[i+1]+row[2]*data[i+2]+row[3] for i in range(0,len(data),3)]
                vertex=heights.index(min(heights))
                v=mesh.vertices[vertex];weights=[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups]
                lod_rows.append({'lod':level,'minimumWorldZ':heights[vertex],'maximumWorldZ':max(heights),'lowestVertex':vertex,'lowestVertexWeights':weights})
            finally:ev.to_mesh_clear()
        hip=rig.pose.bones['RB_P06_Rider_L0_Hip'];rows.append({'frame':frame,'normalizedTime':(frame-start)/(end-start),'hipLocation':list(hip.location),'hipHead':list(hip.head),'lods':lod_rows})
finally:
    rig.animation_data.action=old_action;scene.frame_set(old_frame,subframe=old_sub);bpy.context.view_layer.update()
print('V7R2_FALL_DIAGNOSIS '+json.dumps({'source':bpy.data.filepath,'sourceSaved':False,'clip':action.name,'range':[start,end],'fps':scene.render.fps/scene.render.fps_base,'curves':curves,'samples':rows,'geometryAnimationEdited':False,'visualAccepted':False}))
