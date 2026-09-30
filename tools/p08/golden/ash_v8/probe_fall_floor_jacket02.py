import bpy,json,array,math
EXPECTED='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_Jacket02.blend'
if bpy.data.filepath.replace('\\','/')!=EXPECTED:raise RuntimeError('Owned saved Jacket02 required')
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene
old_action=rig.animation_data.action;old_frame=scene.frame_current;old_subframe=scene.frame_subframe
lods=[bpy.data.objects['AshV7_L'+str(level)+'_Skin'] for level in range(3)]
rows=[]
try:
    rig.animation_data.action=bpy.data.actions['RB_Fall']
    for step in range(145):
        frame=1+step/8.;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();measurements=[]
        for level,obj in enumerate(lods):
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            try:
                if len(mesh.vertices)!=len(obj.data.vertices):raise RuntimeError('Unexpected evaluated vertex count')
                coords=array.array('f',[0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',coords);axis=evaluated.matrix_world[2]
                minimum=None;index_at_minimum=-1
                for index in range(0,len(coords),3):
                    value=axis[0]*coords[index]+axis[1]*coords[index+1]+axis[2]*coords[index+2]+axis[3]
                    if not math.isfinite(value):raise RuntimeError('Nonfinite evaluated vertex')
                    if minimum is None or value<minimum:minimum=value;index_at_minimum=index//3
                measurements.append(dict(lod=level,minimumWorldZ=minimum,vertex=index_at_minimum))
            finally:evaluated.to_mesh_clear()
        rows.append(dict(frame=frame,lods=measurements))
finally:
    rig.animation_data.action=old_action;scene.frame_set(old_frame,subframe=old_subframe);bpy.context.view_layer.update()
minimums=[min(row['lods'][level]['minimumWorldZ'] for row in rows) for level in range(3)]
print('ASH_V8_JACKET02_FLOOR '+json.dumps(dict(source=EXPECTED,samples=145,lodMinimums=minimums,nonpenetrationSamplesPassed=all(value>=0 for value in minimums),rows=rows,
    sourceSaved=False,actionAndFrameRestored=rig.animation_data.action==old_action and scene.frame_current==old_frame,
    scope='Actual evaluated source vertices over the existing Fall clip at1/8frame increments and rootzero. Flat-plane samples only, not slopes/forces/nativeUnity or all transitions.',visualAccepted=False)))
