import bpy,json,array,math
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7R2/RB_Golden_Ash_V7R2.blend',load_ui=False,use_scripts=False)
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene;lods=[bpy.data.objects['AshV7_L'+str(i)+'_Skin'] for i in range(3)];regions=[]
for obj in lods:
    groups={}
    for vertex in obj.data.vertices:
        name=max((g.weight,obj.vertex_groups[g.group].name) for g in vertex.groups)[1].replace('RB_P06_Rider_L0_','')
        if name.startswith('Finger_'):name='Hand_'+name[-1]
        if name not in groups:groups[name]=[]
        groups[name].append(vertex.index)
    regions.append(groups)
rig.animation_data.action=bpy.data.actions['RB_Fall'];rows=[]
for step in range(145):
    frame=1+step/8.;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();lod_rows=[]
    for level,obj in enumerate(lods):
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
        try:
            assert len(mesh.vertices)==len(obj.data.vertices)
            values=array.array('f',[0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',values);axis=ev.matrix_world[2]
            heights=[axis[0]*values[i]+axis[1]*values[i+1]+axis[2]*values[i+2]+axis[3] for i in range(0,len(values),3)]
            assert all(math.isfinite(z) for z in heights)
            measurements={}
            for name,indices in regions[level].items():
                measurements[name]={'minimumWorldZ':min(heights[i] for i in indices),'verticesWithin10mm':sum(0<=heights[i]<=.01 for i in indices),'vertices':len(indices)}
            lod_rows.append({'lod':level,'minimumWorldZ':min(heights),'regions':measurements})
        finally:ev.to_mesh_clear()
    rows.append({'frame':frame,'lods':lod_rows})
print('V7R2_DENSE_REGIONS '+json.dumps({'source':bpy.data.filepath,'sourceSaved':False,'samples':rows,'scope':'Actual source evaluated skin vertices in flat world-Z floor space, grouped by dominant bone; contact proximity is not a force/physics proof.','visualAccepted':False,'nativePending':True}))
