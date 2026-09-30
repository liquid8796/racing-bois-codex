import bpy,json,math
from array import array
ROOT='D:/Project/Unity/racing-bois/'
BASE=ROOT+'ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_PreEdit.blend'
CANDIDATE=ROOT+'ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_Jacket02.blend'
RENDERED=ROOT+'ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_Jacket02_Rendered.blend'
if bpy.data.filepath.replace('\\','/')!=CANDIDATE:raise RuntimeError('Owned Jacket02 scene required')
if bpy.context.preferences.filepaths.use_scripts_auto_execute:raise RuntimeError('Autoexecute must remain off')
# Preserve all current owned render-state changes before switching a scene.
bpy.ops.wm.save_as_mainfile(filepath=RENDERED,compress=True)
def values(collection,property_name,count,kind='f'):
    result=array(kind,[0])*count;collection.foreach_get(property_name,result);return result
def action_values(action):
    curves=[]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    curves.append((curve.data_path,curve.array_index,curve.extrapolation,[(tuple(p.co),tuple(p.handle_left),tuple(p.handle_right),p.interpolation,p.handle_left_type,p.handle_right_type) for p in curve.keyframe_points]))
    return curves
def capture(path):
    bpy.ops.wm.open_mainfile(filepath=path,load_ui=False,use_scripts=False)
    if bpy.data.filepath.replace('\\','/')!=path or bpy.context.preferences.filepaths.use_scripts_auto_execute:raise RuntimeError('Owned input/autoexec changed')
    rig=bpy.data.objects['RB_P06_Rider_Rig'];lods=[]
    for level in range(3):
        obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];mesh=obj.data
        positions=values(mesh.vertices,'co',len(mesh.vertices)*3)
        keys=[]
        if mesh.shape_keys:
            basis=values(mesh.shape_keys.key_blocks[0].data,'co',len(mesh.vertices)*3)
            for key in mesh.shape_keys.key_blocks[1:]:
                coords=values(key.data,'co',len(mesh.vertices)*3)
                keys.append((key.name,array('f',(value-base for value,base in zip(coords,basis)))))
        roles=[set() for vertex in mesh.vertices]
        for polygon in mesh.polygons:
            for index in polygon.vertices:roles[index].add(polygon.material_index)
        weights=[tuple((obj.vertex_groups[group.group].name,group.weight) for group in vertex.groups) for vertex in mesh.vertices]
        protected=set()
        for vertex in mesh.vertices:
            body=roles[vertex.index]
            glove=any(('Finger_' in name or 'Hand_' in name) and weight>.2 for name,weight in weights[vertex.index]) and 1 in body
            if 0 in body or 3 in body or 5 in body or glove:protected.add(vertex.index)
        lods.append(dict(positions=positions,loops=values(mesh.loops,'vertex_index',len(mesh.loops),'i'),
            polygonStarts=values(mesh.polygons,'loop_start',len(mesh.polygons),'i'),polygonCounts=values(mesh.polygons,'loop_total',len(mesh.polygons),'i'),
            polygonMaterials=values(mesh.polygons,'material_index',len(mesh.polygons),'i'),
            uv=[values(layer.data,'uv',len(mesh.loops)*2) for layer in mesh.uv_layers],weights=weights,morphs=keys,roles=roles,protected=protected,
            materials=[material.name for material in mesh.materials]))
    return dict(lods=lods,actions={action.name:action_values(action) for action in bpy.data.actions},
        bones=[(bone.name,bone.parent.name if bone.parent else '',tuple(tuple(row) for row in bone.matrix_local)) for bone in rig.data.bones])
before=capture(BASE);after=capture(CANDIDATE)
if before['actions']!=after['actions'] or before['bones']!=after['bones']:raise RuntimeError('Saved action/rest rig changed')
rows=[]
for level,(old,new) in enumerate(zip(before['lods'],after['lods'])):
    for key in ['loops','polygonStarts','polygonCounts','polygonMaterials','uv','weights','morphs','roles','protected']:
        if old[key]!=new[key]:raise RuntimeError('Saved LOD'+str(level)+' changed '+key)
    changed=[];protected_changed=[];maximum=0
    for index in range(len(old['positions'])//3):
        a=old['positions'][index*3:index*3+3];b=new['positions'][index*3:index*3+3]
        if a==b:continue
        distance=math.sqrt(sum((x-y)**2 for x,y in zip(a,b)));maximum=max(maximum,distance);changed.append(index)
        if index in old['protected']:protected_changed.append(index)
        if not old['roles'][index].issubset({1,2,6,7}) or distance>.008001:raise RuntimeError('Saved garment scope/displacement invalid')
    expected=[('AshV8_'+name+'_WornLeather02') if name in {'AshV4_TailoredLeather_Baked','AshV4_LeatherDetails_Baked','AshV2_OchreThread_Baked'} else name for name in old['materials']]
    if new['materials']!=expected:raise RuntimeError('Unexpected saved material binding change')
    rows.append(dict(lod=level,changedVertices=len(changed),maximumDisplacementMetres=maximum,protectedVertexCount=len(old['protected']),
        changedProtectedVertices=protected_changed,uvTopologyWeightsMorphDeltasExact=True,materialChangesExactlyExpected=True))
if any(row['changedProtectedVertices'] for row in rows):raise RuntimeError('Protected skin/glove/boot/rubber coordinates changed: '+json.dumps(rows))
print('ASH_V8_SAVED_JACKET02 '+json.dumps(dict(passed=True,baseline=BASE,candidate=CANDIDATE,renderStatePreservedAs=RENDERED,
    lods=rows,actionsExact=len(before['actions']),restBonesExact=len(before['bones']),autoexecute=False,visualAccepted=False,poseContactAccepted=False)))
