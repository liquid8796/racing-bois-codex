import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',load_ui=False,use_scripts=False)
lods=[bpy.data.objects['AshV7_L'+str(i)+'_Skin'] for i in range(3)]
rig=bpy.data.objects['RB_P06_Rider_Rig']
def action_values(action):
    values=[]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    values.append((curve.data_path,curve.array_index,curve.extrapolation,[(tuple(p.co),tuple(p.handle_left),tuple(p.handle_right),p.interpolation,p.handle_left_type,p.handle_right_type) for p in curve.keyframe_points]))
    return values
def protected_state():
    meshes=[]
    for obj in lods:
        m=obj.data
        meshes.append((tuple(tuple(v.co) for v in m.vertices),tuple((tuple(p.vertices),p.material_index,p.use_smooth) for p in m.polygons),
            tuple(tuple((g.group,g.weight) for g in v.groups) for v in m.vertices),
            tuple((key.name,tuple(tuple(v.co) for v in key.data)) for key in m.shape_keys.key_blocks),
            tuple(mat.name for mat in m.materials),tuple(tuple(row) for row in obj.matrix_world)))
    bones=tuple((b.name,b.parent.name if b.parent else '',tuple(tuple(row) for row in b.matrix_local),tuple(b.head_local),tuple(b.tail_local)) for b in rig.data.bones)
    actions={a.name:action_values(a) for a in bpy.data.actions if a.name.startswith('RB_')}
    return (meshes,bones,actions)
before=protected_state();rows=[]
for obj in lods:
    mesh=obj.data;ids=set(obj['v7_facing_vertices']);layer=mesh.uv_layers[0]
    faces=[p for p in mesh.polygons if all(v in ids for v in p.vertices)]
    assert len(ids)==72 and len(faces)==70,'Collar facing membership changed'
    assert all(mesh.materials[p.material_index].name=='AshV3_Rubber_Baked' for p in faces)
    loops=set(i for p in faces for i in p.loop_indices);old_uv=[(float(v.uv.x),float(v.uv.y)) for v in layer.data]
    centre=((min(old_uv[i][0] for i in loops)+max(old_uv[i][0] for i in loops))*.5,(min(old_uv[i][1] for i in loops)+max(old_uv[i][1] for i in loops))*.5)
    changes=[]
    for i in loops:
        old=old_uv[i];new=(centre[0]+5*(old[0]-centre[0]),centre[1]+5*(old[1]-centre[1]))
        assert 0<new[0]<1 and 0<new[1]<1
        layer.data[i].uv=new;changes.append({'loop':i,'before':old,'after':[float(layer.data[i].uv.x),float(layer.data[i].uv.y)]})
    assert all((float(v.uv.x),float(v.uv.y))==old_uv[i] for i,v in enumerate(layer.data) if i not in loops),'Unrelated UV changed'
    mesh.calc_loop_triangles();bad=[];minimum=1
    for tri in mesh.loop_triangles:
        a,b,c=[layer.data[i].uv for i in tri.loops]
        cross=(float(b.x)-float(a.x))*(float(c.y)-float(a.y))-(float(b.y)-float(a.y))*(float(c.x)-float(a.x));minimum=min(minimum,abs(cross))
        if abs(cross)<=1e-14:bad.append(tri.polygon_index)
    assert not bad,'Source primary UV gate failed'
    rows.append({'mesh':obj.name,'facingVertices':len(ids),'faces':len(faces),'changedLoops':len(changes),'centre':centre,'scale':5,'authoredRadiusBefore':.0004,'authoredRadiusAfter':.002,'minimumCross':minimum,'changes':changes})
assert before==protected_state(),'Geometry, shape, weight, material, rig or action changed'
source=ROOT+'ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend'
bpy.ops.wm.save_as_mainfile(filepath=source,compress=False)
print('V7R1_COLLAR_UV '+json.dumps({'source':source,'geometryShapesWeightsMaterialsRigActionsExact':True,'allNonCollarUvExact':True,'textureFilesEdited':False,'lods':rows,'normalSamplingMayChange':True,'nativePending':True,'visualAccepted':False}))
